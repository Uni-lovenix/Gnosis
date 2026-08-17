# C10 高可用基础能力（迭代协议）

> 类别：C（构建迭代）。命中 `docs/PROCESS.md` 升级触发条件中的**触及安全边界**——新增备份会复制 `datasources.json`（内含数据源凭证），并扩展文件系统访问范围；因此本迭代必须出独立评估报告，不走 G 类自验。

## 迭代目标

把“高可用”从零散能力（watchdog / 重试退避 / 健康检查）收敛为一组可观测、可恢复的基础设施：

1. 每个 HTTP 请求有 `request_id`，后端所有日志可跨请求关联（补 H1 发现的运行时追踪缺口）。
2. `/v1/health` 从“存活探针”升级为“状态快照”，新增依赖感知的 `/v1/health/ready`。
3. 提供数据目录一致性备份 CLI，SQLite 走 `sqlite3.Connection.backup()`，避免热备份半截文件。
4. 桌面端在服务降级（embedder fallback / 无数据源 / 数据源探活失败）时给出可见横幅。

## 迭代范围

### 1. 请求关联（`server/app/api/middleware.py`）

- 中间件读取或生成 `X-Request-Id`，回写响应头，并用 `structlog.contextvars` 绑定 `request_id / method / path`。
- 每次请求结束打一条 `http.request` 结构化日志（`request_id / method / path / status_code / duration_ms`）。
- 不做破坏性契约变更；现有 API 与 IPC 不动。

### 2. 健康检查（`server/app/api/health.py`）

- `GET /v1/health` 保持快速存活探针，扩展字段：`degraded / started_at / uptime_seconds / embedder_backend / embedder_fallback / active_datasource / data_dir`。
- 新增 `GET /v1/health/ready`：带 15s TTL 缓存，逐一探活 `datasource` 与 `embedder`，返回 `checks`。
- `main.py` 在组件装配完成后调用 `set_runtime_state(...)`，让降级事实（embedder fallback / 无 active 数据源）进入健康快照。

### 3. 备份（`server/app/observability/backup.py`）

- `backup_data_dir(source, backup_root, keep)`：SQLite 文件用官方 backup API 做一致性快照，JSON/其它文件直接复制，写 `manifest.json`，按 `keep` 保留最近 N 份。
- CLI：`python3 -m app.observability.backup`，默认 `KB_DATA_DIR` / `KB_BACKUP_DIR` / `KB_BACKUP_KEEP`。
- 安全边界：备份内含 `datasources.json` 凭证，文档明确要求按数据目录同等权限保护，禁止提交到公开仓库。

### 4. 桌面降级提示

- `HealthInfo` 类型扩展健康字段；`useAppState` 保存最近一次健康快照。
- `App.tsx` 在 `health.degraded` 时渲染 `.kb-banner-degraded`，文案给出可执行动作（启动 Ollama / 配置 active 数据源）。

## 实施计划

1. 先落盘本协议。
2. 实现请求中间件并注册到 `create_app()`。
3. 重构健康 API 并接入 `main.py` 运行时状态。
4. 实现备份模块 + CLI + 单测。
5. 更新桌面类型、状态、横幅与样式。
6. 补测试、文档（API / RUNBOOK / KNOWN_ISSUES / feature_list / progress / session-handoff / evaluator-rubric）。

## 交付物

- `server/app/api/middleware.py`：请求关联中间件。
- `server/app/api/health.py`：健康快照 + readiness 检查。
- `server/app/observability/backup.py`：一致性备份 CLI。
- `server/app/main.py`：注册中间件 + 运行时状态。
- `desktop/src/{shared/types.ts,main/api-client.ts,renderer/lib/state.ts,renderer/App.tsx,renderer/styles.css}`：降级横幅。
- 测试：`server/tests/api/test_health_api.py`、`server/tests/test_request_context.py`、`server/tests/test_backup.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/KNOWN_ISSUES.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c10-high-availability-evaluation.md`。

## 退出标准

- [x] 每个请求有 `X-Request-Id` 响应头，且 `http.request` 日志含同一 `request_id`。
- [x] `/v1/health` 返回降级状态字段；`/v1/health/ready` 返回 datasource / embedder 探活结果。
- [x] 备份 CLI 可运行；SQLite 备份可被新连接完整读取；旧备份按 `keep` 清理。
- [x] 桌面端显示降级横幅；`npm run check` 0 errors。
- [x] `npm run test:unit` 全量通过（记录实测数值）。
- [x] `npm run build` 通过并记录 Vite 体积差值。
- [x] 评估报告 `c10-high-availability-evaluation.md` 由评估者角色出具。

## 决策记录

- **备份放 CLI 而非自动定时**：个人知识库不需要常驻调度；用户按需执行或交给系统 cron/任务计划。
- **`/v1/health` 不实时探活**：它只做存活探针和状态快照，避免桌面 5s 心跳把远端数据源打挂；实时依赖探活放在 `/v1/health/ready`，带 TTL 缓存。
- **备份保留完整 `datasources.json`**：脱敏会让“恢复配置”失效；安全责任通过文档与权限说明承担，而不是牺牲可用性。
- **日志记录所有 HTTP 请求（含 health）**：个人本机流量小，完整请求日志对排障价值远大于噪音成本。
