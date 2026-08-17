# C9 黑板体系落地

## 迭代目标

把现有线性 pipeline 编排升级为标准黑板体系，同时保持公开 HTTP API、IPC 协议、TaskStage 语义和桌面端结构不变。

## 迭代范围

- 新增黑板核心：统一数据模型、词汇表、事件总线、SQLite 投影。
- 新增控制组件：议程、调度器、资源管理、冲突检测。
- 新增知识源注册与发现机制。
- 将导入、检索、浏览生产路径接入黑板控制器。
- 保留旧 pipeline 类与旧 API 注入路径作为兼容测试路径。

## 实施结果

- `server/app/blackboard/` 新增黑板核心、事件、词汇表、注册表、控制组件、投影。
- `server/app/blackboard/sources/` 新增现有能力的 7 个知识源。
- `server/app/main.py` 生产默认创建黑板控制器并注册知识源。
- `server/app/api/files.py` / `search.py` / `chunks.py` 在存在控制器时走黑板路径。
- `server/tests/conftest.py` 固定测试数据目录为 `server/var/test-blackboard`，避免测试写入用户主目录。
- 新增 `tests/blackboard/` 13 项专项测试。

## 验证

- `/opt/anaconda3/bin/ruff check app/blackboard app/api/files.py app/api/search.py app/api/chunks.py app/main.py tests/blackboard tests/conftest.py` 通过。
- `npm run test:unit`：`150 passed, 8 skipped`（Milvus Lite 本机不可用；如 Milvus 可用应为 158 passed）。
- `npm --prefix desktop run check` 通过。
- `npm --prefix desktop run build` 通过；Vite JS 161.91 kB。
