# MySQL O(N) 性能收敛迭代协议（C8）

> 第二个 RUP 周期的第八个迭代：收敛 `docs/KNOWN_ISSUES.md` 中的 KI-02（MySQL 适配器 O(N) cosine，>100k 不可用），让用户在超规模时能看见明确警告与降级路径。

## 目标

收敛 KI-02：MySQL 适配器内置"接近安全扫描上限 / 命中上限"两类结构化日志；能力声明补充 `scan_limit_risk`；RUNBOOK / API.md / server/README 三处文档给出 PostgreSQL pgvector / Milvus 的降级迁移步骤。**不**做自动迁移脚本（迁移涉及数据搬运，超出本迭代范围）。

## 范围

### 1. 运行时警告

`server/app/datasources/mysql_adapter.py`：

- **构造期**：`__init__` 末尾打一条 `mysql.adapter.initialized` info 日志，附 `max_scan_rows` / `dim` / `host` / `table`；新增 `mysql.adapter.small_dataset_only` warning 日志，内容明确"O(N) Python cosine，仅适合 ≤100k 行；>100k 请切 PostgreSQL pgvector 或 Milvus"。
- **检索期**：`search()` 内执行 SQL 后，若返回行数 ≥ `max_scan_rows`，打 `mysql.adapter.scan_limit_hit` warning，附 `scanned_rows` 与 `max_scan_rows`；返回结果仍按 top_k 截断。
- 三个日志事件均为结构化字段（`event` / `level` / 上下文键），方便后续接 metrics。

### 2. 能力声明

- `capabilities()` 在原 `{"metadata_filter", "small_dataset_only"}` 基础上补充 `scan_limit_risk`，告知调用方存在截断风险。
- 新增一条 docstring 注释：MySQL 适配器**不**提供 ANN 索引，**不**承诺完整结果集。

### 3. 文档

| 文档 | 改动 |
|---|---|
| `docs/RUNBOOK.md` §3 "MySQL 适配器查询慢" | 重写为"如何判断 + 何时切 + 切到哪"三段；给出 pgvector 与 Milvus 各一段简短迁移示例（dump → 新实例 → 重新 add） |
| `docs/API.md` 数据源章节 | 在 `GET /v1/datasources` 响应旁加一行注释：`mysql` 的 `capabilities` 含 `scan_limit_risk`，调用方应监控此字段 |
| `server/README.md` | MySQL 行补一句警告 + 链回 RUNBOOK §3 |

### 4. 测试

`server/tests/datasources/test_mysql_adapter.py` 新增：

- `test_mysql_capabilities_include_scan_limit_risk`：验证 `capabilities()` 含 `scan_limit_risk` 与 `small_dataset_only`。
- `test_mysql_search_warns_when_scan_limit_hit`：用 `_FakeCursor._rows` 注入 ≥ `max_scan_rows` 行；用 `caplog.at_level("WARNING")` 断言出现 `mysql.adapter.scan_limit_hit` 事件 + `scanned_rows` 字段；返回结果仍是 top_k。
- `test_mysql_search_no_warn_below_limit`：行数 < `max_scan_rows` 时**不**出现 `scan_limit_hit` 日志。
- `test_mysql_init_warns_small_dataset_only`：用 `caplog` 断言初始化阶段出现 `mysql.adapter.small_dataset_only` warning。

### 5. 状态收尾

| 文件 | 改动 |
|---|---|
| `feature_list.json` | 新增 `feat-ki02-mysql-perf` 条目 `status=pass` |
| `docs/KNOWN_ISSUES.md` | KI-02 行从"已识别但未解决"移入"C8 收敛表" |
| `progress.md` / `session-handoff.md` | C8 收尾段；当前迭代清空 |
| `evaluator-rubric.md`（如适用） | 不变；评估者按本协议出 `c7-evaluation.md` |

## 不在范围

- **自动数据迁移工具**：dump → load 跨库搬运，超出本迭代；后续可单独开迭代。
- **MySQL 性能真实 benchmark**：`scripts/bench.sh` 留待 transition 阶段（见 RUNBOOK §性能基准）。
- **替代 JSON 列的真向量索引**：HeatWave / Vespa 等外部方案不在本迭代评估。
- **其余 KI（KI-01 / KI-03 / KI-08 / KI-10）**：保持已知问题，下一迭代再处理。
- **`max_scan_rows` 行为变更**：仍按"超限即截断 + warning"语义，不引入异常。

## 交付物

| 交付 | 路径 |
|---|---|
| 适配器改动 | `server/app/datasources/mysql_adapter.py` |
| 测试 | `server/tests/datasources/test_mysql_adapter.py` |
| RUNBOOK | `docs/RUNBOOK.md` |
| API 文档 | `docs/API.md` |
| 服务端 README | `server/README.md` |
| 评估 | `docs/construction/c7-evaluation.md`（评估者产出） |
| 状态 | `feature_list.json`、`docs/KNOWN_ISSUES.md`、`progress.md`、`session-handoff.md` |

## 退出标准

- `pytest tests/datasources/test_mysql_adapter.py -v` 全绿，含 4 项新增用例；其他用例不回归。
- `pytest` 全套仍 85+4=89 passed（增量来自 4 项新增）。
- `grep -nE "scan_limit_hit|small_dataset_only|scan_limit_risk" server/app/datasources/mysql_adapter.py` 三个事件名都在。
- `bash init.sh` 通过。
- `docs/RUNBOOK.md` §3、 `docs/API.md`、`server/README.md` 都含 pgvector / Milvus 降级说明。
- `feature_list.json` 新增 `feat-ki02-mysql-perf` 条目 `pass`。
- 评估者按本协议出 `c7-evaluation.md` ≥ 4.5/5。

## 风险

- **R-C8-1**：warning 日志可能污染现有 `_FakeCursor` 测试输出。用 `caplog.at_level` 限定捕获范围，不修改其他测试断言。
- **R-C8-2**：截断语义变更（之前静默截断，现在显式 warning）属于可观测性增强，**不**改变返回结果；不引入 breaking change。
- **R-C8-3**：迁移文档若不写明"导出数据 + 重新 add"两步，可能误导用户以为单条 SQL 就能切库。RUNBOOK 必须给完整两步，并明示无现成 dump 工具。
- **R-C8-4**：MySQL 行数统计使用 `len(rows)`，本身仍是 O(N)；warning 只是"已经慢了"的信号，不是加速手段；docstring 必须讲清。

## 决策

- **warning 而非 exception**：`max_scan_rows` 触发时**不**抛错，与现有行为一致；只多一条结构化 warning，便于告警系统接入。
- **能力字段 `scan_limit_risk`**：与现有 `metadata_filter` / `small_dataset_only` 同形；调用方可按 `capabilities` 决定是否在 UI 高亮"建议切库"。
- **不引入迁移 CLI**：数据搬运超出本迭代；RUNBOOK 给出 SQL 思路 + 链回 `/v1/datasources/test` 预验证。
- **日志事件命名**：`mysql.adapter.<event>` 前缀与 `mysql.schema.ready` 已有日志对齐。

## 实施顺序

1. **数据与报表开发者**先改 `mysql_adapter.py`（warning + capabilities），写 4 项新单测 → `pytest` 全绿。
2. 改 `docs/RUNBOOK.md` / `docs/API.md` / `server/README.md`，交叉引用保持一致。
3. **评估者**按退出标准逐项核对 → 出 `c7-evaluation.md`。
4. **规划者**收尾：更新 `feature_list.json` / `progress.md` / `session-handoff.md` / `docs/KNOWN_ISSUES.md`。