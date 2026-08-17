# 架构基线 -- 灵知 (Gnosis)

> 细化阶段交付物 1/3：技术基线、模块边界、数据流与接口契约。

## 1. 设计目标

1. **可插拔数据源**：4 类数据源在统一接口下互换。
2. **可插拔 embedding**：本地 BGE-M3 与远端 OpenAI 兼容 endpoint 同形调用。
3. **可恢复**：Python 服务崩溃后 Electron 主进程能自动重启并恢复任务。
4. **可单设备离线**：无外网时核心流程仍可工作（除首次下载模型权重）。
5. **可交接**：模块边界清晰，新会话能从代码与文档继续。

## 2. 顶层架构

```
┌──────────────────────────────────────────────────────────────────┐
│ Electron 主进程 (Node + TS)                                       │
│  ├─ 窗口与生命周期管理                                             │
│  ├─ Python 子进程管理（spawn / watchdog / health-check）          │
│  ├─ IPC 路由（preload contextBridge）                             │
│  └─ 本地 SQLite（元数据 + 任务状态）                                │
└──────────────────────────────────────────────────────────────────┘
            │ HTTP (localhost) / stdio fallback
            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Python 服务 (FastAPI + uvicorn)                                   │
│  ├─ /v1/files  解析/切片/导入                                       │
│  ├─ /v1/search 检索                                                │
│  ├─ /v1/datasources 适配器管理                                      │
│  ├─ /v1/embedding 模型管理                                         │
│  ├─ /v1/health 健康检查                                            │
│  └─ 结构化 JSON 日志（structlog）                                   │
└──────────────────────────────────────────────────────────────────┘
            │
            ├─► DataSource 适配器（抽象 + ES/PG/MySQL/Vector）
            ├─► Embedding 抽象（本地 BGE-M3 / 远端 OpenAI 兼容）
            ├─► 文件解析器（excel/word/pdf/markdown）
            └─► 切片器（按 token/字符切分 + overlap）
```

## 2.1 黑板体系结构（C9 基线）

生产默认路径已从“线性 pipeline 编排”升级为黑板体系：

```
FastAPI 路由 → BlackboardController（议程 + 调度器 + 资源管理）
                    ↓ 读写
              Blackboard（统一条目 + 事件总线）
                    ↓ 触发
        独立 Knowledge Source（parse/chunk/embed/write/retrieve/browse）
```

- 黑板是进程内共享状态中心，使用统一 `BlackboardEntry` 数据模型和 `Patch + expected_revision` 乐观并发控制。
- 知识源之间不直接通信；每个知识源只通过 `can_handle` / `execute` 与黑板交互，由控制组件调度。
- SQLite 投影表 `blackboard_entries` 保存当前黑板快照；该表与现有 `tasks`、`task_events` 共存于 TaskStore 数据库。
- 旧 `IndexingPipeline` / `RetrievalPipeline` 仍保留，仅作为兼容测试路径；生产默认使用黑板控制器。

## 3. 模块边界

| 模块 | 职责 | 不做 |
|---|---|---|
| `desktop/` Electron 主进程 | 启停 Python、子进程 watchdog、SQLite 持久化、IPC 桥接 | 不做 UI、不直连数据库 |
| `desktop/renderer/` React 渲染层 | 上传、检索、配置 UI、状态展示 | 不直连数据库、不做解析 |
| `desktop/preload/` | contextBridge 暴露最小 API | 不暴露 fs / net |
| `server/` Python FastAPI | 业务编排：解析→切片→embedding→入库→检索 | 不做 UI、不做模型训练 |
| `server/parsers/` | 各类文件解析为 Document（文本 + 元数据） | 不做切片、不做 embedding |
| `server/chunking/` | 切分 Document 为 Chunk | 不做 embedding |
| `server/embedding/` | 文本 → 向量（含本地/远端） | 不做入库 |
| `server/datasources/` | 向量与元数据写入/读取（4 类适配） | 不做 embedding |
| `server/pipeline/` | 编排：解析→切片→embedding→入库 | 不直连 UI |
| `server/blackboard/` | 黑板条目、事件总线、知识源注册、议程/调度/资源管理 | 不实现具体业务 |
| `server/blackboard/sources/` | 文件解析、切片、embedding、写入、检索、浏览等知识源 | 不直接调用其他知识源 |
| `server/observability/backup.py` | 数据目录一致性备份（SQLite 官方 backup API + JSON 复制 + 保留策略） | 不做自动定时调度 |

## 4. 接口契约

### 4.1 `DataSource` 抽象（Python）

```python
class DataSource(Protocol):
    name: str
    async def add(self, chunks: list[Chunk]) -> list[str]: ...
    async def search(self, vector: list[float], top_k: int, filter: dict | None = None) -> list[Hit]: ...
    async def delete(self, ids: list[str]) -> int: ...
    async def health(self) -> bool: ...
```

四种适配实现：

| 适配器 | 向量存储 | 元数据 |
|---|---|---|
| `ElasticsearchAdapter` | dense_vector 字段 | 同文档 `_source` |
| `PostgresAdapter` | pgvector 扩展 | 同表 JSONB |
| `MysqlAdapter` | 不原生支持向量 → 用 JSON 列存向量；可对接 HeatWave/Vespa 替代 | 同表 JSON |
| `VectorDBAdapter` | Milvus / Qdrant / ChromaDB 统一适配 | 各自带 metadata 字段 |

> 选择 MySQL 适配器走"JSON 列 + 内存向量检索"或"外挂向量库"两条路，前者保证本地零依赖，后者提供更高性能。本迭代默认 JSON 列方案。

### 4.2 `Embedding` 抽象

```python
class Embedder(Protocol):
    name: str
    dim: int
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

实现：`BGEM3Embedder`（本地 sentence-transformers）、`OpenAICompatEmbedder`（远端）。

### 4.3 HTTP API（FastAPI）

| Method | Path | 入参 | 出参 |
|---|---|---|---|
| POST | `/v1/files/import` | multipart file | `{document_id, chunks: int}` |
| POST | `/v1/search` | `{query, top_k, datasource, filter}` | `{hits: [{id, score, text, metadata}]}` |
| GET | `/v1/datasources` | — | `[{name, type, status}]` |
| POST | `/v1/datasources/test` | `{type, config}` | `{ok, latency_ms, message}` |
| POST | `/v1/datasources/active/{name}/switch` | — | `DatasourceConfigResponse`（热切换运行中数据源） |
| GET/PUT/DELETE | `/v1/datasources/failover` | — | `{names: [...]}`（failover 顺序） |
| GET | `/v1/backups` | — | `[{name, path, created_at, files, source}]` |
| POST | `/v1/backups` | — | 201 `BackupInfo` |
| GET | `/v1/health` | — | `{status, version, embedder, datasources}` |
| GET | `/v1/health/ready` | — | `{status, degraded, checks:[{name,ok,...}]}` |
| GET | `/v1/settings/ha` | — | 当前生效的 HA 参数（备份/健康监控/failover，只读） |
| GET | `/v1/tasks/{id}` | — | `{status, progress, error}` |

### 4.4 IPC 契约（Electron preload）

```ts
interface KBAPI {
  importFile(path: string): Promise<{documentId: string; chunks: number}>;
  search(query: string, opts?: {topK?: number; datasource?: string}): Promise<Hit[]>;
  listDatasources(): Promise<Datasource[]>;
  testDatasource(cfg: DatasourceConfig): Promise<TestResult>;
  health(): Promise<Health>;
  onProgress(cb: (task: TaskProgress) => void): () => void;
}
```

## 5. 数据流

### 5.1 导入流程

```
user → renderer 选择文件
     → preload.importFile(path)
     → main 转发到 Python POST /v1/files/import
     → Python 生产默认:
            BlackboardController.submit_import()
            → ParseFileKS → ParsedDocument
            → ChunkTextKS → ChunkSet
            → ChunkEmbeddingKS → EmbeddedChunkSet
            → WriteDatasourceKS → IndexResult
     → 返回 {documentId, chunks} → renderer 列表更新
```

### 5.2 检索流程

```
user → renderer 输入 query
     → preload.search(query, opts)
     → main POST /v1/search
     → Python 生产默认:
            BlackboardController.submit_search()
            → QueryEmbeddingKS → SearchJob(query_vector)
            → SemanticRetrievalKS → SearchResult
     → 返回 hits → renderer 展示
```

## 6. 进程与可靠性

- Electron 主进程拉起 Python 子进程，记录 PID；每 5s 心跳；3 次失败自动重启。
- 每个 HTTP 请求带 `X-Request-Id`，日志经 structlog contextvars 关联；健康快照暴露 `degraded / embedder_fallback / active_datasource`。
- Python 服务启动时打开 SQLite（任务表 + 元数据），崩溃时按 task_id 续跑。
- 任务状态机：`queued → running → done | failed`，失败任务可手动重试。
- 关闭顺序：renderer 先关闭 → main 通知 Python 优雅退出 → main 退出。
- `python3 -m app.observability.backup` 对 `datasources.json` 与 `tasks.db` 做一致性快照，默认保留最近 7 份。
- 桌面端 Backup & Restore：`POST /v1/backups` 创建快照；恢复时主进程先 `server.stop()` → 执行 `backup restore` → `server.start()`，避免覆盖正在使用的 SQLite；恢复前自动保留 `.pre-restore`。
- active 数据源支持热切换：`BlackboardController.replace_datasource` 在 `datasource_write` + `search` 资源锁内替换共享 datasource；`POST /v1/datasources/active/{name}/switch` 构建 + 探活 + 持久化 + 更新健康快照。
- 服务运行期自动备份（默认开启）：启动时 `backup_if_due` 检查一次，之后每小时检查，`KB_BACKUP_INTERVAL_HOURS` 控制最小间隔，关闭时取消后台任务。
- 运行期健康监控（默认开启）：后台每 30s 探活 datasource + embedder，结果写入 `/v1/health` 快照；`/v1/health/ready` 复用同一探活函数；状态变化打 `health.monitor_degraded` / `health.monitor_recovered`。
- 健康驱动自动 failover：`datasources.json` 顶层 `failover` 顺序；监控连续失败达到阈值后调用 `failover_datasource()`，按序 build + 探活 + 热切换 + 更新 active 指针；全部失败打 `datasource.failover_exhausted`。
- failover 恢复回切：failover 顺序第一项视为主数据源；备用数据源连续健康达到阈值后 `recover_primary()` 自动切回主数据源，成功打 `datasource.failover_recovered`。
- 数据源迁移：`DataSource.dump_all`（`dump` capability）导出全量 text/metadata，`python3 -m app.observability.migrate dump/load` 重新 embedding 后写入目标；memory / ES 支持。

## 7. 技术选型

| 关注点 | 选型 | 备选 |
|---|---|---|
| 桌面框架 | Electron 30+ | Tauri（Rust） |
| UI | React 18 + TypeScript + Vite | SolidJS |
| Python Web | FastAPI + uvicorn | Flask / Django |
| 解析 | openpyxl / python-docx / pdfplumber / markdown-it-py | unstructured |
| 切片 | 自实现（token + overlap） | langchain splitters |
| Embedding 本地 | sentence-transformers + BGE-M3 | FlagEmbedding |
| Embedding 远端 | OpenAI 兼容 HTTP | DashScope |
| 向量库（ES） | elasticsearch-py 8+ dense_vector | — |
| 向量库（PG） | psycopg + pgvector | — |
| MySQL | pymysql + JSON 列 | — |
| VectorDB | pymilvus / qdrant-client / chromadb（按需） | — |
| 元数据 | SQLite（stdlib sqlite3） | — |
| 日志 | structlog（JSON） | loguru |
| 测试 | pytest + vitest + supertest | — |

## 8. 目录结构（建议）

```
/Users/paul/projects/t_ek/
├── AGENTS.md
├── CLAUDE.md
├── feature_list.json
├── progress.md
├── session-handoff.md
├── quality-document.md
├── evaluator-rubric.md
├── clean-state-checklist.md
├── init.sh
├── docs/
│   ├── PROCESS.md
│   ├── inception/
│   ├── elaboration/
│   ├── construction/
│   └── transition/
├── agents/
├── agents.json
├── AGENTS.team.md
├── desktop/                # Electron + React + TS
│   ├── package.json
│   ├── tsconfig.json
│   ├── electron.vite.config.ts
│   ├── src/
│   │   ├── main/
│   │   ├── preload/
│   │   └── renderer/
│   └── README.md
├── server/                 # Python FastAPI
│   ├── pyproject.toml
│   ├── README.md
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── parsers/
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── datasources/
│   │   ├── pipeline/
│   │   └── observability/
│   └── tests/
└── scripts/
    └── bench.sh
```

## 9. 退出标准（架构基线）

- [x] 模块边界明确（本文件 §3）。
- [x] 数据流清晰（§5）。
- [x] 接口契约可实现（§4）。
- [x] 技术选型已确认（§7）。
