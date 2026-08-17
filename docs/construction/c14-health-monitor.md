# C14 运行期健康监控（迭代协议）

> 类别：C（构建迭代）。本迭代新增服务后台健康探活与运行态健康快照，属于新增运行时行为，需独立评估报告。

## 迭代目标

让 `/v1/health` 反映**当前**数据源 / embedder 健康，而不是只有启动时降级快照：

1. 后台每 `KB_HEALTH_MONITOR_INTERVAL_SECONDS`（默认 30s）探活 datasource + embedder，结果写入 health runtime。
2. `/v1/health` 的 `degraded` 与 `active_datasource.ok` 使用最近探活结果；`/v1/health/ready` 也会顺手刷新该快照。
3. 桌面端每 15s 轮询 `/v1/health`，降级横幅随运行态变化（远端数据源中断后可见，恢复后消失）。

## 迭代范围

### 1. health 模块

`RuntimeState` 新增：

- `datasource_ok: bool | None`
- `datasource_message: str | None`
- `datasource_latency_ms: float | None`
- `embedder_ok: bool | None`
- `embedder_message: str | None`
- `last_probe_at: str | None`

新增：

- `update_dependency_health(...)`：写探活结果，供后台监控与 `/ready` 复用。
- `refresh_runtime_health()`：执行 `_probe_checks()` 并调用 `update_dependency_health`，返回 `checks`。
- `/v1/health` 响应新增 `embedder_ok`、`last_probe_at`，`active_datasource` 填充 `ok / latency_ms / message`。

### 2. 服务后台监控

`server/app/main.py`：

- `KB_HEALTH_MONITOR`（默认 `true`）、`KB_HEALTH_MONITOR_INTERVAL_SECONDS`（默认 `30`）。
- startup 启动 `_health_monitor_loop`，shutdown 取消。
- 每次探活后记录状态变化：`health.monitor_degraded` / `health.monitor_recovered`。

### 3. 桌面端

- `shared/types` / `api-client` 扩展 `HealthInfo`（`embedder_ok` / `last_probe_at`）。
- `App.tsx` 每 15s 调用 `checkHealth`，让降级横幅实时刷新。
- 横幅文案区分：embedder fallback / active datasource 不可用 / 依赖整体降级。

## 实施计划

1. 先落盘本协议。
2. health 模块扩展 + `refresh_runtime_health`。
3. main.py 后台监控循环。
4. 桌面类型 + 轮询 + 横幅优化。
5. 补测试（health 快照 / ready 刷新 / 降级传播），跑全量验证。
6. 更新文档与 harness + C14 评估。

## 交付物

- `server/app/api/health.py`：依赖健康状态 + `refresh_runtime_health`。
- `server/app/config/settings.py`：`health_monitor` / `health_monitor_interval_seconds`。
- `server/app/main.py`：后台健康监控。
- `desktop/src/shared/types.ts`、`desktop/src/main/api-client.ts`、`desktop/src/renderer/App.tsx`。
- 测试：`server/tests/api/test_health_api.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/elaboration/01-architecture-baseline.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c14-health-monitor.md` + `c14-health-monitor-evaluation.md`。

## 退出标准

- [x] `/v1/health` 使用最近探活结果；`/ready` 探活后 `/health` 立即反映。
- [x] 后台监控默认开启，测试 conftest 固定关闭。
- [x] 桌面端轮询并实时更新降级横幅。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C14 评估报告由评估者角色出具。

## 决策记录

- **后台探活与 `/ready` 共用一套 checks**：避免两套逻辑漂移；TTL 缓存只服务主动调用，后台按固定间隔强制刷新。
- **监控不自动 failover**：C12 提供手动热切换，C14 只让降级可见；自动 failover 留作后续。
- **桌面 15s 轮询**：低于后端 30s 探活周期，能及时展示状态变化，又不给本地 API 造成压力。
