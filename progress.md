# Session Progress Log -- 灵知 (Gnosis)

## Current State

**Last Updated:** 2026-08-18T00:00:00.000Z
**Active Feature:** G18 HA 配置总览（只读 API + 桌面 Settings 总览；H2 政策首个 G 类自验）
**Current RUP Phase:** 移交后增量（transition 已通过）
**Current Iteration:** G1-G7 全 ✅ + H1/H2 ✅ + C9-C17 ✅ + **G18 (HA 配置总览) ✅**

## 实测基线（2026-08-18 G18）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **193 tests collected**（191 + G18 新增 2） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **193 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **167.56 kB JS / 39 modules / 431ms**（165.98 → 167.56，+1.58 kB） |
| `feature_list.json` | **31/31 pass**（新增 `feat-ha-settings-overview`，evidence 非空） |

## 实测基线（2026-08-18 C17）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **191 tests collected**（188 + C17 新增 3） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **191 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors（含清理 math/BaseModel 未用导入） |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **165.98 kB JS / 39 modules / 426ms**（纯后端改动，体积不变） |
| `feature_list.json` | **30/30 pass**（新增 `feat-data-migration`，evidence 非空） |

## 实测基线（2026-08-18 C16）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **188 tests collected**（186 + C16 新增 2） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **188 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **165.98 kB JS / 39 modules / 438ms**（纯后端改动，体积不变） |
| `feature_list.json` | **29/29 pass**（新增 `feat-failover-recover`，evidence 非空） |

## 实测基线（2026-08-18 C15）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **186 tests collected**（180 + C15 新增 6） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **186 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **165.98 kB JS / 39 modules / 451ms**（164.72 → 165.98，+1.26 kB） |
| `feature_list.json` | **28/28 pass**（新增 `feat-auto-failover`，evidence 非空） |

## 实测基线（2026-08-18 C14）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **180 tests collected**（178 + C14 新增 2） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **180 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **164.72 kB JS / 39 modules / 437ms**（164.54 → 164.72，+0.18 kB） |
| `feature_list.json` | **27/27 pass**（新增 `feat-health-monitor`，evidence 非空） |

## 实测基线（2026-08-18 C13）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **178 tests collected**（174 + C13 新增 4） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **178 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **164.54 kB JS / 39 modules / 414ms**（后端改动，体积不变） |
| `feature_list.json` | **26/26 pass**（新增 `feat-auto-backup`，evidence 非空） |

## 实测基线（2026-08-18 C12）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **174 tests collected**（171 + C12 新增 3） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **174 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **164.54 kB JS / 39 modules / 436ms**（164.15 → 164.54，+0.39 kB） |
| `feature_list.json` | **25/25 pass**（新增 `feat-datasource-hot-switch`，evidence 非空） |

## 实测基线（2026-08-18 C11）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **171 tests collected**（167 + C11 新增 4） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **171 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **164.15 kB JS / 39 modules / 396ms**（162.31 → 164.15，+1.84 kB） |
| `feature_list.json` | **24/24 pass**（新增 `feat-backup-restore`，evidence 非空） |

## 实测基线（2026-08-18 C10）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | **167 tests collected**（158 + C10 新增 9） |
| `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/` | **167 passed**（/opt/anaconda3/bin/python3） |
| `ruff check` 新增/改动模块 | 0 errors |
| `npm --prefix desktop run check` / `lint` | 0 errors |
| `npm --prefix desktop run build` | Vite **162.31 kB JS / 39 modules / 403ms**（161.91 → 162.31，+0.40 kB） |
| `feature_list.json` | **23/23 pass**（新增 `feat-high-availability`，evidence 非空） |

## 实测基线（2026-08-17 C9）

| 项 | 值 |
| --- | --- |
| `pytest --collect-only` | 158 tests collected |
| 本沙箱 `pytest tests/` | 150 passed + 8 skipped（Milvus Lite 不可用；若 Milvus 可跑应为 158 passed） |
| `ruff` 新增模块 | 0 errors |
| `npm --prefix desktop run check` | 0 errors |
| `npm --prefix desktop run build` | Vite 161.91 kB JS / 39 modules |

## 实测基线（2026-08-08 复核）

所有数值本轮实跑取得，非历史抄录：

| 项 | 值 |
| --- | --- |
| `npm run test:unit` | 144 passed in 5.21s |
| `npm run test:integration` | 144 passed in 4.68s |
| `npm run check` / `lint` | 0 errors |
| `npm run build` | Vite 158.61 kB JS + 7.00 kB CSS / 38 模块 / 685ms |
| `npm run eval:mock` | 9/10 (90%) |
| `node --test scripts/test-server-manager.cjs` | 2 passed in 30.8s |
| `feature_list.json` | 21/21 pass（evidence 全部非空） |
| git | `main`，HEAD `72d8a2a`，改动仅文档文件 |

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
  - **[2026-08-08 复核修正]** 上面记录的 136 passed 为 Milvus 适配器 skip 状态下的计数。以 `KB_MILVUS_URI=./kb_milvus_lite.db` 全量跑（即根级 `npm run test:unit` 的实际命令）实测为 **144 passed**，差值 8 恰为 `tests/datasources/test_milvus_adapter.py` 的 8 项。非回归，仅为记录口径不一致。以后记录测试数请统一走 `npm run test:unit`。
- [x] **H1 harness 文档同步 + 双层可观测性补分**（纯文档轮，零生产代码改动）：
  - 背景：`quality-document.md` / `clean-state-checklist.md` 停在 G1 基线（13/13、89 passed、148.70 kB），`evaluator-rubric.md` 停在 T1 上下文（7/7、pytest 73），已滞后 6 轮；`feature_list.json` 的 `last_updated` 落后 progress.md 4 天。新会话会读到失真基线。
  - `quality-document.md`：9 维扩到 11 维（新增运行时/过程可观测性两行）；全部数值换成实测；Overall A → **A-**（两个 B 均指向 goal 系列过程工件欠账）；Observability 段列出 19 类实测命中的日志事件。
  - `clean-state-checklist.md`：快照 G1 → G7；Build/Performance/Repository 各项换实测值；`.gitignore` 相关项从"推荐"改为"已实际生效"（核对 `.gitignore` 属实）；新增 2 项**未勾选**项暴露欠账（G1-G4 无协议文档、G1-G7 无评估报告）。
  - `evaluator-rubric.md`：上下文 T1 → G7 累计；补齐自 T1 悬空 7 轮的双层可观测性评分 —— **运行时 4/5**（日志/健康检查/进程事件齐备，但追踪为零：全仓库无 request_id/trace_id，`structlog.contextvars.merge_contextvars` 已挂 processors 却无任何 `bind_contextvars` 调用，唯一关联键 `task_id` 只覆盖 import 路径）、**过程 3/5**（14 轮迭代有 7 轮无评估工件，评分表自身滞后 6 轮）；总分 4.5/5；结论 Accept（功能）+ Revise（过程工件）。
  - `feature_list.json`：`last_updated` → 2026-08-08（19/19 pass 不变，JSON 校验通过）。
  - 验证：实测 `npm run test:unit` 144 passed / `test:integration` 144 passed / `tsc --noEmit` 0 errors / Vite 158.61 kB / `eval:mock` 9/10 / `node --test` 2 passed；19 类日志事件逐个 grep 命中；`git status --porcelain` 仅含本轮 6 个文档文件。
- [x] **H2 过程政策确立**（纯文档轮，零生产代码改动）：
  - 背景：H1 把过程可观测性评为 3/5，依据是 G1-G7 零评估报告 + G1-G4 无迭代协议。根因不是"忘了写"，而是 `docs/PROCESS.md` **从未规定过 goal 系列要不要写**——它只说"每个迭代开始前必须制定迭代协议"，对评估报告的适用范围只字未提；且该文件自身停在 `当前阶段：inception`，是本次整理中滞后最严重的一份。
  - `docs/PROCESS.md` 新增 **§迭代分类与评估策略**：按 C（构建）/ G（目标）/ H（harness）三类定义——三类**均必须**有迭代协议；C 类**必须**出独立评估报告；G/H 类走自验，并写明论据（G 类退出标准本身即可执行断言：测试通过数 / 类型错误数 / 包体积 / 评测命中率 / 端到端返回值，任何后续会话可重跑复现，比追述性报告更难造假；且 G 类不引入新设计决策，只在已验收架构里填空）。
  - 四条**客观可判定**的升级触发条件（命中任一即不得走自验）：破坏性接口变更 / 持久化 schema 迁移 / 新增数据源类型或 embedder 后端 / 触及安全边界。理由：这四类改动的代价转嫁给未来会话或用户数据，自动化断言证明不了"迁移路径对老数据安全"。
  - 自验四项最低要求（缺一不得标 `pass`）：协议先于开发落盘、`progress.md` 留可复核数值、`feature_list.json` evidence 非空、双层可观测性逐条过。
  - G1-G7 **显式追认**为自验通过、政策自 H2 起生效不回溯；**留档判例**：G6 同时命中"破坏性接口变更"（`on_progress` 签名）与"持久化 schema 迁移"（`TaskStore` v1 + `PRAGMA user_version=1`），按新政策本应出独立评估报告。
  - `docs/PROCESS.md` 新增 **§记录口径约定**：测试数一律以 `npm run test:unit` 为准；包体积带前值与差值；`evaluator-rubric.md` 每轮收尾同步（连续两轮未同步即判过程可观测性不合格）；新增维度不得长期挂"待评分"。
  - `docs/PROCESS.md` 陈旧状态修正：阶段表四行 `待进入` → `已通过` + 新增「移交后增量」行；当前阶段 `inception` → 移交后增量；迭代列表 7 行 → 21 行，补全 C5-C8 / G1-G7 / H1-H2 并新增「类别」「状态」两列。
  - `docs/construction/h2-process-policy.md`（新）：H2 迭代协议，含反面案例段 + **附 H1 迭代协议补记**（H1 执行于政策确立前，当时未产出协议，按新规则补记，使 harness 段自身首尾一致）。
  - **意外发现并修复**：`feature_list.json` 中 `feat-construction-1`…`-4` 与 `feat-transition-handoff` 共 5 个条目各有**两个 `evidence` 键**——真实内容在前、空字符串在后。按 JSON 语义后者覆盖前者，这 5 项的 evidence 对**任何标准解析器**都是空值，证据链实际是断的（此前"evidence 齐备"的判断都基于肉眼看原始文本）。已去重并保留真实内容，21/21 条目 evidence 均非空且可被解析器读到。
  - 重评：`evaluator-rubric.md` 过程可观测性 3 → **4**（不给 5 的两条理由：政策尚未被任何 G 类迭代实践检验；G1-G4 协议与 G1-G7 评估报告仍不存在，追认是有记录的主动选择但工件确实缺失）；交接准备度 4 → 5；总分 4.5 → **4.75/5**；结论 Revise → **Accept**。`quality-document.md` 两个 B 回升，Overall A- → **A**。
  - 验证：`npm run verify` 144 passed ×2；`bash init.sh` 全绿；`feature_list.json` 与原始版本逐字段比对——原 19 项内容完全一致，仅新增 H1/H2 两项。
- [x] **C9 黑板体系落地**：生产默认路径从线性 pipeline 切换为黑板控制器。新增 `server/app/blackboard/`（Blackboard / Patch / 事件总线 / 词汇表 / 注册表 / Agenda / Scheduler / ResourceManager / BlackboardProjector）和 `server/app/blackboard/sources/` 7 个知识源（ParseFile / ChunkText / ChunkEmbedding / QueryEmbedding / WriteDatasource / SemanticRetrieval / Browse）。`main.py` 默认创建控制器并注册知识源；files/search/chunks API 在存在控制器时走黑板路径，旧 pipeline 保留兼容路径；`tests/blackboard/` 新增 13 项（条目/事件/乐观并发/注册校验/冲突/资源/导入检索浏览/投影/知识源隔离）。文档：`docs/elaboration/01-architecture-baseline.md` 补黑板结构，`docs/construction/c9-blackboard-architecture.md` + `c9-blackboard-evaluation.md`。验证：`pytest tests/` 158 collected（沙箱 Milvus skip 8，实际 150 passed）；`ruff check` 新增模块 0 errors；desktop check 0 errors；Vite build 161.91 kB。
- [x] **C10 高可用基础能力**：补齐个人知识库的高可用地基。
  - 请求关联：新增 `server/app/api/middleware.py`，每个请求生成/透传 `X-Request-Id`，structlog contextvars 绑定 `request_id / method / path`，结束时打 `http.request`（含 status_code / duration_ms）；所有响应头带 `X-Request-Id`。
  - 健康检查：`GET /v1/health` 扩展 `degraded / started_at / uptime_seconds / embedder_backend / embedder_fallback / active_datasource / data_dir`；新增 `GET /v1/health/ready`（15s TTL 缓存，探活 datasource + embedder，任一失败 status=degraded）；`main.py` 组件装配后 `health_api.set_runtime_state(...)` 暴露降级事实。
  - 一致性备份：新增 `server/app/observability/backup.py` + CLI `python3 -m app.observability.backup`；SQLite 用官方 backup API 在线快照，JSON 复制，写 `manifest.json`，`KB_BACKUP_KEEP`（默认 7）保留策略；文档明确备份含凭证、需同等权限保护。
  - 桌面降级提示：`HealthInfo` 扩展；`useAppState` 保存 `healthInfo`；`App.tsx` 渲染 `.kb-banner-degraded`（embedder fallback / 无 active 数据源 / 数据源不可用）。
  - 测试：`server/tests/api/test_health_api.py` 4 项、`server/tests/test_backup.py` 3 项、`server/tests/test_request_context.py` 2 项，共 +9。
  - 验证：167 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 162.31 kB（+0.40 kB）；`feature_list.json` 22/22 → 23/23。
  - 文档：`docs/construction/c10-high-availability.md` 协议 + `c10-high-availability-evaluation.md` 评估（Accept）；`docs/API.md` 健康段；`docs/RUNBOOK.md` §2b/2c；`docs/KNOWN_ISSUES.md` MI-06/MI-07/MI-08；`evaluator-rubric.md` 运行时可观测性 4 → 5。
- [x] **C11 备份/恢复闭环**：把 C10 的“能备份”推进到“可一键恢复”。
  - backup 模块：新增 `list_backups()`（manifest 汇总、按时间倒序）与 `restore_backup()`（仅接受 `kb-backup-*` + 有效 manifest；先 `backup_data_dir` 到 `<target>/.pre-restore/` keep=3，再按 manifest 复制回目标）；CLI 新增 `list` / `restore <path>` 子命令，无参数仍创建备份。
  - API：`server/app/api/backups.py` 新增 `GET /v1/backups`（列表）与 `POST /v1/backups`（创建，201）；`Settings` 新增 `backup_dir` / `backup_keep`；恢复不放 HTTP，避免覆盖正在使用的 SQLite。
  - 桌面：`shared/types` / `api-client` / `preload` / `main` 新增 `listBackups` / `createBackup` / `restoreBackup`；恢复由主进程 `server.stop()` → `execFile python -m app.observability.backup restore` → `server.start()`（finally 重启兜底）；`SettingsPage` 新增 Backup & Restore 区块（创建 / 列表 / 确认恢复 / toast）。
  - 测试：`test_backup.py` +3（list 汇总 / restore 回写 + `.pre-restore` / 非法目录拒绝）、`test_backups_api.py` +1（POST 201 + GET 列表）。
  - 验证：171 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 164.15 kB（+1.84 kB）；`feature_list.json` 23/23 → 24/24。
  - 文档：`docs/construction/c11-backup-restore.md` 协议 + `c11-backup-restore-evaluation.md` 评估（Accept）；`docs/API.md` §备份；`docs/RUNBOOK.md` §2c；`docs/KNOWN_ISSUES.md` MI-09；`docs/elaboration/01-architecture-baseline.md`。
- [x] **C12 active 数据源热切换**：把“active 切换只影响下次启动”升级为可热切换。
  - 黑板：`BlackboardController.replace_datasource` 用 `datasource_write` + `search` 资源锁串行化切换，替换 `DatasourceResource` 并 best-effort 关闭旧适配器。
  - API：`POST /v1/datasources/active/{name}/switch` 构建 + 探活（health 非 ok 拒绝）→ replace → `store.activate` 持久化 → `chunks_api.set_active_datasource` → `health_api.update_active_datasource` → `datasource.switched` 日志。
  - 健康：`update_active_datasource` 更新运行态、清 readiness 缓存、不重置 `started_at`。
  - 桌面：`switchDatasourceConfig` IPC + Settings “Switch now” 按钮；Activate 保留“下次启动”语义。
  - 测试：`test_controller.py` +1（replace 后 import/search 走新数据源）、`test_datasource_configs_api.py` +2（switch 成功持久化 / 无控制器 503）。
  - 验证：174 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 164.54 kB（+0.39 kB）；`feature_list.json` 24/24 → 25/25。
  - 文档：`docs/construction/c12-hot-switch.md` 协议 + `c12-hot-switch-evaluation.md` 评估（Accept）；`docs/API.md` §数据源热切换；`docs/RUNBOOK.md` §3；`docs/KNOWN_ISSUES.md` MI-10。
- [x] **C13 自动备份**：把“手动/CLI 备份”升级为服务运行期自动备份。
  - settings：`backup_auto`（默认 true）+ `backup_interval_hours`（默认 24.0）。
  - backup 模块：`latest_backup` + `backup_if_due`（无快照创建 / 未到期跳过 / 已到期创建，`now` 可注入测试）。
  - main：`_auto_backup_loop` 启动即检查一次，之后每小时检查；shutdown 取消；`backup.auto_scheduled/auto_created/auto_skipped/auto_failed` 结构化日志。
  - 测试：`test_backup.py` +4；conftest 固定 `KB_BACKUP_AUTO=false`。
  - 验证：178 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 164.54 kB 不变；`feature_list.json` 25/25 → 26/26。
  - 文档：`docs/construction/c13-auto-backup.md` 协议 + `c13-auto-backup-evaluation.md` 评估（Accept）；`docs/RUNBOOK.md` §2c；`docs/KNOWN_ISSUES.md` MI-11。
- [x] **C14 运行期健康监控**：让 `/v1/health` 反映实时依赖健康，而不是只有启动快照。
  - health：RuntimeState 新增 `datasource_ok / datasource_message / datasource_latency_ms / embedder_ok / embedder_message / last_probe_at`；`update_dependency_health` 写探活结果；`refresh_runtime_health` 复用 `_probe_checks`；`/ready` 探活后 `/health` 立即反映。
  - 后台：settings 新增 `health_monitor`（默认 true）+ `health_monitor_interval_seconds`（默认 30）；main `_health_monitor_loop` 启动/关闭管理，状态变化打 `health.monitor_degraded` / `health.monitor_recovered`；conftest 固定关闭。
  - 桌面：`HealthInfo` 扩展 `embedder_ok` / `last_probe_at`；App 每 15s 轮询 `checkHealth`；横幅文案区分 embedder fallback / datasource 不可用 / 依赖降级。
  - 测试：`test_health_api.py` +2（ready 刷新快照 / 运行期 datasource 失败传播）。
  - 验证：180 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 164.72 kB（+0.18 kB）；`feature_list.json` 26/26 → 27/27。
  - 文档：`docs/construction/c14-health-monitor.md` 协议 + `c14-health-monitor-evaluation.md` 评估（Accept）；`docs/API.md` 健康段；`docs/RUNBOOK.md` §2b；`docs/KNOWN_ISSUES.md` MI-12。
- [x] **C15 健康驱动自动 failover**：把“看到降级”升级为“自动切备用”。
  - 存储：`datasources.json` 顶层 `failover`（默认 []），`get_failover` / `set_failover` 只保留已保存配置名、去重保序。
  - API：`GET/PUT/DELETE /v1/datasources/failover`；`failover_datasource()` 按序 build + health 探活 → `replace_datasource` → `store.activate` → 更新 chunks/health；全部失败返回 None + `datasource.failover_exhausted`。
  - 监控：settings 新增 `failover_enabled`（默认 true）+ `failover_consecutive_failures`（默认 2）；`_health_monitor_loop` 连续失败达到阈值触发，成功重置计数。
  - 桌面：`listFailover` / `setFailover` / `clearFailover` IPC + Settings Failover order 区块。
  - 测试：`test_datasource_store.py` +3、`test_datasource_configs_api.py` +3。
  - 验证：186 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 165.98 kB（+1.26 kB）；`feature_list.json` 27/27 → 28/28。
  - 文档：`docs/construction/c15-auto-failover.md` 协议 + `c15-auto-failover-evaluation.md` 评估（Accept）；`docs/API.md` §failover；`docs/RUNBOOK.md` §3b；`docs/KNOWN_ISSUES.md` MI-13。
- [x] **C16 failover 恢复回切**：让 failover 形成“主故障 → 切备用 → 主恢复 → 切回”完整生命周期。
  - API：`recover_primary()` 以 failover 顺序第一项为主数据源；active 已为主 / 主候选 health 失败返回 None；成功 replace + activate + 更新 chunks/health + `datasource.failover_recovered` 日志。
  - 监控：settings 新增 `failover_auto_recover`（默认 true）+ `failover_recover_consecutive_checks`（默认 3）；`_health_monitor_loop` 连续健康计数达到阈值触发，调用后重置。
  - 测试：`test_datasource_configs_api.py` +2；conftest 固定关闭。
  - 验证：188 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 165.98 kB 不变；`feature_list.json` 28/28 → 29/29。
  - 文档：`docs/construction/c16-failover-recover.md` 协议 + `c16-failover-recover-evaluation.md` 评估（Accept）；`docs/API.md` §failover 回切；`docs/RUNBOOK.md` §3b；`docs/KNOWN_ISSUES.md` MI-14。
- [x] **C17 数据源迁移 dump/load**：让数据能在数据源之间复制，failover/换库不再是空库。
  - 抽象：`DataSource.dump_all` 默认 NotSupportedError，capability `dump`；memory / ES 实现（ES 全量文本不分页截断）。
  - CLI：`python3 -m app.observability.migrate dump/load`；dump 写 JSONL（document_id/text/metadata），load 批量重新 embedding 后 `ds.add`。
  - 测试：`test_migrate.py` 2 项（roundtrip 可搜索 / 无 capability 拒绝）+ ES dump_all 1 项。
  - 验证：191 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 165.98 kB 不变；`feature_list.json` 29/29 → 30/30。
  - 文档：`docs/construction/c17-data-migration.md` 协议 + `c17-data-migration-evaluation.md` 评估（Accept）；`docs/RUNBOOK.md` §3c；`docs/KNOWN_ISSUES.md` MI-15。
- [x] **G18 HA 配置总览**：H2 政策生效后的首个 G 类迭代，验证“自验四项最低要求”与四条升级触发条件可判定。
  - API：`GET /v1/settings/ha` 返回自动备份 / 健康监控 / failover 的当前生效参数（只读）。
  - 桌面：Settings 新增 HA Configuration 总览表；`getHaSettings` IPC。
  - 测试：`test_ha_settings_api.py` 2 项（当前生效值完整 / env 覆盖响应变化）。
  - 验证：193 passed；ruff 0 errors；desktop check/lint 0 errors；Vite 167.56 kB（+1.58 kB）；`feature_list.json` 30/30 → 31/31。
  - 自验：协议先落盘（`docs/construction/g18-ha-settings-overview.md`）、progress 留数值、feature evidence 非空、双层可观测性通过；`evaluator-rubric.md` 过程可观测性 4 → 5。
  - 文档：`docs/API.md` §settings/ha；`docs/RUNBOOK.md` §2b。

### What's In Progress

- 无。G18 已收尾。所有 KI-02 / KI-03 / KI-04 / KI-05 / KI-06 / KI-07 / KI-09 均收敛；仅 KI-01 / KI-08 / KI-10 仍 open（低-中严重度、不阻塞个人生产使用）。

### What's Next

**过程侧已闭环**

1. H2 政策的"自验四项最低要求"与四条升级触发条件已由 **G18** 实践验证：协议先行、数值可复核、evidence 非空、双层可观测性全部成立；过程可观测性 4 → 5。

**功能候选**

2. （成本最低、闭环最完整）Settings → "Test connection" 成功后自动调 `mark_tested` 写 `last_tested_at`，UI 加 ✓ 标记。**H1 已核实：`datasource_store.py:188` 有实现 + `test_datasource_store.py:111` 有单测，但全仓库无任何 API/UI 调用方 —— 属有测试无调用方的死代码。**
3. KI-01（PDF OCR）或 KI-08（Word 图片 / 批注）或 KI-10（better-sqlite3 arm64 cross-compile）。已不再是阻塞项，按用户实际遭遇频率决定先后。
4. CI 引入 docker compose 服务化 Milvus，让 conftest 默认 URI 指向 `http://milvus:19530`，1:1 套件 CI 自动跑。
5. （可选，G5 后续）将指数退避提炼成 `app/utils/backoff.py` 通用工具。**H1 已核实该文件不存在**，目前仅 `openai_compat.py` 内联。
6. （G18 后续）把 HA 参数做成可编辑持久化（当前只读展示，配置仍通过 `KB_*` env 设置）。

> 注：上述第 2 项若改动 IPC 协议则命中升级触发条件，需升级为独立评估。

**条件触发**

7. （可选）多 active 数据源加权路由；当前 failover 是线性顺序 + 自动回切。
8. （可选）迁移 UI：把 dump/load 接入桌面端，或增加 Milvus `dump_all`。

## Blockers / Risks

- 详见 `docs/KNOWN_ISSUES.md`（KI-01 / KI-08 / KI-10 仍 open；KI-02 / KI-03 / KI-04 / KI-05 / KI-06 / KI-07 / KI-09 已收敛）。
- KI-06 已由 G3 收敛：真实 bge-m3 经 Ollama OpenAI 兼容接口跑通，`eval:ollama` 10/10。CI 仍走 mock 路径（9/10）维持门禁，本地 sentence-transformers 直载路径仍未装权重（属备用路径，不阻塞）。
- C7 / KI-07：本机 docker mirror 对 `milvusdb/milvus:v2.4.10-standalone` 返回 403；Milvus Lite (`./kb_milvus_lite.db`) 1:1 兜底。
- G1：goal.md 假设的 `src/backend` `src/frontend` 目录在本仓库不存在；功能 100% 已覆盖，详见 `docs/goal/01-mapping.md`。
- G2 的 Activate 仍只持久化、下次启动生效；C12 提供 “Switch now” 热切换，C15 提供健康驱动自动 failover，均无需重启。

## Decisions Made

- RUP 四阶段 + 迭代协议管理；5 个 construction 迭代 + 1 个 transition + 3 个补充收敛迭代（C6 / C7 / C8）+ 7 个 goal 迭代（G1 映射 / G2 数据源 CRUD / G3 Ollama bge-m3 / G4 真实 ES / G5 KI-03 重试退避 / G6 上传进度可观测性 / G7 ES 数据浏览页）+ 2 个 harness 迭代（H1 文档同步 / **H2 过程政策确立**）。
- **C10 分类**：命中 `docs/PROCESS.md` 升级触发条件中的“触及安全边界”（备份复制含凭证的 `datasources.json` + 扩展文件系统访问范围），因此按 C 类出独立评估报告，不走 G 类自验。
- **C11 分类与取舍**：恢复向数据目录写回含凭证文件并停/启子进程，命中安全边界，按 C 类评估。restore 不放 HTTP，由桌面主进程停服后执行；恢复前自动留 `.pre-restore`，误恢复可回退。
- **C12 分类与取舍**：热切换新增运行时数据源语义，按 C 类评估。保留 Activate 的“下次启动”语义，新增显式 Switch now；切换要求 health ok 并把黑板资源锁作为并发边界。
- **C13 分类与取舍**：自动备份新增服务后台调度，按 C 类评估。跟随服务运行、启动即检查 + 每小时检查、默认开启；测试通过 conftest 关闭避免后台任务。
- **C14 分类与取舍**：运行期健康监控新增后台探活与健康快照，按 C 类评估。后台探活与 `/ready` 共用同一 checks；不做自动 failover，降级交给桌面横幅与用户热切换。
- **C15 分类与取舍**：自动 failover 新增配置文件字段与自动切换行为，按 C 类评估。failover 顺序放 `datasources.json` 顶层（缺失兼容）；连续失败阈值默认 2；切换成功后不自动切回，避免 flapping。
- **C16 分类与取舍**：恢复回切新增自动替换运行态行为，按 C 类评估。failover 顺序第一项=主数据源；默认自动回切但要求连续 3 次健康，避免抖动；`KB_FAILOVER_AUTO_RECOVER=false` 可只保留自动 failover。
- **C17 分类与取舍**：数据迁移新增 DataSource 能力与 CLI，按 C 类评估。dump 不保留向量，load 用当前 embedder 重嵌入；`dump_all` 与 `list_chunks` 分离，避免迁移拿截断文本。
- **G18 自验结论**：作为 H2 政策生效后首个 G 类迭代，四项最低要求全部可判定、四条升级触发条件均未命中；过程可观测性 4 → 5，总评 5/5。
- **H2 迭代分类政策**：C 类必须出独立评估报告；G/H 类走自验但必须有迭代协议 + 四项最低要求；四条客观可判定的升级触发条件把高风险改动挡在自验之外。选"定政策"而非"回溯补 7 份评估报告"是用户决策——理由是回溯写作的信息全部来自 `progress.md`，边际价值低于确立规则。
- **H2 记录口径**：测试数一律以根级 `npm run test:unit` 为准（带 `KB_MILVUS_URI=./kb_milvus_lite.db`，Milvus 8 项会全跑）。此前 G7 记的 136 是 Milvus skip 口径，导致口径漂移。
- Python 服务默认走 mock embedder；缺 sentence-transformers 自动降级（事件 `embedder.fallback_to_mock`）。
- 数据源抽象最小能力集：add / search / delete / health；特性能力按适配器扩展。
- 桌面端架构：主进程拉起 Python 子进程 + watchdog；preload 唯一 IPC 暴露点。
- KI-04：文档目录以**桌面端 SQLite**为单一来源。
- KI-05：Python 后端**不**打包进 Electron 产物，运行时通过 `KB_PYTHON` 解析。
- KI-06：CI 仍跑 mock 路径；真实 BGE-M3 路径按需在本机执行。
- KI-07：`_MilvusBackend` 显式 VARCHAR 主键 schema；conftest 通过 `KB_MILVUS_URI` 同时支持 http(s) standalone 与本地 Lite 路径。
- KI-02：warning 而非 exception 与现有截断语义一致；`capabilities()` `scan_limit_risk` 声明风险。C17 已补 dump/load CLI，数据可迁移到 pgvector / Milvus / ES。
- G1：根级 `package.json` 聚合 npm scripts（不动 desktop 的 start/build/dev）；桌面端 `lint` 约定即 tsc 类型检查；pytest 走 Lite 路径跑满 89 项（原 89 → 现 113）。
- G2：数据源配置文件选 **JSON**（用户可 `cat` / `git` 共享 / 备份）；原子写 `os.replace` 避免半截文件；损坏文件自动 `.corrupt` 备份后启动。C12 热切换与 C15 failover 已把“只能下次启动生效”收敛为 Activate 独有语义；未知 type / 缺依赖由 build() 抛错，UI / API 透传为 400 给清晰排错信息。
- G4：真实 ES 接入不引入 docker compose；用户在跑 ES 9.5.0 + 凭证就够，写入 `datasources.json` 走 `_build_default_components()` 启动加载路径；G2 的 v1 schema 已经包含 elasticsearch type，适配器无需改动；ES 9.x 默认 `bbq_hnsw` 自动优于 8.x 的 `hnsw`，mapping 字段名从 `url` 改为 `hosts`（适配器要求）。
- G5：KI-03 重试退避只放在 `openai-compat`（最常见的瞬时错误来源），不改 `Embedder` 抽象契约；其它 embedder（`mock-hash` 无网络、`bge-m3` 本地推理）不背此复杂度。引入辅助 attr `kb_status_code` / `kb_retryable` 而不是新的异常类型，让外层 `try/except EmbedderError` 保持稳定。`max_retries=0` 等价禁用重试，给排错留逃生口。
- G6：`IndexingPipeline.on_progress` 签名从 `Callable[[float], None]` 升级到 `Callable[[ProgressEvent], None]` —— 破坏性变更，但**唯一生产调用点**是 `_run_import`，已同步更新；pipeline 单测同步升级。`TaskStore` v1 schema 迁移自动完成（`ALTER TABLE ... ADD COLUMN stage` 用 try/except OperationalError 兜底重复添加；`PRAGMA user_version=1` 标版本），老 `tasks.db` 不丢数据。事件 ring buffer 32 条，嵌入 `TaskResponse.events` 让渲染端免一次额外 IPC；`/events?since_id=` 备用端点留给未来 live-tail 订阅者。`stage` 默认 `queued`，旧服务器负载 fallback 兼容（前端 `t.stage ?? "queued"`）。`pipeline.stage` structlog 事件在每个 stage 边界打一次，附带 task_id + stage + progress + message 字段。
- G7：仅 ES 适配器实现 `list_chunks` + `aggregate_by_document`，通过新增 capability `"chunk_list"` 声明；其它 adapter（vector / postgres / mysql / milvus）维持默认 `NotSupportedError`，browse 端点统一转 501。理由见 `progress.md` "数据源抽象最小能力集"。Browse 端点读**当前启动期绑定的 active DataSource 实例**（与 import pipeline 同一份），遵循 G2 决策"active 切换只在下次启动生效"。新增 `ChunkSummary` / `DocumentSummary` 放 `observability/models.py`（沿用 `Hit` / `Chunk` 的现有约定）。`aggregate_by_document` 失败时降级为 `{}` 而不是 500（ES 动态 mapping 缺 `metadata.parser` 字段时偶发）；BrowsePage 把 ES 异常用 toast + 永久 banner 区分（banner 用于不支持 capability；toast 用于瞬时错误）。

## Notes for Next Session

- 当前仓库 `feature_list.json` 全部 `pass`（**31/31**，含 C9-C17 + G18），且 evidence 字段全部非空。
- 下次启动：`bash init.sh` → 阅读 README → **PROCESS §迭代分类与评估策略**（开新迭代前必读，决定要不要出评估报告）→ KNOWN_ISSUES → `docs/goal/01-mapping.md` → RUNBOOK §2 数据源配置管理。
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
