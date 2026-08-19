# 质量文档 -- 灵知 (Gnosis)

## 评级标准

- **A**：验证全部通过，架构干净，agent 能读懂，测试稳定。
- **B**：验证通过，基本干净，可读性或测试覆盖有少量缺口。
- **C**：部分可用，有已知缺口，部分代码 agent 不容易理解。
- **D**：不可用，或存在重大结构问题。

## 评分汇总

| 维度 | 评级 | 验证状态 | Agent 可读性 | 测试稳定性 | 关键缺口 | 上次更新 |
|------|------|---------|-------------|-----------|---------|---------|
| 构建与编译 | A | server pytest 196 collected（本机 Milvus Lite 不可用，188 passed + 8 skipped）；desktop 3 tsconfig 0 errors + Vite build 173.63 kB | A | A | 无 | 2026-08-19T00:00:00.000Z |
| 功能完整性 | A | 4 数据源 / 4 解析器 / embedding / 检索 / 桌面端 / 评测集 / goal.md 映射 / 数据源 CRUD / 上传进度 / ES 浏览页 / 黑板体系 / 高可用基础能力 / 备份恢复闭环 / active 热切换 / 自动备份 / 运行期健康监控 / 自动 failover / 恢复回切 / 数据迁移 / HA 配置总览 / SAAM/ATAM P0-P1 优化实施 | A | A | 无（KI-06 已由 G3 Ollama 路径收敛） | 2026-08-19T00:00:00.000Z |
| 需求与团队配置 | A | 7 个角色匹配 4 个 construction 责任区块 + 7 个 goal 迭代 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| RUP 过程管理 | A | inception / elaboration / construction(×5) / transition 全部闭环 + C6-C8 补充收敛 + G1-G19 goal 迭代 + C9-C17 高可用基础能力 | A | A | 无 | 2026-08-19T00:00:00.000Z |
| 协作与评估闭环 | A | C1-C7 + C9-C17 评估报告均通过；G18 首次实践、G19 再次实践 G 类自验；`docs/PROCESS.md` §迭代分类与评估策略 已明文规定其适用性与论据 | A | A | 无（H1 提出的欠账已由 H2 政策关闭） | 2026-08-19T00:00:00.000Z |
| 规则地图与角色文件 | A | AGENTS.md / CLAUDE.md 入口；agents/ 单角色文件 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 导出 Harness | A | 13 个 harness 文件 + 根级 package.json（聚合 scripts） | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 验证与证据 | A | feature_list 34/34 pass 且 evidence 全部非空（H2 修复 5 处重复键）；progress / quality / evaluator / clean / goal-mapping 全部更新到实测证据 | A | A | 无 | 2026-08-19T00:00:00.000Z |
| 文档与交接 | A | README / API / RUNBOOK / KNOWN_ISSUES / transition / goal/01-mapping / PROCESS 完整且状态准确 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 运行时可观测性 | A | structlog JSON；结构化事件 + `http.request` 请求关联；`/v1/health` 降级快照 + `/v1/health/ready` 依赖探活；desktop 心跳 + 自动重启 2 项 node 测试通过；一致性备份 CLI；数据源 schema / mark-tested / Hit.document_id 留证 | A | A | 无 | 2026-08-19T00:00:00.000Z |
| 过程可观测性 | A | C1-C7 + C9-C17 协议 + 评估齐全；G18/G19 两次实践 G 类自验；H2 政策 + 记录口径约定已闭环 | A | A | 无 | 2026-08-19T00:00:00.000Z |

## Overall Grade: A

> H1 曾因 goal 系列过程工件欠账把两项评为 B。H2 确立明文政策消除规则缺位；G18 首次完成 G 类自验，G19 再次验证，政策可执行性已闭环，过程可观测性保持 A。

## 当前快照

- 项目：灵知 (Gnosis)
- 需求：1. 支持多数据源配置（elasticsearch、postgresql、mysql、向量数据库）
2. 文件导入（excel、word、pdf、markdown）
3. embedding 模型 bge-m3
4. 向量化后存入数据库
- 当前 RUP 阶段：移交后增量（transition 已通过）
- 当前迭代：G19 SAAM/ATAM 优化实施（已收尾）
- 智能体数量：7
- 已生成文件：13 个 harness 文件 + 根级 `package.json`（聚合 scripts）+ docs/{inception,elaboration,construction,transition,goal}/ + server/ + desktop/

## 验证命令

> 下列数值为 2026-08-19 实测，非历史抄录。

- `bash init.sh`：harness 校验通过；自动跑 `npm run check` + `npm test` + `npm run build`。
- `npm run verify`：聚合 check + lint + test:unit + test:integration。
- `npm run check` / `npm run lint`：等价 `cd desktop && tsc --noEmit -p tsconfig.json`，0 errors。
- `npm run test:unit`：等价 `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings tests/`，**196 collected；本机 Milvus Lite 不可用 188 passed + 8 skipped**（G19 实测）。
- `npm run test:integration`：等价 `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings`，**196 collected；188 passed + 8 skipped**（G19 实测）。
- `npm run eval:mock`：等价 `cd server && PYTHONPATH=. python3 eval/run_eval.py --embedder mock`，**9/10 (90%)**。
- `npm run eval`（默认 Ollama bge-m3）：等价 `--embedder openai-compat`，需先起 Ollama；G3 记录 10/10 (100%)。
- `npm run build`：等价 `cd desktop && npm run build`，**Vite 173.63 kB JS / 41 模块 / 508ms**，tsc 0 errors。
- `cd desktop && node --test scripts/test-server-manager.cjs`：**2 passed in 30.8s**（含 3 次 ping 失败后重启的真实等待）。

## Evidence of Quality

### Build

- 类型检查与构建：3 个桌面端 tsconfig + Vite build 全部通过；根级 `package.json` 不引入新依赖，仅聚合 scripts。
- 项目自有验证脚本：`init.sh` 校验全部 harness 文件存在；检测到根级 `package.json` 后自动跑 check/test/build。
- Harness 初始化：`feature_list.json` **34/34** 全部 `pass`，且 `evidence` 字段全部非空（H2 修复了 5 处重复 `evidence` 键——真实内容在前、空串在后，按 JSON 语义被后者覆盖，导致证据对解析器不可见）。

### Runtime

- 应用启动和核心流程：`server/app/main.py` 启动时打印结构化 JSON 日志。
- 团队配置导出：harness 文件全量；根级 `package.json` 提供 npm 入口。
- 状态文件与评分文件更新：本文件与 `evaluator-rubric.md`、`clean-state-checklist.md` 已同步到 G19 实测基线。

### Observability

- 结构化日志覆盖：structlog + JSON 输出（含 timestamp、level、event、message）。
- 关键服务事件证据（下列事件名均在 `server/app/` 下 grep 实测命中，非文档声称）：`kb-server.startup`、`vector.ready`、`embedder.ready`、`embedder.fallback_to_mock`、`embedder.retry`、`datasource.from_saved`、`datasource.active_load_failed`、`datasource.config_load_failed`、`datasource.init_failed`、`datasource.default_in_memory`、`mysql.adapter.small_dataset_only`、`mysql.adapter.scan_limit_hit`、`mysql.schema.ready`、`postgres.schema.ready`、`elasticsearch.index.created`、`elasticsearch.aggregate_failed`、`pipeline.stage`、`chunks.browse_failed`、`chunks.browse_not_supported`、`http.request`、`health.readiness_degraded`。
- 请求关联：`server/app/api/middleware.py` 生成/透传 `X-Request-Id`，structlog contextvars 绑定，`http.request` 日志携带同一 id。
- 健康检查：`/v1/health` 返回降级快照；`/v1/health/ready` 探活 datasource + embedder（15s TTL）。
- 备份/恢复：`python3 -m app.observability.backup`（SQLite 官方 backup API + JSON + manifest + 保留策略）；`list` / `restore` CLI；`/v1/backups`；桌面 Backup & Restore 一键恢复（停服 → restore → 重启，`.pre-restore` 回退）。
- 热切换：`POST /v1/datasources/active/{name}/switch` + 黑板资源锁 + health 门槛；桌面 Settings “Switch now”。
- 自动备份：服务启动即检查 + 每小时 `backup_if_due`（默认开启），`backup.auto_*` 日志。
- 运行期健康监控：后台 30s 探活写入 `/v1/health` 快照；桌面 15s 轮询更新降级横幅；`health.monitor_degraded` / `recovered` 日志。
- 自动 failover：`datasources.json` 顶层 failover 顺序；连续失败阈值触发自动热切换；桌面 Settings Failover order。
- failover 恢复回切：failover 顺序第一项=主数据源；主库恢复连续健康自动切回，`datasource.failover_recovered` 日志。
- 数据迁移：`dump_all` + migrate CLI；dump 全量 text/metadata，load 重新 embedding 后写入目标。
- HA 配置总览：`GET /v1/settings/ha` + Settings HA Configuration 只读表。
- 任务级可观测性（G6）：`TaskStage` 7 态 + `TaskEvent` ring buffer 32 + `GET /v1/files/tasks/{id}/events?since_id=`；渲染端阶段 tag + 折叠事件日志。
- 进程可观测性：desktop `server-manager.ts` 5s 心跳 + 3 次失败自动重启，2 项 node 测试实测通过。

### Performance

- 评测 9/10 通过（mock embedder）；真实 bge-m3 经 Ollama 路径 10/10（G3 记录）。
- 本地分析与导出耗时：`pytest -p no:warnings` ≈ 3.4–4.1s（196 collected）；Vite build ≈ 0.51s；根级 `npm run verify` ≈ 12s 端到端。

## Verified Against

| 证据 | 状态 |
| --- | --- |
| `clean-state-checklist.md` | 全部项已具备（类型/构建/测试/harness/架构边界/goal-mapping） |
| `evaluator-rubric.md` | C1-C7 共 7 次评估 ≥4.75/5 通过；G/H 系列按 `docs/PROCESS.md` 政策走自验；总分 5/5，结论 Accept |
| `feature_list.json` | 34/34 features = pass，evidence 全部非空 |
| `eval/run_eval.py --embedder mock` | 9/10 通过 |
| `pytest -p no:warnings` | 196 collected；本机 Milvus Lite 不可用 188 passed + 8 skipped（unit + integration） |
| `tsc --noEmit` × 3 | 0 errors |
| `vite build` | 成功（173.63 kB JS / 41 模块） |
| `node --test scripts/test-server-manager.cjs` | 2 passed |
| `npm run verify` | 全部通过 |
| `docs/goal/01-mapping.md` | goal.md → 实际栈映射三层表 |
