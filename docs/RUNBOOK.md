# 运行手册 (Runbook)

## 常见故障

### 0. Embedder 默认（核心规则）

> **生产默认 = Ollama bge-m3（OpenAI 兼容 1024-dim 真模型）。CI / pytest 默认 = mock。**
>
> 这是用户决策：把真模型路径固化在规则里，避免新会话或协作者误把 mock 当默认。

| 场景 | embed_backend 来源 | 维度 | 启动脚本 |
|---|---|---|---|
| 生产（本地 Ollama） | `openai-compat`（默认） | 1024 | `bash scripts/start_server_ollama.sh` |
| 离线 / 无 Ollama | `mock-hash`（fallback，运行时懒触发） | 1024 | `KB_EMBED_BACKEND=mock-hash uvicorn app.main:app` |
| local sentence-transformers snapshot | `bge-m3`（罕见备用） | 1024 | `pip install -e ".[embedding-local]"` + `scripts/download_bge_m3.sh` |
| pytest 测试 | `mock-hash`（`tests/conftest.py` 强制覆写） | 1024 | `npm run test:unit` |

切换方式：所有路径都通过 `KB_EMBED_BACKEND` env 切换；默认值写在 `server/app/config/settings.py`。

### 1. 桌面端显示 "server unreachable"

按顺序检查：
1. Python 服务是否在 8765 端口监听：`lsof -i :8765`
2. 后端是否启动失败：直接跑 `bash scripts/start_server_ollama.sh` 看日志（生产默认是 Ollama）
3. 若 Ollama 没在跑：先 `ollama serve`，确认 `curl http://127.0.0.1:11434/api/tags | grep bge-m3`
4. 防火墙/代理：服务只绑 `127.0.0.1`

### 2. 用真模型启动服务端（Ollama bge-m3）

`scripts/start_server_ollama.sh` 一键拉起本地 Ollama 上的 bge-m3 作为 OpenAI 兼容远端 embedder：

```bash
# 前置：ollama daemon 在跑、bge-m3 已 pull
ollama pull bge-m3
ollama list  # 看到 bge-m3:latest 才算就绪

bash scripts/start_server_ollama.sh    # 或 npm run server:ollama
# 验证：curl localhost:8765/v1/health  → embed_backend="openai-compat"
```

该脚本预设：

| Env 默认值 | 值 | 说明 |
|---|---|---|
| `KB_EMBED_BACKEND` | `openai-compat` | 与 settings.py 默认一致 |
| `KB_OPENAI_BASE_URL` | `http://127.0.0.1:11434/v1` | Ollama |
| `KB_OPENAI_API_KEY` | `ollama` | Ollama 不校验 |
| `KB_OPENAI_MODEL` | `bge-m3` | Ollama tag |
| `KB_EMBED_MODEL` | `bge-m3` | 与 OpenAI 同名（避免默认 `BAAI/bge-m3` 404） |
| `KB_EMBED_DIM` | `1024` | bge-m3 输出维度 |

手动等价：

```bash
cd server
KB_EMBED_BACKEND=openai-compat \
KB_OPENAI_BASE_URL=http://127.0.0.1:11434/v1 \
KB_OPENAI_API_KEY=ollama \
KB_OPENAI_MODEL=bge-m3 \
KB_EMBED_MODEL=bge-m3 \
PYTHONPATH=. uvicorn app.main:app --port 8765
```

评测：

```bash
npm run eval          # 默认走 Ollama（openai-compat），10/10 = 100%
npm run eval:mock     # 离线 mock，9/10 = 90%
npm run eval:bgem3    # local snapshot 路径
```

排错：

- **`model "BAAI/bge-m3" not found` 404** —— Ollama 上模型 tag 不是 `BAAI/bge-m3`。设 `KB_OPENAI_MODEL=bge-m3`（即上面脚本里 `KB_EMBED_MODEL` 同值；BAAI 前缀是 sentence-transformers 路径）。
- **`Connection refused :11434`** —— Ollama daemon 没在跑；`ollama serve` 起。
- **`remote embed failed 5xx`** —— Ollama 在跑但 bge-m3 没拉：`ollama pull bge-m3`。
- **首次 import 报 `EmbedderError` 而启动日志显示 `embedder.ready`** —— openai-compat 是懒连接，第一次嵌入才真正 ping Ollama；启动期探测开销太大，按设计不在启动时探测。

### 2a. OpenAI 兼容远端的重试退避（KI-03）

`openai-compat` embedder 自带指数退避，**只对瞬时错误重试**：

| 状况 | 是否重试 |
|---|---|
| `httpx.TransportError`（连接拒绝、超时、broken pipe） | ✅ 重试 |
| HTTP 5xx（502/503/504/…） | ✅ 重试 |
| HTTP 429（限流） | ✅ 重试 |
| 其他 4xx（400/401/403/404） | ❌ 直接抛 `EmbedderError`，是配置错误不是抖动 |

退避阶梯：默认 `initial_backoff=0.5s` → `1.0s` → `2.0s` …，封顶 `max_backoff=8s`；带 ±10% jitter 防雪崩。

每次重试打一行结构化日志：

```json
{"event": "embedder.retry", "level": "warning",
 "attempt": 1, "max_attempts": 4, "status_code": 503, "sleep_seconds": 0.48}
```

超过 `max_retries`（默认 3，即初始 + 3 次重试 = 4 次）后抛出：

```
EmbedderError: remote embed failed after 4 attempt(s): ConnectError: ...
```

调参：在数据源 options 里覆盖（KB_EMBED_OPTIONS 或 KB_DATA_DIR/datasources.json）：

```json
{
  "type": "openai-compat",
  "options": {
    "base_url": "http://127.0.0.1:11434/v1",
    "api_key": "ollama",
    "model": "bge-m3",
    "max_retries": 5,
    "initial_backoff": 1.0,
    "max_backoff": 16.0,
    "backoff_jitter": 0.2
  }
}
```

要禁用重试：`max_retries: 0`。

### 2b. 健康检查与降级提示（C10）

服务有三层健康信号：

1. `GET /v1/health` —— 存活快照，返回 `degraded / started_at / uptime_seconds / embedder_backend / embedder_fallback / active_datasource`。桌面端 5s 心跳继续用它；服务能响应就算活，但降级事实会通过顶部黄色横幅展示。
2. `GET /v1/health/ready` —— 依赖就绪探针（15s TTL 缓存），逐个探活当前 active datasource 与 embedder：

```bash
curl -sS http://127.0.0.1:8765/v1/health/ready | python3 -m json.tool
```

3. `X-Request-Id` —— 所有响应头带请求关联 id；后端 `http.request` 日志与业务日志共享同一 `request_id`，排障时按 id 一次拉全链路：

```bash
grep '"request_id": "abc123"' server.log | tail -50
```

服务默认每 30s 后台探活 datasource + embedder，并把结果写进 `/v1/health`；
状态变化时打 `health.monitor_degraded` / `health.monitor_recovered`。桌面端每
15s 轮询 `/v1/health`，远端数据源中断或恢复时降级横幅会自动更新。配置：
`KB_HEALTH_MONITOR`（默认 true）/ `KB_HEALTH_MONITOR_INTERVAL_SECONDS`（默认 30）。
桌面端 Settings → HA Configuration 会只读展示自动备份、健康监控、failover 的
当前生效参数。

降级横幅常见触发：

| 场景 | 显示 | 修法 |
|---|---|---|
| Ollama 没起，embedder 回退 mock | `embedder fell back to mock-hash` | `ollama serve` + `ollama pull bge-m3` 后重启 server |
| active 数据源构建失败，回退内存 | `no active datasource` | 看启动日志 `datasource.active_load_failed`；修配置或重装依赖后重启 |
| `/v1/health/ready` 探活失败 | `datasource ... is not available` | 检查远端 ES / PG / Milvus 连接 |

### 2c. 备份/恢复（C10-C13）

`~/.kb-server` 里的 `datasources.json` 与 `tasks.db`（任务 + 黑板投影）可做一致性快照：

```bash
npm run backup        # 等价：cd server && python3 -m app.observability.backup
# → backup created: /Users/paul/.kb-server/backups/kb-backup-20260818-003000
```

默认配置：

| Env | 默认 | 说明 |
|---|---|---|
| `KB_DATA_DIR` | `~/.kb-server` | 备份来源 |
| `KB_BACKUP_DIR` | `~/.kb-server/backups` | 备份根目录（可放外部磁盘） |
| `KB_BACKUP_KEEP` | `7` | 保留最近 N 份，更早的自动清理 |
| `KB_BACKUP_AUTO` | `true` | 服务运行期间自动备份 |
| `KB_BACKUP_INTERVAL_HOURS` | `24.0` | 自动备份最小间隔（小时） |

SQLite 用官方 backup API 在线快照，不会出现半截文件；JSON 直接复制并写
`manifest.json`。

自动备份（C13）：服务启动时若没有新快照会立即创建一份，之后每小时检查一次
`backup_if_due`，最新快照超过间隔才新建；日志事件为 `backup.auto_scheduled` /
`backup.auto_created` / `backup.auto_skipped` / `backup.auto_failed`。测试环境
固定 `KB_BACKUP_AUTO=false`，生产默认开启，可用 `KB_BACKUP_AUTO=false` 关闭。

查看与恢复：

```bash
cd server && python3 -m app.observability.backup list
# 输出所有快照的 name / path / created_at / files / source

cd server && python3 -m app.observability.backup restore /path/to/kb-backup-...
# 恢复前自动把当前数据目录留到 ~/.kb-server/.pre-restore/（保留 3 份）
```

**恢复必须停 server 后执行**（SQLite 正在被占用时覆盖会损坏数据）。最省事
的方式是桌面端 **Settings → Backup & Restore**：创建备份、看快照列表、点
Restore；主进程会先停 Python 服务 → 执行 restore → 再自动重启。备份目录若
放在外部磁盘，`KB_BACKUP_DIR` 指向该盘即可。

**安全提示**：备份内含 `datasources.json` 的数据库密码。请按 `~/.kb-server`
同等权限保护备份目录，不要提交到公开仓库或网盘明文共享。

### 3. 数据源配置管理（CRUD + active 切换）

UI 路径：Settings → "Add new datasource" / "Saved datasource configs"。
HTTP 路径：`/v1/datasources/{configs,configs/{name},active,active/{name}}`（详见 `docs/API.md`）。
持久化文件：`~/.kb-server/datasources.json`（v1 schema；原子写；可直接 `cat` 检查）。

变更流程：

1. 在 Settings 里填 name / type / options (JSON)；
2. 点 **Test connection** 验联通（向 `/v1/datasources/test` 打探针）；
3. 点 **Save as new config**（或 update 时 **Save changes**）写入；
4. 在表格里点 **Activate** 让下次启动作为默认 datasource；
5. 若想**立即生效**，点 **Switch now**（等待在飞写入/检索结束后热切换，无需重启）；若只想为下次启动预选，保留 Activate。

热切换等价 curl：

```bash
curl -sS -X POST http://127.0.0.1:8765/v1/datasources/active/es-prod/switch
```

排错：**switch 返回 400 "datasource health check failed"** —— 新配置远端不可达；
服务不会切到坏数据源。**返回 503** —— 黑板控制器未初始化，先看启动日志。

常见 type 的 options 示例：

```jsonc
// 内存向量（最快，重启即清零）
{"backend": "memory", "dim": 1024}
// Milvus
{"backend": "milvus", "uri": "http://127.0.0.1:19530", "dim": 1024}
// Elasticsearch 8+ / 9.x（注意：实际字段是 hosts, 不是 url）
{"hosts": ["http://127.0.0.1:9200"], "index": "kb_chunks", "dim": 1024,
 "username": "elastic", "password": "...", "verify_certs": false}
// PostgreSQL + pgvector
{"dsn": "postgresql://user:pwd@127.0.0.1:5432/kb", "table": "kb_chunks", "dim": 1024}
// MySQL（仅小数据集，详见 §5）
{"host": "127.0.0.1", "port": 3306, "user": "root", "password": "...", "database": "kb", "dim": 1024}
```


排错：

- **"unknown datasource type" 400** —— `type` 不在 4 个注册适配器里；看 Settings 顶部的 dropdown 取值。
- **"invalid config" 400** —— adapter 在 build 阶段失败（如 `postgresql` 缺 `dsn`、es 缺客户端库等）；先 `pip install ".[es]"` 或 `pip install ".[pg]"` 等再试。
- **"active_load_failed" 日志** —— 保存的 active 配置成功 build 失败（依赖未装 / 远端连不上）；服务回退到 in-memory vector。下次启动前修好。
- **改了 active 但没生效** —— UI-driven 激活只在下次进程启动生效；active 切换不打断正在运行的 import/search pipeline。

### 3a. 真实 Elasticsearch 接入示例（已验证 prod 路径）

下面这套已经端到端跑通（Ollama bge-m3 真嵌入 + ES 9.5 真实存储 + cosine ANN）：

```bash
# 1. 启服务（Ollama bge-m3）
bash scripts/start_server_ollama.sh &        # http://127.0.0.1:8765

# 2. 保存 ES 配置（curl 直发）
curl -sS -X POST http://127.0.0.1:8765/v1/datasources/configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "es-prod",
    "type": "elasticsearch",
    "options": {
      "hosts": ["http://127.0.0.1:9200"],
      "index": "kb_chunks",
      "dim": 1024,
      "username": "elastic",
      "password": "<your password>",
      "verify_certs": false
    }
  }'

# 3. 探活验证联通
curl -sS -X POST http://127.0.0.1:8765/v1/datasources/test \
  -H "Content-Type: application/json" \
  -d '{"name":"x","type":"elasticsearch","options":{"hosts":["http://127.0.0.1:9200"],"dim":1024,"username":"elastic","password":"...","verify_certs":false}}'
# → {"ok": true, "latency_ms": 6.13, "message": "9.5.0"}

# 4. 设为 active（下次启动生效）
curl -sS -X PUT http://127.0.0.1:8765/v1/datasources/active/es-prod

# 5. 重启 server
pkill -f "uvicorn app.main:app"; bash scripts/start_server_ollama.sh &
# 启动日志会打：datasource.from_saved name=es-prod type=elasticsearch

# 6. 端到端测试
curl -sS -X POST http://127.0.0.1:8765/v1/files/import -F "file=@README.md"
# → 启动 log 会写：elasticsearch.index.created index=kb_chunks

curl -sS -u elastic:$ES_PASS "http://127.0.0.1:9200/kb_chunks/_count"
# → {"count": N, ...}   直查 ES 看到真数据

curl -sS -X POST http://127.0.0.1:8765/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"embedding 模型选用什么","top_k":3}'
# → hits 带 cosine 分数 (0.7+ 区间)，真 ES ANN
```

直接验证 ES 索引 mapping：

```bash
curl -sS -u elastic:$ES_PASS "http://127.0.0.1:9200/kb_chunks/_mapping" | python3 -m json.tool
# 应看到 vector.dims=1024, similarity=cosine, index_options.type=bbq_hnsw (ES 9.x 默认)
```

字段名警告：`hosts`（数组），**不是** `url`。早期 RUNBOOK §3 写错过 `url:`；本 §3a 是已验证模板。

### 3b. 自动 failover（C15）

当 active 数据源连续 N 次健康检查失败时，服务自动按顺序切到第一个健康的备用
数据源：

```bash
# 1. 保存两个配置（UI 或 curl）
# 2. 设置 failover 顺序
curl -sS -X PUT http://127.0.0.1:8765/v1/datasources/failover \
  -H "Content-Type: application/json" -d '{"names": ["es-prod", "mem"]}'
# 3. 查看
curl -sS http://127.0.0.1:8765/v1/datasources/failover
```

配置：

| Env | 默认 | 说明 |
|---|---|---|
| `KB_FAILOVER_ENABLED` | `true` | 是否启用自动 failover |
| `KB_FAILOVER_CONSECUTIVE_FAILURES` | `2` | 连续失败多少次触发切换 |

桌面端 Settings → Failover order 可直接维护逗号分隔的顺序。切换成功后
`active` 指针同步更新，日志 `datasource.failover`；候选全部不可用时打
`datasource.failover_exhausted`，不会反复切回。

主库恢复后会自动回切：failover 顺序第一项视为主数据源，备用数据源连续
`KB_FAILOVER_RECOVER_CONSECUTIVE_CHECKS`（默认 3）次健康后尝试切回主数据源；
成功打 `datasource.failover_recovered`。可用 `KB_FAILOVER_AUTO_RECOVER=false`
关闭自动回切（保留自动 failover）。

### 3c. 数据源迁移（C17）

把数据从旧数据源复制到新数据源（重新 embedding 后写入）：

```bash
cd server

# dump：源必须支持 dump capability（当前 memory / elasticsearch）
python3 -m app.observability.migrate dump \
  --type vector --options '{"backend":"memory","dim":1024}' \
  --output /tmp/kb-dump.jsonl

# load：目标数据源 + 当前 embedder（mock-hash 仅测试；生产用 openai-compat）
python3 -m app.observability.migrate load \
  --type elasticsearch --options '{"hosts":["http://127.0.0.1:9200"],"index":"kb_chunks","dim":1024}' \
  --input /tmp/kb-dump.jsonl --embed openai-compat --dim 1024
```

dump 保留 `document_id / text / metadata`，load 时重新 embedding，避免模型或维度
变化后旧向量失效。迁移量可能很大，建议停服或低峰期执行。

### 4. 导入 PDF 返回空

PDF 仅含扫描图片时，`pdfplumber` 抽不到文字，`metadata.ocr_required=true`。
**绕行**：在桌面端用 OCR 工具预转文本后导入；或后续接 OCR 适配器。

### 4a. 上传进度可观测性（G6）

桌面端 `ImportPage` 现在同时显示**进度条** + **当前阶段文字**（"解析文档"/"切片中"/"Embedding 中"/"写入数据源"/"完成"）+ **事件日志**（带时间戳的最近 ~32 条 stage 转换）。后端对应的事件流：

- `IndexingPipeline.run` 在 4 个边界点发出 `ProgressEvent(stage, progress, message)`：`parsing (0.05)` → `chunking (0.30)` → `embedding (0.30+0.50·frac)`（每个 batch）→ `writing (1.0)`。
- `app/api/files.py::_run_import` 在每个 stage 边界调 `store.add_event(...)` + `store.update(stage=...)`，并打 structlog 事件 `pipeline.stage`。
- `TaskStore` 持久化：v1 schema 加 `stage` 列 + `task_events` 表（ring buffer 32 条）；老库自动 `ALTER TABLE` + `PRAGMA user_version` 升到 1，不丢数据。
- 客户端通过 `GET /v1/files/tasks/{id}` 的 `events` 字段直接消费；`/events?since_id=` 留给未来的 live-tail 消费者。

排错：跑 `grep pipeline.stage server.log | tail` 看实时阶段；用 `KB_DATA_DIR/tasks.db` + `sqlite3 "select ts, stage, message from task_events where task_id=… order by id"` 看历史事件。

调优：如个别 import 阶段文案过吵（Ollama bge-m3 大文件每个 batch 都打），可在 `app/api/files.py::_run_import::_progress` 里按 `batch_size` 过滤；目前保留全量便于排错。

### 4b. ES 数据浏览（goal-es-browse / G7）

桌面端 Browse tab 调 `GET /v1/chunks`（仅 `elasticsearch` 适配器实现 `chunk_list` capability；其它 adapter 报 501）。请求和响应详见 `docs/API.md` §浏览。

排错：

- **打开 browse tab 看到 "datasource 'xxx' does not support chunk_list"** —— 当前 active 不是 ES。要么切到 ES（见 §3a）；要么接受该数据源不支持浏览，回到 import / search tab。
- **响应 503** —— 服务启动期未绑定 active 数据源；查启动日志 `kb-server.startup` 看 `datasources=...` 与 `datasource.from_saved` / `datasource.default_in_memory` 事件。
- **`metadata.parser` terms aggregation 失败** —— 索引里第一个 doc 没有 `parser` 字段；dynamic mapping 没建好。修法：在 ES 端手动补 mapping 或重灌一次 import（pipeline 会自动 `ensure_index()`）。
- **active 切换后还看老数据** —— 遵循 G2 决策：active 切换**只在下次 server 启动生效**；重启桌面端即可。

性能：`aggregate_by_document` 使用 ES `terms` agg（size=1000）+ `top_hits`（size=1）；在百万级文档下仍可控。如未来需要 >1000 个 doc 的聚合可改用 `composite` agg。

### 5. MySQL 适配器查询慢（KI-02）

`mysql_adapter` 在 Python 内对全表/扫描行做 cosine 相似度，复杂度 O(N)。当库内行数逼近 `max_scan_rows`（默认 100,000）时，检索延迟会显著上升且结果可能被截断。`mysql_adapter` 自 C8 起会在两类时机打结构化日志：

- `mysql.adapter.small_dataset_only`（warning，构造时）—— 提示本适配器仅适合小库，建议切到 PostgreSQL pgvector 或 Milvus。
- `mysql.adapter.scan_limit_hit`（warning，检索时）—— 当一次 search 返回行数 ≥ `max_scan_rows` 时触发，附 `scanned_rows` / `max_scan_rows` 字段；结果仍按 `top_k` 截断。

`capabilities()` 也新增 `scan_limit_risk`，调用方可在 UI 上据此高亮"建议切库"。

#### 何时切换

- 数据量稳定超过 50k 且 `scan_limit_hit` 日志频繁出现：建议尽快切换。
- 平均 search 延迟 > 500ms 且 tail latency 持续劣化：同上。
- 评测命中率（`server/eval/run_eval.py`）下降：可能是 top_k 截断在起作用，必须切。

#### 切到 PostgreSQL pgvector（推荐）

适用：已有 PostgreSQL 运维、希望保留 SQL 接口、需要 IVFFlat 索引。

1. 在新 PostgreSQL 实例启用扩展：`CREATE EXTENSION IF NOT EXISTS vector;`
2. 用 `postgres_adapter` 重建表（schema 由适配器自动 `CREATE TABLE IF NOT EXISTS` + `ivfflat` 索引）。
3. **数据迁移两步**：
   - 旧实例逐条 `search()` 导出 `{id, document_id, text, metadata, vector}`（项目内暂无批量 dump CLI，可写一次性脚本；规模可控时直接调 `/v1/files/import` 重跑亦可）。
   - 在新适配器上调 `POST /v1/datasources/test` 验证联通 → `add()` 批量灌入。
4. 验证 `eval/run_eval.py --datasource postgresql` 命中率不下降；UI 切换到新数据源。

#### 切到 Milvus / Qdrant（更大规模）

适用：≥ 1M 向量、需要 ANN 召回 + 元数据过滤混合查询。

1. 用 `bash scripts/start_milvus.sh`（或自带 Milvus 集群）拉起 standalone。
2. `vector_db_adapter` 选 `backend=milvus` + 配置 `uri=http://127.0.0.1:19530`。
3. 数据迁移与 pgvector 类似：先 dump → 新实例 `add()`。
4. 项目自带 `tests/datasources/test_milvus_adapter.py` 8 项 1:1 单测可用作回归基线。

> C8 收敛边界：仅打日志 + 文档化迁移路径，**不**内置 dump/load 工具；规模增长后再单独开迭代。

### 6. Electron 主进程拉起 Python 失败

- 确认 `server/` 与 `desktop/` 同级（默认从 `desktop/dist/main/index.js` 回溯三层到仓库根）。
- 用 `KB_PYTHON=/path/to/python3.11` 指定解释器。
- macOS 上若 venv 缺少 `python3` symlink，可 `ln -s $(which python3) .venv/bin/python3`。

### 7. 评测命中率低于门槛

10 条 fixture 默认 60% 门禁。Mock embedder 下命中约 90%。若降到 <60%：
- 检查 chunk_size 是否过大导致段落混在一起（默认 1200）。
- 检查 query 是否与 corpus 关键词重叠。
- 切到真实 BGE-M3 通常显著提升。

## 平台差异

| 关注点 | macOS | Linux | Windows |
|---|---|---|---|
| `better-sqlite3` 编译 | xcrun + clang | gcc / musl | MSVC + python |
| Python 默认 | `/opt/homebrew/bin/python3` | 系统 `python3` | `py -3` |
| 路径分隔 | `/` | `/` | `\\`（代码全部用 `path.join`，透明） |
| 后台进程信号 | SIGTERM | SIGTERM | taskkill /F |

## 回滚 / 数据迁移

- 元数据在 `~/.kb-server/tasks.db` (server) 与 `<userData>/kb-desktop/metadata.db` (desktop)。删除即清空，不影响向量库。
- 向量库切换需要先 `POST /v1/datasources/test` 验证新配置 OK → 老实例 `delete` → 新实例 `add`（API 暂未批量迁移，C5+ 补）。
- 桌面端的"设置 → 测试连接"页可用于切换前预验证。

## 日志与排错

- 服务端结构化 JSON 日志写到 stderr：`{"event": "...", "level": "info", "timestamp": "..."}`。
- 桌面端主进程把 `[kb-server]` 前缀的子进程 stdout/stderr 透传到 Electron stderr。
- 检索评测报告：`PYTHONPATH=. python3 eval/run_eval.py` 输出 JSON。

## 性能基准

可执行（`server/scripts/` 暂无）— 计划在 transition 阶段补 `benchmark.sh`，覆盖：
- 1000 chunks 的 embedding 吞吐（BGE-M3 vs mock）
- 4 类数据源在 10k / 100k / 1M 下的检索延迟
- PDF / Excel 大文件的解析耗时
