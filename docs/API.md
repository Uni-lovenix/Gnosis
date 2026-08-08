# KB Server HTTP API

Base URL: `http://127.0.0.1:8765`

所有响应均为 JSON；错误使用 HTTP 4xx/5xx + `{"detail": "..."}`。

## 健康

### `GET /v1/health`

返回 200 表示服务存活。

```json
{
  "status": "ok",
  "version": "0.1.0",
  "embed_backend": "bge-m3",
  "embed_dim": 1024,
  "datasources": ["elasticsearch", "mysql", "postgresql", "vector"]
}
```

## 数据源

### `GET /v1/datasources`

列出已注册的适配器类型及其能力。

```json
[
  {"name": "vector", "type": "vector", "capabilities": ["metadata_filter"]},
  {"name": "postgresql", "type": "postgresql", "capabilities": []},
  ...
]
```

> 各适配器 `capabilities` 含义：
> - `metadata_filter` —— 支持按 metadata 等值过滤；
> - `small_dataset_only` —— 仅适合小数据集（≤ `max_scan_rows` 行）；
> - `scan_limit_risk` —— `mysql` 特有，search 可能被 `max_scan_rows` 截断；当数据量逼近上限时应切换到 `postgresql`（pgvector）或 `vector`（Milvus）。详见 `docs/RUNBOOK.md` §3。

### `POST /v1/datasources/test`

联通性测试。

请求：
```json
{"name": "test", "type": "vector", "options": {"backend": "memory", "dim": 64}}
```

响应：
```json
{"ok": true, "latency_ms": 0.42, "message": null}
```

### 已保存的数据源配置 CRUD（goal.md 第 16 条）

> 持久化文件：`~/.kb-server/datasources.json`（v1 schema；原子写）。
> "active" 配置在下次服务启动时作为默认 datasource。
> 桌面端 Settings → Add new datasource / Save / Activate / Delete 全部直接打这套接口。

#### `GET /v1/datasources/configs`

列出所有用户保存的配置（按 `saved_at` 升序）。

```json
[
  {
    "name": "vec-local",
    "type": "vector",
    "options": {"backend": "memory", "dim": 64},
    "saved_at": "2026-08-05T05:00:00Z",
    "last_tested_at": null
  }
]
```

#### `POST /v1/datasources/configs`

新增或覆盖一条配置（按 `name` upsert）。建议调用前先用 `/test` 验过相同 payload。

请求：
```json
{"name": "vec-local", "type": "vector", "options": {"backend": "memory", "dim": 64}}
```

错误：
- `400 unknown datasource type` —— `type` 不在注册表里；
- `400 invalid config` —— adapter 在 build 阶段抛错（缺依赖、options 不合法等）。

#### `DELETE /v1/datasources/configs/{name}`

按名删除；若删除的是当前 active，则同时清空 active。

```json
{"name": "vec-local", "deleted": true}
```

#### `GET /v1/datasources/active`

返回当前 active 配置（active 切换在下次启动生效）。

```json
{"name": "vec-local", "config": { ... }}
```

#### `PUT /v1/datasources/active/{name}`

把 `name` 对应的保存配置标记为 active。已存在的 active 会被覆盖。

错误：
- `404` —— 找不到该 name 的保存配置。

#### `DELETE /v1/datasources/active`

清空 active；服务下次启动回退到 in-memory vector。

```json
{"name": null, "deleted": true}
```

## 文件

### `POST /v1/files/import`（multipart）

表单字段 `file`。

支持类型：`.xlsx .xls .docx .doc .pdf .md .markdown .txt`。

成功响应（200）：
```json
{
  "task_id": "abc123",
  "document_id": "doc456",
  "chunks": 12,
  "parser": "markdown",
  "mime": "text/markdown",
  "size": 1024
}
```

错误：
- `400`：文件为空
- `415`：不支持的文件类型
- `422`：解析错误
- `500`：embedding 或写入失败

### `GET /v1/files/tasks/{task_id}`

查询后台任务进度与阶段日志（goal-upload-progress / G6）。

```json
{
  "task_id": "abc123",
  "kind": "import",
  "status": "running",          // queued | running | done | failed
  "progress": 0.45,
  "stage": "embedding",         // queued | parsing | chunking | embedding | writing | done | failed
  "events": [                   // 最近 ~32 条 ring buffer（按时间升序）
    {"ts": "2026-08-06T12:00:00Z", "stage": "parsing",   "progress": 0.05, "message": "parsing notes.md"},
    {"ts": "2026-08-06T12:00:01Z", "stage": "chunking",  "progress": 0.30, "message": "12 chunks"},
    {"ts": "2026-08-06T12:00:03Z", "stage": "embedding", "progress": 0.55, "message": "8/12 chunks embedded"}
  ],
  "error": null,
  "result": null
}
```

- `stage` —— 渲染端用它显示"解析中"/"Embedding 中"等阶段文字。
- `events[*].message` —— 人类可读的提示（文件名、chunk 计数等），用于事件日志。
- 字段缺席时视为旧服务器：渲染端 fallback 到 `stage="queued"` `events=[]`。

### `GET /v1/files/tasks/{task_id}/events`

增量事件流（备用）。当前渲染端消费 `TaskResponse.events`，本接口留给未来的事件流订阅者。

Query：`since_id`（可选，默认 `0`）—— 只返回 row id > `since_id` 的事件。

```json
{
  "events": [
    {"ts": "...", "stage": "writing", "progress": 1.0, "message": "wrote 12 chunks"}
  ],
  "next_since_id": 5
}
```

错误：`404 task not found`。

## 检索

### `POST /v1/search`

请求：
```json
{
  "query": "BGE-M3 嵌入维度",
  "top_k": 5,
  "filter": {"document_id": "doc456"}  // 可选
}
```

响应：
```json
{
  "hits": [
    {
      "id": "chunk-id",
      "score": 0.83,
      "text": "...",
      "metadata": {"document_id": "...", "src": "..."}
    }
  ]
}
```

`filter` 按 metadata JSON 字段等值匹配；不同数据源适配器可能有差异，详见各适配器 README。

## 浏览（goal-es-browse / G7）

### `GET /v1/chunks`

读取当前 active 数据源里的 chunks，用于桌面端的"数据检查"页。

Query：
- `document_id` —— 可选，过滤到单个 `document_id`。
- `parser` —— 可选，过滤到单个 `parser`（来自 metadata）。
- `offset` —— 默认 `0`，分页偏移。
- `limit` —— 默认 `20`，范围 `[1, 100]`。

响应（200）：
```json
{
  "chunks": [
    {
      "chunk_id": "abc123",
      "document_id": "doc456",
      "text": "前 240 字符…",
      "text_length": 1380,
      "metadata": {"parser": "markdown"}
    }
  ],
  "total": 8,
  "aggregations": {
    "doc456": {
      "document_id": "doc456",
      "chunk_count": 8,
      "parsers": ["markdown"],
      "first_chunk_id": "abc123",
      "sample_text": "前 240 字符…"
    }
  }
}
```

错误：
- `400` / `422` —— `limit` 或 `offset` 非法（FastAPI Query 校验返回 422；处理器内手动校验返回 400）。
- `501` —— 当前 active 数据源不支持 `chunk_list` capability（仅 `elasticsearch` 实现；其它 adapter 见 `docs/RUNBOOK.md` §3 迁移路径）。
- `503` —— 启动期未绑定 active 数据源；检查启动日志。

> 数据源绑定遵循 G2 设计：active 切换**只在下次启动生效**。运行时热切换不在本迭代范围。

## 配置

通过 `KB_*` 环境变量（详见 `server/README.md` 与 `docs/RUNBOOK.md` §0）：
- `KB_PORT`（默认 8765）
- `KB_DATA_DIR`（默认 `~/.kb-server`）
- `KB_EMBED_BACKEND`（**默认 `openai-compat`** = 本地 Ollama bge-m3；备选 `bge-m3` / `mock-hash`）
- `KB_EMBED_MODEL`、`KB_EMBED_DIM`（默认 `bge-m3` / `1024`）
- `KB_OPENAI_BASE_URL`（默认 `http://127.0.0.1:11434/v1`）
- `KB_OPENAI_API_KEY`（默认 `ollama`）
- `KB_OPENAI_MODEL`（默认 `bge-m3`）
- `KB_LOG_LEVEL`、`KB_LOG_JSON`