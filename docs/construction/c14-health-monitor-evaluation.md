# C14 运行期健康监控评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | `/ready` 探活后 `/health` 立即反映；运行期 datasource 失败会传播为 degraded + active_datasource.ok=false；后台监控状态变化日志正确。 |
| 验证 | 5 | `test_health_api.py` 6/6（新增 2）；全量 180 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 164.72 kB。 |
| 范围纪律 | 5 | 只做运行期健康快照与桌面轮询；未新增 HTTP/IPC 契约（健康响应为扩展字段）。 |
| 可靠性 | 5 | 后台探活异常只打日志不中断服务；`/ready` 与后台共用同一 checks 逻辑；shutdown 取消任务。 |
| 可维护性 | 5 | 健康状态集中在 health 模块，`refresh_runtime_health` 复用 `_probe_checks`；conftest 明确关闭测试后台任务。 |
| 可观测性 | 5 | `health.monitor_degraded` / `recovered` 记录状态转移；`/v1/health` 带 `last_probe_at`；桌面横幅随轮询实时更新。 |

## 证据

- `server/app/api/health.py`：依赖健康状态 + `update_dependency_health` + `refresh_runtime_health`。
- `server/app/main.py`：`_health_monitor_loop` + startup/shutdown 生命周期。
- `desktop/src/renderer/App.tsx`：15s 轮询 + 降级横幅文案。
- 实测：180 tests collected / 180 passed；Vite 164.72 kB JS / 39 modules；`feature_list.json` 27/27 pass。

## 遗留风险

- 监控只报告降级，不自动 failover；用户仍需通过 C12 “Switch now” 切换。
- 桌面 15s 轮询略快于后端 30s 探活，状态变化最多延迟约 30s 可见。
- `embedder.health()` 默认会执行一次真实嵌入；远端 embedder 若较慢，探活超时仍按降级处理。
