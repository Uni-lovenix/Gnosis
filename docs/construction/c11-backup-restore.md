# C11 备份/恢复闭环（迭代协议）

> 类别：C（构建迭代）。命中 `docs/PROCESS.md` 升级触发条件中的**触及安全边界**——恢复会向数据目录写回含凭证的 `datasources.json` 与 `tasks.db`，并由桌面主进程停/启 Python 子进程；因此本迭代必须出独立评估报告，不走 G 类自验。

## 迭代目标

把 C10 的“能备份”推进为“可一键恢复”：

1. 提供 `restore` 与 `list` CLI，恢复前自动为当前数据目录留一份 `.pre-restore` 快照。
2. 提供 `GET /v1/backups`（列表）与 `POST /v1/backups`（创建），让桌面端可发现快照。
3. 桌面端 Settings 新增 Backup & Restore 区块：创建备份、列出快照、一键恢复。
4. 恢复由桌面主进程编排：先停 Python 服务 → 执行 restore CLI → 再启动服务，避免覆盖正在使用的 SQLite。

## 迭代范围

### 1. `server/app/observability/backup.py`

- `list_backups(backup_root)`：按时间倒序返回快照目录，读 `manifest.json` 汇总 `name / path / created_at / files / source`。
- `restore_backup(backup_path, target_dir)`：
  - 仅接受 `kb-backup-*` 目录且必须含 `manifest.json`，否则 `ValueError`。
  - 先把当前数据目录备份到 `<target>/.pre-restore/`（复用 `backup_data_dir`，保留 3 份），再按 manifest 把文件复制回目标目录。
  - 返回 `{restored_files, pre_restore}`。
- CLI 扩展为子命令：默认 `backup`；新增 `list` 与 `restore <backup-path>`；旧调用方式 `python3 -m app.observability.backup` 保持创建备份。

### 2. `server/app/api/backups.py`

- `GET /v1/backups`：列出 `KB_BACKUP_DIR`（默认 `<data_dir>/backups`）下的快照。
- `POST /v1/backups`：创建一份快照，返回 `BackupInfo`。
- 不提供 HTTP restore 端点：恢复会替换正在使用的 SQLite，必须由桌面主进程停服后执行。

### 3. 桌面端

- `shared/types.ts` 新增 `BackupInfo` 与 `KBAPI.listBackups / createBackup / restoreBackup`。
- `api-client.ts` 实现 `listBackups` / `createBackup`。
- `main/index.ts`：
  - `listBackups` / `createBackup` 走 HTTP。
  - `restoreBackup(name)`：查快照路径 → `server.stop()` → `python3 -m app.observability.backup restore <path>` → `server.start()` → 返回结果；任何失败都会在 finally 中重启服务。
- `SettingsPage.tsx`：新增 Backup & Restore 区块，含“Create backup now”、快照列表、每个快照的 Restore 按钮与确认对话框。

## 实施计划

1. 先落盘本协议。
2. 扩展 backup 模块（list / restore / CLI）。
3. 新增 backups API 并在 `main.py` 注册。
4. 桌面类型、ApiClient、IPC handler、Settings UI 与样式。
5. 补测试（backup 模块 3 项 + API 2 项），跑全量 pytest / tsc / Vite build。
6. 更新文档与 harness（API / RUNBOOK / feature_list / progress / session-handoff / evaluator-rubric + C11 评估）。

## 交付物

- `server/app/observability/backup.py`：list / restore / CLI。
- `server/app/api/backups.py`：`GET /v1/backups` + `POST /v1/backups`。
- `server/app/main.py`：注册 backups router。
- `desktop/src/shared/types.ts`、`desktop/src/main/api-client.ts`、`desktop/src/main/index.ts`、`desktop/src/preload/index.ts`、`desktop/src/renderer/pages/SettingsPage.tsx`、`desktop/src/renderer/styles.css`。
- 测试：`server/tests/test_backup.py` 扩展 + `server/tests/api/test_backups_api.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/KNOWN_ISSUES.md`、`docs/elaboration/01-architecture-baseline.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c11-backup-restore.md` + `c11-backup-restore-evaluation.md`。

## 退出标准

- [x] `restore_backup` 能恢复 JSON + SQLite，并先留 `.pre-restore` 快照；非法路径拒绝。
- [x] `list_backups` 返回 manifest 汇总；CLI `list` / `restore` 可执行。
- [x] `GET /v1/backups` / `POST /v1/backups` 通过 API 测试。
- [x] 桌面端可创建备份、列出快照、确认后恢复，且恢复过程停/启服务。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C11 评估报告由评估者角色出具。

## 决策记录

- **restore 不放 HTTP**：SQLite 正在被服务占用时覆盖会损坏数据；由桌面主进程停服后执行，安全边界更清晰。
- **恢复前自动留 `.pre-restore`**：误恢复可回退，符合“可恢复的高可用”而不是“不可逆覆盖”。
- **默认 `KB_BACKUP_DIR` 保留 `<data_dir>/backups`**：与 C10 一致，避免把备份目录写到系统临时目录导致用户找不到。
