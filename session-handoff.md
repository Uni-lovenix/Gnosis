# Session Handoff -- 个人知识库

## Current Objective

- Goal: 1. 支持多数据源配置（elasticsearch、postgresql、mysql、向量数据库）
  2. 文件导入（excel、word、pdf、markdown）
  3. embedding 模型 bge-m3
  4. 向量化后存入数据库
- Current status: **G1 / G2 / G3 / G4 / G5 / G6 / G7 全 pass**；`feature_list.json` 19/19 = pass。
  - G5 = KI-03 收敛（OpenAI 兼容远端指数退避）。`npm run verify` 120 passed（113 + 7）；`embedder.retry` 结构化日志可见。
  - G6 = 上传进度可观测性（阶段文字 + 事件日志）。`TaskStore` v1 schema（`stage` 列 + `task_events` ring buffer）；`TaskResponse.events` 嵌入最近 32 条；`npm run verify` 125 passed（113 + 12）；前端 ImportPage 新增 stage tag + 折叠事件日志；Vite 153.74 kB。
  - G7 = ES 数据浏览页（chunk-level + 文档聚合 + 过滤 + 分页）。`ElasticsearchAdapter` 加 `list_chunks` + `aggregate_by_document`；`DataSource` 基类新增可选 `list_chunks`/`aggregate_by_document`（默认抛 `NotSupportedError`，仅 ES 实现 `chunk_list` capability）；新增 `GET /v1/chunks`；前端 BrowsePage（parser 下拉 + document_id debounce 输入 + 聚合表 + 分页 + 不支持 capability 永久 banner）；`npm run verify` 136 passed（125 + 11）；Vite 158.61 kB。
- Branch / commit: 待下一会话填写

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
- [x] **G7 ES 数据浏览页**：`server/app/datasources/base.py` 新增 `NotSupportedError(DatasourceError)` + `DataSource.list_chunks` / `aggregate_by_document` 默认抛 `NotSupportedError`；`server/app/observability/models.py` 新增 `ChunkSummary` / `DocumentSummary`；`server/app/datasources/elasticsearch_adapter.py` `capabilities()` 增 `"chunk_list"`，实现 `list_chunks`（match_all + bool filter + from/size + sort + `_source` 限定 + text 服务端截 240 字 + ES 异常降级为空 dict）+ `aggregate_by_document`（ES terms agg + 嵌套 parser terms + top_hits sample + 异常降级）；`server/app/api/chunks.py`（新）`GET /v1/chunks?document_id&parser&offset&limit` 返回 `BrowseResponse {chunks, total, aggregations}`，400/422 非法参数、501 capability 缺失、503 active 未绑定；`server/app/main.py` 启动期 `chunks_api.set_active_datasource(ds)` 绑定；前端 `desktop/src/shared/types.ts` + `desktop/src/main/api-client.ts` 加 `ChunkSummary` / `DocumentSummary` / `BrowseResponse` / `BrowseOpts` + `ApiClient.browseChunks(opts)`；`desktop/src/preload/index.ts` + `desktop/src/main/index.ts` 加 `browseChunks` IPC handler；`desktop/src/renderer/App.tsx` Tab union 加 `"browse"`；`desktop/src/renderer/pages/BrowsePage.tsx`（新）：active ds 角标 + 永久 `.kb-banner-warn`（不支持 capability）+ parser 下拉（seed + 实际 union）+ document_id 输入（250ms debounce）+ 文档聚合表（点击行 = 应用 document_id 过滤）+ chunk 列表（preview + `<details>` 折叠 JSON metadata）+ 分页（prev/next + offset/limit + total）+ 错误 toast；`desktop/src/renderer/styles.css` 加 `.kb-chunks` / `.kb-agg-table` / `.kb-banner-warn` / `.kb-browse-filters` / `.kb-pagination` 系列样式。测试：`server/tests/datasources/test_elasticsearch_adapter.py` 扩 5 项（list_chunks 分页 + sort + 文本截断 + 过滤；aggregate 分组；ES 异常降级；capabilities 含 chunk_list）；`server/tests/api/test_chunks_api.py`（新）7 项（200 完整 / 过滤参数透传 / limit 非法 / 负 offset / 501 capability / 503 active / aggregate NotSupportedError 转 501）。`pytest tests/` 125 → **136 passed**（+11 G7 new）；`npm run verify` 125 → 136 / 125 → 136 全绿；`npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite 153.74 → **158.61 kB**（+4.87 kB）；`docs/API.md` §浏览 + `docs/RUNBOOK.md` §4b + `docs/goal/01-mapping.md` G7 行 + `docs/construction/g7-es-browse.md` 协议；`feature_list.json` 18 → **19 pass**。

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
| `feature_list.json` 合法 | `python3 -c "json.load(open('feature_list.json'))"` | OK（14/14） |
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
| **G7 verify 集成** | `npm run verify` | **136 passed**（test:unit + test:integration 均 136；原 125 + G7 新增 11） |
| **G7 npm check** | `npm run check` | **OK**（tsc 0 errors） |
| **G7 npm build** | `npm run build` | **Vite 158.61 kB**（+4.87 kB vs G6 的 153.74） |

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

## Decisions Made

- 累计迭代：5 个 construction + 1 个 transition + 3 个补充收敛（C6/C7/C8）+ 7 个 goal（G1/G2/G3/G4/G5/G6/G7）。
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

1. 阅读 `README.md`、`docs/PROCESS.md`、`progress.md`、`session-handoff.md`、`docs/goal/01-mapping.md`、`docs/RUNBOOK.md` §2。
2. 跑 `bash init.sh`，或直接 `npm run verify`（根级聚合）。
3. 检查 `docs/KNOWN_ISSUES.md` 决定下一迭代（推荐 KI-03 OpenAI 重试退避 或 KI-01 / KI-08 / KI-10）。

## Recommended Next Step

下一迭代（按用户实际遭遇频率决定先后）：

1. KI-01（PDF OCR）或 KI-08（Word 图片 / 批注）或 KI-10（better-sqlite3 cross-compile）—— 都已不再是阻塞项。
2. CI 引入 docker compose 服务化 Milvus 让 1:1 套件 CI 自动跑。
3. （可选）`active` 热切换 + datasource 池；或 G5 抽象出 `app/utils/backoff.py` 通用工具。
