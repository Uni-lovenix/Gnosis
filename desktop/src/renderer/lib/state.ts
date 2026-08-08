/**
 * Tiny global state machine for the renderer.
 *
 * State enum: idle | uploading | indexing | completed | searching | error
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
  | {
      // Terminal state after an import finishes. Persists in the UI until the
      // user starts another import (which sets ``kind: "uploading"`` and
      // naturally displaces this branch).
      kind: "completed";
      file: string;
      taskId: string;
      stage: "done" | "failed";
      progress: number;
      events: TaskEvent[];
      lastMessage: string;
      error: string | null;
    }
  | { kind: "searching"; query: string }
  | { kind: "error"; message: string };

export function useAppState() {
  const [state, setState] = useState<AppState>({ kind: "idle" });
  const [results, setResults] = useState<Hit[]>([]);
  const [serverReady, setServerReady] = useState<boolean>(false);
  // Monotonic counter bumped each time an import lands in ``completed``.
  // The import-history panel watches this to know when to re-fetch.
  const [historyRefreshKey, setHistoryRefreshKey] = useState<number>(0);

  useEffect(() => {
    const off = kb.onProgress((t: TaskStatus) => {
      // Normalize for older servers that don't yet emit stage/events.
      const stage: TaskStage = t.stage ?? "queued";
      const events: TaskEvent[] = t.events ?? [];
      const lastEvent = events[events.length - 1];
      const lastMessage = lastEvent ? lastEvent.message : "";

      // Done / failed transitions freeze the final progress view on screen
      // (instead of collapsing back to idle) so the user sees what happened.
      // The next ``importFile`` call resets to ``uploading`` and clears it.
      if (t.status === "done" || t.status === "failed") {
        setState((s) => {
          if (s.kind !== "indexing" || s.taskId !== t.task_id) return s;
          return {
            kind: "completed",
            file: s.file,
            taskId: s.taskId,
            stage: t.status as "done" | "failed",
            progress: t.status === "done" ? 1 : s.progress,
            events: t.events ?? s.events,
            lastMessage: t.error ?? lastMessage,
            error: t.error,
          };
        });
        // A new completed import just landed — nudge the history panel.
        setHistoryRefreshKey((k) => k + 1);
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
    // Reset any prior completed view immediately; the user just started a new
    // import, so the previous panel should clear as part of the same action.
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

  return {
    state,
    results,
    serverReady,
    checkHealth,
    importFile,
    search,
    resetError,
    historyRefreshKey,
  };
}
