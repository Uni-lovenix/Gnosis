/**
 * Compact "recently imported" recap rendered inside the Import page.
 *
 * Pulls the local document catalog via ``kb.listDocuments()`` (already sorted
 * ``ORDER BY imported_at DESC`` server-side) and shows the top ``HISTORY_LIMIT``
 * rows. There is no delete action here — use the Documents tab for that.
 *
 * Refresh triggers (defense in depth — any one of them is sufficient):
 *   1. On mount via ``useEffect``.
 *   2. Whenever ``historyRefreshKey`` changes (incremented by ``useAppState``
 *      when a new task transitions to ``kind: "completed"``).
 *   3. Whenever the AppState transitions to ``kind: "completed"`` with a
 *      different ``taskId`` than the last refresh we observed. This watches
 *      the import state machine directly so that the panel refreshes even if
 *      the counter signal above is missed (e.g. a renderer that mounts
 *      before the counter is wired, or a re-render that doesn't take the
 *      counter path).
 *   4. When the user clicks the inline "刷新" button.
 *
 * The state-based trigger uses a ``useRef`` keyed on ``taskId`` so we never
 * fire the same refresh twice for one task, regardless of how many signals
 * arrive.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { kb } from "../lib/kb";
import type { AppState } from "../lib/state";
import type { DocumentInfo } from "../../shared/types";

const HISTORY_LIMIT = 10;

interface Props {
  /** Current renderer state machine value. Drives the state-based refresh. */
  state: AppState;
  /** Monotonic counter incremented on each completed import (legacy trigger). */
  historyRefreshKey: number;
  /** Optional callback to switch to the Documents tab (for "查看全部"). */
  onViewAll?: () => void;
}

export function ImportHistoryPanel({ state, historyRefreshKey, onViewAll }: Props): JSX.Element {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // Track the last ``taskId`` we refreshed for so repeated renders of the
  // same ``completed`` state don't re-fetch.
  const lastRefreshedTaskIdRef = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await kb.listDocuments();
      setDocs(next);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + historyRefreshKey trigger.
  useEffect(() => {
    void refresh();
  }, [refresh, historyRefreshKey]);

  // State-based trigger: refresh when a new task lands in ``completed``,
  // and reset the dedupe ref when a fresh import starts so the next
  // completion is treated as new again.
  useEffect(() => {
    if (state.kind === "completed") {
      if (state.taskId !== lastRefreshedTaskIdRef.current) {
        lastRefreshedTaskIdRef.current = state.taskId;
        void refresh();
      }
    } else if (state.kind === "uploading" || state.kind === "indexing") {
      lastRefreshedTaskIdRef.current = null;
    }
  }, [state, refresh]);

  const visible = docs.slice(0, HISTORY_LIMIT);
  const overflow = Math.max(0, docs.length - HISTORY_LIMIT);

  return (
    <section className="kb-page-section" aria-label="导入历史">
      <header className="kb-page-section-header">
        <h3>导入历史</h3>
        <button
          className="kb-page-section-action"
          onClick={() => void refresh()}
          disabled={loading}
          style={{
            background: "transparent",
            color: "var(--fg-dim)",
            border: "1px solid #232634",
            borderRadius: 4,
            padding: "2px 8px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          {loading ? "刷新…" : "刷新"}
        </button>
      </header>

      {error && <p className="kb-history-empty">加载失败:{error}</p>}
      {!error && docs.length === 0 && !loading && (
        <p className="kb-history-empty">还没有导入任何文件。</p>
      )}
      {!error && docs.length > 0 && (
        <>
          <table className="kb-history-table">
            <thead>
              <tr>
                <th>文件</th>
                <th>解析器</th>
                <th>切片</th>
                <th>导入时间</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((d) => (
                <tr key={d.id}>
                  <td className="kb-history-path" title={d.source_path}>
                    {d.source_path}
                  </td>
                  <td>{d.parser ?? "—"}</td>
                  <td className="kb-history-chunks">{d.chunks}</td>
                  <td className="kb-history-imported">{d.imported_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {overflow > 0 && (
            <p className="kb-history-more">
              {onViewAll ? (
                <button onClick={onViewAll}>查看全部 ({docs.length} 条)</button>
              ) : (
                <>还有 {overflow} 条,请到 Documents 标签页查看。</>
              )}
            </p>
          )}
        </>
      )}
    </section>
  );
}