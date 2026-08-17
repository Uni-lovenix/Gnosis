# C17 数据源迁移 dump/load（迭代协议）

> 类别：C（构建迭代）。本迭代新增 DataSource 抽象能力 `dump_all` 与迁移 CLI，属于新增责任区块，需独立评估报告。

## 迭代目标

让数据能在数据源之间复制：从旧数据源 dump 全量文本/metadata，load 到新数据源时重新 embedding 后写入。这样：

- 切换/迁移到 ES、pgvector、Milvus 等新后端时有真实数据复制路径；
- failover 备用数据源可以先灌入数据，而不是空库；
- 突破 C8 “无 dump / load CLI” 的边界。

## 迭代范围

### 1. DataSource 抽象

- 新增可选 `dump_all(offset=0, limit=100)` → `(list[Chunk], total)`，默认抛 `NotSupportedError`。
- 新增 capability `"dump"`。
- `ElasticsearchAdapter`：实现 dump_all（搜索全量文本 + metadata，不分页截断）。
- `VectorDBAdapter`（memory backend）：实现 dump_all；Milvus 暂不实现。

### 2. 迁移模块

`server/app/observability/migrate.py`：

- `dump_chunks(ds, output_path, page_size=100)`：要求 `dump` capability，分页写 JSONL（`document_id / text / metadata`）。
- `load_chunks(ds, embedder, input_path, batch_size=16)`：按批 embedding，构造 `Chunk` 写入目标数据源。
- CLI：
  - `python3 -m app.observability.migrate dump --type vector --options '{"backend":"memory","dim":32}' --output dump.jsonl`
  - `python3 -m app.observability.migrate load --type vector --options '...' --embed mock-hash --input dump.jsonl`

### 3. 测试

- memory `dump_all` 返回全量数据；
- dump → load roundtrip 后新数据源可搜索到原 chunk；
- 无 `dump` capability 的源拒绝 dump。

## 实施计划

1. 先落盘本协议。
2. base + memory + ES 实现 `dump_all`。
3. 实现 migrate CLI。
4. 补测试，跑全量验证。
5. 更新文档与 harness + C17 评估。

## 交付物

- `server/app/datasources/base.py`、`vector_db_adapter.py`、`elasticsearch_adapter.py`。
- `server/app/observability/migrate.py`。
- 测试：`server/tests/test_migrate.py`、`server/tests/datasources/test_vector_adapter.py`、`server/tests/datasources/test_elasticsearch_adapter.py`。
- 文档：`docs/RUNBOOK.md`、`docs/elaboration/01-architecture-baseline.md`、`docs/KNOWN_ISSUES.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c17-data-migration.md` + `c17-data-migration-evaluation.md`。

## 退出标准

- [x] memory / ES 声明 `dump` capability 且 `dump_all` 返回全量文本。
- [x] dump → load roundtrip 后新数据源可搜索。
- [x] 无 capability 的源给出清晰错误。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C17 评估报告由评估者角色出具。

## 决策记录

- **dump 只保留 text/metadata，不保留向量**：load 时用当前 embedder 重新向量化，避免模型升级/维度变化后旧向量失效。
- **dump_all 与 list_chunks 分离**：browse 需要截断预览，迁移需要全量文本；两者语义不同，不混用。
- **CLI 而非 HTTP**：迁移可能很大且耗时长，不适合阻塞 API 请求；用户可在停服/低峰期执行。
