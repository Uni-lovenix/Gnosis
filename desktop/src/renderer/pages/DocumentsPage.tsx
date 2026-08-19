import React, { useCallback, useEffect, useState } from "react";
import { kb } from "../lib/kb";
import { formatError } from "../lib/errors";
import { ConfirmDialog } from "../components/ConfirmDialog";
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
      setState({ kind: "error", message: formatError(e, "文档列表加载失败") });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onDelete = useCallback(
    async (id: string) => {
      setPendingDelete(id);
      setState({ kind: "loading" });
      try {
        await kb.deleteDocument(id);
        await refresh();
      } catch (e) {
        setState({ kind: "error", message: formatError(e, "删除失败") });
      } finally {
        setPendingDelete(null);
      }
    },
    [refresh],
  );

  return (
    <section className="kb-page">
      <header className="kb-page-header">
        <h2>导入的文档</h2>
        <button onClick={() => void refresh()} disabled={state.kind === "loading"}>
          刷新
        </button>
      </header>
      {state.kind === "loading" && <p>加载中…</p>}
      {state.kind === "error" && (
        <p className="kb-error" role="alert">
          {state.message} <button onClick={() => void refresh()}>重试</button>
        </p>
      )}
      {state.kind === "ready" && state.docs.length === 0 && (
        <p>还没有文档。请到“导入”页导入文件。</p>
      )}
      {state.kind === "ready" && state.docs.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>路径</th>
              <th>解析器</th>
              <th>切片</th>
              <th>大小</th>
              <th>导入时间</th>
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
                    {pendingDelete === d.id ? "删除中…" : "删除"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {pendingDelete && (
        <ConfirmDialog
          title="删除文档记录"
          body={
            <>
              此操作仅删除本地目录中的文档记录，不修改数据源中的切片。
              <br />
              请确认删除文档 <code>{pendingDelete}</code>。
            </>
          }
          confirmLabel="删除"
          matchText={pendingDelete}
          busy={pendingDelete !== null && state.kind === "loading"}
          onConfirm={() => void onDelete(pendingDelete)}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </section>
  );
}
