# C7 评估：MySQL O(N) 性能收敛迭代（KI-02）

> 评估者对 `docs/construction/c7-mysql-perf.md` 中 KI-02 交付的核对。

## 验证证据

| 检查项 | 命令 / 文件 | 结果 |
|---|---|---|
| 迭代协议存在 | `docs/construction/c7-mysql-perf.md` | OK（目标 / 范围 / 交付物 / 退出标准齐备） |
| adapter docstring 更新 | `server/app/datasources/mysql_adapter.py` | OK——明示 KI-02 mitigation 与"无 ANN / 无完整结果集"承诺 |
| `mysql.adapter.initialized` info 日志 | 同上 | OK——构造末尾，附 `table` / `dim` / `max_scan_rows` / `host` |
| `mysql.adapter.small_dataset_only` warning | 同上 | OK——构造末尾，附 `hint` 指向 pgvector / Milvus |
| `mysql.adapter.scan_limit_hit` warning | 同上 | OK——`search()` 返回行数 ≥ `max_scan_rows` 时触发，附 `scanned_rows` / `max_scan_rows` / `hint` |
| `scan_limit_risk` 能力字段 | 同上 `capabilities()` | OK——`{"metadata_filter", "small_dataset_only", "scan_limit_risk"}` |
| 新增 4 项单测 | `server/tests/datasources/test_mysql_adapter.py` | OK——`capabilities_include_scan_limit_risk` / `init_warns_small_dataset_only` / `search_warns_when_scan_limit_hit` / `search_no_warn_below_limit` |
| 单测全绿 | `pytest tests/datasources/test_mysql_adapter.py -v` | **11/11 通过**（原 7 + 新增 4；1.23s） |
| 全套不回归 | `KB_MILVUS_URI=./kb_milvus_lite.db pytest` | **89 passed**（原 85 + KI-02 新增 4；2.67s） |
| 三事件 grep | `grep -nE "scan_limit_hit\|small_dataset_only\|scan_limit_risk" server/app/datasources/mysql_adapter.py` | OK——9 处命中 |
| RUNBOOK §3 重写 | `docs/RUNBOOK.md` | OK——"如何判断 + 何时切 + 切到哪"三段；pgvector / Milvus 各一段迁移示例；明确"无 dump CLI" |
| API.md 数据源说明 | `docs/API.md` | OK——`capabilities` 字段含义展开，含 `scan_limit_risk` 注释与 RUNBOOK §3 反链 |
| server/README MySQL 行警告 | `server/README.md` | OK——"**仅适合 ≤100k 行**；超规模请切 PostgreSQL pgvector 或 Milvus"，反链 RUNBOOK §3 |
| init.sh | `bash init.sh` | OK |

## 评分（参考 `evaluator-rubric.md`）

| 维度 | 分数 | 备注 |
| --- | --- | --- |
| 正确性 | 5 | 三个结构化日志事件名、字段、触发条件与协议一致；`capabilities` 增量最小；`search()` 返回行数被 `len(rows)` 准确记录 |
| 验证 | 5 | 4 项新增单测覆盖：capabilities、init warning、scan_limit_hit 触发、scan_limit_hit 不触发；其他 7 项原单测零回归 |
| 范围纪律 | 5 | 严格按协议 C7：仅 MySQL adapter + 三处文档；未触及 KI-01/03/08/10；未引入 dump CLI |
| 可靠性 | 5 | warning 而非 exception，与现有 `max_scan_rows` 语义一致；截断风险显式声明不破坏既有调用方 |
| 可维护性 | 5 | 日志事件名沿用 `mysql.adapter.<event>` 前缀；docstring 顶部明确 KI-02 上下文；能力字段同形 |
| 交接准备度 | 5 | RUNBOOK §3 给出 pgvector / Milvus 完整两步迁移说明；明确"无 dump CLI"边界；API/README 反链 RUNBOOK |
| **运行时可观测性** | 5 | 三条结构化日志：构造期 info+warning 一次性告知，检索期按命中阈值实时告警；`capabilities` 新字段供 UI/调用方识别 |
| **过程可观测性** | 5 | 协议 C7 / 本评估 / KNOWN_ISSUES 三处对齐；grep 三个事件名即可证明实施落地；新增 4 项单测即可证明行为正确 |

**Overall: 5 / 5**

## 结论

- [x] Accept
- [ ] Revise
- [ ] Block

## 后续动作

- 推荐下一迭代：**KI-03** OpenAI 兼容远端重试退避（severity 低，纯代码改动；与本迭代互补，覆盖另一条远端依赖风险）。或 KI-01 / KI-08 / KI-10 之一。
- C7 收敛边界已声明"不内置 dump CLI"；如数据增长真触发 `scan_limit_hit` 高频告警，下一迭代可单独开 C9 做数据迁移工具。