# G19 SAAM/ATAM 优化实施（灵知 Gnosis）

> 类别：G（目标迭代，在已验收架构内做增量功能）。
> 输入：H3 SAAM 报告 `docs/construction/h3-saam-ux-analysis-report.md` + H4 ATAM 优化方案 `docs/construction/h4-atam-optimization-plan.md`。

## 1. 迭代目标

把 H4 中“下一实现迭代优先”的 P0 与 addtive P1 落到桌面端和后端：

1. P0-1 检索四态与结果来源。
2. P0-2 可操作错误文案。
3. P0-3 导入失败保留上下文。
4. P1-1 per-type 数据源表单模板 + `mark_tested` 接通。
5. P1-2 页面级错误上下文。
6. P1-3 应用内 typed-confirm。
7. P1-4 Browse 能力面板。
8. P1-5 语言一致性。

同时纳入两项低风险 P2 打磨：自适应健康轮询、基础响应式与可访问性。

## 2. 迭代范围

- 范围内：`desktop/src/renderer/*`、`desktop/src/shared/types.ts`、`desktop/src/main/api-client.ts`、`desktop/src/main/index.ts`、`server/app/api/datasources.py`、`server/app/observability/models.py`、四个数据源适配器的 `search()` 来源字段、`server/tests/test_datasource_configs_api.py`。
- 不在范围内：破坏性 API/IPC 变更、SQLite/配置文件 schema 迁移、新增数据源类型、打包策略变更。

## 3. 实施计划

1. 后端：`Hit` 增加可选 `document_id`；新增 `GET /v1/datasources/schemas`；新增 `POST /v1/datasources/configs/{name}/tested`；同步桌面 IPC。
2. 渲染层：新增错误映射；`useAppState` 收敛为“健康 + 导入”全局职责，检索/浏览/配置错误下沉到页面。
3. Search：四态 + 来源信息。
4. Settings：per-type 表单 + 高级 JSON、mark-tested、应用内确认、HA/备份中文分区。
5. Browse：能力面板 + document_id 下拉 + 迁移指引。
6. Documents：应用内删除确认。
7. 文案、ARIA、响应式与自适应健康轮询。

## 4. 交付物

- 代码：上述前后端文件。
- 测试：`server/tests/test_datasource_configs_api.py` 新增 schemas / mark-tested 用例。
- 文档：本协议；`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`clean-state-checklist.md` 同步。

## 5. 退出标准

- `npm run check` / `npm run lint`：0 errors。
- `npm run build`：Vite 构建成功，记录包体积与差值。
- `npm run test:unit` / `test:integration`：全绿，记录通过数。
- `rg "window\\.confirm" desktop/src`：无残留。
- Search 四态、导入失败上下文、Browse 501 可读文案可通过代码引用与（可行时）运行时 smoke 复核。
- `feature_list.json` 新增 `feat-g19-saam-atam-ux-implementation`，evidence 非空。
- `git status` 不含计划外改动。
