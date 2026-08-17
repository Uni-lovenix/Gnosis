/**
 * Top-level renderer App. Renders the 4-page tabbed UI: Import / Search /
 * Documents / Settings.
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

export function App(): JSX.Element {
  const {
    state,
    results,
    serverReady,
    healthInfo,
    checkHealth,
    importFile,
    search,
    resetError,
    historyRefreshKey,
  } = useAppState();
  const [tab, setTab] = useState<Tab>("search");
  const [datasources, setDatasources] = useState<DatasourceInfo[]>([]);

  useEffect(() => {
    void (async () => {
      await checkHealth();
      try {
        setDatasources(await (window as any).kb.listDatasources());
      } catch {
        // ignore; UI shows banner
      }
    })();
    const id = setInterval(() => void checkHealth(), 15_000);
    return () => clearInterval(id);
  }, [checkHealth]);

  return (
    <div className="kb-app">
      <header className="kb-header">
        <h1>KB Desktop</h1>
        <span className={`kb-status ${serverReady ? "ok" : "down"}`}>
          {serverReady ? "server ok" : "server unreachable"}
        </span>
        <nav>
          {(["import", "search", "browse", "documents", "settings"] as Tab[]).map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
      </header>
      {healthInfo?.degraded && (
        <div className="kb-banner-degraded" role="alert">
          <strong>degraded</strong>
          <span>
            {healthInfo.embedder_fallback
              ? `embedder fell back to ${healthInfo.embedder_backend ?? "mock"}`
              : healthInfo.active_datasource && healthInfo.active_datasource.ok === false
                ? `datasource ${healthInfo.active_datasource.name} is not available`
                : healthInfo.embedder_ok === false
                  ? "embedder is not available"
                  : healthInfo.active_datasource
                    ? "dependencies degraded"
                    : "no active datasource"}
          </span>
        </div>
      )}
      {state.kind === "error" && (
        <div className="kb-error" role="alert">
          {state.message} <button onClick={resetError}>dismiss</button>
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
        {tab === "search" && <SearchPage results={results} onSearch={search} />}
        {tab === "browse" && <BrowsePage />}
        {tab === "documents" && <DocumentsPage />}
        {tab === "settings" && <SettingsPage datasources={datasources} />}
      </main>
    </div>
  );
}
