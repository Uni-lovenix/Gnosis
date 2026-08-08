import React from "react";
import type { AppState } from "../lib/state";
import type { TaskEvent, TaskStage } from "../../shared/types";
import { ImportHistoryPanel } from "./ImportHistoryPanel";

interface Props {
  state: AppState;
  onImport: () => Promise<void>;
  historyRefreshKey: number;
  /** Optional callback to switch to the Documents tab (for "查看全部"). */
  onViewAll?: () => void;
}

/**
 * Human-readable label for each pipeline stage. The renderer also uses
 * these as tags inside the event log.
 */
const STAGE_LABELS: Record<TaskStage, string> = {
  queued: "排队中",
  parsing: "解析文档",
  chunking: "切片中",
  embedding: "Embedding 中",
  writing: "写入数据源",
  done: "完成",
  failed: "失败",
};

function stageLabel(stage: TaskStage): string {
  return STAGE_LABELS[stage] ?? stage;
}

/**
 * Normalized view of the current state for rendering. Pulls a single
 * "what to show right now" object so the JSX stays declarative regardless
 * of which AppState variant we're in.
 */
interface ImportView {
  busy: boolean;
  file: string | null;
  progress: number;
  stage: TaskStage;
  events: TaskEvent[];
  lastMessage: string;
  error: string | null;
  showProgress: boolean;
}

function deriveView(state: AppState): ImportView {
  switch (state.kind) {
    case "idle":
      return {
        busy: false,
        file: null,
        progress: 0,
        stage: "queued",
        events: [],
        lastMessage: "",
        error: null,
        showProgress: false,
      };
    case "uploading":
      return {
        busy: true,
        file: state.file,
        progress: 0.1,
        stage: "queued",
        events: [],
        lastMessage: "",
        error: null,
        showProgress: true,
      };
    case "indexing":
      return {
        busy: true,
        file: state.file,
        progress: state.progress,
        stage: state.stage,
        events: state.events,
        lastMessage: state.lastMessage,
        error: null,
        showProgress: true,
      };
    case "completed":
      return {
        busy: false,
        file: state.file,
        // 1.0 for successful imports; the frozen last value for failures.
        progress: state.progress,
        stage: state.stage,
        events: state.events,
        lastMessage: state.lastMessage,
        error: state.error,
        showProgress: true,
      };
    case "searching":
    case "error":
      // No import context to display. (The error banner lives in App.)
      return {
        busy: false,
        file: null,
        progress: 0,
        stage: "queued",
        events: [],
        lastMessage: "",
        error: null,
        showProgress: false,
      };
  }
}

export function ImportPage({ state, onImport, historyRefreshKey, onViewAll }: Props): JSX.Element {
  const view = deriveView(state);

  return (
    <section className="kb-page">
      <h2>导入文档</h2>
      <p>支持:Excel、Word、PDF、Markdown、纯文本。</p>
      <button
        className="kb-button-primary"
        disabled={view.busy}
        onClick={onImport}
      >
        <span className="kb-button-content">
          {view.busy ? (
            <>
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <circle cx="8" cy="8" r="6" />
              </svg>
              <span>处理中…</span>
            </>
          ) : (
            <>
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <line x1="8" y1="3" x2="8" y2="13" />
                <line x1="3" y1="8" x2="13" y2="8" />
              </svg>
              <span>选择文件</span>
            </>
          )}
        </span>
      </button>
      {view.showProgress && view.file && (
        <div className="kb-progress">
          <code>{view.file}</code>
          <div className="kb-progress-bar">
            <progress max={1} value={view.progress} />
            <span className="kb-progress-pct">{Math.round(view.progress * 100)}%</span>
          </div>
          <p className="kb-stage">
            <span className={`kb-stage-tag kb-stage-${view.stage}`}>
              {stageLabel(view.stage)}
            </span>
            {view.lastMessage && (
              <span className="kb-stage-message">— {view.lastMessage}</span>
            )}
          </p>
          {state.kind === "completed" && view.error && (
            <p className="kb-stage-message" style={{ color: "var(--error)" }}>
              失败原因:{view.error}
            </p>
          )}
          <details className="kb-event-log" open={view.events.length > 0}>
            <summary>事件日志({view.events.length})</summary>
            {view.events.length === 0 ? (
              <p className="kb-event-empty">暂无事件。</p>
            ) : (
              <ol>
                {view.events
                  .slice()
                  .reverse()
                  .map((e, i) => (
                    <li key={`${e.ts}-${i}`}>
                      <code className="kb-event-ts">{e.ts.slice(11, 19)}Z</code>
                      <span className={`kb-stage-tag kb-stage-${e.stage}`}>
                        {stageLabel(e.stage)}
                      </span>
                      <span className="kb-event-progress">{e.progress.toFixed(2)}</span>
                      {e.message && (
                        <span className="kb-event-message">— {e.message}</span>
                      )}
                    </li>
                  ))}
              </ol>
            )}
          </details>
        </div>
      )}
      <ImportHistoryPanel
        state={state}
        historyRefreshKey={historyRefreshKey}
        onViewAll={onViewAll}
      />
    </section>
  );
}