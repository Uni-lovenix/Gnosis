import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { kb } from "../lib/kb";
import type {
  ActiveDatasourceResponse,
  BrowseResponse,
  ChunkSummary,
  DocumentSummary,
} from "../../shared/types";

const DEFAULT_PAGE_SIZE = 20;
const DEBOUNCE_MS = 250;

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
  const [docFilter, setDocFilter] = useState("");
  const [docFilterDraft, setDocFilterDraft] = useState("");
  const [parser, setParser] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<LoadState>({ kind: "idle" });
  const [toast, setToast] = useState<Toast>(null);
  const debounceRef = useRef<number | null>(null);

  // Probe active datasource + capability on mount. We hit the static
  // /v1/datasources list (with type-specific capability advertisement) and
  // compare against the active type; this avoids a separate capability
  // endpoint.
  useEffect(() => {
    void (async () => {
      try {
        const [active, catalog] = await Promise.all([
          kb.getActiveDatasource(),
          kb.listDatasources(),
        ]);
        setActiveDs(active);
        const ds = catalog.find((d) => d.type === (active.config?.type ?? ""));
        setActiveCapability(ds ? ds.capabilities.includes("chunk_list") : false);
      } catch (e) {
        // Server unreachable — main banner covers it; here we just hide the page.
        setActiveCapability(false);
        setToast({ kind: "info", message: `browse ready check failed: ${String(e)}` });
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
      } catch (e) {
        const msg = String(e);
        // 501 = capability missing; surface as a permanent banner instead of
        // a transient error toast.
        if (/501/.test(msg) || /chunk_list/.test(msg)) {
          setActiveCapability(false);
        }
        setState({ kind: "error", message: msg });
        setToast({ kind: "error", message: msg });
      }
    },
    [],
  );

  // Debounce doc-id input so typing doesn't spam the API.
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setDocFilter(docFilterDraft);
      setOffset(0);
      void refresh(0, docFilterDraft, parser);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
    // refresh is stable (useCallback with no deps), parser/offset are reactive.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docFilterDraft, parser]);

  // Initial load.
  useEffect(() => {
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
    setDocFilterDraft(docId);
    setOffset(0);
    void refresh(0, docId, parser);
  }

  function gotoPage(nextOffset: number): void {
    setOffset(nextOffset);
    void refresh(nextOffset, docFilter, parser);
  }

  return (
    <section className="kb-page">
      <h2>Browse chunks</h2>
      <p className="kb-help">
        Inspect chunks stored in the active datasource. Per the G2 design, the
        datasource bound here is the one loaded at server startup — restart
        the desktop after changing the active datasource in Settings.
      </p>

      {activeDs?.config && (
        <p className="kb-help">
          Active: <strong>{activeDs.name}</strong> ({activeDs.config.type})
        </p>
      )}

      {activeCapability === false && (
        <div className="kb-banner-warn">
          {activeDs?.config
            ? `datasource "${activeDs.name}" (type=${activeDs.config.type}) does not support chunk_list; see RUNBOOK §3 for migration paths.`
            : "no active datasource; the browse endpoint needs one bound at server startup."}
        </div>
      )}

      <div className="kb-browse-filters">
        <label>
          parser
          <select
            value={parser}
            onChange={(e) => {
              setParser(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">(all)</option>
            {parserOptions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          document_id
          <input
            type="text"
            value={docFilterDraft}
            onChange={(e) => setDocFilterDraft(e.target.value)}
            placeholder="filter by document_id"
          />
        </label>
        <button onClick={() => gotoPage(0)} disabled={state.kind === "loading"}>
          Refresh
        </button>
      </div>

      {toast && (
        <div className={`kb-toast kb-toast-${toast.kind}`}>{toast.message}</div>
      )}

      {data && data.aggregations && Object.keys(data.aggregations).length > 0 && (
        <>
          <h3>Documents ({Object.keys(data.aggregations).length})</h3>
          <table className="kb-agg-table">
            <thead>
              <tr>
                <th>document_id</th>
                <th>parsers</th>
                <th className="kb-agg-count">chunks</th>
                <th>sample</th>
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
          ← Prev
        </button>
        <button
          disabled={!hasNext || state.kind === "loading"}
          onClick={() => gotoPage(offset + DEFAULT_PAGE_SIZE)}
        >
          Next →
        </button>
        <span className="kb-pagination-info">
          {total === 0
            ? "no chunks"
            : `${pageStart}–${pageEnd} of ${total}`}
        </span>
      </div>

      {state.kind === "loading" && <p className="kb-help">loading…</p>}
      {state.kind === "error" && (
        <p className="kb-error">{state.message}</p>
      )}

      {data && (
        <ul className="kb-chunks">
          {data.chunks.length === 0 ? (
            <li>No chunks match the current filters.</li>
          ) : (
            data.chunks.map((c: ChunkSummary) => (
              <li key={c.chunk_id}>
                <div className="kb-chunk-header">
                  <code>{c.chunk_id}</code>
                  <span className="kb-chunk-doc">{c.document_id}</span>
                  <span className="kb-chunk-meta">
                    {c.text.length} / {c.text_length} chars
                  </span>
                </div>
                <p className="kb-chunk-preview">{c.text}</p>
                <details>
                  <summary>metadata ({Object.keys(c.metadata).length})</summary>
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