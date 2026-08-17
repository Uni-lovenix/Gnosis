# C12 active 数据源热切换（迭代协议）

> 类别：C（构建迭代）。本迭代新增运行时数据源切换语义并触碰黑板资源锁，属于新增责任区块，需独立评估报告。

## 迭代目标

把“active 切换只在下次启动生效”升级为**可热切换**：

1. 新增 `POST /v1/datasources/active/{name}/switch`：构建新适配器 → 探活 → 加资源锁 → 替换黑板 `DatasourceResource` → 持久化 active → 更新健康快照。
2. 切换使用黑板 `ResourceManager` 的 `datasource_write` + `search` 锁，避免替换发生在正在运行的写入/检索中途。
3. 桌面端 Settings 增加 “Switch now” 按钮，不改变原 “Activate”（仅持久化下次启动）语义。

## 迭代范围

### 1. 黑板控制器

`BlackboardController.replace_datasource(datasource)`：

- 用 `self.resources.acquire(["datasource_write", "search"])` 串行化切换。
- 成功后 `self.datasource_resource.set(datasource)`，并关闭旧 datasource（如有 `close`）。

### 2. 数据源 API

`server/app/api/datasources.py`：

- 新增 `set_controller` / `set_embedder_dim` / `set_active_datasource` 注入点。
- 新增 `POST /v1/datasources/active/{name}/switch`：
  - 配置不存在 → 404；
  - 无控制器 → 503；
  - build 失败 → 400；
  - `health()` 非 ok → 400（避免切到不可用数据源）；
  - 成功后 `store.activate(name)` 持久化 + `chunks_api.set_active_datasource(ds)` + `health_api.update_active_datasource(ds)` + `datasource.switched` 日志。

### 3. 健康快照

`health_api.update_active_datasource(ds, source)` 更新 `_runtime.datasource` 与
`datasource_source`，不重置 `started_at`，并清空 readiness 缓存。

### 4. 桌面端

- `shared/types` / `api-client` / `preload` / `main` 新增 `switchDatasourceConfig(name)`。
- Settings 保存配置表格中新增 “Switch now” 按钮，成功 toast 显示 `switched to X`。
- 帮助文案区分 Activate（下次启动）与 Switch now（立即生效）。

## 实施计划

1. 先落盘本协议。
2. 实现 `BlackboardController.replace_datasource`。
3. 扩展 datasources API + health update。
4. main.py 注入 controller / embedder dim / active ds。
5. 桌面端新增 IPC 与按钮。
6. 补测试（controller 切换 + API 切换 + 健康快照），跑全量验证。
7. 更新文档与 harness + C12 评估。

## 交付物

- `server/app/blackboard/control.py`：`replace_datasource`。
- `server/app/api/datasources.py`：`POST /v1/datasources/active/{name}/switch`。
- `server/app/api/health.py`：`update_active_datasource`。
- `server/app/main.py`：注入 datasources API 运行时依赖。
- `desktop/src/{shared/types.ts,main/api-client.ts,main/index.ts,preload/index.ts,renderer/pages/SettingsPage.tsx}`。
- 测试：`tests/blackboard/test_controller.py` + `tests/test_datasource_configs_api.py`。
- 文档：`docs/API.md`、`docs/RUNBOOK.md`、`docs/KNOWN_ISSUES.md`、`docs/elaboration/01-architecture-baseline.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c12-hot-switch.md` + `c12-hot-switch-evaluation.md`。

## 退出标准

- [x] `replace_datasource` 在锁内替换，且切换后新数据源立即被 search/browse/import 使用。
- [x] switch 端点对 404 / 503 / build 失败 / health 失败给出明确错误。
- [x] 桌面端 “Switch now” 可调用且不重启服务。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C12 评估报告由评估者角色出具。

## 决策记录

- **保留 Activate 语义**：原按钮仍只持久化、下次启动生效；热切换用显式 “Switch now”，避免把“保存配置”和“打断运行”混在一起。
- **切换要求 health ok**：热切换是把运行中的 pipeline 切到新后端，先探活可以避免把坏配置写进运行态。
- **用黑板锁而非进程级全局锁**：切换只与写入/检索资源相关，黑板资源锁已表达该边界；切换会等待在飞任务结束。
