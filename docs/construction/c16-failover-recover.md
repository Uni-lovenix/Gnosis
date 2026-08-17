# C16 failover 恢复回切（迭代协议）

> 类别：C（构建迭代）。本迭代新增自动回切行为（后台健康监控会主动替换运行态数据源），需独立评估报告。

## 迭代目标

让 failover 形成完整生命周期：**主库故障 → 自动切备用 → 主库恢复 → 自动切回**。

1. 新增 `recover_primary()`：failover 顺序的第一项视为主数据源；当 active 不是主数据源且主数据源探活健康时，自动热切换回主数据源。
2. 健康监控在备用数据源连续 `KB_FAILOVER_RECOVER_CONSECUTIVE_CHECKS`（默认 3）次健康后触发回切，避免抖动。
3. 回切同样更新 active 指针、chunks/health 快照，并打 `datasource.failover_recovered` 日志。

## 迭代范围

### 1. datasources API

`recover_primary()`：

- failover 顺序为空、active 已是主数据源、无控制器 → 返回 `None`。
- 主数据源 build + health 探活失败 → 返回 `None`，不切换。
- 成功 → `replace_datasource` + `store.activate` + 更新 chunks/health + 日志。

### 2. 健康监控

`main._health_monitor_loop`：

- 新增连续健康计数；
- `KB_FAILOVER_AUTO_RECOVER`（默认 true）+ `KB_FAILOVER_RECOVER_CONSECUTIVE_CHECKS`（默认 3）；
- 达到阈值时调用 `recover_primary()`，调用后重置计数。

### 3. 测试隔离

`server/tests/conftest.py` 固定 `KB_FAILOVER_AUTO_RECOVER=false`。

## 实施计划

1. 先落盘本协议。
2. settings 增加回切参数。
3. datasources API 增加 `recover_primary`。
4. 健康监控接入回切。
5. 补测试，跑全量验证。
6. 更新文档与 harness + C16 评估。

## 交付物

- `server/app/api/datasources.py`：`recover_primary`。
- `server/app/config/settings.py`：`failover_auto_recover` / `failover_recover_consecutive_checks`。
- `server/app/main.py`：健康监控回切逻辑。
- `server/tests/conftest.py` + `server/tests/test_datasource_configs_api.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/elaboration/01-architecture-baseline.md`、`docs/KNOWN_ISSUES.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c16-failover-recover.md` + `c16-failover-recover-evaluation.md`。

## 退出标准

- [x] `recover_primary` 只在主数据源健康时切回，并同步 active/健康快照。
- [x] 监控连续健康达到阈值才触发，单次健康不切。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C16 评估报告由评估者角色出具。

## 决策记录

- **failover 顺序第一项 = 主数据源**：用户把首选放最前即可，无需额外字段。
- **默认自动回切但需要连续 3 次健康**：避免主库刚恢复又抖动，形成反复切换。
- **回切同样持久化 active**：下次启动继续使用主数据源，与 C15 切换语义一致。
