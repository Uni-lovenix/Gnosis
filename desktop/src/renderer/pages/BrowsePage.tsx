import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { kb } from "../lib/kb";
import { formatError } from "../lib/errors";
import type {
  ActiveDatasourceResponse,
  BrowseResponse,
  ChunkSummary,
  DocumentSummary,
} from "../../shared/types";

const DEFAULT_PAGE_SIZE = 20;

type LoadState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: BrowseResponse }
  | { kind: "error"; message: string };

type Toast =
  | { kind: "info"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ok"; message: string }
  | null;

const SEED_PARSERS = ["excel", "word", "pdf", "markdown", "text"];

const CAPABILITY_LABELS: Record<string, string> = {
  chunk_list: "浏览切片",
  dump: "数据迁移导出",
  metadata_filter: "元数据过滤",
  delete_by_filter: "按条件删除",
  bm25_hybrid: "BM25 混合检索",
  small_dataset_only: "仅适合小数据集",
  scan_limit_risk: "扫描上限提示",
};

/** Build the list of parser options: union of the seed list with whatever
 * we've actually seen in the response, sorted alphabetically. */
function unionParsers(seen: string[]): string[] {
  const set = new Set<string>(SEED_PARSERS);
  for (const p of seen) if (p) set.add(p);
  return Array.from(set).sort();
}

export function BrowsePage(): JSX.Element {
  const [activeDs, setActiveDs] = useState<ActiveDatasourceResponse | null>(null);
  const [activeCapability, setActiveCapability] = useState<boolean | null>(null);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [docFilter, setDocFilter] = useState("");
  const [parser, setParser] = useState("");
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<LoadState>({ kind: "idle" });
  const [toast, setToast] = useState<Toast>(null);
  const bootedRef = useRef(false);
  const initialLoadRef = useRef(false);

  // Probe active datasource + capability on mount. We hit the static
  // /v1/datasources list (with type-specific capability advertisement) and
  // compare against the active type; this avoids a separate capability
  // endpoint.
  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;
    void (async () => {
      try {
        const [active, catalog] = await Promise.all([
          kb.getActiveDatasource(),
          kb.listDatasources(),
        ]);
        setActiveDs(active);
        const ds = catalog.find((d) => d.type === (active.config?.type ?? ""));
        const caps = ds ? ds.capabilities : [];
        setCapabilities(caps);
        setActiveCapability(caps.includes("chunk_list"));
      } catch (e) {
        // Server unreachable — main banner covers it; here we just hide the page.
        setActiveCapability(false);
        setToast({ kind: "info", message: formatError(e, "浏览准备失败") });
      }
    })();
  }, []);

  const refresh = useCallback(
    async (nextOffset: number, nextDoc: string, nextParser: string) => {
      setState({ kind: "loading" });
      try {
        const data = await kb.browseChunks({
          document_id: nextDoc || undefined,
          parser: nextParser || undefined,
          offset: nextOffset,
          limit: DEFAULT_PAGE_SIZE,
        });
        setState({ kind: "ready", data });
        setToast(null);
      } catch (e) {
        const msg = String(e);
        // 501 = capability missing; surface as a permanent banner instead of
        // a transient error toast.
        if (/501/.test(msg) || /chunk_list/.test(msg)) {
          setActiveCapability(false);
        }
        setState({ kind: "error", message: formatError(e, "浏览失败") });
        setToast({ kind: "error", message: formatError(e, "浏览失败") });
      }
    },
    [],
  );

  // Initial load.
  useEffect(() => {
    if (initialLoadRef.current) return;
    initialLoadRef.current = true;
    void refresh(0, docFilter, parser);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const data = state.kind === "ready" ? state.data : null;

  // Parser dropdown options: seed + everything we've actually seen.
  const parserOptions = useMemo(() => {
    const seen: string[] = [];
    if (data) for (const agg of Object.values(data.aggregations)) seen.push(...agg.parsers);
    return unionParsers(seen);
  }, [data]);

  const total = data?.total ?? 0;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + DEFAULT_PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = pageEnd < total;

  function gotoDoc(docId: string): void {
    setDocFilter(docId);
    setOffset(0);
    void refresh(0, docId, parser);
  }

  function gotoPage(nextOffset: number): void {
    setOffset(nextOffset);
    void refresh(nextOffset, docFilter, parser);
  }

  return (
    <section className="kb-page">
      <h2>数据浏览</h2>
      <p className="kb-help">
        查看 active 数据源中已索引的切片。Settings 中的 Switch now 可热切换数据源，无需重启桌面端。
      </p>

      {activeDs?.config && (
        <div className="kb-browse-capabilities" aria-label="数据源能力">
          <h3>当前数据源能力</h3>
          <p className="kb-help">
            当前数据源：<strong>{activeDs.name}</strong>（{activeDs.config.type}）
          </p>
          {activeCapability === null ? (
            <p className="kb-help">正在检查能力…</p>
          ) : (
            <>
              {capabilities.length > 0 ? (
                <ul className="kb-capability-list">
                  {capabilities.map((c) => (
                    <li key={c}>{CAPABILITY_LABELS[c] ?? c}</li>
                  ))}
                </ul>
              ) : (
                <p className="kb-help">该数据源没有声明附加能力。</p>
              )}
              {activeCapability === false && (
                <div className="kb-banner-warn">
                  当前数据源不支持浏览切片。建议迁移到 Elasticsearch 数据源，迁移路径见 RUNBOOK §3。
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="kb-browse-filters">
        <label>
          解析器
          <select
            value={parser}
            onChange={(e) => {
              setParser(e.target.value);
              setOffset(0);
              void refresh(0, docFilter, e.target.value);
            }}
          >
            <option value="">全部</option>
            {parserOptions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          文档
          <select
            value={docFilter}
            onChange={(e) => gotoDoc(e.target.value)}
          >
            <option value="">全部文档</option>
            {data &&
              Object.values(data.aggregations).map((agg: DocumentSummary) => (
                <option key={agg.document_id} value={agg.document_id}>
                  {agg.document_id}（{agg.chunk_count}）
                </option>
              ))}
          </select>
        </label>
        <button onClick={() => gotoPage(0)} disabled={state.kind === "loading"}>
          刷新
        </button>
      </div>

      {toast && (
        <div className={`kb-toast kb-toast-${toast.kind}`} role={toast.kind === "error" ? "alert" : "status"}>
          {toast.message}
        </div>
      )}

      {data && data.aggregations && Object.keys(data.aggregations).length > 0 && (
        <>
          <h3>文档聚合（{Object.keys(data.aggregations).length}）</h3>
          <table className="kb-agg-table">
            <thead>
              <tr>
                <th>文档</th>
                <th>解析器</th>
                <th className="kb-agg-count">切片数</th>
                <th>样例</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(data.aggregations)
                .sort((a, b) => b.chunk_count - a.chunk_count)
                .map((agg: DocumentSummary) => (
                  <tr key={agg.document_id} onClick={() => gotoDoc(agg.document_id)}>
                    <td><code>{agg.document_id}</code></td>
                    <td>{agg.parsers.join(", ") || "—"}</td>
                    <td className="kb-agg-count">{agg.chunk_count}</td>
                    <td>{agg.sample_text || "—"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}

      <div className="kb-pagination">
        <button
          disabled={!hasPrev || state.kind === "loading"}
          onClick={() => gotoPage(Math.max(0, offset - DEFAULT_PAGE_SIZE))}
        >
          上一页
        </button>
        <button
          disabled={!hasNext || state.kind === "loading"}
          onClick={() => gotoPage(offset + DEFAULT_PAGE_SIZE)}
        >
          下一页
        </button>
        <span className="kb-pagination-info">
          {total === 0 ? "没有切片" : `${pageStart}–${pageEnd} / ${total}`}
        </span>
      </div>

      {state.kind === "loading" && <p className="kb-help" role="status">加载中…</p>}
      {state.kind === "error" && (
        <div className="kb-error-inline" role="alert">
          {state.message}
        </div>
      )}

      {data && (
        <ul className="kb-chunks">
          {data.chunks.length === 0 ? (
            <li>没有匹配当前筛选条件的切片。</li>
          ) : (
            data.chunks.map((c: ChunkSummary) => (
              <li key={c.chunk_id}>
                <div className="kb-chunk-header">
                  <code>{c.chunk_id}</code>
                  <span className="kb-chunk-doc">{c.document_id}</span>
                  <span className="kb-chunk-meta">
                    {c.text.length} / {c.text_length} 字符
                  </span>
                </div>
                <p className="kb-chunk-preview">{c.text}</p>
                <details>
                  <summary>元数据（{Object.keys(c.metadata).length}）</summary>
                  <pre>{JSON.stringify(c.metadata, null, 2)}</pre>
                </details>
              </li>
            ))
          )}
        </ul>
      )}
    </section>
  );
}
