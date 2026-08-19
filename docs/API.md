# KB Server HTTP API

Base URL: `http://127.0.0.1:8765`

所有响应均为 JSON；错误使用 HTTP 4xx/5xx + `{"detail": "..."}`。

## 健康

### `GET /v1/health`

返回 200 表示服务进程存活。`degraded: true` 表示 embedder 已回退或 active
数据源未绑定，但服务仍可响应（桌面端会显示降级横幅）。

```json
{
  "status": "ok",
  "version": "0.1.0",
  "embed_backend": "openai-compat",
  "embed_dim": 1024,
  "datasources": ["elasticsearch", "mysql", "postgresql", "vector"],
  "degraded": false,
  "started_at": "2026-08-18T00:00:00+00:00",
  "uptime_seconds": 12.345,
  "embedder_backend": "openai-compat",
  "embedder_fallback": false,
  "embedder_ok": true,
  "active_datasource": {
    "name": "es-prod",
    "type": "elasticsearch",
    "source": "active",
    "ok": true,
    "latency_ms": 6.13,
    "message": "9.5.0"
  },
  "data_dir": "/Users/paul/.kb-server",
  "last_probe_at": "2026-08-18T00:00:12+00:00"
}
```

服务默认每 30s（`KB_HEALTH_MONITOR_INTERVAL_SECONDS`）后台探活一次 datasource
与 embedder，结果写入上述快照；`/v1/health/ready` 每次探活也会刷新同一快照。
后台监控可用 `KB_HEALTH_MONITOR=false` 关闭。

### `GET /v1/health/ready`

带 15s TTL 缓存的依赖就绪探针。对当前 active datasource 和 embedder 各做
一次健康检查；返回 `checks` 列表，任一失败时 `status="degraded"`。

```json
{
  "status": "ready",
  "degraded": false,
  "checks": [
    {"name": "server", "ok": true},
    {"name": "datasource", "ok": true, "latency_ms": 6.13, "message": "9.5.0"},
    {"name": "embedder", "ok": true, "latency_ms": 18.2, "message": "probe ok"}
  ]
}
```

所有响应头都会带 `X-Request-Id`（调用方未传时由服务端生成），同一请求期间
后端日志中的 `http.request` / 业务事件共享该 id。

### `GET /v1/settings/ha`

返回当前生效的高可用参数（来自 `KB_*` 环境变量，只读）：

```json
{
  "backup_auto": true,
  "backup_interval_hours": 24.0,
  "backup_keep": 7,
  "health_monitor": true,
  "health_monitor_interval_seconds": 30,
  "failover_enabled": true,
  "failover_consecutive_failures": 2,
  "failover_auto_recover": true,
  "failover_recover_consecutive_checks": 3
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

### `GET /v1/datasources/schemas`

返回每个数据源类型的可编辑字段 schema，供桌面端表单模式渲染；该接口只读，
不改变既有 JSON 配置路径。

```json
{
  "vector": {
    "type": "vector",
    "label": "向量数据库",
    "fields": [
      {
        "key": "backend",
        "label": "后端",
        "type": "select",
        "required": true,
        "sensitive": false,
        "default": "memory",
        "help": "memory 适合小规模个人库；milvus 适合更大规模向量检索。",
        "options": ["memory", "milvus"]
      }
    ]
  }
}
```

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

#### `POST /v1/datasources/configs/{name}/tested`

在用户测试连接成功后，为已保存配置写入 `last_tested_at` 时间戳。

```json
{"name": "vec-local", "type": "vector", "options": {"backend": "memory", "dim": 64}, "saved_at": "...", "last_tested_at": "2026-08-19T00:00:00Z"}
```

错误：`404` —— 找不到该 name 的保存配置。

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

#### `POST /v1/datasources/active/{name}/switch`

**热切换**当前运行中的 active datasource，无需重启服务：

- 构建并探活新适配器（health 非 ok 时 400，不切换）；
- 等待黑板 `datasource_write` / `search` 资源锁，避免打断在飞写入/检索；
- 替换共享 datasource 后持久化 active 指针（下次启动保持一致）；
- 更新健康快照，返回与 `PUT /active/{name}` 相同的 `DatasourceConfigResponse`。

错误：
- `400` —— build 失败或 health 检查未通过；
- `404` —— 找不到该 name 的保存配置；
- `503` —— 黑板控制器未初始化。

#### `GET /v1/datasources/failover`

返回配置的 failover 顺序（`datasources.json` 顶层 `failover` 字段，缺失视为空）。

```json
{"names": ["es-prod", "mem"]}
```

#### `PUT /v1/datasources/failover`

请求 `{"names": ["es-prod", "mem"]}`。服务端只保留已保存配置名、去重保序，返回实际保存结果。

#### `DELETE /v1/datasources/failover`

清空 failover 顺序，返回 `{"names": []}`。

> 自动 failover：健康监控连续 `KB_FAILOVER_CONSECUTIVE_FAILURES`（默认 2）次
> 探到 active datasource 不健康时，按该顺序尝试第一个健康候选并热切换；全部
> 失败不切换并打 `datasource.failover_exhausted`。
> 自动回切：failover 顺序第一项视为主数据源；备用数据源连续
> `KB_FAILOVER_RECOVER_CONSECUTIVE_CHECKS`（默认 3）次健康后，服务会尝试切回
> 主数据源，成功打 `datasource.failover_recovered`。

#### `DELETE /v1/datasources/active`

清空 active；服务下次启动回退到 in-memory vector。

```json
{"name": null, "deleted": true}
```

## 备份

### `GET /v1/backups`

列出 `KB_BACKUP_DIR`（默认 `<data_dir>/backups`）下的快照，按时间倒序。

```json
[
  {
    "name": "kb-backup-20260818-003000",
    "path": "/Users/paul/.kb-server/backups/kb-backup-20260818-003000",
    "created_at": "2026-08-18T00:30:00Z",
    "files": ["datasources.json", "tasks.db"],
    "source": "/Users/paul/.kb-server"
  }
]
```

### `POST /v1/backups`

创建一份新快照（SQLite 走官方 backup API，JSON 直接复制），返回 201 与同上的
`BackupInfo`。

> 恢复不提供 HTTP 端点：恢复会替换正在使用的 SQLite，必须由桌面主进程先停
> Python 服务，再执行 `python3 -m app.observability.backup restore <path>`，
> 完成后重新启动服务。桌面端 Settings → Backup & Restore 已封装该流程。

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
      "metadata": {"document_id": "...", "src": "..."},
      "document_id": "doc456"
    }
  ]
}
```

`document_id` 为可选来源字段（G19 起返回）；桌面端用它展示结果来源，旧客户端
忽略该字段即可。

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
