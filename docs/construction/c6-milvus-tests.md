# Milvus 1:1 单测迭代协议（C6）

> 第二个 RUP 周期的第二个迭代：收敛 `docs/KNOWN_ISSUES.md` 中的 KI-07（Milvus 适配器仅 import smoke，无 1:1 单测）。

## 目标

让 Milvus 适配器具备与 `_MemoryBackend` 等价的 1:1 单测覆盖，CI / 本地任一环境都能无副作用地跑：

1. **启动脚本** —— `scripts/start_milvus.sh` 一键拉起 standalone 容器；幂等，已运行则跳过；端口与默认 `uri` 对齐。
2. **测试集** —— `server/tests/datasources/test_milvus_adapter.py` 覆盖 add / search / delete / filter / idempotent / health / dim mismatch / chunk-without-vector；用 `tests/datasources/conftest.py` 的 `milvus_client` fixture 在 19530 端口不可达时自动 skip，避免 CI 噪音。
3. **文档** —— `server/README.md` 补充 Milvus 1:1 单测章节（启动 / 跑测 / 关闭）；`server/tests/datasources/README.md`（新增）写清 pytest 选择器与 skip 语义。

## 范围

### 启动脚本

- `scripts/start_milvus.sh`：
  - 默认镜像 `milvusdb/milvus:v2.4.10-standalone`（与 `pyproject.toml` 的 `pymilvus>=2.4` 对齐）。
  - 默认端口 `19530`；容器名 `kb_milvus`；数据卷 `kb_milvus_data`。
  - `docker start kb_milvus` 在已停止时恢复；`docker run` 在缺失时创建。
  - `scripts/stop_milvus.sh`（可选）保留做关闭用。
  - `set -euo pipefail`；写日志到 stderr。

### 测试夹具

- `server/tests/datasources/conftest.py`：
  - `milvus_uri` fixture 默认 `http://127.0.0.1:19530`，可用 `KB_MILVUS_URI` 覆盖。
  - `require_milvus(uri)` 助手：TCP 连接握手 + `pymilvus.MilvusClient` 实例化；失败时 `pytest.skip("milvus not available at <uri>: ...")`。
  - `milvus_collection` fixture：每个用例一个唯一 collection（UUID 16-hex），teardown 时 `drop_collection` + `close()`，保证无副作用。

### 1:1 单测

- `server/tests/datasources/test_milvus_adapter.py`，与 `test_vector_adapter.py` 一一对应：
  - `test_add_search_delete`：3 个向量，top_k=2，验排序；delete 一条后再搜，验消失。
  - `test_add_is_idempotent`：同 id 二次 add，长度不变，hits 唯一。
  - `test_search_with_filter`：metadata 过滤按 `document_id` 命中子集。
  - `test_search_empty_store_returns_empty`：空 collection 返回 `[]`。
  - `test_health_ok`：`health()` 返回 `ok=True`。
  - `test_chunk_without_vector_rejected`：缺 vector 的 chunk 抛 `DatasourceError`。
  - `test_dimension_mismatch_rejected`：构造时 `dim=4` 但送入长度 2 的向量，add 阶段报错。
  - `test_capabilities_declared`：`metadata_filter` 在 `capabilities()`。

### 文档

- `server/README.md`：新增「Milvus 1:1 单测」章节 —— docker 启动脚本、pytest 选择器、关闭、CI skip 说明。
- `server/tests/datasources/README.md`（新增）：列 5 个 adapter 测试入口、Milvus skip 语义、conftest 用法。

## 不在范围

- KI-01（OCR）、KI-02（MySQL 性能）、KI-03（重试退避）、KI-08（Word 图片）、KI-10（arm64 编译）：保持已知问题，下一迭代再处理。
- Milvus Lite（嵌入式 SQLite 模式）：本轮只验证 standalone；Lite 留作可选优化（未来）。
- 真实 Qdrant 适配器：项目已用 qdrant 容器做 E2E，但 adapter 只暴露 Milvus + 内存。
- CI 改造：默认仍 skip Milvus（容器未在 CI 跑）；本机脚本可重现。

## 交付物

| 交付 | 路径 |
|---|---|
| 启动脚本 | `scripts/start_milvus.sh` |
| 关闭脚本（可选） | `scripts/stop_milvus.sh` |
| 测试夹具 | `server/tests/datasources/conftest.py` |
| 1:1 单测 | `server/tests/datasources/test_milvus_adapter.py` |
| 文档 | `server/README.md` + `server/tests/datasources/README.md` |
| 验证证据 | `docs/construction/c6-evaluation.md`（评估者产出） |
| 状态更新 | `feature_list.json`、`progress.md`、`session-handoff.md`、`docs/KNOWN_ISSUES.md` |

## 退出标准

- `bash scripts/start_milvus.sh` 幂等拉起 Milvus，`docker ps` 看到 `kb_milvus` 健康。
- `cd server && pytest tests/datasources/test_milvus_adapter.py -v` 全绿；`test_vector_adapter.py` 不回归。
- `cd server && pytest` 旧测试集通过（不回归 in-memory + 其余 4 类 adapter）。
- 无 Milvus 时（如卸载 docker）：同命令输出 `X skipped` 且非零失败。
- `bash init.sh` 通过。
- `feature_list.json` 中新增 `feat-ki07-milvus-tests` 条目 `pass`。

## 风险

- **R-C6-1**：本机未启动 Milvus 时，整套 `pytest` 会增加 skip 输出但 0 失败。CI 默认 skip 即可。
- **R-C6-2**：Milvus standalone 镜像 ~1GB；首次 `docker run` 拉镜像耗时；脚本不强制 healthcheck 超时（用户按需观察日志）。
- **R-C6-3**：collection 命名随机化避免脏数据；但若脚本异常退出，残留 collection 需用户手动清理；teardown 加 `try/except` 兜底。
- **R-C6-4**：`pymilvus` 未安装时 `_MilvusBackend.__init__` 会抛 `DatasourceError`；fixture 阶段提前检测，避免用例内崩溃。

## 决策

- 镜像版本 `milvusdb/milvus:v2.4.10-standalone`：与 `pyproject.toml` 中 `pymilvus>=2.4` 对齐；避免 latest 漂移。
- 端口 `19530`：与适配器默认 `VectorDBConfig.options["uri"]` 一致。
- 用例 collection 用 `kb_test_<uuid8>`：人类可读前缀 + 随机后缀，便于排查残留。
- CI 行为：默认 skip（容器未跑）；本机 `bash scripts/start_milvus.sh && pytest` 即可全绿。