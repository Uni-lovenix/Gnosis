# 数据源适配器测试

本目录覆盖 4 类数据源适配器 + 1 个契约测试 + 1 个 Milvus 1:1 套件。

| 文件 | 后端 | 依赖 |
|---|---|---|
| `test_contract.py` | 公共契约（add/search/delete/health） | 无 |
| `test_elasticsearch_adapter.py` | Elasticsearch 8+（真实 HTTP） | 本机 / Docker ES |
| `test_postgres_adapter.py` | PostgreSQL + pgvector | 本机 / Docker Postgres |
| `test_mysql_adapter.py` | MySQL（JSON 列向量） | 本机 / Docker MySQL |
| `test_vector_adapter.py` | Vector 内存后端（numpy） | 无 |
| `test_milvus_adapter.py` | Vector Milvus 后端（真实 / Lite） | 见下 |

## Milvus 1:1 单测

```bash
# Standalone（docker）
bash scripts/start_milvus.sh
KB_MILVUS_URI=http://127.0.0.1:19530 pytest tests/datasources/test_milvus_adapter.py -v

# 或 Lite（嵌入式）
pip install "pymilvus[milvus_lite]"
KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/datasources/test_milvus_adapter.py -v
```

**Skip 语义**：conftest 在 19530 端口不可达（或 `KB_MILVUS_URI` 指向的 http 端点不可达）时 `pytest.skip(...)`，并在提示中给出 `scripts/start_milvus.sh` 或 Lite 的指引；本地路径不进行 TCP 探测，由 `MilvusClient` 自身握手失败兜底。

**Collection 命名**：每个用例 `kb_test_<uuid8>`；teardown 调 `drop_collection` + `close()`，不会污染 Milvus 实例。

**用例对照**（与 `test_vector_adapter.py` 1:1）：

- `test_add_search_delete`
- `test_add_is_idempotent`
- `test_search_with_filter`
- `test_search_empty_store_returns_empty`
- `test_health_ok`
- `test_chunk_without_vector_rejected`
- `test_dimension_mismatch_rejected`
- `test_capabilities_declared`

## 退出准则

- 不修改 `test_vector_adapter.py` 现有用例；
- 修改 `_MilvusBackend.__init__` 时保持 `DatasourceError` 抛错语义不变（缺依赖 → 清晰报错）；
- 任何新的 schema 字段需在 `tests/datasources/test_milvus_adapter.py` 里同步覆盖。