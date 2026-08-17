# C17 数据源迁移 dump/load 评估

## 结论

Accept。

## 评分

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | 5 | memory dump → JSONL → load（重新 embedding）后新库可搜索；ES `dump_all` 返回全量文本不截断；无 capability 源拒绝。 |
| 验证 | 5 | `test_migrate.py` 2/2、ES adapter +1；全量 191 passed；`ruff` 0 errors；desktop check/lint 0 errors；Vite 165.98 kB（纯后端）。 |
| 范围纪律 | 5 | 只做迁移能力与 CLI；未改既有 HTTP/IPC 契约，`dump_all` 为新增可选能力。 |
| 可靠性 | 5 | dump 分页避免内存爆炸；load 分批 embedding；迁移不依赖目标库原向量，模型/维度变化安全。 |
| 可维护性 | 5 | `dump_all` 与 browse `list_chunks` 分离；migrate 模块集中编排；CLI 可直接被 cron/脚本调用。 |
| 可观测性 | 5 | CLI 输出 dumped/loaded 数量；JSONL 可人工检查；能力声明可经 `/v1/datasources` 查看。 |

## 证据

- `server/app/datasources/base.py`：`dump_all` 默认 + `dump` capability 约定。
- `server/app/datasources/vector_db_adapter.py`：memory `dump_all`。
- `server/app/datasources/elasticsearch_adapter.py`：`dump_all`（match_all + 全量 text）。
- `server/app/observability/migrate.py`：dump/load CLI。
- 实测：191 tests collected / 191 passed；Vite 165.98 kB JS / 39 modules；`feature_list.json` 30/30 pass。

## 遗留风险

- Milvus backend 尚未实现 `dump_all`；迁移 Milvus 需先切到 memory/ES 或后续补实现。
- dump 不包含向量，load 会重新 embedding；若 embedder 临时不可用，迁移会失败。
- CLI 需要手动执行，未接入桌面端 UI。
