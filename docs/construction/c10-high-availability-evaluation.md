# C10 高可用基础能力评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | request_id 中间件、健康快照/readiness、备份 CLI、桌面降级横幅四项交付均通过专项测试；167 项全量测试无回归。 |
| 验证 | 5 | `tests/api/test_health_api.py` 4/4、`tests/test_backup.py` 3/3、`tests/test_request_context.py` 2/2；`ruff` 0 errors；desktop `check`/`lint` 0 errors；Vite 162.31 kB。 |
| 范围纪律 | 5 | 只做协议列出的高可用四项；未引入新依赖，未改既有 HTTP/IPC 契约（健康响应为扩展字段）。 |
| 兼容性 | 5 | `/v1/health` 旧字段全部保留，新增字段为纯增量；desktop 心跳仍用 `/v1/health`，新增 `/v1/health/ready` 不改变任何既有调用方。 |
| 可维护性 | 5 | 中间件、健康状态、备份各一个职责单一模块；桌面类型仍以 `shared/types.ts` 为单一源。 |
| 可观测性 | 5 | `http.request` + `X-Request-Id` 补齐追踪维度；`health.readiness_degraded` 记录依赖失败；`/v1/health/ready` 可人工复核。 |
| 安全 | 4 | 备份会复制含凭证的 `datasources.json`，已在 RUNBOOK 与模块 docstring 明示权限要求，但仍建议后续提供 `KB_BACKUP_EXCLUDE_CREDENTIALS` 脱敏选项（默认关闭，保证可恢复）。 |

## 证据

- `server/app/api/middleware.py`：生成/透传 `X-Request-Id`，响应头回写，structlog contextvars 绑定，`http.request` 日志含 `request_id / method / path / status_code / duration_ms`。
- `server/app/api/health.py`：`/v1/health` 返回 `degraded / embedder_backend / embedder_fallback / active_datasource / started_at / uptime_seconds`；`/v1/health/ready` 15s TTL 探活 datasource + embedder。
- `server/app/observability/backup.py`：SQLite 官方 backup API 在线快照，JSON 复制，`manifest.json`，`KB_BACKUP_KEEP` 保留策略。
- 桌面端：`HealthInfo` 扩展 + `.kb-banner-degraded`；降级状态不再静默。
- 实测：167 tests collected / 167 passed；Vite 162.31 kB JS / 39 modules；`feature_list.json` 23/23 pass。

## 遗留风险

- 备份目录含明文凭证；已文档化，未做脱敏开关。
- `/v1/health/ready` 的探活结果有 15s TTL，远端刚恢复后最多延迟 15s 反映。
- `http.request` 会记录 health 心跳，日志量略增；个人本机流量下可接受。
