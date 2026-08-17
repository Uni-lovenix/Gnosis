# 已知问题与绕行方案

## 已识别但未解决

| 编号 | 描述 | 严重度 | 绕行 |
|---|---|---|---|
| KI-01 | PDF 扫描件无 OCR | 中 | 桌面端用外部 OCR 工具预处理；或后续接 OCR 适配器 |
| KI-08 | Word 解析不支持嵌入式图片与批注 | 低 | 用 mammoth 替代可补 |
| KI-10 | better-sqlite3 在某些 arm64 Linux 镜像上需手动编译 | 低 | 文档化 platform note |

## C5 / C6 / C7 / G5 已收敛

| 编号 | 描述 | 收敛方式 |
|---|---|---|
| KI-04 | desktop DocumentsPage 仅占位 | `MetaDB` 暴露 `listDocuments / getDocument / deleteDocument`，renderer 拉真实目录 + 删除按钮；类型同步 `KBAPI`。见 `docs/construction/c5-known-issues.md` |
| KI-05 | electron-builder 打包脚本未提供 | `desktop/electron-builder.yml` + `pack / dist / dist:{mac,win,linux}` 脚本；README 新增打包章节。 |
| KI-06 | 真实 BGE-M3 模型权重未在 CI 验证 | **G3 已完成**：本地 Ollama + bge-m3 通过 OpenAI 兼容接口跑通；`scripts/start_server_ollama.sh` 一键起服务，`eval/run_eval.py --embedder openai-compat` 评测 10/10 = 100%。`scripts/download_bge_m3.sh` + `bge-m3` local snapshot 路径仍保留作为备用。详见 `docs/goal/01-mapping.md` G3 段。 |
| KI-07 | Milvus 适配器仅 import smoke，无 1:1 单测 | `tests/datasources/test_milvus_adapter.py` 8 用例与 in-memory 1:1 对应；`conftest.py` 在 19530 不可达时 skip；`scripts/start_milvus.sh` 幂等拉起 `milvusdb/milvus:v2.4.10-standalone`；Lite（`KB_MILVUS_URI=./kb_milvus_lite.db`）作为同等 1:1 兜底。`_MilvusBackend` 显式 VARCHAR 主键 schema 规避 pymilvus ≥ 3 默认 int64。 |
| KI-09 | 任务表无过期清理 | `TaskStore.purge_stale(ttl_days=30)` 仅清理超过 TTL 的 `done`/`failed` 任务；`queued`/`running` 不受影响。调用方按需显式触发。 |
| KI-02 | MySQL 适配器 O(N) cosine，>100k 不可用 | `MysqlAdapter.__init__` 打 `mysql.adapter.small_dataset_only` warning；`search()` 命中 `max_scan_rows` 时打 `mysql.adapter.scan_limit_hit` warning（附 `scanned_rows` / `max_scan_rows` / `hint`），截断语义不变；`capabilities()` 新增 `scan_limit_risk`。`docs/RUNBOOK.md` §3 给出 pgvector / Milvus 两段迁移示例（明示无 dump CLI 边界）；`docs/API.md` 与 `server/README.md` 反链 RUNBOOK。详见 `docs/construction/c7-mysql-perf.md`。 |
| KI-03 | OpenAI 兼容远端无指数退避（瞬时错误裸抛） | `OpenAICompatEmbedder` 新增指数退避：只对 `httpx.TransportError` / 5xx / 429 重试；4xx 立即抛；阶梯 `initial_backoff=0.5s` × 2^n，封顶 `max_backoff=8s`，±10% jitter。每次重试打 `embedder.retry` 结构化日志（`attempt` / `max_attempts` / `status_code` / `sleep_seconds`）。可配选项：`max_retries` / `initial_backoff` / `max_backoff` / `backoff_jitter`。`tests/embedding/test_embedders.py` 新增 7 项单测覆盖：瞬时错误重试至成功、耗尽抛错、4xx 不重试、429 重试、5xx 重试、退避数学、retry 日志。`docs/RUNBOOK.md` §2a 给完整调参示例与不重试矩阵。`npm run test:unit` 113 → **120 passed**。 |

## 已缓解

| 编号 | 描述 | 缓解 |
|---|---|---|
| MI-01 | sentence-transformers 未安装 | `main.py` 检测到 ImportError 时自动 fallback 到 `mock-hash`，写日志 `embedder.fallback_to_mock` |
| MI-02 | Python 服务崩溃 | desktop `server-manager.ts` 5s 心跳 + 3 次失败自动重启 |
| MI-03 | 桌面端 IPC 类型漂移 | `src/shared/types.ts` 单一源，main/preload/renderer 共用 |
| MI-04 | 配置文件缺字段 | 所有 `*Config` 都对缺省字段有 `.get(key, default)` 兜底 |
| MI-05 | 评测随机性 | mock embedder 确定性；切换真实 BGE-M3 时固定 `random_state` |
| MI-06 | 运行时无请求关联追踪 | `server/app/api/middleware.py` 生成/透传 `X-Request-Id`，structlog contextvars 绑定，`http.request` 日志携带同一 id |
| MI-07 | 数据目录无一致性备份 | `python3 -m app.observability.backup`（SQLite 官方 backup API + JSON 复制 + 保留策略），默认 `~/.kb-server/backups` 保留 7 份 |
| MI-08 | 启动降级静默（embedder fallback / active 数据源失败） | `/v1/health` 暴露 `degraded / embedder_fallback / active_datasource`，桌面端显示降级横幅 |
| MI-09 | 备份只有 CLI，无恢复入口 | C11：`restore` / `list` CLI + `/v1/backups` + Settings Backup & Restore（停服 → 恢复 → 重启），恢复前自动留 `.pre-restore` |
| MI-10 | active 切换需重启服务 | C12：`POST /v1/datasources/active/{name}/switch` + Settings “Switch now”，黑板锁等待在飞写入/检索后热切换 |
| MI-11 | 备份依赖手动执行 | C13：服务启动即检查 + 每小时 `backup_if_due` 自动快照（默认开启，`KB_BACKUP_AUTO=false` 可关） |
| MI-12 | 运行期降级不反映到 /v1/health | C14：后台每 30s 探活 datasource + embedder 写入健康快照；桌面 15s 轮询自动更新降级横幅 |
| MI-13 | 数据源故障只能手动切换 | C15：failover 顺序配置 + 连续失败自动热切换；`datasource.failover` / `failover_exhausted` 日志 |
| MI-14 | failover 后不会自动切回主数据源 | C16：主库恢复后连续健康达到阈值自动回切；`datasource.failover_recovered` 日志，`KB_FAILOVER_AUTO_RECOVER=false` 可关 |
| MI-15 | 数据无法跨数据源复制 | C17：`dump_all` capability + `python3 -m app.observability.migrate dump/load`（memory / ES 支持，load 重新 embedding） |

## 报告新问题

请在 `docs/KNOWN_ISSUES.md` 追加一行；带 "编号 / 描述 / 严重度 / 绕行" 四列，便于交接会话快速定位。
