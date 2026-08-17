"""/v1/files endpoints — file import + task status.

This iteration implements the full import path: parse → chunk → embed → write
to the configured datasource.

Import is dispatched as a FastAPI ``BackgroundTask`` so the HTTP handler
returns immediately with a ``task_id`` and the renderer can poll
``GET /v1/files/tasks/{task_id}`` for progress. Without this split, the
POST blocks until Ollama bge-m3 finishes every chunk and the user sees a
frozen "uploading" indicator with no feedback. (Fix-KB-Upload-Progress.)

Stage observability: ``TaskStore`` keeps a ``stage`` column (latest
pipeline stage) plus a ``task_events`` ring buffer (most recent 32
transitions). The renderer uses both to show "what's happening" alongside
the progress bar. ``GET /v1/files/tasks/{task_id}/events?since_id=N``
exposes the ring buffer as a separate endpoint for future incremental
tailing consumers; the renderer currently consumes the events embedded
in the main ``TaskResponse`` payload to avoid an extra IPC hop.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.chunking import TextChunker, ChunkParams
from app.observability.logging import get_logger
from app.observability.models import TaskEvent, TaskStage, TaskStatus, new_id
from app.observability.task_store import TaskStore
from app.parsers import parse_excel, parse_markdown, parse_pdf, parse_word
from app.pipeline.indexing import IndexingPipeline, ProgressEvent

log = get_logger(__name__)

router = APIRouter(prefix="/v1/files", tags=["files"])


def detect_parser(suffix: str):
    s = suffix.lower()
    if s in {".xlsx", ".xls"}:
        return parse_excel
    if s in {".docx", ".doc"}:
        return parse_word
    if s == ".pdf":
        return parse_pdf
    if s in {".md", ".markdown"}:
        return parse_markdown
    return None


class ImportResponse(BaseModel):
    task_id: str
    document_id: str
    chunks: int
    parser: str | None
    mime: str | None
    size: int


class TaskResponse(BaseModel):
    task_id: str
    kind: str
    status: str
    progress: float
    stage: TaskStage = TaskStage.QUEUED
    events: list[TaskEvent] = []
    error: str | None = None
    result: dict | None = None


class TaskEventsResponse(BaseModel):
    events: list[TaskEvent]
    next_since_id: int


# Process-wide state, set by main.py.
_task_store: TaskStore | None = None
_pipeline: IndexingPipeline | None = None
_controller = None


def set_task_store(store: TaskStore) -> None:
    global _task_store
    _task_store = store


def set_pipeline(p: IndexingPipeline | None) -> None:
    global _pipeline
    _pipeline = p


def set_controller(controller) -> None:
    global _controller
    _controller = controller


def get_task_store() -> TaskStore:
    if _task_store is None:
        raise HTTPException(status_code=503, detail="task store not initialized")
    return _task_store


def get_pipeline() -> IndexingPipeline | None:
    return _pipeline


def get_controller():
    return _controller


def _parser_name_for_suffix(suffix: str) -> str | None:
    s = suffix.lower()
    if s in {".xlsx", ".xls"}:
        return "excel"
    if s in {".docx", ".doc"}:
        return "word"
    if s == ".pdf":
        return "pdf"
    if s in {".md", ".markdown"}:
        return "markdown"
    return None


def _record_blackboard_progress(
    store: TaskStore,
    task_id: str,
    change,
) -> None:
    """Map blackboard changes to the existing TaskStage/progress contract."""
    kind = change.kind
    status = change.status
    if kind == "import_job" and status == "ready":
        store.add_event(task_id, TaskStage.QUEUED.value, 0.05, "queued blackboard import")
        store.update(task_id, stage=TaskStage.QUEUED.value, progress=0.05)
        return
    if kind == "parsed_document" and status == "ready":
        message = f"parsed {change.entry.payload.get('source_path', 'document')}"
        store.add_event(task_id, TaskStage.PARSING.value, 0.15, message)
        store.update(task_id, stage=TaskStage.PARSING.value, progress=0.15)
        return
    if kind == "chunk_set" and status == "ready":
        count = change.entry.payload.get("count", 0)
        store.add_event(task_id, TaskStage.CHUNKING.value, 0.30, f"{count} chunks")
        store.update(task_id, stage=TaskStage.CHUNKING.value, progress=0.30)
        return
    if kind == "embedded_chunk_set" and status == "ready":
        count = change.entry.payload.get("count", 0)
        store.add_event(task_id, TaskStage.EMBEDDING.value, 0.80, f"embedded {count} chunks")
        store.update(task_id, stage=TaskStage.EMBEDDING.value, progress=0.80)
        return
    if kind == "index_result" and status == "done":
        written = change.entry.payload.get("written", 0)
        store.add_event(task_id, TaskStage.WRITING.value, 1.0, f"wrote {written} chunks")
        store.update(task_id, stage=TaskStage.WRITING.value, progress=1.0)
        return
    if status == "failed":
        message = change.entry.error or change.summary
        store.add_event(task_id, TaskStage.FAILED.value, 0.0, message)
        store.update(task_id, status="failed", stage=TaskStage.FAILED.value, error=message)


async def _run_import_via_blackboard(
    task_id: str,
    tmp_path: Path,
    parser_name: str,
    mime: str | None,
    size: int,
) -> None:
    controller = get_controller()
    store = get_task_store()

    async def on_change(change) -> None:
        _record_blackboard_progress(store, task_id, change)

    unsubscribe = controller.subscribe(on_change)
    try:
        snapshot = await controller.submit_import(
            task_id,
            file_path=str(tmp_path),
            parser=parser_name,
            mime=mime,
            size=size,
        )
    except Exception as e:  # noqa: BLE001
        store.add_event(task_id, TaskStage.FAILED.value, 0.0, f"blackboard error: {e}")
        store.update(task_id, status="failed", stage=TaskStage.FAILED.value, error=str(e))
        return
    finally:
        unsubscribe()

    index_result = next(
        (entry for entry in snapshot if entry.kind == "index_result"),
        None,
    )
    if index_result is not None:
        result = dict(index_result.payload)
        parsed = next(
            (entry for entry in snapshot if entry.kind == "parsed_document"),
            None,
        )
        if parsed is not None:
            result["parser"] = parsed.payload.get("metadata", {}).get("parser")
        store.add_event(
            task_id,
            TaskStage.DONE.value,
            1.0,
            f"indexed {index_result.payload['written']} chunks for {index_result.payload['document_id']}",
        )
        store.update(
            task_id,
            status="done",
            stage=TaskStage.DONE.value,
            progress=1.0,
            result=result,
        )
        return

    chunk_set = next(
        (entry for entry in snapshot if entry.kind == "chunk_set"),
        None,
    )
    chunks = chunk_set.payload.get("count", 0) if chunk_set else 0
    parsed = next(
        (entry for entry in snapshot if entry.kind == "parsed_document"),
        None,
    )
    store.add_event(task_id, TaskStage.DONE.value, 1.0, "empty document; nothing indexed")
    store.update(
        task_id,
        status="done",
        stage=TaskStage.DONE.value,
        progress=1.0,
        result={
            "document_id": parsed.payload.get("document_id") if parsed else "",
            "chunks": chunks,
            "embedded": 0,
            "written": 0,
            "parser": parsed.payload.get("metadata", {}).get("parser") if parsed else None,
            "note": "no chunks to index",
        },
    )


async def _run_import(
    task_id: str,
    tmp_path: Path,
    parser,
    parser_name: str | None,
    mime: str | None,
    size: int,
) -> None:
    """Background-task body: parse → chunk → embed → write.

    Updates ``task_store`` along the way so the renderer poll loop sees real
    progress plus a stage label and an event-log entry. Without the stage
    info the UI is stuck at "uploading" until the pipeline emits 1.0.
    """
    store = get_task_store()
    store.update(
        task_id,
        status="running",
        stage=TaskStage.PARSING.value,
        progress=0.10,
    )
    store.add_event(task_id, TaskStage.PARSING.value, 0.10, f"queued by {_run_import.__name__}")
    if get_controller() is not None and get_pipeline() is None and parser_name is not None:
        await _run_import_via_blackboard(task_id, tmp_path, parser_name, mime, size)
        return
    try:
        doc = parser(tmp_path)
    except Exception as e:  # noqa: BLE001
        store.add_event(task_id, TaskStage.FAILED.value, 0.10, f"parse error: {e}")
        store.update(task_id, status="failed", stage=TaskStage.FAILED.value,
                     error=f"parse error: {e}")
        return

    pipeline = get_pipeline()
    if pipeline is None:
        # No embedder/datasource wired (rare). Record chunk count but mark done.
        try:
            chunks = TextChunker(ChunkParams()).split(doc)
        except Exception as e:  # noqa: BLE001
            store.update(task_id, status="failed", stage=TaskStage.FAILED.value,
                         error=f"chunker error: {e}")
            return
        store.update(
            task_id,
            status="done",
            stage=TaskStage.DONE.value,
            progress=1.0,
            result={
                "document_id": doc.id,
                "chunks": len(chunks),
                "parser": doc.metadata.get("parser"),
                "size": size,
                "note": "no pipeline configured; chunks not indexed",
            },
        )
        return

    def _progress(ev: ProgressEvent | float) -> None:
        # Pipeline emits ProgressEvent; be tolerant of legacy float-only
        # callbacks (e.g. older tests).
        if isinstance(ev, ProgressEvent):
            stage = ev.stage
            progress = ev.progress
            message = ev.message
        else:
            stage = TaskStage.EMBEDDING.value
            progress = float(ev)
            message = ""
        store.add_event(task_id, stage, progress, message)
        store.update(task_id, stage=stage, progress=progress)
        log.info("pipeline.stage", task_id=task_id, stage=stage,
                 progress=round(progress, 3), message=message)

    previous = pipeline.on_progress
    pipeline.on_progress = _progress
    try:
        result = await pipeline.run(doc)
    except Exception as e:  # noqa: BLE001
        store.add_event(task_id, TaskStage.FAILED.value, 0.0, f"pipeline error: {e}")
        store.update(task_id, status="failed", stage=TaskStage.FAILED.value,
                     error=f"pipeline error: {e}")
        return
    finally:
        pipeline.on_progress = previous  # type: ignore[assignment]

    store.add_event(task_id, TaskStage.DONE.value, 1.0,
                    f"indexed {result.written} chunks for {result.document_id}")
    store.update(
        task_id,
        status="done",
        stage=TaskStage.DONE.value,
        progress=1.0,
        result={
            "document_id": result.document_id,
            "chunks": result.chunks,
            "embedded": result.embedded,
            "written": result.written,
            "parser": doc.metadata.get("parser"),
        },
    )


@router.post("/import", response_model=ImportResponse)
async def import_file(
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> ImportResponse:
    """Save the upload, kick off parsing + indexing in the background, return
    the ``task_id`` immediately so the renderer can poll for progress."""
    suffix = Path(file.filename or "").suffix
    parser = detect_parser(suffix)
    if parser is None:
        raise HTTPException(status_code=415, detail=f"unsupported file type: {suffix}")

    store = get_task_store()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    task_id = new_id()
    store.create(task_id, "import")

    tmp_dir = Path(store.path).parent / "imports"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{task_id}{suffix}"
    tmp_path.write_bytes(data)

    # Stub values: real chunks/embedded/written come from the background task.
    # We reserve 0 so the renderer knows the task is queued, not yet processed.
    store.update(
        task_id,
        status="queued",
        stage=TaskStage.QUEUED.value,
        progress=0.0,
        result={"document_id": "", "chunks": 0, "parser": None, "size": len(data)},
    )

    background.add_task(
        _run_import,
        task_id,
        tmp_path,
        parser,
        _parser_name_for_suffix(suffix),
        file.content_type,
        len(data),
    )

    return ImportResponse(
        task_id=task_id,
        document_id="",  # filled in by background task
        chunks=0,
        parser=None,
        mime=file.content_type,
        size=len(data),
    )


def _task_to_response(t: TaskStatus) -> TaskResponse:
    return TaskResponse(
        task_id=t.task_id,
        kind=t.kind,
        status=t.status,
        progress=t.progress,
        stage=t.stage,
        events=t.events,
        error=t.error,
        result=t.result,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    store = get_task_store()
    t = store.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _task_to_response(t)


@router.get("/tasks/{task_id}/events", response_model=TaskEventsResponse)
async def get_task_events(
    task_id: str,
    since_id: int = Query(0, ge=0, description="Return events with row id > since_id"),
) -> TaskEventsResponse:
    """Return the retained event log for a task, optionally only events
    emitted after ``since_id``. Used by future live-tail consumers; the
    current renderer pulls events embedded in the main ``TaskResponse``."""
    store = get_task_store()
    t = store.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="task not found")
    if since_id == 0:
        events = t.events
    else:
        events = store.list_events_since(task_id, since_id)
    return TaskEventsResponse(events=events, next_since_id=store.last_event_id(task_id))
