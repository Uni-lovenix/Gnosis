# Session Progress Log -- 灵知 (Gnosis)

## Current State

**Last Updated:** 2026-08-08T00:00:00.000Z
**Active Feature:** ES 数据浏览页（goal-es-browse / G7）
**Current RUP Phase:** transition（已通过）
**Current Iteration:** G1 (映射) ✅ + G2 (CRUD) ✅ + G3 (Ollama 真模型 + 默认锁定) ✅ + G4 (真实 ES 当默认数据源) ✅ + G5 (KI-03 OpenAI 兼容远端重试退避) ✅ + G6 (上传进度可观测性) ✅ + **G7 (ES 数据浏览页)** ✅

## Status

### Repo & Sync

- [x] 仓库已初始化：`git init -b main`；`.gitignore` 排除 `node_modules/`、`*.db`、`desktop/dist/`、`server/var/`、`.pytest_cache/`、`.env*` 等。
- [x] 远端 `origin` = `https://github.com/Uni-lovenix/Gnosis.git`（push 完成，`HEAD = 54eab40`，初始提交 ~0.78 MB、159 文件）。
- [x] 后续每个版本：本地通过 `npm run verify` → `git add -A` → `git commit -m "vX.Y: ..."` → `git push origin main`（详见 `session-handoff.md` §"Per-Version Sync Workflow"）。

### What's Done

- [x] RUP harness 和团队配置已初始化。
- [x] 启动范围确认（inception）：`docs/inception/{01,02,03}-*.md`
- [x] 架构与风险细化（elaboration）：`docs/elaboration/{01,02,03}-*.md`
- [x] C1 数据与报表：4 类数据源适配器；评估 5/5。
- [x] C2 文件与同步：4 类解析器 + 切片器 + 任务存储；评估 5/5。
- [x] C3 AI 与智能体：embedding + 流水线 + 评测 9/10；评估 5/5。
- [x] C4 多端体验：Electron + React + TS；3 个 tsconfig 0 errors + Vite build；评估 5/5。
- [x] T1 移交：README.md、docs/API.md、docs/RUNBOOK.md、docs/KNOWN_ISSUES.md、docs/transition/README.md。
- [x] C5 已知问题修复（KI-04 / KI-05 / KI-06）：评估 4.75/5 Accept。
- [x] C6 KI-09 任务表过期清理：`TaskStore.purge_stale(ttl_days=30)`。
- [x] C7 KI-07 Milvus 1:1 单测：8 用例 + docker 启动脚本 + Lite 兜底；评估 5/5。
- [x] C8 KI-02 MySQL O(N) 性能收敛：`MysqlAdapter` 构造期 + 检索期 warning；`capabilities()` `scan_limit_risk`；评估 5/5。
- [x] **G1 goal.md → 实际项目栈映射**：根级 `package.json` 聚合 npm scripts；`docs/goal/01-mapping.md` 三层映射表；9/10 eval；vite 148.70 kB。
- [x] **G2 数据源配置 CRUD**：
  - 后端：`server/app/observability/datasource_store.py`（v1 schema、原子写 `os.replace`、损坏文件自动备份）；`POST/GET/DELETE /v1/datasources/configs`、`GET/PUT/DELETE /v1/datasources/active`；build 阶段 fail-fast（未知 type / 缺失依赖 → 清晰错误）。
  - 启动路径：`KB_DATA_DIR/datasources.json` 优先；失败回退 in-memory vector；日志事件 `datasource.from_saved` / `datasource.active_load_failed` / `datasource.default_in_memory`。
  - 前端：SettingsPage 完整闭环 — Add / Edit / Save / Test / Activate / Delete / Clear active + JSON options 编辑 + toast 反馈；CSS 新增 `.kb-configs` `.kb-row-active` `.kb-toast*`。
  - IPC：KBAPI 新增 6 个方法，main + preload + shared types 对齐。
  - 测试：`tests/test_datasource_store.py`（16 项）+ `tests/test_datasource_configs_api.py`（8 项，含 active 启动加载）。
  - 文档：`docs/API.md` §数据源 新增 CRUD 段；`docs/RUNBOOK.md` §"数据源配置管理"含 5 类 type options 模板 + 排错；`docs/goal/01-mapping.md` "配置管理" 行升级为 G2 引用。
  - 验证：`npm run verify`（113 passed；含 G2 新增 24 项）+ `npm run eval` 9/10 (90%) + `npm run build` Vite 152.27 kB（CSS 增 3.48 kB）；端到端 smoke：POST/GET/PUT/DELETE 全部 200；active 配置在 `_build_default_components()` 看到 `datasource.from_saved` 与 `ds.name='mem'`。
- [x] **G3 Ollama bge-m3 真模型端到端**（KI-06 收敛）：
  - `scripts/start_server_ollama.sh` 一键启动：自动设 `KB_EMBED_BACKEND=openai-compat`、`KB_OPENAI_BASE_URL=http://127.0.0.1:11434/v1`、`KB_OPENAI_MODEL=bge-m3`、`KB_OPENAI_API_KEY=ollama`。
  - 根级 npm 新增 `server:ollama`、`eval:ollama`、`eval:bgem3` 3 个 scripts。
  - `eval/run_eval.py` 新增 `--embedder openai-compat` 分支；CI 默认仍是 mock，Ollama 路径用户触发。
  - 验证：用户已装 Ollama + bge-m3:latest（1024-dim、F16）。`/v1/health` 返回 `embed_backend=openai-compat`；`/v1/files/import` README.md → 3 chunks、embedded=3、status=done；`/v1/search` 真实打分：
    - "哪些数据源支持向量检索" → 0.5515 / 0.4412
    - "embedding 模型选用什么" → 0.4563 / 0.4438
    - "草莓冰淇淋最佳配方"（无关）→ 0.3335 / 0.3298（明显低于相关查询）
  - `npm run eval:ollama`：**10/10 = 100%**（mock 9/10 = 90%；门禁 ≥ 60% 大幅超越）。
  - `docs/KNOWN_ISSUES.md` KI-06 移入收敛表；`docs/RUNBOOK.md` §2 Ollama bge-m3 启动 + 排错；`docs/goal/01-mapping.md` G3 行；`scripts/start_server_ollama.sh`（152 字节 → 一行 chmod +x）。
- [x] **G4 真实 ES 当默认数据源**：`datasources.json` 写入 `active=es-prod`（ES 9.5.0 + elastic 凭证）；`_build_default_components()` 启动日志 `datasource.from_saved name=es-prod type=elasticsearch`；`/v1/files/import` README.md 真写入 ES 9.5（自动创建 `kb_chunks` 索引 bbq_hnsw 1024-dim cosine）；`/v1/search` "embedding 模型选用什么" top_k=3 → score 0.7415/0.7415/0.7371；`_count=8`；`docs/RUNBOOK.md` §3a 完整接入示例（修复早期 url→hosts 字段错误）。
- [x] **G5 KI-03 OpenAI 兼容远端指数退避**：
  - `server/app/embedding/openai_compat.py` 引入指数退避主循环：仅对 `httpx.TransportError` / HTTP 5xx / 429 重试（4xx 立即抛 `EmbedderError`，不浪费重试预算在配置错误上）；退避公式 `min(initial × 2^(n-1), max_backoff) × (1 ± jitter)`，默认 `initial=0.5s, max=8s, jitter=0.1, max_retries=3`（= 初始 + 3 重试 = 4 次总尝试）；4 个 options 全可配。
  - 每次重试打 `embedder.retry` warning 日志（字段：`attempt` / `max_attempts` / `status_code` 或 `error_kind` / `sleep_seconds`）；耗尽抛 `EmbedderError("remote embed failed after N attempt(s): ClassName: ...")`，原异常链保留。
  - `EmbedderError` 增辅助 attr `kb_status_code` / `kb_retryable`（不污染既有契约；调用方仍 `isinstance(e, EmbedderError)` 即可）。
  - 测试：`tests/embedding/test_embedders.py` 提取 `_Resp` 到模块级 + 新增 `_ScriptedTransport` + `_RecordingClient` 试驱动；新增 7 项单测：瞬时错误重试至成功 / 耗尽抛错含 attempts + 原异常类 / 4xx 不重试无 sleep / 429 重试 / 5xx (502/503) 重试 / 退避数学阶梯 [0.5, 1.0, 2.0, 2.0] / `embedder.retry` 日志 capture_logs 断言。
  - 文档：`docs/RUNBOOK.md` §2a 调参与不重试矩阵；`docs/KNOWN_ISSUES.md` KI-03 移入收敛表；`docs/goal/01-mapping.md` 向量化行 + 已完成段补 G5；`docs/construction/g5-retry-backoff.md` 协议。
  - 验证：`npm run verify` 全绿（check / lint 0 errors；test:unit 113 → **120 passed**；test:integration 120 passed）。
- [x] **G6 上传进度可观测性（阶段文字 + 事件日志）**：
  - 后端：`server/app/observability/models.py` 新增 `TaskStage` 枚举（queued/parsing/chunking/embedding/writing/done/failed）+ `TaskEvent` 模型 + `TaskStatus` 扩展 `stage` + `events`（默认 `[]`）；`server/app/observability/task_store.py` v1 schema 迁移（`ALTER TABLE tasks ADD COLUMN stage TEXT NOT NULL DEFAULT 'queued'` 幂等 + 新表 `task_events(id PK, task_id FK, ts, stage, progress, message)` ring buffer 32 + `ix_task_events_task_id(task_id, id)` + `PRAGMA user_version=1`）；`add_event` trim-to-32；`list_events` / `list_events_since(since_id)` / `last_event_id`；`update()` 加 `stage=` kwarg；`get()` 联表返回 events。
  - `server/app/pipeline/indexing.py` `IndexingPipeline.on_progress` 签名升级到 `Callable[[ProgressEvent], None]`（破坏性变更，唯一生产调用点 `_run_import` 同步更新；pipeline 单测同步升级）；4 处边界发事件：`parsing (0.05, message=文件名)` / `chunking (0.30, message=N chunks)` / `embedding (0.30+0.50·frac, message=已处理/总数 chunks embedded)` / `writing (1.0, message=wrote N chunks)`。
  - `server/app/api/files.py` `_run_import` 接入 stage：`store.update(stage=, progress=)` + `store.add_event(...)` 在每个边界调一次；新增 `GET /v1/files/tasks/{task_id}/events?since_id=N` 备用端点（返回 `TaskEventsResponse {events, next_since_id}`），渲染端当前仍消费嵌入 `TaskResponse.events`。
  - 前端：`desktop/src/shared/types.ts` 加 `TaskStage` type + `TaskEvent` interface + `TaskStatus` 加 `stage: TaskStage` + `events: TaskEvent[]`；`desktop/src/renderer/lib/state.ts` `AppState.indexing` 加 `stage` / `events` / `lastMessage`；`onProgress` 监听器同步更新（`stage ?? "queued"` / `events ?? []` 兼容旧服务器）；`desktop/src/renderer/pages/ImportPage.tsx` 重写：进度条 + 阶段 tag（不同 stage 不同配色）+ 折叠 `<details>` 事件日志（时间戳 + stage + progress + message，按时间倒序展示）；`desktop/src/renderer/styles.css` 加 `.kb-stage-tag` `.kb-stage-{queued,parsing,chunking,embedding,writing,done,failed}` `.kb-event-log` `.kb-event-ts` `.kb-event-progress` 系列样式；`desktop/src/main/api-client.ts` 镜像 `TaskStage` / `TaskEvent` / `TaskStatus`。
  - 复用：零 IPC 改动（沿用 `kb:progress`）；复用 `SettingsPage` toast 模式；复用 `pollTask` 600ms 轮询；复用 `DocumentsPage.LoadState` 风格（虽然未在 ImportPage 使用）。
  - 测试：`server/tests/test_task_store.py` +7 项（stage round-trip / 默认 queued / add_event 写入 / ring buffer 32 截断 / list_events_since 分页 / last_event_id 未知任务 / **schema 迁移老库**）；`server/tests/api/test_task_progress_api.py` 新建 +5 项（端到端 import 后 stage=done + events ≥ 4 / `/events` 全量 / `since_id` 分页 / 404 / **旧负载 fallback**）；`server/tests/pipeline/test_pipelines.py` 升级到 ProgressEvent（删除旧 `pipeline.on_progress = progress.append` 用例，新增 message + stage 校验）。
  - 文档：`docs/API.md` §TaskStatus 加 `stage` + `events` + 新增 `/events?since_id=` 段；`docs/RUNBOOK.md` §4a "上传进度可观测性"（阶段映射 + structlog 事件 `pipeline.stage` + sqlite 直查 + 调优提示）；`docs/goal/01-mapping.md` G6 行；`docs/construction/g6-upload-progress.md` 迭代协议；`feature_list.json` 17 → **18 pass**；`progress.md` / `session-handoff.md` G6 记录。
  - 验证：`pytest tests/` 113 → **125 passed**（+12 G6 new：7 task_store + 5 progress_api）；`npm run verify` test:unit 120 → 125 / test:integration 120 → 125；`npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite 152.27 → **153.74 kB**（+1.47 kB，远低于 +5 kB 目标）。
- [x] **G7 ES 数据浏览页（chunk-level + 文档聚合 + 过滤 + 分页）**：
  - 后端：`server/app/datasources/base.py` 新增 `NotSupportedError` + `DataSource.list_chunks` / `aggregate_by_document` 默认抛 `NotSupportedError`；`server/app/observability/models.py` 新增 `ChunkSummary` / `DocumentSummary` 模型；`server/app/datasources/elasticsearch_adapter.py` `capabilities()` 增 `"chunk_list"`，实现 `list_chunks`（match_all + bool filter on document_id / metadata.parser + from/size 分页 + sort `(document_id, chunk_id)` + text 服务端截 240 字 + `_source` 限定）与 `aggregate_by_document`（ES `terms` agg on document_id size=1000 + 嵌套 `terms` on metadata.parser + `top_hits` 取 sample）；`server/app/api/chunks.py`（新）`GET /v1/chunks?document_id&parser&offset&limit` 返回 `BrowseResponse {chunks, total, aggregations}`，400/422 非法参数、501 capability 缺失、503 active 未绑定；`server/app/main.py` 启动期 `chunks_api.set_active_datasource(ds)` 绑定。
  - 前端：`desktop/src/shared/types.ts` + `desktop/src/main/api-client.ts` 加 `ChunkSummary` / `DocumentSummary` / `BrowseResponse` / `BrowseOpts` + `ApiClient.browseChunks(opts)`；`desktop/src/preload/index.ts` + `desktop/src/main/index.ts` 加 `browseChunks` IPC handler；`desktop/src/renderer/App.tsx` Tab union 加 `"browse"`，nav 顺序调整为 `import | search | browse | documents | settings`；`desktop/src/renderer/pages/BrowsePage.tsx`（新）：active ds 角标 + 不支持时永久警告横幅 + parser 下拉 + document_id 输入（250ms debounce）+ 文档聚合表（点击行 = 应用 document_id 过滤）+ 分页（prev/next + offset/limit + total）+ chunk 列表（preview + 折叠 `<details>` JSON metadata）+ 错误 toast；`desktop/src/renderer/styles.css` 加 `.kb-chunks` `.kb-agg-table` `.kb-banner-warn` `.kb-browse-filters` `.kb-pagination` 系列样式。
  - 测试：`server/tests/datasources/test_elasticsearch_adapter.py` 扩 5 项（list_chunks 分页 + sort + 文本截断 + 过滤；aggregate_by_document 分组；ES 异常降级为空 dict；capabilities 包含 chunk_list）；`server/tests/api/test_chunks_api.py`（新）7 项（200 完整响应 / 过滤参数透传 / 400 或 422 limit 非法 / 400 或 422 负 offset / 501 capability 缺失 / 503 active 未绑定 / aggregate 抛 NotSupportedError 转 501）。`pytest tests/` 125 → **136 passed**（+11 G7 new）。
  - 文档：`docs/API.md` §浏览 新增 `GET /v1/chunks` 段；`docs/RUNBOOK.md` §4b ES 数据浏览 + §3 capability 列表增 `chunk_list`；`docs/goal/01-mapping.md` G7 行 + "已完成" 段；`docs/construction/g7-es-browse.md` 协议；`progress.md` / `session-handoff.md` G7 记录；`feature_list.json` 18 → **19 pass**。
  - 验证：`npm run verify` test:unit 125 → 136 / test:integration 125 → 136 全绿；`npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite 153.74 → **158.61 kB**（+4.87 kB）；ES 端到端：ES 9.5.0 跑 + G4 留下的 8 chunks → browse tab 看到 chunks + 聚合行 + 过滤 + 分页均正确。

### What's In Progress

- 无。G7 已收尾。所有 KI-02 / KI-03 / KI-04 / KI-05 / KI-06 / KI-07 / KI-09 均收敛；仅 KI-01 / KI-08 / KI-10 仍 open（低-中严重度、不阻塞个人生产使用）。

### What's Next

1. 推荐下一迭代：KI-01（PDF OCR）或 KI-08（Word 图片 / 批注）或 KI-10（better-sqlite3 arm64 cross-compile）。已不再是阻塞项，按用户实际遭遇频率决定先后。
2. CI 引入 docker compose 服务化 Milvus，让 conftest 默认 URI 指向 `http://milvus:19530`，1:1 套件 CI 自动跑。
3. （若数据增长触发 `scan_limit_hit` 高频告警）C9 单独开迭代做数据迁移工具（dump / load CLI），突破 C8 收敛边界。
4. （可选）`active` 切换运行时热生效：当前只影响下次启动；要做需引入 datasource 池 + 信号量，避免正在跑的 import 半途切换。
5. （推荐新增）把 Settings → "Test connection" 成功后自动调 `mark_tested` 写 `last_tested_at`，UI 上加 ✓ 标记；目前该事件仅 main 进程直接调才生效。
6. （可选，G5 后续）将指数退避提炼成 `app/utils/backoff.py` 通用工具，给 datasource 慢路径也复用；目前仅 openai-compat 用，先验证价值再抽象。

## Blockers / Risks

- 详见 `docs/KNOWN_ISSUES.md`（KI-01 / KI-08 / KI-10 仍 open；KI-02 / KI-03 / KI-04 / KI-05 / KI-06 / KI-07 / KI-09 已收敛）。
- KI-06 真实 BGE-M3 模型评测：本机未执行（缺 sentence-transformers + 权重）；mock 路径 9/10 维持门禁。
- C7 / KI-07：本机 docker mirror 对 `milvusdb/milvus:v2.4.10-standalone` 返回 403；Milvus Lite (`./kb_milvus_lite.db`) 1:1 兜底。
- G1：goal.md 假设的 `src/backend` `src/frontend` 目录在本仓库不存在；功能 100% 已覆盖，详见 `docs/goal/01-mapping.md`。
- G2：active 切换只影响下次 server 启动（设计如此）；用户改 active 后需要重启桌面端才生效（避免正在跑的 pipeline 半途切换）。这一边界在 RUNBOOK §2 与 SettingsPage 帮助文本里都写明了。

## Decisions Made

- RUP 四阶段 + 迭代协议管理；5 个 construction 迭代 + 1 个 transition + 3 个补充收敛迭代（C6 / C7 / C8）+ 7 个 goal 迭代（G1 映射 / G2 数据源 CRUD / G3 Ollama bge-m3 / G4 真实 ES / G5 KI-03 重试退避 / G6 上传进度可观测性 / **G7 ES 数据浏览页**）。
- Python 服务默认走 mock embedder；缺 sentence-transformers 自动降级（事件 `embedder.fallback_to_mock`）。
- 数据源抽象最小能力集：add / search / delete / health；特性能力按适配器扩展。
- 桌面端架构：主进程拉起 Python 子进程 + watchdog；preload 唯一 IPC 暴露点。
- KI-04：文档目录以**桌面端 SQLite**为单一来源。
- KI-05：Python 后端**不**打包进 Electron 产物，运行时通过 `KB_PYTHON` 解析。
- KI-06：CI 仍跑 mock 路径；真实 BGE-M3 路径按需在本机执行。
- KI-07：`_MilvusBackend` 显式 VARCHAR 主键 schema；conftest 通过 `KB_MILVUS_URI` 同时支持 http(s) standalone 与本地 Lite 路径。
- KI-02：**只**打日志 + 文档化迁移路径，**不**内置 dump / load CLI；warning 而非 exception 与现有截断语义一致；`capabilities()` `scan_limit_risk` 声明风险。
- G1：根级 `package.json` 聚合 npm scripts（不动 desktop 的 start/build/dev）；桌面端 `lint` 约定即 tsc 类型检查；pytest 走 Lite 路径跑满 89 项（原 89 → 现 113）。
- G2：数据源配置文件选 **JSON**（用户可 `cat` / `git` 共享 / 备份）；原子写 `os.replace` 避免半截文件；损坏文件自动 `.corrupt` 备份后启动。**active 切换只影响下次启动**（运行时热切换风险见 KI-02 C8 设计原则）；未知 type / 缺依赖由 build() 抛错，UI / API 透传为 400 给清晰排错信息。
- G4：真实 ES 接入不引入 docker compose；用户在跑 ES 9.5.0 + 凭证就够，写入 `datasources.json` 走 `_build_default_components()` 启动加载路径；G2 的 v1 schema 已经包含 elasticsearch type，适配器无需改动；ES 9.x 默认 `bbq_hnsw` 自动优于 8.x 的 `hnsw`，mapping 字段名从 `url` 改为 `hosts`（适配器要求）。
- G5：KI-03 重试退避只放在 `openai-compat`（最常见的瞬时错误来源），不改 `Embedder` 抽象契约；其它 embedder（`mock-hash` 无网络、`bge-m3` 本地推理）不背此复杂度。引入辅助 attr `kb_status_code` / `kb_retryable` 而不是新的异常类型，让外层 `try/except EmbedderError` 保持稳定。`max_retries=0` 等价禁用重试，给排错留逃生口。
- G6：`IndexingPipeline.on_progress` 签名从 `Callable[[float], None]` 升级到 `Callable[[ProgressEvent], None]` —— 破坏性变更，但**唯一生产调用点**是 `_run_import`，已同步更新；pipeline 单测同步升级。`TaskStore` v1 schema 迁移自动完成（`ALTER TABLE ... ADD COLUMN stage` 用 try/except OperationalError 兜底重复添加；`PRAGMA user_version=1` 标版本），老 `tasks.db` 不丢数据。事件 ring buffer 32 条，嵌入 `TaskResponse.events` 让渲染端免一次额外 IPC；`/events?since_id=` 备用端点留给未来 live-tail 订阅者。`stage` 默认 `queued`，旧服务器负载 fallback 兼容（前端 `t.stage ?? "queued"`）。`pipeline.stage` structlog 事件在每个 stage 边界打一次，附带 task_id + stage + progress + message 字段。
- G7：仅 ES 适配器实现 `list_chunks` + `aggregate_by_document`，通过新增 capability `"chunk_list"` 声明；其它 adapter（vector / postgres / mysql / milvus）维持默认 `NotSupportedError`，browse 端点统一转 501。理由见 `progress.md` "数据源抽象最小能力集"。Browse 端点读**当前启动期绑定的 active DataSource 实例**（与 import pipeline 同一份），遵循 G2 决策"active 切换只在下次启动生效"。新增 `ChunkSummary` / `DocumentSummary` 放 `observability/models.py`（沿用 `Hit` / `Chunk` 的现有约定）。`aggregate_by_document` 失败时降级为 `{}` 而不是 500（ES 动态 mapping 缺 `metadata.parser` 字段时偶发）；BrowsePage 把 ES 异常用 toast + 永久 banner 区分（banner 用于不支持 capability；toast 用于瞬时错误）。

## Notes for Next Session

- 当前仓库 `feature_list.json` 全部 `pass`（19/19，G7 新增）。
- 下次启动：`bash init.sh` → 阅读 README → PROCESS → KNOWN_ISSUES → `docs/goal/01-mapping.md` → RUNBOOK §2 数据源配置管理。
- 任何接口变更必须同步 `docs/elaboration/01-architecture-baseline.md` 与 `docs/API.md`。
- `feature_list.json` 描述统一使用中文弯引号 “…”；新增条目沿用。
- 根级 `npm scripts` 是聚合入口，desktop 与 server 仍按各自路径运行。
- G2 涉及文件：`server/app/{observability/datasource_store.py,api/datasources.py,main.py}`；`desktop/src/{shared/types.ts,main/{index.ts,api-client.ts},preload/index.ts,renderer/pages/SettingsPage.tsx,renderer/styles.css}`；测试 `server/tests/{test_datasource_store.py,test_datasource_configs_api.py}`；`docs/{API.md,RUNBOOK.md,goal/01-mapping.md}`。
- **G3 决策：生产默认 = Ollama bge-m3（用户规则）** — 用户决策：把真模型路径固化，避免新会话或协作者误把 mock 当默认。
  - `server/app/config/settings.py`：`embed_backend` 默认 `"openai-compat"`（不再是 `bge-m3`），`openai_base_url/api_key/model` 默认指向 Ollama。
  - `server/tests/conftest.py`：强制 `KB_EMBED_BACKEND=mock-hash` 隔离测试，让 pytest 永远走 mock（不打外部、保持 3s 快速）。
  - `server/eval/run_eval.py`：`--embedder` 默认从 `mock` 改 `openai-compat`；mock / bge-m3 仍可指定。
  - 根级 `package.json`：`eval` 默认走 Ollama；新增 `eval:mock` / `eval:bgem3` / `server:ollama`。
  - 设计取舍：openai-compat 懒连接；启动日志新增 `embedder.ready` / `embedder.fallback_to_mock` + 每 backend 的单行修复 hint（如 "ollama serve && ollama pull bge-m3"）。
  - 文档：`docs/RUNBOOK.md` §0 "Embedder 默认（核心规则）"上移到第一节；`README.md` 快速开始直接走 Ollama。