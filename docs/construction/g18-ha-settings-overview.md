# G18 HA 配置总览（迭代协议）

> 类别：G（目标迭代）。不新增设计决策，只在已验收架构里把生效的 HA 参数暴露成只读 API + 桌面总览；不命中升级触发条件（无破坏性接口、无 schema 迁移、无新数据源/embedder、不触及安全边界）。

## 迭代目标

把自动备份、健康监控、failover 的生效配置在桌面端 Settings 直接可见：

1. `GET /v1/settings/ha` 返回当前生效参数（来自 `KB_*` 环境变量）。
2. Settings 新增 HA Configuration 只读总览表。
3. 本轮同时作为 **H2 政策生效后的第一个 G 类迭代**，验证“自验四项最低要求”与四条升级触发条件是否真的可判定。

## 迭代范围

### 1. API

`server/app/api/ha.py`：

- `GET /v1/settings/ha` → `HaSettingsResponse`：
  - `backup_auto` / `backup_interval_hours` / `backup_keep`
  - `health_monitor` / `health_monitor_interval_seconds`
  - `failover_enabled` / `failover_consecutive_failures`
  - `failover_auto_recover` / `failover_recover_consecutive_checks`

`main.py` 注册 router。

### 2. 桌面端

- `shared/types` / `api-client` / `preload` / `main` 新增 `getHaSettings()`。
- SettingsPage 新增 HA Configuration 只读表。

### 3. 测试

`server/tests/api/test_ha_settings_api.py`：

- 默认值响应字段完整；
- 覆盖 `KB_BACKUP_INTERVAL_HOURS` / `KB_FAILOVER_CONSECUTIVE_FAILURES` 后响应变化。

## 自验依据（H2 政策）

- 迭代协议先于开发落盘：本文件。
- `progress.md` 留可复核数值：pytest 通过数、tsc 错误数、Vite 体积。
- `feature_list.json` 新增条目且 evidence 非空。
- 双层可观测性：`http.request` + request_id 覆盖新端点；过程侧协议/评分表/feature 同步。

## 退出标准

- [x] `GET /v1/settings/ha` 返回全部 HA 参数，测试覆盖默认与覆盖。
- [x] 桌面端显示 HA Configuration 总览；`npm run check` 0 errors。
- [x] `npm run test:unit` 全量通过并记录数值。
- [x] `npm run build` 通过并记录 Vite 体积差值。
- [x] H2 自验四项逐条落档。

## 决策记录

- **只读不写**：参数仍以环境变量为单一来源，避免新增持久化配置 schema；本轮先把可见性补齐，后续再考虑可编辑持久化。
- **G 类自验**：新端点不引入设计决策，退出标准全部可重跑断言，符合 `docs/PROCESS.md` 对 G 类的定义。
