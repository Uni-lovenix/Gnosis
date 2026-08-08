# Session Handoff -- 灵知 (Gnosis)

## Current Objective

- Goal: 1. 支持多数据源配置（elasticsearch、postgresql、mysql、向量数据库）
  2. 文件导入（excel、word、pdf、markdown）
  3. embedding 模型 bge-m3
  4. 向量化后存入数据库
- Current status: **G1-G7 + H1 + H2 全 pass**；`feature_list.json` 21/21 = pass（evidence 全部非空）。
  - G5 = KI-03 收敛（OpenAI 兼容远端指数退避）。`npm run verify` 120 passed（113 + 7）；`embedder.retry` 结构化日志可见。
  - G6 = 上传进度可观测性（阶段文字 + 事件日志）。`TaskStore` v1 schema（`stage` 列 + `task_events` ring buffer）；`TaskResponse.events` 嵌入最近 32 条；`npm run verify` 125 passed（113 + 12）；前端 ImportPage 新增 stage tag + 折叠事件日志；Vite 153.74 kB。
  - G7 = ES 数据浏览页（chunk-level + 文档聚合 + 过滤 + 分页）。`ElasticsearchAdapter` 加 `list_chunks` + `aggregate_by_document`；`DataSource` 基类新增可选 `list_chunks`/`aggregate_by_document`（默认抛 `NotSupportedError`，仅 ES 实现 `chunk_list` capability）；新增 `GET /v1/chunks`；前端 BrowsePage（parser 下拉 + document_id debounce 输入 + 聚合表 + 分页 + 不支持 capability 永久 banner）；Vite 158.61 kB。
  - H1 = harness 文档同步 + 双层可观测性补分（纯文档轮，零生产代码改动）。三份 harness 文件从 G1/T1 基线同步到 G7 实测；补齐自 T1 悬空 7 轮的可观测性评分（运行时 4/5、过程 3/5）。
  - H2 = 过程政策确立（纯文档轮，零生产代码改动）。`docs/PROCESS.md` 新增 §迭代分类与评估策略（C 类必须评估报告，G/H 类走自验 + 四项最低要求 + 四条升级触发条件）与 §记录口径约定；修正该文件此前停在 `当前阶段：inception` 的陈旧状态；顺带修复 `feature_list.json` 5 处重复 `evidence` 键。过程可观测性 3 → 4，总分 4.5 → 4.75/5，结论 Accept。
- **实测基线（2026-08-08 复核，取代此前所有历史抄录）**：`npm run test:unit` **144 passed in 5.21s**；`test:integration` **144 passed in 4.68s**；`tsc --noEmit` 0 errors；Vite **158.61 kB JS + 7.00 kB CSS / 38 模块**；`eval:mock` 9/10；`node --test scripts/test-server-manager.cjs` 2 passed。
  - ⚠️ G7 记录的 "136 passed" 是 Milvus 适配器 skip 状态下的计数，差值 8 = `tests/datasources/test_milvus_adapter.py` 的 8 项。**非回归**。记录测试数请统一走 `npm run test:unit`（它带 `KB_MILVUS_URI=./kb_milvus_lite.db`，Milvus 会全跑）。
- Branch / commit: `main` · HEAD `72d8a2a` · remote `origin` = `https://github.com/Uni-lovenix/Gnosis.git`（已 push，仓库现非空）

## Git Remote & Per-Version Sync Workflow

**Remote**: `origin` → `https://github.com/Uni-lovenix/Gnosis.git`（默认分支 `main`，用户名 `Uni-lovenix`）

每个版本开发结束 → 按下面三步同步，远端永远是已验证代码：

```bash
# 1) 确认 working tree 干净（跑过 npm run verify / smoke test）
git status

# 2) 提交——版本号 + 主题 + 验证证据
git add -A
git commit -m "vX.Y: <主题>  (npm run verify: N passed; eval: n/10)"

# 3) 推送到远端
git push origin main
```

规则：
- 一个版本 = 一个 commit（或一个简短系列），禁止一次性堆多个未验证迭代。
- commit message 必须带 **版本号 + 验证证据**（`npm run verify` 结果 / eval 命中率 / Vite 体积变化）。
- push 之前必须先 `git pull --rebase` 以应对多端开发。
- 任何破坏 `npm run verify` 的代码不要 push。

## Completed This Session

- [x] 启动范围确认（inception）：`docs/inception/{01-project-scope,02-initial-risks,03-initial-iteration-plan}.md`
- [x] 架构与风险细化（elaboration）：`docs/elaboration/{01-architecture-baseline,02-risk-update,03-iteration-protocols}.md`
- [x] C1 数据与报表：4 类数据源适配器 + 抽象 + 单元测试；`docs/construction/c1-data-sources.md` + `c1-evaluation.md`（5/5）
- [x] C2 文件与同步：4 类解析器 + 切片器 + 任务存储 + files API；`c2-files-and-sync.md` + `c2-evaluation.md`（5/5）
- [x] C3 AI 与智能体：Embedder 抽象 + 3 种实现 + 流水线 + 评测 9/10；`c3-ai-embedding.md` + `c3-evaluation.md`（5/5）
- [x] C4 多端体验：Electron + React + TS；`c4-multi-experience.md` + `c4-evaluation.md`（5/5）
- [x] T1 移交：README.md、docs/API.md、docs/RUNBOOK.md、docs/KNOWN_ISSUES.md、docs/transition/README.md
- [x] C5 已知问题修复（KI-04 / KI-05 / KI-06）：`docs/construction/c5-known-issues.md` + `c5-evaluation.md`（4.75/5）
- [x] C6 KI-09 任务表过期清理：`docs/construction/c6-milvus-tests.md` + `c6-evaluation.md`（5/5）
- [x] C7 KI-07 Milvus 1:1 单测：`docs/construction/c6-milvus-tests.md` + `c6-evaluation.md`（5/5）
- [x] C8 KI-02 MySQL O(N) 性能收敛：`docs/construction/c7-mysql-perf.md` + `c7-evaluation.md`（5/5）
- [x] G1 goal.md → 实际项目栈映射：`docs/goal/01-mapping.md`（目录结构 + 验收项 + 验证命令三层映射表）；新建根级 `package.json`（不动 `desktop/package.json` 的 start/build/dev）：`npm run check`（= `tsc --noEmit`）0 errors、`npm run lint` 0 errors、`npm run test:unit` 89 passed、`npm run test:integration` 89 passed、`npm run eval` 9/10 (90%)、`npm run build` Vite 148.70 kB。
- [x] **G2 数据源配置 CRUD**：`server/app/observability/datasource_store.py`（v1 schema、原子写 `os.replace`、损坏文件自动备份）+ `server/app/api/datasources.py` 5 个新 endpoints + `main._build_default_components()` 启动加载 active 配置 + `SettingsPage.tsx` 完整 CRUD UI（Add / Edit / Test / Save / Activate / Delete / Clear active）+ `docs/API.md` §数据源 + `RUNBOOK.md` §"数据源配置管理" + `goal/01-mapping.md` 验收映射更新；`npm run test:unit` 113 passed（+24）、`npm run test:integration` 113 passed（+24）、`npm run build` Vite 152.27 kB。
- [x] **G3 Ollama bge-m3 真模型**：`scripts/start_server_ollama.sh` + `eval --embedder openai-compat`；`/v1/files/import` README.md 真嵌入；`/v1/search` 真实打分；eval 10/10 = 100%。
- [x] **G4 真实 ES 当默认数据源**：ES 9.5.0 + elastic 凭证；`datasources.json active=es-prod`；`datasource.from_saved` 日志；bbq_hnsw 1024-dim cosine 真写入；search 0.74+；`docs/RUNBOOK.md` §3a 接入示例。
- [x] **G5 KI-03 OpenAI 兼容远端指数退避**：`server/app/embedding/openai_compat.py` 引入指数退避主循环（仅 `httpx.TransportError` / 5xx / 429 重试；4xx 立即抛）；`max_retries` / `initial_backoff` / `max_backoff` / `backoff_jitter` 4 个 options；每次重试打 `embedder.retry` warning 日志；`tests/embedding/test_embedders.py` 新增 7 项单测（瞬时错误重试至成功 / 耗尽抛错 / 4xx 不重试 / 429 / 5xx / 退避数学 / 日志结构）；`docs/RUNBOOK.md` §2a 调参与不重试矩阵；`docs/KNOWN_ISSUES.md` KI-03 收敛；`npm run test:unit` 113 → **120 passed**。
- [x] **G6 上传进度可观测性**：`server/app/observability/models.py` 新增 `TaskStage` 枚举 + `TaskEvent` 模型 + `TaskStatus` 加 `stage` / `events` 字段；`server/app/observability/task_store.py` v1 schema 迁移（`stage` 列 + `task_events` ring buffer 32 + `PRAGMA user_version=1`）+ `add_event` / `list_events` / `list_events_since` / `last_event_id`；`server/app/pipeline/indexing.py` `IndexingPipeline.on_progress` 签名升级到 `Callable[[ProgressEvent], None]`（4 处边界发事件，message 含文件名 + chunk 计数）；`server/app/api/files.py` `_run_import` 接入 stage + 新增 `GET /v1/files/tasks/{task_id}/events?since_id=` 备用端点；前端 `desktop/src/shared/types.ts` 加 `TaskStage` / `TaskEvent` + `TaskStatus` 扩展；`desktop/src/renderer/lib/state.ts` `AppState.indexing` 加 `stage` / `events` / `lastMessage`；`desktop/src/renderer/pages/ImportPage.tsx` 加 stage tag + 折叠 `<details>` 事件日志；`desktop/src/renderer/styles.css` 加 `.kb-stage*` `.kb-event-log` 系列样式；`desktop/src/main/api-client.ts` 镜像类型；`server/tests/test_task_store.py` +7 项（stage round-trip / 默认值 / add_event / ring buffer 32 / since_id 分页 / last_event_id / schema 迁移）；`server/tests/api/test_task_progress_api.py` 新建 +5 项（端到端 import → stage + events；`/events` 全量；`since_id` 分页；404；旧负载 fallback）；`tests/pipeline/test_pipelines.py` 升级到 ProgressEvent；`docs/API.md` §TaskStatus 加 stage/events + 新增 `/events` 端点段；`docs/RUNBOOK.md` §4a 上传进度可观测性；`npm run verify` 120 → **125 passed**；`npm run build` Vite 152.27 → 153.74 kB（+1.47 kB）。
- [x] **G7 ES 数据浏览页**：`server/app/datasources/base.py` 新增 `NotSupportedError(DatasourceError)` + `DataSource.list_chunks` / `aggregate_by_document` 默认抛 `NotSupportedError`；`server/app/observability/models.py` 新增 `ChunkSummary` / `DocumentSummary`；`server/app/datasources/elasticsearch_adapter.py` `capabilities()` 增 `"chunk_list"`，实现 `list_chunks`（match_all + bool filter + from/size + sort + `_source` 限定 + text 服务端截 240 字 + ES 异常降级为空 dict）+ `aggregate_by_document`（ES terms agg + 嵌套 parser terms + top_hits sample + 异常降级）；`server/app/api/chunks.py`（新）`GET /v1/chunks?document_id&parser&offset&limit` 返回 `BrowseResponse {chunks, total, aggregations}`，400/422 非法参数、501 capability 缺失、503 active 未绑定；`server/app/main.py` 启动期 `chunks_api.set_active_datasource(ds)` 绑定；前端 `desktop/src/shared/types.ts` + `desktop/src/main/api-client.ts` 加 `ChunkSummary` / `DocumentSummary` / `BrowseResponse` / `BrowseOpts` + `ApiClient.browseChunks(opts)`；`desktop/src/preload/index.ts` + `desktop/src/main/index.ts` 加 `browseChunks` IPC handler；`desktop/src/renderer/App.tsx` Tab union 加 `"browse"`；`desktop/src/renderer/pages/BrowsePage.tsx`（新）：active ds 角标 + 永久 `.kb-banner-warn`（不支持 capability）+ parser 下拉（seed + 实际 union）+ document_id 输入（250ms debounce）+ 文档聚合表（点击行 = 应用 document_id 过滤）+ chunk 列表（preview + `<details>` 折叠 JSON metadata）+ 分页（prev/next + offset/limit + total）+ 错误 toast；`desktop/src/renderer/styles.css` 加 `.kb-chunks` / `.kb-agg-table` / `.kb-banner-warn` / `.kb-browse-filters` / `.kb-pagination` 系列样式。测试：`server/tests/datasources/test_elasticsearch_adapter.py` 扩 5 项（list_chunks 分页 + sort + 文本截断 + 过滤；aggregate 分组；ES 异常降级；capabilities 含 chunk_list）；`server/tests/api/test_chunks_api.py`（新）7 项（200 完整 / 过滤参数透传 / limit 非法 / 负 offset / 501 capability / 503 active / aggregate NotSupportedError 转 501）。`pytest tests/` 125 → **136 passed**（+11 G7 new；注：该计数为 Milvus skip 状态，全量实测 144，见上文实测基线）；`npm run verify` 125 → 136 / 125 → 136 全绿；`npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite 153.74 → **158.61 kB**（+4.87 kB）；`docs/API.md` §浏览 + `docs/RUNBOOK.md` §4b + `docs/goal/01-mapping.md` G7 行 + `docs/construction/g7-es-browse.md` 协议；`feature_list.json` 18 → **19 pass**。
- [x] **H1 harness 文档同步 + 双层可观测性补分**（纯文档轮，**零生产代码改动**）：`quality-document.md` 9 维 → 11 维（新增运行时/过程可观测性两行）、全部数值换实测；`clean-state-checklist.md` 快照 G1 → G7、`.gitignore` 项从"推荐"改为"已生效"、新增 2 项未勾选项暴露欠账；`evaluator-rubric.md` 上下文 T1 → G7 累计、补齐自 T1 悬空 7 轮的双层可观测性评分（**运行时 4/5** —— 日志/健康检查/进程事件齐备但追踪为零：无 `request_id`/`trace_id`，`structlog.contextvars.merge_contextvars` 已挂 processors 却无任何 `bind_contextvars` 调用；**过程 3/5** —— 14 轮迭代 7 轮无评估工件，评分表自身滞后 6 轮）；`feature_list.json` `last_updated` → 2026-08-08。取证：19 类日志事件逐个 grep 命中；`mark_tested` 确认为有测试无调用方的死代码；`app/utils/backoff.py` 确认不存在；实测修正 136 → 144。
- [x] **H2 过程政策确立**（纯文档轮，**零生产代码改动**）：`docs/PROCESS.md` 新增 §迭代分类与评估策略——C / G / H 三类迭代**均必须**有迭代协议，C 类**必须**出独立评估报告，G/H 类走自验并写明论据（G 类退出标准本身即可执行断言，可重跑复现，比追述性报告更难造假；且不引入新设计决策）；四条**客观可判定**的升级触发条件（破坏性接口变更 / 持久化 schema 迁移 / 新增数据源或 embedder 后端 / 安全边界）命中任一即不得自验；自验四项最低要求（协议先行 / progress.md 留数值 / evidence 非空 / 双层可观测性过）缺一不得标 pass；G1-G7 显式追认不回溯，G6 命中两条升级条件留档为判例。新增 §记录口径约定（测试数以 `npm run test:unit` 为准 / 包体积带差值 / 评分表每轮同步，连续两轮未同步即判不合格 / 新增维度不得长期挂"待评分"）。修正陈旧状态：阶段表四行 `待进入` → `已通过` + 新增「移交后增量」行，当前阶段 `inception` → 移交后增量，迭代列表 7 → 21 行。新建 `docs/construction/h2-process-policy.md`（含反面案例 + **H1 迭代协议补记**）。**意外修复**：`feature_list.json` 5 个条目各有两个 `evidence` 键（真实内容在前、空串在后），按 JSON 语义证据对解析器不可见——已去重保留真实内容。重评：过程可观测性 3 → 4、交接准备度 4 → 5、总分 4.5 → **4.75/5**、结论 Revise → **Accept**；`quality-document.md` Overall A- → **A**。

## Verification Evidence

| Check | Command | Result |
|---|---|---|
| 团队配置存在 | `ls AGENTS.team.md agents.json` | OK |
| 角色文件存在 | `ls agents` | OK（7 个） |
| Harness 文件存在 | `ls AGENTS.md CLAUDE.md ...` | OK |
| 启动校验 | `bash init.sh` | OK |
| Milvus 1:1（Lite 路径） | `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/datasources/test_milvus_adapter.py -q` | **8/8 通过**（1.33s） |
| 服务端测试（Lite 全套） | `KB_MILVUS_URI=./kb_milvus_lite.db pytest` | **89 → 113 passed**（+24 G2 new） |
| MySQL 新增 4 项单测 | `pytest tests/datasources/test_mysql_adapter.py -v` | **11/11 通过** |
| `feature_list.json` 合法 | `python3 -c "json.load(open('feature_list.json'))"` | OK（**21/21**，evidence 全部非空） |
| **G1/G2 npm check** | `npm run check` | **OK**（tsc --noEmit 0 errors） |
| **G1/G2 npm lint** | `npm run lint` | **OK**（tsc --noEmit 0 errors） |
| **G1/G2 npm test:unit** | `npm run test:unit` | **113 passed in 3.42s** |
| **G1/G2 npm test:integration** | `npm run test:integration` | **113 passed in 2.78s** |
| **G1/G2 npm eval** | `npm run eval` | **9/10 = 90%**（rate 0.9 ≥ 60% 门禁） |
| **G1/G2 npm build** | `npm run build` | **Vite 152.27 kB + tsc 0 errors** |
| **G2 数据源 store 单测** | `pytest tests/test_datasource_store.py -v` | **16/16 通过** |
| **G2 配置 CRUD API 单测** | `pytest tests/test_datasource_configs_api.py -v` | **8/8 通过** |
| **G2 端到端 smoke** | `KB_DATA_DIR=/tmp/... uvicorn ...` + curl | POST/GET/PUT/DELETE 全部 200；`datasources.json` 原子写出 |
| **G2 active 启动加载** | `_build_default_components()` 调用 | `ds.name='mem'` + 日志 `datasource.from_saved` |
| **G2 es 缺依赖失败信息** | `POST /v1/datasources/configs {type:'elasticsearch'}` | 400：`elasticsearch package not installed. pip install -e '.[es]'.` |
| **G3 Ollama 启动** | `bash scripts/start_server_ollama.sh` | 服务起来 `embed_backend=openai-compat` |
| **G3 真模型评测** | `npm run eval:ollama` | **10/10 = 100%** |
| **G4 真 ES 启动加载** | 重启 + `_build_default_components()` | 日志 `datasource.from_saved name=es-prod` |
| **G4 真 ES 写入** | `POST /v1/files/import` README.md | `chunks=4 embedded=4 written=4` + `elasticsearch.index.created` |
| **G4 真 ES 检索** | `POST /v1/search` "embedding 模型选用什么" top_k=3 | score **0.7415 / 0.7415 / 0.7371** |
| **G5 retry 单测** | `pytest tests/embedding/test_embedders.py -v` | **15/15 通过**（原 8 + KI-03 新增 7） |
| **G5 retry 退避数学** | 单元测试 `test_openai_compat_backoff_doubles_and_caps` | `[0.5, 1.0, 2.0, 2.0]`，阶梯 + 封顶正确 |
| **G5 retry 日志** | `structlog.testing.capture_logs` | `event=embedder.retry, log_level=warning, attempt=1, max_attempts=4, error_kind=_T` |
| **G5 verify 集成** | `npm run verify` | **120 passed**（test:unit + test:integration 均 120） |
| **G6 task_store 单测** | `pytest tests/test_task_store.py -v` | **15/15 通过**（原 8 + G6 新增 7：stage round-trip / 默认值 / add_event / ring buffer 32 / since_id 分页 / last_event_id / schema 迁移） |
| **G6 progress API 单测** | `pytest tests/api/test_task_progress_api.py -v` | **5/5 通过**（端到端 stage + events / /events 全量 / since_id / 404 / 旧负载 fallback） |
| **G6 pipeline 单测** | `pytest tests/pipeline/test_pipelines.py -v` | **6/6 通过**（升级到 ProgressEvent；新增 message 校验） |
| **G6 verify 集成** | `npm run verify` | **125 passed**（test:unit + test:integration 均 125；原 113 + G6 新增 12） |
| **G6 npm check** | `npm run check` | **OK**（tsc 0 errors） |
| **G6 npm build** | `npm run build` | **Vite 153.74 kB**（+1.47 kB vs G5 的 152.27） |
| **G7 ES adapter 单测** | `pytest tests/datasources/test_elasticsearch_adapter.py -v` | **9/9 通过**（原 4 + G7 新增 5：list_chunks 分页/sort/截断/过滤；aggregate 分组；ES 异常降级；capabilities 含 chunk_list） |
| **G7 chunks API 单测** | `pytest tests/api/test_chunks_api.py -v` | **7/7 通过**（200 完整 / 过滤 / limit 非法 / 负 offset / 501 / 503 / NotSupportedError → 501） |
| **G7 verify 集成** | `npm run verify` | **136 passed**（Milvus skip 口径；全量实测 144，见 H1 行） |
| **G7 npm check** | `npm run check` | **OK**（tsc 0 errors） |
| **G7 npm build** | `npm run build` | **Vite 158.61 kB**（+4.87 kB vs G6 的 153.74） |
| **H1 test:unit（当前基线）** | `npm run test:unit` | **144 passed in 5.21s** |
| **H1 test:integration（当前基线）** | `npm run test:integration` | **144 passed in 4.68s** |
| **H1 build（当前基线）** | `npm run build` | **158.61 kB JS + 7.00 kB CSS / 38 模块 / 685ms** |
| **H1 eval（当前基线）** | `npm run eval:mock` | **9/10 = 90%** |
| **H1 desktop 进程守护** | `cd desktop && node --test scripts/test-server-manager.cjs` | **2 passed in 30.8s**（含 3 次 ping 失败后重启的真实等待） |
| **H1 日志事件取证** | `grep -r <event> server/app` | **19 类事件逐个命中**（含 `kb-server.startup` / `embedder.retry` / `datasource.from_saved` / `pipeline.stage` / `chunks.browse_*`） |
| **H1 追踪能力取证** | `grep -r "request_id\|trace_id\|correlation_id\|bind_contextvars" server/app` | **0 命中** → 运行时可观测性扣 1 分的依据 |
| **H1 过程工件取证** | `ls docs/construction/` | 协议 c1-c7 + g5/g6/g7（**G1-G4 缺**）；评估 c1-c7（**G1-G7 缺**）→ 过程可观测性 3/5 的依据 |
| **H1 死代码取证** | `grep -r mark_tested server desktop` | 仅 `datasource_store.py:188`（实现）+ `test_datasource_store.py:111`（单测），**无调用方** |
| **H2 PROCESS.md 陈旧度** | `grep -n "当前阶段\|待进入" docs/PROCESS.md`（修正前） | `当前阶段：inception`；细化/构建/移交三行均 `待进入` → 本次整理中**滞后最严重**的一份 |
| **H2 重复键取证** | `json.load(..., object_pairs_hook=)` 检测 | `feat-construction-1`…`-4` + `feat-transition-handoff` 共 **5 处重复 `evidence` 键**（真实内容在前、空串在后），标准解析器读到空值 → 证据链实际断裂 |
| **H2 修复后校验** | 与 `git show HEAD:feature_list.json` 逐字段比对 | 原 19 项 `name`/`description`/`status`/`evidence`/`testedAt`/`rupPhase`/`iteration`/`ownerRole`/`dependencies` **全部一致**，仅新增 H1/H2 两项；21/21 evidence 非空 |
| **H2 verify 集成** | `npm run verify` | **144 passed ×2 全绿**（零生产代码改动） |
| **H2 harness 校验** | `bash init.sh` | 全绿 |

## Files Changed

- `docs/construction/c7-mysql-perf.md`、`docs/construction/c7-evaluation.md`（C8 协议 + 评估）
- `server/app/datasources/mysql_adapter.py`（docstring KI-02 mitigation；`__init__` `mysql.adapter.small_dataset_only` warning；`search()` `mysql.adapter.scan_limit_hit` warning；`capabilities()` `scan_limit_risk`）
- `server/tests/datasources/test_mysql_adapter.py`（4 项新单测）
- `docs/RUNBOOK.md` §3（pgvector / Milvus 迁移示例）
- `docs/API.md`（`GET /v1/datasources` 章节 capabilities 含义）
- `server/README.md`（MySQL 行 + RUNBOOK §3 反链）
- `feature_list.json` / `progress.md` / `session-handoff.md` / `KNOWN_ISSUES.md`（状态更新）
- **G1**：`package.json`（根级聚合 npm scripts；`desktop/package.json` 未触碰）；`docs/goal/01-mapping.md`；`feature_list.json`（追加 G1 条目；14/14 pass）
- **G2 后端**：`server/app/observability/datasource_store.py`（新增 16 项单测）；`server/app/api/datasources.py`（新增 5 个 endpoints）；`server/app/main.py`（active 配置启动加载 + `_resolve_default_datasource` helper）；`server/tests/test_datasource_store.py`（16 项）+ `server/tests/test_datasource_configs_api.py`（8 项）
- **G2 前端**：`desktop/src/shared/types.ts`（KBAPI +6 方法 + `DatasourceConfigRecord` / `ActiveDatasourceResponse`）；`desktop/src/main/api-client.ts`（ApiClient 实现）；`desktop/src/main/index.ts`（IPC 绑定）；`desktop/src/preload/index.ts`（contextBridge）；`desktop/src/renderer/pages/SettingsPage.tsx`（完整 CRUD UI：Add/Edit/Save/Test/Activate/Delete/Clear active + toast 反馈）；`desktop/src/renderer/styles.css`（`.kb-configs` `.kb-row-active` `.kb-toast*`）
- **G2 文档**：`docs/API.md` §数据源 CRUD 段；`docs/RUNBOOK.md` §"数据源配置管理"（5 类 options 模板 + 排错）；`docs/goal/01-mapping.md`（"配置管理"行升级为 G2 引用）
- **G3**：`scripts/start_server_ollama.sh`（新增 30 行 bash，自动设 `KB_EMBED_BACKEND=openai-compat` + 4 个 `KB_OPENAI_*` 与 `KB_EMBED_*` env）；`server/eval/run_eval.py`（新增 `openai-compat` 分支 + `--embedder` choices 扩到 3 项）；根级 `package.json`（`server:ollama` / `eval:ollama` / `eval:bgem3`）；`docs/KNOWN_ISSUES.md`（KI-06 移入收敛表）；`docs/RUNBOOK.md` §2（Ollama 启动 + 排错：`BAAI/bge-m3` 404 → `bge-m3` 覆盖说明；`:11434` 连接拒绝说明；`base_url/api_key` 启动失败说明）；`docs/goal/01-mapping.md` G3 行；`feature_list.json` 追加 G3 条目（15/15）
- **G4**：`~/.kb-server/datasources.json` 写入 `active=es-prod`；`_build_default_components()` 启动加载路径产 `datasource.from_saved` 日志；`/v1/files/import` README.md 真写入 ES 9.5（`elasticsearch.index.created` 日志）；`/v1/search` 真实打分 0.74+；`docs/RUNBOOK.md` §3a 接入示例（`hosts` 而非 `url`）；`feature_list.json` 16/16。
- **G5**：`server/app/embedding/openai_compat.py`（重试主循环 + `_is_retryable_response` + `_backoff_for` + `kb_status_code` / `kb_retryable` 辅助 attr；`max_retries=3`, `initial_backoff=0.5s`, `max_backoff=8s`, `backoff_jitter=0.1`）；`server/tests/embedding/test_embedders.py`（提取 `_Resp` 到模块级 + 新增 `_ScriptedTransport` + `_RecordingClient` + 7 项单测）；`docs/RUNBOOK.md` §2a（调参与不重试矩阵）；`docs/KNOWN_ISSUES.md`（KI-03 收敛）；`docs/goal/01-mapping.md` 向量化行 + 已完成段补 G5；`docs/construction/g5-retry-backoff.md`（迭代协议）；`feature_list.json` 17/17；`progress.md` / `session-handoff.md` G5 记录。
- **H1**（纯文档轮，**零生产代码改动**）：`quality-document.md`（9 维 → 11 维 + 全部数值换实测）；`clean-state-checklist.md`（快照 G1 → G7 + `.gitignore` 项改为"已生效" + 新增 2 项未勾选欠账项）；`evaluator-rubric.md`（整篇重写：上下文 T1 → G7 累计 + 双层可观测性补分 + 偏差表 + 后续动作）；`feature_list.json`（仅 `last_updated`）；`progress.md`（实测基线表 + H1 条目 + What's Next 重排）；`session-handoff.md`。
- **H2**（纯文档轮，**零生产代码改动**）：`docs/PROCESS.md`（重写：新增 §迭代分类与评估策略 + §记录口径约定；修正阶段表 / 当前迭代 / 迭代列表 7 → 21 行）；`docs/construction/h2-process-policy.md`（新建，含 H1 协议补记）；`evaluator-rubric.md`（过程维度重评 3 → 4 + 交接准备度 4 → 5 + 新增重复键偏差行 + 结论 Accept）；`feature_list.json`（+2 条目至 21，修复 5 处重复 `evidence` 键）；`quality-document.md`（两个 B 回升 + Overall A- → A）；`clean-state-checklist.md`（Harness Integrity 段按新政策重写）；`progress.md` / `session-handoff.md`。

## Decisions Made

- 累计迭代：5 个 construction + 1 个 transition + 3 个补充收敛（C6/C7/C8）+ 7 个 goal（G1-G7）+ 2 个 harness（H1 文档同步 / H2 过程政策）。
- **H1 记录口径**：测试数一律以根级 `npm run test:unit` 为准（它带 `KB_MILVUS_URI=./kb_milvus_lite.db`，Milvus 8 项会全跑）。此前 G7 记的 136 是 Milvus skip 口径，导致口径漂移。H2 已把该约定写进 `docs/PROCESS.md`。
- **H1 评分立场**：双层可观测性两个维度基于仓库实测补分，依据逐条写进 `evaluator-rubric.md` §双层可观测性取证，可复核可推翻——不是拍脑袋给分。
- **H2 政策取舍**：面对"G1-G7 零评估报告"，选择**确立明文政策**而非回溯补 7 份报告（用户决策）。理由：回溯写作的信息全部来自 `progress.md`，是把自述换个文件名重述一遍，边际价值低于消除规则缺位这个根因。但政策必须写明**免除的论据**和**升级的触发条件**，否则就是把"没写"重新包装成"不用写"。
- **H2 不回溯原则**：G1-G4 无协议、G1-G7 无评估报告，统一显式追认、政策自 H2 起生效。同时把 G6 命中两条升级条件这一事实留档为判例——追认不等于粉饰，工件缺失照实记录在 `evaluator-rubric.md` 的扣分理由里。
- **G3 默认锁定**：用户决策。settings.py embed_backend 默认 `openai-compat` (Ollama)，pytest conftest 强制 mock，eval 默认走 Ollama。
- **G4 真实 ES 接入**：用户场景提供 ES 9.5.0 + 凭证；通过 `/v1/datasources/configs` + `/active` API 写入 `~/.kb-server/datasources.json` 的 `active=es-prod`；重启加载 → 启动期 `datasource.from_saved` 日志 → 真 ES 上跑 import/search；8 chunks 真存（_count API）；`vector.dims=1024` mapping OK；`/v1/search` 实分 0.74+；ES 索引 `bbq_hnsw`（ES 9.x 默认）。
- Python 服务默认走 mock embedder；缺 sentence-transformers 自动降级。
- 数据源抽象：add / search / delete / health；`capabilities()` 扩展。
- 桌面端：主进程拉 Python 子进程 + watchdog；preload 唯一 IPC。
- KI-02：**只**日志 + 文档化迁移路径；**不**内置 dump / load。
- KI-07：VARCHAR 主键 schema + Lite 兜底。
- G1：根级 `package.json` 聚合 npm scripts；pytest 走 Lite 跑满 89 项。
- G2：数据源配置用 **JSON 文件**（可 `cat` / 可 git 共享 / 可备份）而非 SQLite；原子写 `os.replace`；损坏文件 `.corrupt` 备份自愈；**active 切换只在下次启动生效**（运行时热切换的并发风险见 KI-02 C8 设计原则，UI 与 RUNBOOK 都明示）。
- G5：指数退避只放 `openai-compat`；`Embedder` 抽象契约不变；其它 embedder（mock / bge-m3）无需此能力。引入 `kb_status_code` / `kb_retryable` 作为辅助 attr 不开新异常类型；外层 `try/except EmbedderError` 仍稳定。`max_retries=0` 等价禁用重试。
- G6：进度回调从 `Callable[[float], None]` 升级到 `Callable[[ProgressEvent], None]`（破坏性变更，但唯一生产调用点 `_run_import` 已同步更新；pipeline 单测同步升级）。`TaskStore` v1 schema 自动迁移（`ALTER TABLE ... ADD COLUMN stage` + `PRAGMA user_version=1`），老 `tasks.db` 不丢数据。事件 ring buffer 32 条（写入时 trim），嵌入 `TaskResponse.events` 让渲染端免一次 IPC；`/events?since_id=` 备用端点留给未来 live-tail 订阅者。`stage` 默认 `queued`；旧服务器负载 fallback 兼容。
- G7：仅 ES 适配器实现 `list_chunks` + `aggregate_by_document`，通过新增 `capabilities() == {"metadata_filter", "delete_by_filter", "bm25_hybrid", "chunk_list"}` 声明；其它 adapter（vector / postgres / mysql / milvus）维持默认 `NotSupportedError`，browse 端点统一转 501。Browse 端点读**当前启动期绑定的 active DataSource 实例**（与 import pipeline 同一份），遵循 G2 "active 切换只在下次启动生效"。`ChunkSummary` / `DocumentSummary` 放 `observability/models.py`（沿用 `Hit` / `Chunk` 约定）。`aggregate_by_document` 异常降级为 `{}` 而不是 500（ES 动态 mapping 缺字段时偶发）。
- `feature_list.json` 早期条目使用中文弯引号 “…”；新条目请沿用。

## Blockers / Risks

- 真实 BGE-M3 模型权重未在 CI 验证；脚本 (`scripts/download_bge_m3.sh`) 与 `--embedder bge-m3` 路径就绪。
- 本机 docker mirror 对 `milvusdb/milvus:v2.4.10-standalone` 返回 403；Milvus Lite (`./kb_milvus_lite.db`) 1:1 兜底。
- MySQL adapter 在数据逼近 `max_scan_rows` 时持续打 warning；规模真增长需 C9 dump / load CLI 突破。
- G2 决策边界：active 切换运行时**不**热生效——必须重启桌面端。改进路径：引入 datasource 池 + 信号量在后台替换 pipeline（见 progress.md "What's Next" §4）。
- goal.md 假设的 `src/backend` `src/frontend` 不存在；功能 100% 覆盖详见 `docs/goal/01-mapping.md`。
- G5 边界：退避只覆盖**单次 embedding call**；pipeline 层面（一次 import 跑多个 batch 时的部分失败重试）仍由上层 orchestrator 决定；当前 `IndexingPipeline` 直接传 `embedder.embed`，不在 embedder 内部重试整批。
- 其余详见 `docs/KNOWN_ISSUES.md`。

## Next Session Startup

1. 阅读 `README.md`、**`docs/PROCESS.md` §迭代分类与评估策略（开新迭代前必读）**、`progress.md`、`session-handoff.md`、`docs/goal/01-mapping.md`、`docs/RUNBOOK.md` §2。
2. 跑 `bash init.sh`，或直接 `npm run verify`（根级聚合）。当前基线 **144 passed**——低于此数先查原因再动代码。
3. 开迭代前先按 `docs/PROCESS.md` §升级触发条件自查：命中破坏性接口变更 / schema 迁移 / 新增数据源或 embedder 后端 / 安全边界任一条，就不能走自验，必须出独立评估报告。
4. 读 `evaluator-rubric.md` §双层可观测性取证，了解剩余两处 4 分项（运行时缺追踪、政策待实践检验）。
5. 检查 `docs/KNOWN_ISSUES.md` 决定下一迭代。

## Recommended Next Step

**过程侧只剩一项待验证**

1. 下一轮 G 类迭代收尾时，验证 H2 政策的"自验四项最低要求"与四条升级触发条件是否**真的可判定**。这是过程可观测性从 4 升 5 的唯一前置条件——规则写得清楚 ≠ 规则可执行。

**功能候选（挑一个）**

2. （成本最低、闭环最完整）Settings "Test connection" 成功后调 `mark_tested` 写 `last_tested_at` + UI ✓ 标记——后端已就绪，只差一次调用；H1 已确认它是有测试无调用方的死代码。注意：若改动 IPC 协议则命中"破坏性接口变更"，需升级为独立评估。
3. （对应运行时可观测性 4/5 缺口）引入 `request_id` + `bind_contextvars`，让已挂载的 `merge_contextvars` 真正生效，把 search / browse 路径纳入关联。不改契约，可走自验。
4. KI-01（PDF OCR）/ KI-08（Word 图片、批注）/ KI-10（better-sqlite3 cross-compile）——都不阻塞，按实际遭遇频率选。
5. CI 引入 docker compose 服务化 Milvus，让 1:1 套件 CI 自动跑。
6. （可选）`active` 热切换 + datasource 池；或把 G5 退避抽成 `app/utils/backoff.py`（H1 已确认该文件不存在）。
