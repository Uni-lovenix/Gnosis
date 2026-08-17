# C16 failover 恢复回切评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | `recover_primary` 只在主数据源健康时切回；已为主 / 无候选 / health 失败均 no-op；active 指针与健康快照同步。 |
| 验证 | 5 | `test_datasource_configs_api.py` +2；全量 188 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 165.98 kB（纯后端）。 |
| 范围纪律 | 5 | 只做恢复回切；未新增 API/UI，仅扩展监控与内部函数。 |
| 可靠性 | 5 | 连续 3 次健康才回切，避免抖动；切换复用黑板资源锁；`KB_FAILOVER_AUTO_RECOVER=false` 可保留“只 failover 不回切”。 |
| 可维护性 | 5 | 回切逻辑集中在 datasources API，监控只维护计数；failover 第一项即主数据源，无需额外配置字段。 |
| 可观测性 | 5 | `datasource.failover_recovered` 记录 from/to；active 指针与健康快照同步；RUNBOOK 明确参数。 |

## 证据

- `server/app/api/datasources.py`：`recover_primary`。
- `server/app/config/settings.py`：`failover_auto_recover` / `failover_recover_consecutive_checks`。
- `server/app/main.py`：`_health_monitor_loop` 连续健康触发回切。
- 实测：188 tests collected / 188 passed；Vite 165.98 kB JS / 39 modules；`feature_list.json` 29/29 pass。

## 遗留风险

- 自动回切只在服务运行且监控开启时发生；服务重启后会按 active 指针继续使用当前数据源。
- 探活只验证 `health()`，不验证完整 schema；若主库 schema 已变化，回切后首次写入可能报错。
- `KB_FAILOVER_AUTO_RECOVER=false` 关闭回切后，用户需手动 `Switch now` 回到主数据源。
