# 质量文档 -- 灵知 (Gnosis)

## 评级标准

- **A**：验证全部通过，架构干净，agent 能读懂，测试稳定。
- **B**：验证通过，基本干净，可读性或测试覆盖有少量缺口。
- **C**：部分可用，有已知缺口，部分代码 agent 不容易理解。
- **D**：不可用，或存在重大结构问题。

## 评分汇总

| 维度 | 评级 | 验证状态 | Agent 可读性 | 测试稳定性 | 关键缺口 | 上次更新 |
|------|------|---------|-------------|-----------|---------|---------|
| 构建与编译 | A | server pytest 144 passed；desktop 3 tsconfig 0 errors + Vite build 158.61 kB | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 功能完整性 | A | 4 数据源 / 4 解析器 / embedding / 检索 / 桌面端 / 评测集 / goal.md 映射 / 数据源 CRUD / 上传进度 / ES 浏览页 | A | A | 无（KI-06 已由 G3 Ollama 路径收敛） | 2026-08-08T00:00:00.000Z |
| 需求与团队配置 | A | 7 个角色匹配 4 个 construction 责任区块 + 7 个 goal 迭代 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| RUP 过程管理 | A | inception / elaboration / construction(×5) / transition 全部闭环 + C6-C8 补充收敛 + G1-G7 goal 迭代 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 协作与评估闭环 | A | C1-C7 共 7 份评估报告均 ≥4.75/5；G/H 系列走自验，`docs/PROCESS.md` §迭代分类与评估策略 已明文规定其适用性与论据 | A | A | 无（H1 提出的欠账已由 H2 政策关闭） | 2026-08-08T00:00:00.000Z |
| 规则地图与角色文件 | A | AGENTS.md / CLAUDE.md 入口；agents/ 单角色文件 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 导出 Harness | A | 13 个 harness 文件 + 根级 package.json（聚合 scripts） | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 验证与证据 | A | feature_list 21/21 pass 且 evidence 全部非空（H2 修复 5 处重复键）；progress / quality / evaluator / clean / goal-mapping 全部更新到实测证据 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 文档与交接 | A | README / API / RUNBOOK / KNOWN_ISSUES / transition / goal/01-mapping / PROCESS 完整且状态准确 | A | A | 无 | 2026-08-08T00:00:00.000Z |
| 运行时可观测性 | A | structlog JSON；19 类结构化事件全部在 `server/app/` 实测可查；`/v1/health` 健康检查；desktop 心跳 + 自动重启 2 项 node 测试通过 | A | A | 无追踪能力（无 request_id / trace_id；`merge_contextvars` 已挂载但无 bind 调用） | 2026-08-08T00:00:00.000Z |
| 过程可观测性 | A- | C1-C7 协议 + 评估成对齐全；G5/G6/G7 有协议；H2 确立三类迭代的评估策略 + 四条升级触发条件 + 记录口径约定 | A | A | 政策尚未被任何 G 类迭代实践检验；G1-G4 协议与 G1-G7 评估报告仍不存在（已显式追认，非遗漏） | 2026-08-08T00:00:00.000Z |

## Overall Grade: A

> H1 曾因 goal 系列过程工件欠账把两项评为 B。H2 确立明文政策（`docs/PROCESS.md` §迭代分类与评估策略）消除了规则缺位这一根因，两项回升。过程可观测性保留 A-：政策本身尚未经一轮 G 类迭代检验。

## 当前快照

- 项目：灵知 (Gnosis)
- 需求：1. 支持多数据源配置（elasticsearch、postgresql、mysql、向量数据库）
2. 文件导入（excel、word、pdf、markdown）
3. embedding 模型 bge-m3
4. 向量化后存入数据库
- 当前 RUP 阶段：移交后增量（transition 已通过）
- 当前迭代：H2 过程政策确立（已收尾）
- 智能体数量：7
- 已生成文件：13 个 harness 文件 + 根级 `package.json`（聚合 scripts）+ docs/{inception,elaboration,construction,transition,goal}/ + server/ + desktop/

## 验证命令

> 下列数值为 2026-08-08 实测，非历史抄录。

- `bash init.sh`：harness 校验通过；自动跑 `npm run check` + `npm test` + `npm run build`。
- `npm run verify`：聚合 check + lint + test:unit + test:integration。
- `npm run check` / `npm run lint`：等价 `cd desktop && tsc --noEmit -p tsconfig.json`，0 errors。
- `npm run test:unit`：等价 `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings tests/`，**144 passed in 5.21s**。
- `npm run test:integration`：等价 `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings`，**144 passed in 4.68s**。
- `npm run eval:mock`：等价 `cd server && PYTHONPATH=. python3 eval/run_eval.py --embedder mock`，**9/10 (90%)**。
- `npm run eval`（默认 Ollama bge-m3）：等价 `--embedder openai-compat`，需先起 Ollama；G3 记录 10/10 (100%)。
- `npm run build`：等价 `cd desktop && npm run build`，**Vite 158.61 kB JS + 7.00 kB CSS / 38 模块 / 685ms**，tsc 0 errors。
- `cd desktop && node --test scripts/test-server-manager.cjs`：**2 passed in 30.8s**（含 3 次 ping 失败后重启的真实等待）。

## Evidence of Quality

### Build

- 类型检查与构建：3 个桌面端 tsconfig + Vite build 全部通过；根级 `package.json` 不引入新依赖，仅聚合 scripts。
- 项目自有验证脚本：`init.sh` 校验全部 harness 文件存在；检测到根级 `package.json` 后自动跑 check/test/build。
- Harness 初始化：`feature_list.json` **21/21** 全部 `pass`，且 `evidence` 字段全部非空（H2 修复了 5 处重复 `evidence` 键——真实内容在前、空串在后，按 JSON 语义被后者覆盖，导致证据对解析器不可见）。

### Runtime

- 应用启动和核心流程：`server/app/main.py` 启动时打印结构化 JSON 日志。
- 团队配置导出：harness 文件全量；根级 `package.json` 提供 npm 入口。
- 状态文件与评分文件更新：本文件与 `evaluator-rubric.md`、`clean-state-checklist.md` 已同步到 G7 实测基线。

### Observability

- 结构化日志覆盖：structlog + JSON 输出（含 timestamp、level、event、message）。
- 关键服务事件证据（下列事件名均在 `server/app/` 下 grep 实测命中，非文档声称）：`kb-server.startup`、`vector.ready`、`embedder.ready`、`embedder.fallback_to_mock`、`embedder.retry`、`datasource.from_saved`、`datasource.active_load_failed`、`datasource.config_load_failed`、`datasource.init_failed`、`datasource.default_in_memory`、`mysql.adapter.small_dataset_only`、`mysql.adapter.scan_limit_hit`、`mysql.schema.ready`、`postgres.schema.ready`、`elasticsearch.index.created`、`elasticsearch.aggregate_failed`、`pipeline.stage`、`chunks.browse_failed`、`chunks.browse_not_supported`。
- 健康检查：`server/app/api/health.py` 暴露 `/v1/health`，返回 `embed_backend` 等运行时事实。
- 任务级可观测性（G6）：`TaskStage` 7 态 + `TaskEvent` ring buffer 32 + `GET /v1/files/tasks/{id}/events?since_id=`；渲染端阶段 tag + 折叠事件日志。
- 进程可观测性：desktop `server-manager.ts` 5s 心跳 + 3 次失败自动重启，2 项 node 测试实测通过。

### Performance

- 评测 9/10 通过（mock embedder）；真实 bge-m3 经 Ollama 路径 10/10（G3 记录）。
- 本地分析与导出耗时：`pytest -p no:warnings` ≈ 4.7–5.2s（144 项）；Vite build ≈ 0.69s；根级 `npm run verify` ≈ 15s 端到端。

## Verified Against

| 证据 | 状态 |
| --- | --- |
| `clean-state-checklist.md` | 全部项已具备（类型/构建/测试/harness/架构边界/goal-mapping） |
| `evaluator-rubric.md` | C1-C7 共 7 次评估 ≥4.75/5 通过；G/H 系列按 `docs/PROCESS.md` 政策走自验；总分 4.75/5，结论 Accept |
| `feature_list.json` | 21/21 features = pass，evidence 全部非空 |
| `eval/run_eval.py --embedder mock` | 9/10 通过 |
| `pytest -p no:warnings` | 144 passed（unit + integration） |
| `tsc --noEmit` × 3 | 0 errors |
| `vite build` | 成功（158.61 kB JS / 7.00 kB CSS / 38 模块） |
| `node --test scripts/test-server-manager.cjs` | 2 passed |
| `npm run verify` | 全部通过 |
| `docs/goal/01-mapping.md` | goal.md → 实际栈映射三层表 |