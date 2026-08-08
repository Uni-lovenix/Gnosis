# goal.md → 实际项目栈 映射说明

> 本文件回答："goal.md 验收标准如何在当前项目（Python + Electron 双子项目）里被满足？"

## TL;DR

- 功能验收（C1-C8 12/12 + G2 数据源 CRUD + G3 Ollama bge-m3 真模型）已 100% 覆盖 goal.md 列出的 7 条功能标准，包括"添加/编辑/删除数据源连接信息"的图形界面 + 持久化 + **生产默认走真实 bge-m3 embedding**（不再是 mock）。
- goal.md 验证命令以 `npm` 为入口；本项目在根目录**新增** `package.json` 作为聚合入口，包装 server 的 pytest 与 desktop 的 tsc/vite。`npm run eval` 默认 = Ollama bge-m3（10/10 = 100%）；mock 通过 `npm run eval:mock` 切换。
- 桌面端 `lint` 约定是 `tsc --noEmit -p tsconfig.json`（非 ESLint），与 goal.md 期望一致（`npm run lint` → tsc 类型检查）。
- **生产 Embedder 默认 = openai-compat (Ollama bge-m3)**，写在 `server/app/config/settings.py`；pytest 用 `tests/conftest.py` 强制 `KB_EMBED_BACKEND=mock-hash` 让测试不依赖外部服务。详见 `docs/RUNBOOK.md` §0。

## 目录结构映射

| goal.md 假设 | 实际位置 |
|---|---|
| `src/backend/` | `server/app/` (FastAPI) |
| `src/frontend/src/components/` | `desktop/src/renderer/` (React + TS) |
| `src/frontend/src/api/` | `desktop/src/preload/` + `server/app/api/` |
| `src/shared/types/` | `desktop/src/shared/types.ts` |
| `src/main.ts`（Electron 主进程） | `desktop/src/main/index.ts`（不改 goal.md 假定；仅在不破坏前提下扩展） |
| `scripts/` | `scripts/` + `server/eval/` + `server/tests/` |
| `docker-compose.yml` | 暂未提供；以 `scripts/start_milvus.sh` 单服务脚本 + Lite 兜底 |

## 验收标准映射

| goal.md 验收项 | 实现位置 | 验证证据 |
|---|---|---|
| 配置管理：图形界面 / 配置文件 + 添加 / 编辑 / 删除 + 测试连接 | `server/app/observability/datasource_store.py` + `server/app/api/datasources.py`（CRUD） + `desktop/src/renderer/pages/SettingsPage.tsx`（UI） | `~/.kb-server/datasources.json`（v1 schema、原子写）；`GET/POST/DELETE /v1/datasources/configs` + `GET/PUT/DELETE /v1/datasources/active`；Settings UI **Add / Edit / Save / Activate / Delete / Clear active**；`tests/test_datasource_store.py`（16 项）+ `tests/test_datasource_configs_api.py`（8 项） |
| 4 类数据源配置（ES/PG/MySQL/Vector DB） | `server/app/datasources/{elasticsearch,postgres,mysql,vector_db}_adapter.py` | `docs/construction/c1-data-sources.md`；4 类适配器单测 + capabilities 接口 |
| 文件上传 + 4 格式解析（xlsx/docx/pdf/md） | `server/app/parsers/{excel,word,pdf,markdown}.py` + `server/app/api/files.py` | `docs/construction/c2-files-and-sync.md`；解析器单测 |
| bge-m3 embedding（1024 维）+ 元数据 | `server/app/embedding/{bge_m3,openai_compat,mock_embedder}.py` | `docs/construction/c3-ai-embedding.md`；eval/run_eval.py |
| 向量化鲁棒性（OpenAI 兼容远端重试退避，KI-03） | `server/app/embedding/openai_compat.py`（指数退避 + jitter + 结构化日志） | `docs/construction/g5-retry-backoff.md`；`tests/embedding/test_embedders.py` 7 项 |
| **前端进度反馈（stage + event log，G6）** | `desktop/src/renderer/pages/ImportPage.tsx`（阶段 tag + 折叠事件日志）+ `server/app/observability/task_store.py`（v1 schema：`stage` 列 + `task_events` ring buffer 32）+ `server/app/pipeline/indexing.py`（`ProgressEvent` 签名） | `docs/construction/g6-upload-progress.md`；`tests/test_task_store.py` +7 项 + `tests/api/test_task_progress_api.py` 5 项 |
| **ES 数据浏览页（chunk-level + 聚合 + 过滤，G7）** | `desktop/src/renderer/pages/BrowsePage.tsx`（parser 下拉 + document_id debounce + 聚合表 + 分页）+ `server/app/api/chunks.py`（`GET /v1/chunks`）+ `server/app/datasources/elasticsearch_adapter.py`（`list_chunks` + `aggregate_by_document` + `chunk_list` capability） | `docs/construction/g7-es-browse.md`；`tests/datasources/test_elasticsearch_adapter.py` +5 项 + `tests/api/test_chunks_api.py` 7 项 |
| Elasticsearch 优先存储 | `server/app/datasources/elasticsearch_adapter.py`（`_build_index` + `index/8.x`） | `docs/construction/c1-data-sources.md` 矩阵；ES 适配器单测 |
| `npm run test:integration` 端到端 | 根级 `package.json` → `cd server && pytest -q` | 根级 `npm run test:integration` |
| `npx tsc --noEmit` | `desktop/` 三个 tsconfig 各自 0 errors | 根级 `npm run check` / `npm run lint` |
| `npm run lint`（= tsc 类型检查） | 桌面端 `lint` script 即 `tsc --noEmit -p tsconfig.json` | 根级 `npm run lint` |
| 前端进度反馈 | `desktop/src/renderer/` 内上传组件 + `desktop/src/main/index.ts` task 状态推送 | `docs/construction/c4-multi-experience.md` |

## 验证命令映射

| goal.md 命令 | 实际命令 | 根级 npm wrapper |
|---|---|---|
| `npx tsc --noEmit` | `cd desktop && tsc --noEmit -p tsconfig.json` | `npm run check` |
| `npm run lint` | `cd desktop && npm run lint`（= tsc --noEmit） | `npm run lint` |
| `npm run test:unit` | `cd server && pytest -q tests/`（含全部单测） | `npm run test:unit` |
| `npm run test:integration` | `cd server && pytest -q`（含单测 + API + eval 关联套件） | `npm run test:integration` |
| `npm run dev` | `cd desktop && npm run dev`（自动拉 Python 子进程） | `npm run dev` |
| `npm run build` | `cd desktop && npm run build`（3 段 tsc + Vite） | `npm run build` |

## 范围约束遵循

- ✅ 不改 `desktop/package.json` 中 `start` / `build` / `dev` 已有脚本：根级 `package.json` 是新建文件，不冲突
- ✅ 不改 `migrations/`、`src/main.ts`（Electron 主进程入口文件 `desktop/src/main/index.ts` 本会话未触碰）
- ✅ 不改 `.github/workflows/`：本项目未提供 CI 工作流文件
- ✅ `docker-compose.yml`：未新建；Milvus 用 `scripts/start_milvus.sh` + Lite 兜底（已在 C7 落地）

## 已完成 vs 待补

- [x] 功能实现（C1-C8 + G2 数据源 CRUD，feature_list.json 14/14 = pass）
- [x] 桌面端 3 tsconfig 0 errors + Vite build
- [x] server pytest 113 passed（含 G2 新增 24 项 — 数据源 store + configs API + 启动 active 加载）
- [x] eval/run_eval.py 9/10 = 90% ≥ 60% 门禁
- [x] **G1**：根级 `package.json` 聚合 npm scripts
- [x] **G1**：本映射文档
- [x] **G1**：根级 `npm run check/lint/test:unit/test:integration` 全部通过
- [x] **G2**：数据源配置 CRUD 持久化（`/v1/datasources/configs*` + `~/.kb-server/datasources.json` + Settings UI 完整闭环）
- [x] **G2**：`tests/test_datasource_store.py` 16 项 + `tests/test_datasource_configs_api.py` 8 项 全过
- [x] **G3** Ollama bge-m3 真模型跑通：`scripts/start_server_ollama.sh` + `npm run eval:ollama` 端到端；`/v1/files/import` 真实嵌入 200、`/v1/search` 语义打分（相关查询 0.55、0.45；无关 0.33 — 区分清晰）；eval 10/10 = 100%（KI-06 收敛）。
- [x] **G4** 真实 Elasticsearch 当默认数据源：`datasources.json` `active=es-prod`，重启加载 → `datasource.from_saved`，`/v1/files/import` 真写入 ES 9.5（bbq_hnsw 1024-dim cosine），`_count=8`，`/v1/search` 实分 0.74+。
- [x] **G5** KI-03 OpenAI 兼容远端指数退避：`openai_compat.py` 仅对 `httpx.TransportError` / 5xx / 429 重试（4xx 不重试）；可配 `max_retries` / `initial_backoff` / `max_backoff` / `backoff_jitter`；每次重试打 `embedder.retry` warning 日志；7 项新单测（瞬时错误重试至成功 / 耗尽抛错 / 4xx 不重试 / 429 重试 / 5xx 重试 / 退避数学 / 日志结构）。`npm run test:unit` 113 → **120 passed**。`docs/RUNBOOK.md` §2a 调参与不重试矩阵。
- [x] **G6** 上传进度可观测性：`IndexingPipeline.on_progress` 升级到 `Callable[[ProgressEvent], None]`（4 处边界发事件：`parsing/chunking/embedding/writing`，message 含文件名 + chunk 计数）；`TaskStore` v1 schema 自动迁移（`ALTER TABLE tasks ADD COLUMN stage` + `task_events` ring buffer 32 + `PRAGMA user_version=1`）；`TaskResponse` 嵌入最近 32 条事件；新增 `GET /v1/files/tasks/{id}/events?since_id=` 备用端点；前端 `ImportPage` 重写：进度条 + stage tag + 折叠事件日志；`stage` 默认 `queued`、events 默认 `[]` 兼容旧服务器；7 项 task_store + 5 项 progress_api + pipeline 单测升级；`pytest tests/` 113 → **125 passed**；`npm run build` Vite 152.27 → **153.74 kB**（+1.47 kB）。
- [x] **G7** ES 数据浏览页：`server/app/datasources/base.py` 加 `NotSupportedError` + `DataSource.list_chunks`/`aggregate_by_document` 默认抛 `NotSupportedError`；`server/app/observability/models.py` 加 `ChunkSummary` + `DocumentSummary`；`server/app/datasources/elasticsearch_adapter.py` 加 `chunk_list` capability + 实现两个方法；`server/app/api/chunks.py` 新建 `GET /v1/chunks?document_id&parser&offset&limit`（400 / 422 / 501 / 503）；`server/app/main.py` 启动期 `chunks_api.set_active_datasource(ds)` 绑定；前端 `BrowsePage`（active ds 角标 + 永久 banner + parser 下拉 + document_id debounce 输入 + 文档聚合表 + 分页 + 不支持 banner）；App.tsx 加 browse tab；`kb.browseChunks(opts)` IPC 新增；5 项 ES 适配器 + 7 项 chunks API 单测；`pytest tests/` 125 → **136 passed**；`npm run build` Vite 153.74 → **158.61 kB**（+4.87 kB）。