import React, { useCallback, useEffect, useMemo, useState } from "react";
import { kb } from "../lib/kb";
import type {
  BackupInfo,
  DatasourceConfigRecord,
  DatasourceInfo,
  HaSettings,
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
  const [haSettings, setHaSettings] = useState<HaSettings | null>(null);
  const [failoverText, setFailoverText] = useState<string>("");
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [backupBusy, setBackupBusy] = useState<boolean>(false);
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

  const refreshBackups = useCallback(async () => {
    try {
      setBackups(await kb.listBackups());
    } catch (e) {
      setToast({ kind: "error", message: `backup list failed: ${String(e)}` });
    }
  }, []);

  const refreshFailover = useCallback(async () => {
    try {
      setFailoverText((await kb.listFailover()).join(", "));
    } catch (e) {
      setToast({ kind: "error", message: `failover list failed: ${String(e)}` });
    }
  }, []);

  const refreshHaSettings = useCallback(async () => {
    try {
      setHaSettings(await kb.getHaSettings());
    } catch (e) {
      setToast({ kind: "error", message: `ha settings load failed: ${String(e)}` });
    }
  }, []);

  useEffect(() => {
    void refresh();
    void refreshBackups();
    void refreshFailover();
    void refreshHaSettings();
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

  async function runSwitch(name: string): Promise<void> {
    try {
      const cfg = await kb.switchDatasourceConfig(name);
      setActiveName(cfg.name);
      setToast({ kind: "ok", message: `switched active datasource to "${cfg.name}" without restart` });
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: `switch failed: ${String(e)}` });
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

  async function runCreateBackup(): Promise<void> {
    setBackupBusy(true);
    try {
      const b = await kb.createBackup();
      setToast({ kind: "ok", message: `backup created: ${b.name}` });
      await refreshBackups();
    } catch (e) {
      setToast({ kind: "error", message: `create backup failed: ${String(e)}` });
    } finally {
      setBackupBusy(false);
    }
  }

  async function runRestoreBackup(name: string): Promise<void> {
    if (!window.confirm(`Restore snapshot "${name}"? The server will stop and restart.`)) return;
    setBackupBusy(true);
    try {
      const r = await kb.restoreBackup(name);
      setToast({
        kind: "ok",
        message: `restored ${r.restored} file(s); pre-restore kept at ${r.pre_restore}`,
      });
      await refreshBackups();
    } catch (e) {
      setToast({ kind: "error", message: `restore failed: ${String(e)}` });
    } finally {
      setBackupBusy(false);
    }
  }

  async function runSaveFailover(): Promise<void> {
    const names = failoverText.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const saved = await kb.setFailover(names);
      setFailoverText(saved.join(", "));
      setToast({ kind: "ok", message: `failover order saved: ${saved.join(", ") || "none"}` });
    } catch (e) {
      setToast({ kind: "error", message: `save failover failed: ${String(e)}` });
    }
  }

  async function runClearFailover(): Promise<void> {
    try {
      await kb.clearFailover();
      setFailoverText("");
      setToast({ kind: "info", message: "failover order cleared" });
    } catch (e) {
      setToast({ kind: "error", message: `clear failover failed: ${String(e)}` });
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
        <strong>Activate</strong> persists the pointer for the next server start;
        <strong>Switch now</strong> hot-swaps the running datasource (waits for
        in-flight writes/searches, then applies immediately).
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
                  <button onClick={() => runSwitch(cfg.name)}>
                    Switch now
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

      <h3>HA Configuration</h3>
      {haSettings ? (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>parameter</th>
              <th>value</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>auto backup</td><td>{haSettings.backup_auto ? "on" : "off"}</td></tr>
            <tr><td>backup interval (h)</td><td>{haSettings.backup_interval_hours}</td></tr>
            <tr><td>backup retention</td><td>{haSettings.backup_keep}</td></tr>
            <tr><td>health monitor</td><td>{haSettings.health_monitor ? "on" : "off"}</td></tr>
            <tr><td>health monitor interval (s)</td><td>{haSettings.health_monitor_interval_seconds}</td></tr>
            <tr><td>failover</td><td>{haSettings.failover_enabled ? "on" : "off"}</td></tr>
            <tr><td>failover consecutive failures</td><td>{haSettings.failover_consecutive_failures}</td></tr>
            <tr><td>auto recover</td><td>{haSettings.failover_auto_recover ? "on" : "off"}</td></tr>
            <tr><td>recover consecutive checks</td><td>{haSettings.failover_recover_consecutive_checks}</td></tr>
          </tbody>
        </table>
      ) : (
        <p className="kb-help">Loading HA settings...</p>
      )}

      <h3>Failover order</h3>
      <p className="kb-help">
        Comma-separated saved config names. When the active datasource fails{" "}
        <code>KB_FAILOVER_CONSECUTIVE_FAILURES</code> consecutive health checks,
        the server switches to the first healthy name in this order.
      </p>
      <div className="kb-form">
        <label>
          failover names{" "}
          <input
            value={failoverText}
            onChange={(e) => setFailoverText(e.target.value)}
            placeholder="es-prod, mem"
          />
        </label>
        <div className="kb-form-row">
          <button onClick={runSaveFailover}>Save failover order</button>
          <button onClick={runClearFailover}>Clear</button>
        </div>
      </div>

      <h3>Backup & Restore</h3>
      <p className="kb-help">
        Snapshots live under <code>~/.kb-server/backups</code> (or{" "}
        <code>KB_BACKUP_DIR</code>). Restoring stops the Python service, copies
        the snapshot back, and restarts it; a pre-restore copy is kept in{" "}
        <code>.pre-restore</code>.
      </p>
      <div className="kb-form-row">
        <button onClick={runCreateBackup} disabled={backupBusy}>
          Create backup now
        </button>
      </div>
      {backups.length === 0 ? (
        <p className="kb-help">No snapshots yet.</p>
      ) : (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>snapshot</th>
              <th>created at</th>
              <th>files</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.name}>
                <td>{b.name}</td>
                <td>{b.created_at || "—"}</td>
                <td>{b.files.join(", ") || "—"}</td>
                <td className="kb-actions">
                  <button onClick={() => runRestoreBackup(b.name)} disabled={backupBusy}>
                    Restore
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
