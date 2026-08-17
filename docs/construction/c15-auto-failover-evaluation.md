# C15 健康驱动自动 failover 评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | failover 顺序存取正确；`failover_datasource` 按序 build + 探活 + 热切换 + 持久化 active；无候选保持现状；监控连续失败阈值触发。 |
| 验证 | 5 | store +3 / API +3；全量 186 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 165.98 kB。 |
| 范围纪律 | 5 | 只做自动 failover；原有 Activate / Switch now 语义不变，新增 failover API 为纯增量。 |
| 可靠性 | 5 | 切换复用黑板资源锁；健康检查门槛避免切到坏数据源；`datasource.failover_exhausted` 防止无候选时反复误切。 |
| 可维护性 | 5 | failover 顺序与配置同源；`failover_datasource` 集中在 datasources API；监控循环只负责计数与触发。 |
| 可观测性 | 5 | `datasource.failover` / `failover_exhausted` 日志；active 指针与健康快照同步更新；桌面可查看/编辑顺序。 |

## 证据

- `server/app/observability/datasource_store.py`：`get_failover` / `set_failover`。
- `server/app/api/datasources.py`：`GET/PUT/DELETE /v1/datasources/failover` + `failover_datasource`。
- `server/app/main.py`：`_health_monitor_loop` 连续失败触发。
- `SettingsPage.tsx`：Failover order 编辑。
- 实测：186 tests collected / 186 passed；Vite 165.98 kB JS / 39 modules；`feature_list.json` 28/28 pass。

## 遗留风险

- failover 切换后不自动切回主数据源；主库恢复后需手动 `Switch now`。
- 探活只验证 `health()`，不验证完整 schema/写入能力；首次写入仍可能报错。
- `datasources.json` 顶层 `failover` 是可选字段；旧文件自动视为空列表，不触发迁移。
