import React, { useState } from "react";
import type { Hit } from "../../shared/types";
import { describeError } from "../lib/errors";
import type { HumanError } from "../lib/errors";

interface Props {
  onSearch: (q: string) => Promise<Hit[]>;
}

type SearchStatus = "idle" | "loading" | "ready" | "error";

function sourceLabel(hit: Hit): string {
  if (hit.document_id) return hit.document_id;
  const path = hit.metadata["source_path"];
  if (typeof path === "string" && path) return path;
  return "未知来源";
}

function metadataSummary(hit: Hit): string {
  const skip = new Set(["document_id", "source_path", "parser"]);
  const entries = Object.entries(hit.metadata).filter(
    ([key, value]) => !skip.has(key) && value !== null && value !== undefined && value !== "",
  );
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}=${String(value).slice(0, 24)}`)
    .join(" · ");
}

export function SearchPage({ onSearch }: Props): JSX.Element {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [error, setError] = useState<HumanError | null>(null);

  async function runSearch(event?: React.FormEvent): Promise<void> {
    event?.preventDefault();
    const query = q.trim();
    if (!query) {
      setHits([]);
      setStatus("idle");
      setError(null);
      return;
    }
    setStatus("loading");
    setError(null);
    try {
      setHits(await onSearch(query));
      setStatus("ready");
    } catch (e) {
      setError(describeError(e, "检索失败"));
      setStatus("error");
    }
  }

  return (
    <section className="kb-page">
      <h2>知识检索</h2>
      <form
        onSubmit={(e) => void runSearch(e)}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="向知识库提问…"
          autoFocus
          aria-label="检索问题"
        />
        <button type="submit" disabled={status === "loading"}>
          {status === "loading" ? "检索中…" : "检索"}
        </button>
      </form>

      {status === "idle" && (
        <p className="kb-help">输入问题开始检索，结果会显示相关度、来源文档和解析器。</p>
      )}
      {status === "loading" && hits.length === 0 && (
        <p className="kb-help" role="status">正在检索，请稍候…</p>
      )}
      {status === "ready" && hits.length === 0 && (
        <p className="kb-search-empty" role="status">
          无匹配，检查是否已导入文档，或换个问法。
        </p>
      )}
      {status === "error" && error && (
        <div className="kb-error-inline" role="alert">
          <strong>{error.title}</strong>
          <span>{error.hint}</span>
          <button onClick={() => void runSearch()}>
            重试
          </button>
          <details>
            <summary>技术详情</summary>
            <code>{error.raw}</code>
          </details>
        </div>
      )}
      {status === "loading" && hits.length > 0 && (
        <p className="kb-help" role="status">检索中，保留上次结果…</p>
      )}
      <ol className="kb-hits">
        {hits.map((h) => (
          <li key={h.id}>
            <div className="kb-hit-header">
              <span className="kb-score">相关度 {h.score.toFixed(3)}</span>
              <span className="kb-hit-source" title={sourceLabel(h)}>
                {sourceLabel(h)}
              </span>
              {typeof h.metadata.parser === "string" && (
                <span className="kb-hit-parser">{h.metadata.parser}</span>
              )}
            </div>
            <p>{h.text.slice(0, 400)}</p>
            {metadataSummary(h) && (
              <div className="kb-hit-meta">{metadataSummary(h)}</div>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
