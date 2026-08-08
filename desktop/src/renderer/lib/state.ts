/**
 * Tiny global state machine for the renderer.
 *
 * State enum: idle | uploading | indexing | searching | error
 *
 * Callbacks returned from the hook are wrapped in ``useCallback`` so their
 * identity is stable across renders; otherwise consumers like ``App`` whose
 * ``useEffect`` depends on ``checkHealth`` would re-run on every render and
 * spam IPC. (KB-Desktop-Renderer-Stability.)
 */
import { useCallback, useEffect, useState } from "react";
import { kb } from "./kb";
import type { Hit, TaskEvent, TaskStage, TaskStatus } from "../../shared/types";

export type AppState =
  | { kind: "idle" }
  | { kind: "uploading"; file: string }
  | {
      kind: "indexing";
      file: string;
      taskId: string;
      progress: number;
      stage: TaskStage;
      events: TaskEvent[];
      lastMessage: string;
    }
  | { kind: "searching"; query: string }
  | { kind: "error"; message: string };

export function useAppState() {
  const [state, setState] = useState<AppState>({ kind: "idle" });
  const [results, setResults] = useState<Hit[]>([]);
  const [serverReady, setServerReady] = useState<boolean>(false);

  useEffect(() => {
    const off = kb.onProgress((t: TaskStatus) => {
      // Normalize for older servers that don't yet emit stage/events.
      const stage: TaskStage = t.stage ?? "queued";
      const events: TaskEvent[] = t.events ?? [];
      const lastEvent = events[events.length - 1];
      const lastMessage = lastEvent ? lastEvent.message : "";

      // Done / failed transitions clear the progress bar so the user sees
      // completion instead of a frozen 100% indicator.
      if (t.status === "done" || t.status === "failed") {
        setState((s) =>
          s.kind === "indexing" && s.taskId === t.task_id
            ? { kind: "idle" }
            : s,
        );
        return;
      }
      setState((s) =>
        s.kind === "indexing" && s.taskId === t.task_id
          ? { ...s, progress: t.progress, stage, events, lastMessage }
          : s,
      );
    });
    return off;
  }, []);

  const checkHealth = useCallback(async (): Promise<void> => {
    try {
      await kb.health();
      setServerReady(true);
    } catch (e) {
      setServerReady(false);
      setState({ kind: "error", message: `Server unreachable: ${String(e)}` });
    }
  }, []);

  const importFile = useCallback(async (): Promise<void> => {
    const p = await kb.pickFile();
    if (!p) return;
    setState({ kind: "uploading", file: p });
    try {
      const r = await kb.importFile(p);
      // Start at 0 with stage="queued"; the first poll from the main process
      // will push the actual server-side progress (typically stage="parsing"
      // at 0.10) within ~600ms.
      setState({
        kind: "indexing",
        file: p,
        taskId: r.task_id,
        progress: 0,
        stage: "queued",
        events: [],
        lastMessage: "",
      });
    } catch (e) {
      setState({ kind: "error", message: `Import failed: ${String(e)}` });
    }
  }, []);

  const search = useCallback(async (query: string): Promise<void> => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setState({ kind: "searching", query });
    try {
      const hits = await kb.search(query, { top_k: 8 });
      setResults(hits);
      setState({ kind: "idle" });
    } catch (e) {
      setState({ kind: "error", message: `Search failed: ${String(e)}` });
    }
  }, []);

  const resetError = useCallback((): void => {
    setState({ kind: "idle" });
  }, []);

  return { state, results, serverReady, checkHealth, importFile, search, resetError };
}
