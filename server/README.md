# KB Server -- 灵知 (Gnosis) 后端

FastAPI 服务，承载文件解析、embedding、向量存储与检索。

## 快速开始

```bash
# 推荐：可编辑安装 + 解析 + embedding-local
pip install -e ".[parsers,embedding-local,test]"

# 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

## 可选依赖（按需启用）

| 名称 | 启用命令 | 说明 |
|---|---|---|
| Elasticsearch | `pip install -e ".[es]"` | dense_vector 适配 |
| PostgreSQL + pgvector | `pip install -e ".[pg]"` | pgvector 适配 |
| MySQL | `pip install -e ".[mysql]"` | JSON 列向量适配（O(N) Python cosine，**仅适合 ≤100k 行**；超规模请切 PostgreSQL pgvector 或 Milvus，详见 RUNBOOK §3） |
| Milvus | `pip install -e ".[vector]"` | 向量库适配 |
| 文件解析 | `pip install -e ".[parsers]"` | excel/word/pdf/markdown |
| 本地 embedding | `pip install -e ".[embedding-local]"` | BGE-M3 本地推理 |

## 环境变量

| 名称 | 默认 | 说明 |
|---|---|---|
| `KB_HOST` | `127.0.0.1` | 监听地址 |
| `KB_PORT` | `8765` | 端口 |
| `KB_DATA_DIR` | `~/.kb-server` | 元数据与缓存目录 |
| `KB_EMBED_BACKEND` | `bge-m3` | `bge-m3` 或 `openai-compat` |
| `KB_EMBED_MODEL` | `BAAI/bge-m3` | sentence-transformers 模型名 |
| `KB_EMBED_DIM` | `1024` | 向量维度（BGE-M3 默认 1024） |
| `KB_OPENAI_BASE_URL` | — | 远端 OpenAI 兼容 base url |
| `KB_OPENAI_API_KEY` | — | 远端 API key |
| `KB_OPENAI_MODEL` | `bge-m3` | 远端模型名 |
| `KB_LOG_LEVEL` | `INFO` | 日志级别 |
| `KB_LOG_JSON` | `true` | JSON 结构化日志 |

## 路由

- `GET  /v1/health`
- `GET  /v1/datasources`
- `POST /v1/datasources/test`
- `POST /v1/files/import`
- `GET  /v1/tasks/{task_id}`
- `POST /v1/search`

## 测试

```bash
pytest
```

> 数据源适配器测试使用 mock；如需真实联通，请在本地启动对应服务并设置环境变量。

### Milvus 1:1 单测

`tests/datasources/test_milvus_adapter.py` 用真实 Milvus 后端跑与内存后端 1:1 对应的用例（add / search / delete / filter / idempotent / health / dim mismatch）。无 Milvus 时自动 skip，不会让其他用例失败。

```bash
# 1) 安装 pymilvus（如未装）
pip install -e ".[vector]"

# 2a) 启动独立 Milvus（容器方式）
bash scripts/start_milvus.sh
pytest tests/datasources/test_milvus_adapter.py -v
bash scripts/stop_milvus.sh    # 关停

# 2b) 或用 Milvus Lite（嵌入式，无需 docker）
pip install "pymilvus[milvus_lite]"
KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/datasources/test_milvus_adapter.py -v
```

`KB_MILVUS_URI` 默认是 `http://127.0.0.1:19530`，即 `scripts/start_milvus.sh` 启动的 standalone 容器；任意 MilvusClient 接受的 URI 都可覆盖（包含 http(s) 与本地 Lite 路径）。

> 1:1 测试每次会建一个独立 collection（`kb_test_<uuid8>`），teardown 自动 drop；除非脚本异常中断，Milvus 不会残留脏数据。

## 检索评测

详见 `server/eval/README.md`。

```bash
# mock 路径（默认，CI 跑这条）
PYTHONPATH=. python3 eval/run_eval.py

# 真实 BGE-M3 路径（首次需要下载权重）
./scripts/download_bge_m3.sh
pip install -e ".[embedding-local]"
PYTHONPATH=. python3 eval/run_eval.py --embedder bge-m3
```