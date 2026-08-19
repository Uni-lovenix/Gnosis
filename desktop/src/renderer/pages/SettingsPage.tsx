import React, { useCallback, useEffect, useMemo, useState } from "react";
import { kb } from "../lib/kb";
import { formatError } from "../lib/errors";
import { ConfirmDialog } from "../components/ConfirmDialog";
import type {
  BackupInfo,
  DatasourceConfigRecord,
  DatasourceInfo,
  DatasourceSchema,
  DatasourceSchemaField,
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

const EMPTY_FORM: FormState = {
  name: "vec-local",
  type: "vector",
  optionsRaw: '{\n  "backend": "memory",\n  "dim": 64\n}',
};

function schemaDefaults(schema: DatasourceSchema | undefined): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const field of schema?.fields ?? []) {
    if (field.default !== undefined) out[field.key] = field.default;
  }
  return out;
}

export function SettingsPage({ datasources }: Props): JSX.Element {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [advancedJson, setAdvancedJson] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testOk, setTestOk] = useState(false);
  const [schemas, setSchemas] = useState<Record<string, DatasourceSchema>>({});
  const [saved, setSaved] = useState<DatasourceConfigRecord[]>([]);
  const [activeName, setActiveName] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [haSettings, setHaSettings] = useState<HaSettings | null>(null);
  const [failoverText, setFailoverText] = useState<string>("");
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [backupBusy, setBackupBusy] = useState<boolean>(false);
  const [restoreMessage, setRestoreMessage] = useState<string | null>(null);
  const [pendingDeleteName, setPendingDeleteName] = useState<string | null>(null);
  const [pendingRestoreName, setPendingRestoreName] = useState<string | null>(null);
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
      setToast({ kind: "error", message: formatError(e, "配置加载失败") });
    }
  }, []);

  const refreshBackups = useCallback(async () => {
    try {
      setBackups(await kb.listBackups());
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "备份列表加载失败") });
    }
  }, []);

  const refreshFailover = useCallback(async () => {
    try {
      setFailoverText((await kb.listFailover()).join(", "));
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "Failover 列表加载失败") });
    }
  }, []);

  const refreshHaSettings = useCallback(async () => {
    try {
      setHaSettings(await kb.getHaSettings());
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "HA 配置加载失败") });
    }
  }, []);

  useEffect(() => {
    void refresh();
    void refreshBackups();
    void refreshFailover();
    void refreshHaSettings();
    void kb.listDatasourceSchemas().then(setSchemas).catch(() => setSchemas({}));
  }, [refresh, refreshBackups, refreshFailover, refreshHaSettings]);

  const parsedOptions = useMemo<Record<string, unknown> | null>(() => {
    if (!form.optionsRaw.trim()) return {};
    try {
      return JSON.parse(form.optionsRaw) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [form.optionsRaw]);

  const currentSchema = schemas[form.type];

  function startEdit(cfg: DatasourceConfigRecord): void {
    setEditingName(cfg.name);
    setAdvancedJson(false);
    setForm({
      name: cfg.name,
      type: cfg.type,
      optionsRaw: JSON.stringify(cfg.options, null, 2),
    });
    setTestResult(null);
    setTestOk(false);
    setToast(null);
  }

  function resetForm(): void {
    setEditingName(null);
    setForm(EMPTY_FORM);
    setAdvancedJson(false);
    setTestResult(null);
    setTestOk(false);
  }

  function changeType(nextType: string): void {
    const defaults = schemaDefaults(schemas[nextType]);
    setForm({
      ...form,
      type: nextType,
      optionsRaw:
        Object.keys(defaults).length > 0 ? JSON.stringify(defaults, null, 2) : form.optionsRaw,
    });
    setTestResult(null);
    setTestOk(false);
  }

  function updateField(field: DatasourceSchemaField, value: unknown): void {
    const current = parsedOptions ?? {};
    setForm({
      ...form,
      optionsRaw: JSON.stringify({ ...current, [field.key]: value }, null, 2),
    });
    setTestResult(null);
    setTestOk(false);
  }

  function fieldValue(field: DatasourceSchemaField): unknown {
    return (parsedOptions ?? {})[field.key];
  }

  async function runTest(): Promise<void> {
    if (parsedOptions === null) {
      setTestResult("配置 JSON 无效，请检查括号与引号。");
      setTestOk(false);
      return;
    }
    try {
      const r = await kb.testDatasource({
        name: form.name || "test",
        type: form.type,
        options: parsedOptions,
      });
      setTestResult(
        `${r.ok ? "连接成功" : "连接失败"} · 延迟 ${r.latency_ms?.toFixed(2) ?? "—"}ms${
          r.message ? ` · ${r.message}` : ""
        }`,
      );
      setTestOk(r.ok);
    } catch (e) {
      setTestResult(formatError(e, "连接测试失败"));
      setTestOk(false);
    }
  }

  async function runSave(): Promise<void> {
    if (parsedOptions === null) {
      setToast({ kind: "error", message: "配置 JSON 无效，请检查括号与引号后重试。" });
      return;
    }
    if (!form.name.trim()) {
      setToast({ kind: "error", message: "请填写配置名称。" });
      return;
    }
    try {
      const savedCfg = await kb.saveDatasourceConfig({
        name: form.name.trim(),
        type: form.type,
        options: parsedOptions,
      });
      if (testOk) {
        try {
          await kb.markDatasourceTested(savedCfg.name);
        } catch {
          // The save succeeded; marking tested is a best-effort UX enhancement.
        }
      }
      setToast({
        kind: "ok",
        message: editingName ? `已更新“${form.name.trim()}”。` : `已保存“${form.name.trim()}”。`,
      });
      resetForm();
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "保存失败") });
    }
  }

  async function runActivate(name: string): Promise<void> {
    try {
      await kb.activateDatasourceConfig(name);
      setActiveName(name);
      setToast({ kind: "ok", message: `已将“${name}”设为下次启动激活的数据源。` });
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "激活失败") });
    }
  }

  async function runSwitch(name: string): Promise<void> {
    try {
      const cfg = await kb.switchDatasourceConfig(name);
      setActiveName(cfg.name);
      setToast({ kind: "ok", message: `已热切换到“${cfg.name}”，无需重启。` });
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "热切换失败") });
    }
  }

  async function runDeactivate(): Promise<void> {
    try {
      await kb.deactivateDatasource();
      setActiveName(null);
      setToast({ kind: "info", message: "已清除激活指向；下次启动将回退到内存向量库。" });
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "清除激活失败") });
    }
  }

  async function confirmDelete(name: string): Promise<void> {
    try {
      await kb.deleteDatasourceConfig(name);
      if (editingName === name) resetForm();
      setToast({ kind: "info", message: `已删除“${name}”。` });
      await refresh();
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "删除失败") });
    } finally {
      setPendingDeleteName(null);
    }
  }

  async function runCreateBackup(): Promise<void> {
    setBackupBusy(true);
    setRestoreMessage(null);
    try {
      const b = await kb.createBackup();
      setToast({ kind: "ok", message: `备份已创建：${b.name}` });
      await refreshBackups();
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "创建备份失败") });
    } finally {
      setBackupBusy(false);
    }
  }

  async function confirmRestore(name: string): Promise<void> {
    setBackupBusy(true);
    setRestoreMessage("正在停止服务并恢复快照，请稍候…");
    try {
      const r = await kb.restoreBackup(name);
      setRestoreMessage(`已恢复 ${r.restored} 个文件。可回到检索页确认结果。`);
      setToast({ kind: "ok", message: "恢复完成，服务已重新启动。" });
      await refreshBackups();
    } catch (e) {
      setRestoreMessage(null);
      setToast({ kind: "error", message: formatError(e, "恢复失败") });
    } finally {
      setBackupBusy(false);
      setPendingRestoreName(null);
    }
  }

  async function runSaveFailover(): Promise<void> {
    const names = failoverText.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const savedNames = await kb.setFailover(names);
      setFailoverText(savedNames.join(", "));
      setToast({ kind: "ok", message: `已保存 Failover 顺序：${savedNames.join(", ") || "无"}` });
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "保存 Failover 失败") });
    }
  }

  async function runClearFailover(): Promise<void> {
    try {
      await kb.clearFailover();
      setFailoverText("");
      setToast({ kind: "info", message: "已清空 Failover 顺序。" });
    } catch (e) {
      setToast({ kind: "error", message: formatError(e, "清空 Failover 失败") });
    }
  }

  return (
    <section className="kb-page">
      <h2>设置</h2>

      {toast && (
        <div className={`kb-toast kb-toast-${toast.kind}`} role={toast.kind === "error" ? "alert" : "status"}>
          {toast.message}
        </div>
      )}

      <h3>{editingName ? `编辑数据源“${editingName}”` : "添加数据源"}</h3>
      <div className="kb-form">
        <label>
          名称
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="例如 es-prod"
          />
        </label>
        <label>
          类型
          <select value={form.type} onChange={(e) => changeType(e.target.value)}>
            {datasources.map((d) => (
              <option key={d.type} value={d.type}>
                {schemas[d.type]?.label ?? d.type}
              </option>
            ))}
          </select>
        </label>

        {currentSchema && (
          <div className="kb-form-row">
            <button
              type="button"
              className={!advancedJson ? "kb-mode-active" : ""}
              onClick={() => setAdvancedJson(false)}
            >
              表单模式
            </button>
            <button
              type="button"
              className={advancedJson ? "kb-mode-active" : ""}
              onClick={() => setAdvancedJson(true)}
            >
              高级 JSON
            </button>
          </div>
        )}

        {!advancedJson && currentSchema && (
          <div className="kb-schema-fields">
            {currentSchema.fields.map((field) => (
              <label key={field.key}>
                <span>
                  {field.label}
                  {field.required ? " *" : ""}
                </span>
                {field.type === "boolean" ? (
                  <input
                    type="checkbox"
                    checked={Boolean(fieldValue(field))}
                    onChange={(e) => updateField(field, e.target.checked)}
                  />
                ) : field.type === "select" ? (
                  <select
                    value={String(fieldValue(field) ?? field.default ?? "")}
                    onChange={(e) => updateField(field, e.target.value)}
                  >
                    {field.options.map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                ) : field.type === "list" ? (
                  <textarea
                    rows={2}
                    value={JSON.stringify(fieldValue(field) ?? field.default ?? [])}
                    onChange={(e) => {
                      try {
                        updateField(field, JSON.parse(e.target.value));
                      } catch {
                        updateField(field, e.target.value);
                      }
                    }}
                    spellCheck={false}
                  />
                ) : (
                  <input
                    type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
                    value={String(fieldValue(field) ?? field.default ?? "")}
                    onChange={(e) =>
                      updateField(
                        field,
                        field.type === "number" ? Number(e.target.value) : e.target.value,
                      )
                    }
                    autoComplete="off"
                  />
                )}
                {field.help && <small>{field.help}</small>}
              </label>
            ))}
          </div>
        )}

        {(advancedJson || !currentSchema) && (
          <label className="kb-form-wide">
            options（JSON）
            <textarea
              rows={8}
              value={form.optionsRaw}
              onChange={(e) => {
                setForm({ ...form, optionsRaw: e.target.value });
                setTestResult(null);
                setTestOk(false);
              }}
              spellCheck={false}
            />
          </label>
        )}

        <div className="kb-form-row">
          <button onClick={runTest} disabled={parsedOptions === null}>
            测试连接
          </button>
          <button onClick={runSave} disabled={parsedOptions === null}>
            {editingName ? "保存修改" : "保存为配置"}
          </button>
          {editingName && <button onClick={resetForm}>取消编辑</button>}
        </div>
        {testResult && (
          <pre className={`kb-result ${testOk ? "kb-result-ok" : "kb-result-error"}`}>
            {testResult}
          </pre>
        )}
      </div>

      <h3>已保存的数据源配置</h3>
      <p className="kb-help">
        配置保存在服务端数据目录的 <code>datasources.json</code>。激活表示下次启动生效；
        立即切换会热替换当前运行中的数据源。
      </p>
      {saved.length === 0 ? (
        <p className="kb-help">还没有保存配置。</p>
      ) : (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>最近测试</th>
              <th>保存时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {saved.map((cfg) => (
              <tr key={cfg.name} className={cfg.name === activeName ? "kb-row-active" : undefined}>
                <td>{cfg.name}{cfg.name === activeName ? "（当前激活）" : ""}</td>
                <td>{cfg.type}</td>
                <td>{cfg.last_tested_at ? `✓ ${cfg.last_tested_at}` : "—"}</td>
                <td>{cfg.saved_at}</td>
                <td className="kb-actions">
                  <button onClick={() => runActivate(cfg.name)} disabled={cfg.name === activeName}>
                    激活
                  </button>
                  <button onClick={() => runSwitch(cfg.name)}>立即切换</button>
                  <button onClick={() => startEdit(cfg)}>编辑</button>
                  <button onClick={() => setPendingDeleteName(cfg.name)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {activeName !== null && (
        <p className="kb-help">
          当前激活：<strong>{activeName}</strong>{" "}
          <button onClick={runDeactivate}>清除激活</button>
        </p>
      )}

      <h3>HA 配置</h3>
      {haSettings ? (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>参数</th>
              <th>值</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>自动备份</td><td>{haSettings.backup_auto ? "开" : "关"}</td></tr>
            <tr><td>备份间隔（小时）</td><td>{haSettings.backup_interval_hours}</td></tr>
            <tr><td>备份保留数量</td><td>{haSettings.backup_keep}</td></tr>
            <tr><td>健康监控</td><td>{haSettings.health_monitor ? "开" : "关"}</td></tr>
            <tr><td>健康监控间隔（秒）</td><td>{haSettings.health_monitor_interval_seconds}</td></tr>
            <tr><td>自动 Failover</td><td>{haSettings.failover_enabled ? "开" : "关"}</td></tr>
            <tr><td>Failover 连续失败阈值</td><td>{haSettings.failover_consecutive_failures}</td></tr>
            <tr><td>自动回切</td><td>{haSettings.failover_auto_recover ? "开" : "关"}</td></tr>
            <tr><td>回切连续健康检查</td><td>{haSettings.failover_recover_consecutive_checks}</td></tr>
          </tbody>
        </table>
      ) : (
        <p className="kb-help">正在加载 HA 配置…</p>
      )}

      <h3>Failover 顺序</h3>
      <p className="kb-help">
        逗号分隔已保存的配置名。active 数据源连续健康检查失败时，服务会按此顺序切换到第一个健康的数据源。
      </p>
      <div className="kb-form">
        <label>
          Failover 名称
          <input
            value={failoverText}
            onChange={(e) => setFailoverText(e.target.value)}
            placeholder="es-prod, mem"
          />
        </label>
        <div className="kb-form-row">
          <button onClick={runSaveFailover}>保存 Failover 顺序</button>
          <button onClick={runClearFailover}>清空</button>
        </div>
      </div>

      <h3>备份与恢复</h3>
      <p className="kb-help">
        快照保存在备份目录。恢复会停止 Python 服务、回写快照并自动重启；恢复前会保留一份 pre-restore 副本。
      </p>
      <div className="kb-form-row">
        <button onClick={runCreateBackup} disabled={backupBusy}>
          立即创建备份
        </button>
      </div>
      {restoreMessage && <p className="kb-help" role="status">{restoreMessage}</p>}
      {backups.length === 0 ? (
        <p className="kb-help">还没有快照。</p>
      ) : (
        <table className="kb-configs">
          <thead>
            <tr>
              <th>快照</th>
              <th>创建时间</th>
              <th>文件</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.name}>
                <td>{b.name}</td>
                <td>{b.created_at || "—"}</td>
                <td>{b.files.join(", ") || "—"}</td>
                <td className="kb-actions">
                  <button onClick={() => setPendingRestoreName(b.name)} disabled={backupBusy}>
                    恢复
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>可用的数据源类型</h3>
      <ul>
        {datasources.map((d) => (
          <li key={d.type}>
            {schemas[d.type]?.label ?? d.type} — 能力：{d.capabilities.map(capabilityLabel).join(", ") || "—"}
          </li>
        ))}
      </ul>

      {pendingDeleteName && (
        <ConfirmDialog
          title="删除数据源配置"
          body={
            <>
              删除后配置不可恢复；已写入数据源的数据不受影响。
              <br />
              请确认要删除“{pendingDeleteName}”。
            </>
          }
          confirmLabel="删除"
          matchText={pendingDeleteName}
          onConfirm={() => void confirmDelete(pendingDeleteName)}
          onCancel={() => setPendingDeleteName(null)}
        />
      )}
      {pendingRestoreName && (
        <ConfirmDialog
          title="恢复备份"
          body={
            <>
              恢复会停止 Python 服务并回写数据目录，完成后自动重启。
              <br />
              请确认恢复快照“{pendingRestoreName}”。
            </>
          }
          confirmLabel="恢复"
          matchText={pendingRestoreName}
          busy={backupBusy}
          onConfirm={() => void confirmRestore(pendingRestoreName)}
          onCancel={() => setPendingRestoreName(null)}
        />
      )}
    </section>
  );
}

function capabilityLabel(capability: string): string {
  const labels: Record<string, string> = {
    chunk_list: "浏览切片",
    dump: "数据迁移导出",
    metadata_filter: "元数据过滤",
    delete_by_filter: "按条件删除",
    bm25_hybrid: "BM25 混合检索",
    small_dataset_only: "仅适合小数据集",
    scan_limit_risk: "扫描上限提示",
  };
  return labels[capability] ?? capability;
}
