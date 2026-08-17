# C15 健康驱动自动 failover（迭代协议）

> 类别：C（构建迭代）。本迭代新增数据源 failover 语义、配置文件字段与自动切换行为，触及持久化配置 schema（datasources.json 顶层新增可选 `failover` 列表），因此按 C 类出独立评估报告。

## 迭代目标

把“监控到降级 → 手动 Switch now”升级为“**自动切到备用数据源**”：

1. `datasources.json` 支持顶层 `failover` 顺序列表（`["es-prod", "mem"]`），向后兼容（缺失 = 空）。
2. 新增 `GET/PUT/DELETE /v1/datasources/failover` 管理 failover 顺序。
3. 健康监控连续 N 次（默认 2）探到 active datasource 不健康时，按 failover 顺序尝试下一个可用数据源并自动切换、持久化 active。
4. 桌面端 Settings 可查看/保存/清空 failover 顺序。

## 迭代范围

### 1. DatasourceStore

- `_read_locked()` 对顶层 `failover` 做 `setdefault([])`，缺失兼容。
- `get_failover()` / `set_failover(names)`：只保留已保存配置名，去重保序；空列表即清空。

### 2. datasources API

- `GET /v1/datasources/failover` → `{names: [...]}`。
- `PUT /v1/datasources/failover` body `{names}` → 校验后保存并返回。
- `DELETE /v1/datasources/failover` → 清空。
- `failover_datasource()`（内部异步函数）：
  - 当前 active 不在候选内；
  - 按顺序 build + health 探活，成功后 `controller.replace_datasource` + `store.activate` + 更新 chunks/health 快照；
  - 全部失败返回 `None` 并打 `datasource.failover_exhausted`。

### 3. 健康监控

`main._health_monitor_loop`：

- 统计连续 datasource 探活失败次数；
- 达到 `KB_FAILOVER_CONSECUTIVE_FAILURES`（默认 2）且 `KB_FAILOVER_ENABLED`（默认 true）时调用 `datasources_api.failover_datasource()`；
- 切换成功后重置计数；继续探活新数据源。

### 4. 桌面端

- `shared/types` / `api-client` / `preload` / `main` 新增 `listFailover` / `setFailover` / `clearFailover`。
- SettingsPage 新增 Failover order 区块：逗号分隔输入、保存、清空。

## 实施计划

1. 先落盘本协议。
2. DatasourceStore failover 支持 + 单测。
3. datasources API failover 管理 + `failover_datasource` + API 测试。
4. 健康监控接入自动 failover。
5. 桌面端 IPC + Settings UI。
6. 跑全量验证并更新文档/harness + C15 评估。

## 交付物

- `server/app/observability/datasource_store.py`：failover 顺序。
- `server/app/api/datasources.py`：failover API + `failover_datasource`。
- `server/app/config/settings.py`：`failover_enabled` / `failover_consecutive_failures`。
- `server/app/main.py`：健康监控触发 failover。
- `desktop/src/{shared/types.ts,main/api-client.ts,main/index.ts,preload/index.ts,renderer/pages/SettingsPage.tsx}`。
- 测试：`server/tests/test_datasource_store.py`、`server/tests/test_datasource_configs_api.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/elaboration/01-architecture-baseline.md`、`docs/KNOWN_ISSUES.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c15-auto-failover.md` + `c15-auto-failover-evaluation.md`。

## 退出标准

- [x] failover 顺序可存取，缺失字段向后兼容。
- [x] failover API 校验已保存配置名。
- [x] 监控连续失败达到阈值时自动切换并持久化 active；全部候选失败不切换并留日志。
- [x] 桌面端可管理 failover 顺序。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C15 评估报告由评估者角色出具。

## 决策记录

- **failover 顺序放在 datasources.json 顶层**：用户可 `cat` / 版本管理，且与配置同源；缺失默认空，旧文件兼容。
- **连续失败阈值默认 2**：单次抖动不触发切换，避免误切；恢复后不自动切回，避免 flapping（用户可手动 Switch now 回主数据源）。
- **failover 切换也更新 active 指针**：与 C12 热切换一致，下次启动继续使用备用数据源，不反复回跳。
