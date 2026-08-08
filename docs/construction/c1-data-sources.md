# 数据与报表迭代交付（C1）

> 构造阶段第一个迭代的交付物说明与能力矩阵。

## 模块清单

| 模块 | 文件 | 说明 |
|---|---|---|
| 抽象与契约 | `server/app/datasources/base.py` | `DataSource` ABC、`DatasourceConfig`、`HealthStatus`、注册表 |
| 适配器 ES | `server/app/datasources/elasticsearch_adapter.py` | Elasticsearch 8+ dense_vector（cosine） |
| 适配器 PG | `server/app/datasources/postgres_adapter.py` | pgvector + ivfflat + JSONB 元数据 |
| 适配器 MySQL | `server/app/datasources/mysql_adapter.py` | JSON 列存向量（Python 端 cosine，限 ≤100k） |
| 适配器 Vector | `server/app/datasources/vector_db_adapter.py` | 默认 in-memory；可切换 Milvus 后端 |
| 工厂 | `server/app/datasources/factory.py` | `DatasourceConfig → DataSource` |
| 注册表 | `server/app/datasources/registry.py` | 启动时侧导入注册所有内置适配器 |
| API | `server/app/api/datasources.py` | `GET /v1/datasources` + `POST /v1/datasources/test` |
| 健康检查 | `server/app/api/health.py` | `GET /v1/health` |
| 应用入口 | `server/app/main.py` | FastAPI app 构造 + 启动日志 |

## 能力矩阵

| 能力 | ES | PG | MySQL | Vector(mem) | Vector(milvus) |
|---|---|---|---|---|---|
| add (upsert) | ✓ | ✓ | ✓ | ✓ | ✓ |
| search (cosine) | ✓ | ✓ | ✓ (in-py) | ✓ | ✓ |
| delete by id | ✓ | ✓ | ✓ | ✓ | ✓ |
| metadata filter | ✓ | ✓ | ✓ (JSON_EXTRACT) | ✓ | ✓ |
| bm25 hybrid | ✓ | — | — | — | — |
| 自带 ANN | ✓ (HNSW/IVFFlat) | ✓ (ivfflat) | — | — | ✓ (Milvus) |
| 数据规模 | 高 | 中 | 小（≤100k） | 小（≤50k） | 高 |

## 依赖分层

- 必备：`fastapi`、`pydantic`、`structlog`、`numpy`、`httpx`
- 可选：`elasticsearch`（ES 适配）、`psycopg + pgvector`（PG 适配）、`PyMySQL`（MySQL 适配）、`pymilvus`（Vector 适配）
- 设计原则：适配器即便在可选依赖缺失时也能被导入（`register_datasource` 立即生效）；构造时才报错，便于冷启动与 CI。

## 验证证据

```bash
$ cd server && python3 -m pytest tests/datasources -q
...............................                                          [100%]
31 passed in 0.XX s
```

| 测试文件 | 用例数 | 验证内容 |
|---|---|---|
| `test_contract.py` | 3 | 抽象行为契约 |
| `test_registry.py` | 3 | 注册表 + 工厂 |
| `test_vector_adapter.py` | 8 | in-memory 后端 add/search/delete/filter/health |
| `test_elasticsearch_adapter.py` | 4 | ES 适配器（mock client）：建索引、bulk、knn 搜索、健康 |
| `test_postgres_adapter.py` | 5 | PG 适配器（mock conn）：建表、insert、cosine、delete |
| `test_mysql_adapter.py` | 7 | MySQL 适配器（mock conn）：建表、upsert、search、filter、health |

API 端到端（TestClient）：

```bash
GET  /v1/health           → 200  status=ok, datasources=[es,mysql,pg,vector]
GET  /v1/datasources      → 200  4 types
POST /v1/datasources/test → 200  {ok:true, latency_ms:<1ms}  (vector memory)
POST /v1/datasources/test → 400  invalid config              (unknown type)
```

## 不在范围内（按协议 C1）

- 解析器、embedding、桌面端集成。
- 真实数据库的端到端联通测试（依赖本机/容器部署，迁移到 C2/C3 的手工验证脚本中）。

## 已知缺口

- Milvus 适配器在 v1.0 未做 1:1 单元测试覆盖，仅做 import smoke；后续迭代补。
- PG/ES/MySQL 适配器使用 `IndexingFailure` 等统一异常的边界未单独测试，依赖未来 CI 接 docker-compose。