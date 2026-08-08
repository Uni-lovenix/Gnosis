import React, { useCallback, useEffect, useMemo, useState } from "react";
import { kb } from "../lib/kb";
import type {
  DatasourceConfigRecord,
  DatasourceInfo,
} from "../../shared/types";

interface Props {
  datasources: DatasourceInfo[];
}

type Toast =
  | { kind: "info"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ok"; message: string }
  | null;

interface FormState {
  name: string;
  type: string;
  optionsRaw: string; // free-form JSON
}

const EMPTY_FORM: FormState = { name: "vec-local", type: "vector", optionsRaw: '{\n  "backend": "memory",\n  "dim": 64\n}' };

export function SettingsPage({ datasources }: Props): JSX.Element {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [saved, setSaved] = useState<DatasourceConfigRecord[]>([]);
  const [activeName, setActiveName] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);

  const refresh = useCallback(async () => {
    try {
      const [list, active] = await Promise.all([
        kb.listDatasourceConfigs(),
        kb.getActiveDatasource(),
      ]);
      setSaved(list);
      setActiveName(active.name);
    } catch (e) {
      setToast({ kind: "error", message: `load failed: ${String(e)}` });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const parsedOptions = useMemo<Record<string, unknown> | null>(() => {
    if (!form.optionsRaw.trim()) return {};
    try {
      return JSON.parse(form.optionsRaw) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [form.optionsRaw]);

  function startEdit(cfg: DatasourceConfigRecord): void {
    setEditingName(cfg.name);
    setForm({
      name: cfg.name,
      type: cfg.type,
      optionsRaw: JSON.stringify(cfg.options, null, 2),
    });
    setTestResult(null);
    setToast(null);
  }

  function resetForm(): void {
    setEditingName(null);
    setForm(EMPTY_FORM);
    setTestResult(null);
  }

  async function runTest(): Promise<void> {
    if (parsedOptions === null) {
      setTestResult("FAIL: options JSON is invalid");
      return;
    }
    try {
      const r = await kb.testDatasource({
        name: form.name || "test",
        type: form.type,
        options: parsedOptions,
      });
      setTestResult(`${r.ok ? "OK" : "FAIL"} latency=${r.latency_ms?.toFixed(2)}ms ${r.message ?? ""}`);
    } catch (e) {
      setTestResult(`error: ${String(e)}`);
    }
  }

  async function runSave(): Promise<void> {
    if (parsedOptions === null) {
      setToast({ kind: "error", message: "options JSON is invalid — fix and retry" });
      return;
    }
    if (!form.name.trim()) {
      setToast({ kind: "error", message: "name is required" });
      return;
    }
    try {
      await kb.saveDatasourceConfig({
        name: form.name.trim(),
        type: form.type,
        options: parsedOptions,
      });
      setToast({
        kind: "ok",
        message: editingName ? `updated "${form.name.trim()}"` : `saved "${form.name.trim()}"`,
      });
      resetForm();
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: `save failed: ${String(e)}` });
    }
  }

  async function runActivate(name: string): Promise<void> {
    try {
      await kb.activateDatasourceConfig(name);
      setActiveName(name);
      setToast({
        kind: "ok",
        message: `set "${name}" as the active datasource (takes effect on next server start)`,
      });
    } catch (e) {
      setToast({ kind: "error", message: `activate failed: ${String(e)}` });
    }
  }

  async function runDeactivate(): Promise<void> {
    try {
      await kb.deactivateDatasource();
      setActiveName(null);
      setToast({ kind: "info", message: "deactivated; server will fall back to in-memory vector on next start" });
    } catch (e) {
      setToast({ kind: "error", message: `deactivate failed: ${String(e)}` });
    }
  }

  async function runDelete(name: string): Promise<void> {
    if (!window.confirm(`Delete datasource config "${name}"?`)) return;
    try {
      await kb.deleteDatasourceConfig(name);
      if (editingName === name) resetForm();
      setToast({ kind: "info", message: `deleted "${name}"` });
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: `delete failed: ${String(e)}` });
    }
  }

  return (
    <section className="kb-page">
      <h2>Settings</h2>

      {toast && (
        <div className={`kb-toast kb-toast-${toast.kind}`}>{toast.message}</div>
      )}

      <h3>
        {editingName ? `Edit datasource "${editingName}"` : "Add new datasource"}
      </h3>
      <div className="kb-form">
        <label>
          name{" "}
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>
        <label>
          type{" "}
          <select
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
          >
            {datasources.map((d) => (
              <option key={d.type} value={d.type}>
                {d.type}
              </option>
            ))}
          </select>
        </label>
        <label className="kb-form-wide">
          options (JSON){" "}
          <textarea
            rows={6}
            value={form.optionsRaw}
            onChange={(e) => setForm({ ...form, optionsRaw: e.target.value })}
            spellCheck={false}
          />
        </label>
        <div className="kb-form-row">
          <button onClick={runTest} disabled={parsedOptions === null}>
            Test connection
          </button>
          <button onClick={runSave} disabled={parsedOptions === null}>
            {editingName ? "Save changes" : "Save as new config"}
          </button>
          {editingName && <button onClick={resetForm}>Cancel edit</button>}
        </div>
        {testResult && <pre className="kb-result">{testResult}</pre>}
      </div>

      <h3>Saved datasource configs</h3>
      <p className="kb-help">
        Configs persist on the server side at <code>~/.kb-server/datasources.json</code>.
        The active one is loaded on the next server start (UI-driven edits do not
        swap a running pipeline mid-flight; restart the desktop app to apply).
      </p>
      {saved.length === 0 ? (
        <p className="kb-help">No saved configs yet.</p>
      ) : (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>name</th>
              <th>type</th>
              <th>last tested</th>
              <th>saved at</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            {saved.map((cfg) => (
              <tr key={cfg.name} className={cfg.name === activeName ? "kb-row-active" : undefined}>
                <td>{cfg.name}{cfg.name === activeName ? " (active)" : ""}</td>
                <td>{cfg.type}</td>
                <td>{cfg.last_tested_at ?? "—"}</td>
                <td>{cfg.saved_at}</td>
                <td className="kb-actions">
                  <button onClick={() => runActivate(cfg.name)} disabled={cfg.name === activeName}>
                    Activate
                  </button>
                  <button onClick={() => startEdit(cfg)}>Edit</button>
                  <button onClick={() => runDelete(cfg.name)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {activeName !== null && (
        <p className="kb-help">
          Active: <strong>{activeName}</strong>{" "}
          <button onClick={runDeactivate}>Clear active</button>
        </p>
      )}

      <h3>Available datasource adapter types</h3>
      <ul>
        {datasources.map((d) => (
          <li key={d.type}>
            {d.type} — capabilities: {d.capabilities.join(", ") || "—"}
          </li>
        ))}
      </ul>
    </section>
  );
}
