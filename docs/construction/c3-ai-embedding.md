# AI 与智能体迭代交付（C3）

> 构造阶段第三个迭代的交付物说明。

## 模块清单

| 模块 | 文件 | 说明 |
|---|---|---|
| Embedder 抽象 | `server/app/embedding/base.py` | `Embedder` ABC、`EmbedderConfig`、注册表 |
| BGE-M3 本地 | `server/app/embedding/bge_m3.py` | sentence-transformers / FlagEmbedding 双 backend，懒加载 |
| OpenAI 兼容远端 | `server/app/embedding/openai_compat.py` | httpx 调 `/embeddings` |
| Hash Mock（测试） | `server/app/embedding/mock_embedder.py` | 确定性、归一化的伪向量 |
| 工厂 | `server/app/embedding/factory.py` | `EmbedderConfig → Embedder` |
| 索引流水线 | `server/app/pipeline/indexing.py` | chunk → embed → 写入 datasource |
| 检索流水线 | `server/app/pipeline/retrieval.py` | embed(query) → datasource.search |
| Search API | `server/app/api/search.py` | `POST /v1/search` |
| 评测 fixture | `server/eval/fixtures/cases.json` + `corpus/snippets.md` | 10 条检索 + 10 篇底料 |
| 评测 harness | `server/eval/run_eval.py` | 端到端跑流水线 + 命中率 |
| Files API 集成 | `server/app/api/files.py` | `POST /v1/files/import` 现在走完整流水线 |

## 端到端流水线

```
file → parse(Document) → chunker.split(Chunk[]) → embedder.embed → datasource.add
query → embedder.embed([query]) → datasource.search(vector, top_k) → Hit[]
```

进度上报：`pipeline.on_progress(p)` 由 files API 接到 `task_store.update(progress=...)`。

## 评测结果

```bash
$ PYTHONPATH=. python3 eval/run_eval.py
{"passed": 9, "total": 10, "rate": 0.9, "threshold": 0.6, ...}
```

9/10 通过，命中率 90% ≥ 60% 门禁。失败案例是 `kb-03 (embedding model name)`，原因是 mock embedder 把 "BAAI/bge-m3" 与 "bge-m3" 散列到接近的桶但 top-3 内未命中；真实 BGE-M3 模型会显著提升。

## 验证证据

```bash
$ pytest
73 passed in 0.69s
```

| 测试文件 | 用例数 | 验证内容 |
|---|---|---|
| `tests/embedding/test_embedders.py` | 8 | 注册表、mock 归一化、确定性、cosine、openai-compat HTTP、bge-m3 懒加载失败语义 |
| `tests/pipeline/test_pipelines.py` | 5 | 索引端到端、空 doc 跳过、检索 top-k、batch 进度 |
| `tests/api/test_search_api.py` | 3 | 文件导入后检索、empty query、pipeline 未配置 503 |

## 不在范围内（按协议 C3）

- 多模态 embedding。
- 桌面端集成。
- Milvus 真实联通（依赖外部服务）。

## 已知缺口

- mock embedder 评测 90%；真实 BGE-M3 模型下载 + 加载约 2.4 GB，本环境未安装 sentence-transformers，迁移到 transition 阶段用 docker 验证。
- OpenAI 兼容远端未做指数退避重试；429 时直接 500。后续可加。