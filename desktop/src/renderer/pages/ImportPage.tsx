import React from "react";
import type { AppState } from "../lib/state";
import type { TaskStage } from "../../shared/types";

interface Props {
  state: AppState;
  onImport: () => Promise<void>;
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

export function ImportPage({ state, onImport }: Props): JSX.Element {
  const busy = state.kind === "uploading" || state.kind === "indexing";
  const file = state.kind === "uploading" || state.kind === "indexing" ? state.file : null;
  const progress =
    state.kind === "indexing"
      ? state.progress
      : state.kind === "uploading"
        ? 0.1
        : 0;
  const stage =
    state.kind === "indexing" ? state.stage : state.kind === "uploading" ? "queued" : "queued";
  const events = state.kind === "indexing" ? state.events : [];
  const lastMessage = state.kind === "indexing" ? state.lastMessage : "";

  return (
    <section className="kb-page">
      <h2>导入文档</h2>
      <p>支持：Excel、Word、PDF、Markdown、纯文本。</p>
      <button disabled={busy} onClick={onImport}>
        {busy ? "处理中…" : "选择文件"}
      </button>
      {file && (
        <div className="kb-progress">
          <code>{file}</code>
          <div className="kb-progress-bar">
            <progress max={1} value={progress} />
            <span className="kb-progress-pct">{Math.round(progress * 100)}%</span>
          </div>
          {state.kind === "indexing" && (
            <>
              <p className="kb-stage">
                <span className={`kb-stage-tag kb-stage-${stage}`}>
                  {stageLabel(stage)}
                </span>
                {lastMessage && <span className="kb-stage-message">— {lastMessage}</span>}
              </p>
              <details className="kb-event-log" open={events.length > 0}>
                <summary>事件日志（{events.length}）</summary>
                {events.length === 0 ? (
                  <p className="kb-event-empty">暂无事件。</p>
                ) : (
                  <ol>
                    {events
                      .slice()
                      .reverse()
                      .map((e, i) => (
                        <li key={`${e.ts}-${i}`}>
                          <code className="kb-event-ts">{e.ts.slice(11, 19)}Z</code>
                          <span className={`kb-stage-tag kb-stage-${e.stage}`}>
                            {stageLabel(e.stage)}
                          </span>
                          <span className="kb-event-progress">{e.progress.toFixed(2)}</span>
                          {e.message && <span className="kb-event-message">— {e.message}</span>}
                        </li>
                      ))}
                  </ol>
                )}
              </details>
            </>
          )}
        </div>
      )}
    </section>
  );
}