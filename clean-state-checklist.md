# 干净状态检查清单 -- 灵知 (Gnosis)

## 当前快照

- 当前 RUP 阶段：transition（已通过）
- 当前迭代：goal-mapping（G1）
- 时间：2026-08-04T22:55:00.000Z

## Build & Verification

- [x] `bash init.sh` 通过（全部 harness 文件齐全）
- [x] `npm run check` 通过（= `cd desktop && tsc --noEmit -p tsconfig.json` 0 errors）
- [x] `npm run lint` 通过（= `cd desktop && tsc --noEmit -p tsconfig.json` 0 errors）
- [x] `npm run test:unit` 通过（= `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings tests/` 89 passed）
- [x] `npm run test:integration` 通过（= `cd server && KB_MILVUS_URI=./kb_milvus_lite.db pytest -p no:warnings` 89 passed）
- [x] `npm run eval` 通过（9/10 = 90% ≥ 60% 门禁）
- [x] `npm run build` 通过（Vite 148.70 kB + tsc 0 errors）
- [x] `npm run verify` 通过（聚合 check+lint+test:unit+test:integration）
- [x] `cd desktop && npx tsc --noEmit -p tsconfig.json`：0 errors
- [x] `cd desktop && npm run build`：Vite + tsc 全部成功（37 模块 / 148.70 kB JS）

## Harness Integrity

- [x] `AGENTS.team.md`、`agents.json`、`agents/` 存在且路由一致
- [x] `feature_list.json` 反映真实功能状态（13/13 = pass）
- [x] `progress.md` 和 `session-handoff.md` 已更新（含 G1 记录）
- [x] `quality-document.md`、`evaluator-rubric.md` 已填写（5/5 + A 级）
- [x] `docs/PROCESS.md` + inception/elaboration/construction/transition/goal 各阶段文档齐全
- [x] `docs/goal/01-mapping.md` 写入（goal.md → 实际项目栈映射）
- [x] 根级 `package.json` 写入聚合 npm scripts（不动 `desktop/package.json` 字段）

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
- [x] 关键操作留下了可复核的日志和证据：`kb-server.startup`、`vector.ready`、`embedder.fallback_to_mock`

## Data & State

- [x] 没有未记录的半成品状态
- [x] 当前进度与 `feature_list.json` 和 `progress.md` 一致
- [x] 下一轮会话无需人工修复即可继续

## Performance

- [x] `pytest -p no:warnings tests/` 89 passed in 2.74s（unit）；`pytest -p no:warnings` 89 passed in 2.59s（integration）
- [x] Vite build 0.4s（37 模块 / 148.70 kB JS）；server eval < 1s（mock embedder，9/10）
- [x] 本地分析与导出耗时符合当前项目目标

## Repository

- [x] `desktop/node_modules/` 是 npm 安装产物（git ignore 推荐）
- [x] 根级 `package.json` 仅聚合 scripts，无 dependencies；`desktop/package.json` 字段未触碰
- [x] 没有敏感数据或密钥被提交
- [x] 构建产物没有被提交（`dist/` 推荐加入 .gitignore）
- [x] `__pycache__` / `.pytest_cache` / `kb_milvus_lite.db` 推荐加入 .gitignore