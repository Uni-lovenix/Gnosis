import React, { useCallback, useEffect, useState } from "react";
import { kb } from "../lib/kb";
import type { DocumentInfo } from "../../shared/types";

type LoadState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; docs: DocumentInfo[] }
  | { kind: "error"; message: string };

export function DocumentsPage(): JSX.Element {
  const [state, setState] = useState<LoadState>({ kind: "idle" });
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const docs = await kb.listDocuments();
      setState({ kind: "ready", docs });
    } catch (e) {
      setState({ kind: "error", message: (e as Error).message });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onDelete = useCallback(
    async (id: string) => {
      const ok = window.confirm(`Delete document ${id}? This removes the local catalog entry only.`);
      if (!ok) return;
      setPendingDelete(id);
      try {
        await kb.deleteDocument(id);
        await refresh();
      } catch (e) {
        setState({ kind: "error", message: (e as Error).message });
      } finally {
        setPendingDelete(null);
      }
    },
    [refresh],
  );

  return (
    <section className="kb-page">
      <header className="kb-page-header">
        <h2>Imported documents</h2>
        <button onClick={() => void refresh()} disabled={state.kind === "loading"}>
          refresh
        </button>
      </header>
      {state.kind === "loading" && <p>loading…</p>}
      {state.kind === "error" && (
        <p className="kb-error" role="alert">
          {state.message} <button onClick={() => void refresh()}>retry</button>
        </p>
      )}
      {state.kind === "ready" && state.docs.length === 0 && (
        <p>No documents listed yet. Import a file from the Import tab to populate this catalog.</p>
      )}
      {state.kind === "ready" && state.docs.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Path</th>
              <th>Parser</th>
              <th>Chunks</th>
              <th>Size</th>
              <th>Imported</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {state.docs.map((d) => (
              <tr key={d.id}>
                <td>{d.source_path}</td>
                <td>{d.parser ?? "—"}</td>
                <td>{d.chunks}</td>
                <td>{d.size}</td>
                <td>{d.imported_at}</td>
                <td>
                  <button
                    onClick={() => void onDelete(d.id)}
                    disabled={pendingDelete === d.id}
                  >
                    {pendingDelete === d.id ? "deleting…" : "delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}