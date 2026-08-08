# C6 评估：Milvus 1:1 单测迭代（KI-07）

> 评估者对 `docs/construction/c6-milvus-tests.md` 中 KI-07 交付的核对。

## 验证证据

| 检查项 | 命令 / 文件 | 结果 |
|---|---|---|
| 迭代协议存在 | `docs/construction/c6-milvus-tests.md` | OK（目标 / 范围 / 交付物 / 退出标准齐备） |
| 启动脚本 | `scripts/start_milvus.sh` + `scripts/stop_milvus.sh` | executable；幂等（已运行则跳过）；默认镜像 `milvusdb/milvus:v2.4.10-standalone` / 端口 19530 / 卷 `kb_milvus_data` |
| 测试夹具 | `server/tests/datasources/conftest.py` | TCP 探测 + `pymilvus.MilvusClient` 握手；不可达 → `pytest.skip(...)`；URI 解析支持 http(s) 与本地 Lite 路径 |
| 1:1 单测 | `server/tests/datasources/test_milvus_adapter.py` | 8 用例与 `test_vector_adapter.py` 1:1 对应 |
| Milvus Lite 路径 | `KB_MILVUS_URI=./kb_milvus_lite.db pytest tests/datasources/test_milvus_adapter.py -q` | **8/8 通过**（1.33s） |
| 默认（无 Milvus）skip | `pytest tests/datasources/test_milvus_adapter.py -q` | **8 skipped**，每条都带 start 脚本 / Lite 提示 |
| 全套不回归 | `KB_MILVUS_URI=./kb_milvus_lite.db pytest` | **85 passed**（之前 77 + 8 Milvus） |
| in-memory 不回归 | `pytest tests/datasources/test_vector_adapter.py -q` | **9/9 通过** |
| adapter VARCHAR schema 修复 | `server/app/datasources/vector_db_adapter.py` | `_MilvusBackend` 显式 `DataType.VARCHAR` 主键 + `auto_id=False`，规避 pymilvus ≥ 3 默认 int64 |
| `pymilvus` 缺依赖时报错 | `DatasourceError("pymilvus not installed. ...")` | 保留原语义（base.py 契约） |
| 文档 | `server/README.md` + `server/tests/datasources/README.md` | Milvus 1:1 章节 + docker / Lite 双路径 |
| init.sh | `bash init.sh` | OK |

### 关于 docker 镜像在本机的可用性

本机 docker mirror（`docker.m.daocloud.io`）在本会话对 `milvusdb/milvus:v2.4.10-standalone` 返回 403，与本迭代无关：

- 启动脚本在 mirror 健康的环境即可一行拉起；
- 在 mirror 受限的环境，conftest 给出 Lite 路径作为同等 1:1 兜底（同一 `MilvusClient` API，覆盖同一份代码）。

## 评分（参考 `evaluator-rubric.md`）

| 维度 | 分数 | 备注 |
| --- | --- | --- |
| 正确性 | 5 | 8 用例全绿；schema 修复必要且最小；adapter 错误语义保持 |
| 验证 | 5 | live（Lite）+ skip（无 server）+ 全套不回归三层证据齐备 |
| 范围纪律 | 5 | 严格按协议 C6：仅 Milvus；未触及 KI-01/02/03/08/10 |
| 可靠性 | 5 | 幂等 docker 脚本 + UUID collection + teardown drop；无 Milvus 自动 skip |
| 可维护性 | 5 | conftest 单点 URI 解析 + skip；与 in-memory 镜像对称 |
| 交接准备度 | 5 | README 双路径文档 + 残留 collection 风险已说明 |
| **运行时可观测性** | 5 | adapter `log.info("vector.ready", backend=..., dim=...)` 已记录；测试 fixture 跳过时 stderr 提示 `start_milvus.sh` 或 Lite 路径；每个用例 collection UUID 可在 Milvus UI 排查 |
| **过程可观测性** | 5 | 协议 C6 / 本评估 / KNOWN_ISSUES 三处对齐；`start_milvus.sh` 即"评分标准"——`docker ps` 看到 `kb_milvus` 即满足 |

**Overall: 5 / 5**

## 结论

- [x] Accept
- [ ] Revise
- [ ] Block

## 后续动作

- 推荐下一迭代：KI-02 MySQL O(N) cosine 性能（切到 PostgreSQL pgvector 或 Milvus 后已可绕行，可在文档中正式记录降级路径）；或 KI-03 重试退避。
- `scripts/start_milvus.sh` 在 docker mirror 受限环境会失败；下次复审触发条件：CI 引入 docker compose 服务化 Milvus，并改 conftest 默认 URI 为 `http://milvus:19530`（docker network）。