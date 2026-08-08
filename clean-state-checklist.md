# 干净状态检查清单 -- 灵知 (Gnosis)

## 当前快照

- 当前 RUP 阶段：移交后增量（transition 已通过）
- 当前迭代：H2 过程政策确立（已收尾）
- 时间：2026-08-08T00:00:00.000Z

## Build & Verification

- [x] `bash init.sh` 通过（全部 harness 文件齐全）
- [x] `npm run check` 通过（= `cd desktop && tsc --noEmit -p tsconfig.json` 0 errors）
- [x] `npm run lint` 通过（= `cd desktop && tsc --noEmit -p tsconfig.json` 0 errors）
- [x] `npm run test:unit` 通过（= `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings tests/` **144 passed in 5.21s**）
- [x] `npm run test:integration` 通过（= `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings` **144 passed in 4.68s**）
- [x] `npm run eval:mock` 通过（9/10 = 90% ≥ 60% 门禁）
- [x] `npm run build` 通过（Vite **158.61 kB JS + 7.00 kB CSS / 38 模块 / 685ms** + tsc 0 errors）
- [x] `npm run verify` 通过（聚合 check+lint+test:unit+test:integration）
- [x] `cd desktop && npx tsc --noEmit -p tsconfig.json`：0 errors
- [x] `cd desktop && node --test scripts/test-server-manager.cjs`：2 passed in 30.8s
- [ ] `npm run eval`（默认 Ollama bge-m3 路径）：本轮未跑，需先 `ollama serve`；G3 记录 10/10

## Harness Integrity

- [x] `AGENTS.team.md`、`agents.json`、`agents/` 存在且路由一致
- [x] `feature_list.json` 反映真实功能状态（**21/21 = pass**，evidence 全部非空）
- [x] `progress.md` 和 `session-handoff.md` 已更新（含 G7 / H1 / H2 记录）
- [x] `quality-document.md`、`evaluator-rubric.md` 已填写（A 级 / 4.75 分；双层可观测性已补分并在 H2 重评）
- [x] `docs/PROCESS.md` + inception/elaboration/construction/transition/goal 各阶段文档齐全
- [x] `docs/PROCESS.md` 状态准确（H2 修正：此前停在 `当前阶段：inception`，阶段表四行标 `待进入`）
- [x] `docs/goal/01-mapping.md` 写入（goal.md → 实际项目栈映射）
- [x] 根级 `package.json` 写入聚合 npm scripts（不动 `desktop/package.json` 字段）
- [x] 迭代协议与评估报告的适用范围有明文规则（H2：`docs/PROCESS.md` §迭代分类与评估策略）
- [x] G1-G4 无协议 / G1-G7 无评估报告 → 已由 H2 显式追认，非隐性欠账
- [ ] H2 政策尚未经任何 G 类迭代实践检验（下一轮 G 类迭代收尾时验证"自验四项最低要求"与四条升级触发条件是否真的可判定）

## Architecture Boundaries

- [x] 渲染层没有直接导入 Node.js / electron 模块（仅通过 `window.kb`）
- [x] IPC channel 只定义在共享类型源（`src/shared/types.ts`）与 preload（`src/preload/index.ts`）
- [x] 文件系统和对话框只存在于主进程（`dialog.showOpenDialog` 在 `src/main/index.ts`）

## Runtime & Clean State

- [x] 应用可以启动：`cd server && uvicorn app.main:app --port 8765`
- [x] 桌面端可以启动：`cd desktop && npm run dev`
- [x] 本地草稿和设置可以重置：删除 `<userData>/kb-desktop` 与 `~/.kb-server` 即清空
- [x] 导出后的 harness 通过落盘校验（`bash init.sh`）

## Observability

- [x] 日志是结构化 JSON：structlog 输出含 timestamp、level、event
- [x] 关键操作留下了可复核的日志和证据：`kb-server.startup`、`vector.ready`、`embedder.ready`、`embedder.retry`、`datasource.from_saved`、`pipeline.stage`、`chunks.browse_*` 等 19 类事件（本轮在 `server/app/` 下 grep 逐个实测命中）
- [x] 健康检查端点存在：`server/app/api/health.py` → `/v1/health`
- [x] 任务级可观测性：`TaskStage` 7 态 + `TaskEvent` ring buffer 32 + `/v1/files/tasks/{id}/events?since_id=`（G6）
- [x] 进程可观测性：desktop 5s 心跳 + 3 次失败自动重启，2 项 node 测试通过

## Data & State

- [x] 没有未记录的半成品状态
- [x] 当前进度与 `feature_list.json` 和 `progress.md` 一致
- [x] 下一轮会话无需人工修复即可继续

## Performance

- [x] `pytest -p no:warnings tests/` **144 passed in 5.21s**（unit）；`pytest -p no:warnings` **144 passed in 4.68s**（integration）
- [x] Vite build 0.69s（**38 模块 / 158.61 kB JS / 7.00 kB CSS**）；server eval < 1s（mock embedder，9/10）
- [x] 本地分析与导出耗时符合当前项目目标

## Repository

- [x] working tree 干净（`git status --porcelain` 空）；分支 `main`
- [x] `desktop/node_modules/` 是 npm 安装产物，已在 `.gitignore` 生效
- [x] 根级 `package.json` 仅聚合 scripts，无 dependencies；`desktop/package.json` 字段未触碰
- [x] 没有敏感数据或密钥被提交（`.env` / `.env.*` 已 ignore）
- [x] 构建产物没有被提交（`desktop/dist/` 等已在 `.gitignore` 实际生效，非"推荐"）
- [x] `__pycache__` / `.pytest_cache` / `*.db` / `kb_milvus_lite.db/` 已在 `.gitignore` 实际生效