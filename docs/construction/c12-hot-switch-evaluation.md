# C12 active 数据源热切换评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | replace 后新数据源立即被 import/search 使用；switch 端点构建 + 探活 + 替换 + 持久化 + 健康快照更新；404/400/503 错误语义清晰。 |
| 验证 | 5 | `test_controller.py` +1、`test_datasource_configs_api.py` +2；全量 174 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 164.54 kB。 |
| 范围纪律 | 5 | 只做 active 热切换；保留 Activate 的“下次启动”语义，未改既有契约（新增端点为纯增量）。 |
| 可靠性 | 5 | 黑板 `datasource_write` + `search` 锁避免在飞写入/检索中途替换；health 非 ok 拒绝切换；旧适配器 best-effort close。 |
| 可维护性 | 5 | 切换逻辑集中在 controller 与 datasources API；健康快照更新独立方法，不重置 started_at；桌面 IPC 单一来源。 |
| 可观测性 | 5 | `datasource.switched` 结构化日志；健康快照 active_datasource 反映新数据源；`/v1/health/ready` 缓存被清除。 |

## 证据

- `server/app/blackboard/control.py`：`replace_datasource` 在资源锁内替换。
- `server/app/api/datasources.py`：`POST /v1/datasources/active/{name}/switch`。
- `server/app/api/health.py`：`update_active_datasource`。
- `SettingsPage.tsx`：Switch now 按钮与提示。
- 实测：174 tests collected / 174 passed；Vite 164.54 kB JS / 39 modules；`feature_list.json` 25/25 pass。

## 遗留风险

- 热切换是显式人工触发；健康驱动自动 failover 尚未实现。
- 切换要求新配置 `health()` ok，但部分适配器 health 只做连接探活，不保证索引 schema 完全匹配；首次写入时仍可能报错。
- 旧适配器关闭是 best-effort，若远端连接卡住，close 可能阻塞切换完成。
