/**
 * Top-level renderer App. Renders the 5-page tabbed UI and keeps the health
 * banner as the only app-wide error surface; page-level concerns live in the
 * page components.
 */
import React, { useEffect, useState } from "react";
import { useAppState } from "./lib/state";
import { ImportPage } from "./pages/ImportPage";
import { SearchPage } from "./pages/SearchPage";
import { BrowsePage } from "./pages/BrowsePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { DatasourceInfo } from "../shared/types";

type Tab = "import" | "search" | "browse" | "documents" | "settings";

const TAB_LABELS: Record<Tab, string> = {
  import: "导入",
  search: "检索",
  browse: "浏览",
  documents: "文档",
  settings: "设置",
};

export function App(): JSX.Element {
  const {
    state,
    serverReady,
    healthInfo,
    healthError,
    checkHealth,
    importFile,
    search,
    resetHealthError,
    historyRefreshKey,
  } = useAppState();
  const [tab, setTab] = useState<Tab>("search");
  const [datasources, setDatasources] = useState<DatasourceInfo[]>([]);
  const [pollMs, setPollMs] = useState(15_000);

  useEffect(() => {
    void (async () => {
      try {
        setDatasources(await (window as any).kb.listDatasources());
      } catch {
        // ignore; health banner covers the failure
      }
    })();
  }, []);

  useEffect(() => {
    void checkHealth();
    const id = setInterval(() => void checkHealth(), pollMs);
    return () => clearInterval(id);
  }, [checkHealth, pollMs]);

  // Degraded states should be noticed quickly; healthy states poll less often
  // so the desktop does not hammer a remote datasource.
  useEffect(() => {
    if (!serverReady) setPollMs(5_000);
    else if (healthInfo?.degraded) setPollMs(10_000);
    else setPollMs(30_000);
  }, [serverReady, healthInfo?.degraded]);

  return (
    <div className="kb-app">
      <header className="kb-header">
        <h1>灵知 Gnosis</h1>
        <span className={`kb-status ${serverReady ? "ok" : "down"}`}>
          {serverReady ? "服务正常" : "服务不可达"}
        </span>
        <nav>
          {(["import", "search", "browse", "documents", "settings"] as Tab[]).map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              aria-current={tab === t ? "page" : undefined}
              onClick={() => setTab(t)}
            >
              {TAB_LABELS[t]}
            </button>
          ))}
        </nav>
      </header>
      {healthInfo?.degraded && (
        <div className="kb-banner-degraded" role="alert">
          <strong>依赖降级</strong>
          <span>
            {healthInfo.embedder_fallback
              ? `Embedding 已降级到 ${healthInfo.embedder_backend ?? "mock"}，可正常启动但检索质量可能下降`
              : healthInfo.active_datasource && healthInfo.active_datasource.ok === false
                ? `数据源 ${healthInfo.active_datasource.name} 不可用`
                : healthInfo.embedder_ok === false
                  ? "Embedding 服务不可用"
                  : healthInfo.active_datasource
                    ? "依赖状态异常"
                    : "尚未激活数据源"}
          </span>
        </div>
      )}
      {healthError && (
        <div className="kb-error" role="alert">
          <span>{healthError}</span>
          <button onClick={resetHealthError}>关闭</button>
        </div>
      )}
      <main>
        {tab === "import" && (
          <ImportPage
            state={state}
            onImport={importFile}
            historyRefreshKey={historyRefreshKey}
            onViewAll={() => setTab("documents")}
          />
        )}
        {tab === "search" && <SearchPage onSearch={search} />}
        {tab === "browse" && <BrowsePage />}
        {tab === "documents" && <DocumentsPage />}
        {tab === "settings" && <SettingsPage datasources={datasources} />}
      </main>
    </div>
  );
}
