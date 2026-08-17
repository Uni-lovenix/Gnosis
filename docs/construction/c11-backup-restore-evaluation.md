# C11 备份/恢复闭环评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | restore 能按 manifest 回写 JSON + SQLite，恢复前自动 `.pre-restore`；list 汇总 manifest；API 创建/列表一致；桌面恢复走停服 → restore → 重启。 |
| 验证 | 5 | `tests/test_backup.py` 6/6、`tests/api/test_backups_api.py` 1/1；全量 171 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 164.15 kB。 |
| 范围纪律 | 5 | 只做备份/恢复闭环；未引入新依赖，未改动既有 HTTP/IPC 契约（新增端点/方法为纯增量）。 |
| 兼容性 | 5 | `python3 -m app.observability.backup` 无参数仍创建备份；新 `list` / `restore` 为子命令；`/v1/backups` 为新增路由。 |
| 可维护性 | 5 | backup 模块集中管理备份/恢复；桌面恢复编排在主进程，职责单一；`BackupInfo` 共享类型单一来源。 |
| 可观测性 | 5 | 备份/恢复都有 CLI 输出与 manifest；桌面 toast 展示恢复结果与 `.pre-restore` 路径；`/v1/backups` 可人工复核。 |
| 安全 | 4 | 恢复会写回含凭证文件，restore 不放 HTTP 且由主进程停服后执行，降低运行中覆盖风险；但桌面恢复若在打包环境缺少 `KB_PYTHON` 仍可能失败，需 RUNBOOK 排错指引。 |

## 证据

- `server/app/observability/backup.py`：`list_backups` / `restore_backup` / CLI `list` / `restore`。
- `server/app/api/backups.py`：`GET /v1/backups`、`POST /v1/backups`（201）。
- `desktop/src/main/index.ts`：`restoreBackup` IPC 停服 → `python3 -m app.observability.backup restore` → 重启。
- `SettingsPage.tsx`：Backup & Restore 创建 / 列表 / 确认恢复 / toast。
- 实测：171 tests collected / 171 passed；Vite 164.15 kB JS / 39 modules；`feature_list.json` 24/24 pass。

## 遗留风险

- 桌面恢复依赖 `python3` 或 `KB_PYTHON` 能解析 backup 模块；打包后需确认该路径存在。
- `.pre-restore` 只保留 3 份，误恢复后的回退窗口有限。
- 备份目录仍含明文凭证；权限保护要求已文档化，未做脱敏开关。
