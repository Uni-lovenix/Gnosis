# 上传进度可观测性迭代协议（G6）

> 第二轮 Goal 段第六个迭代：让 ImportPage 在显示进度条的同时，显示当前 pipeline 阶段和最近事件日志。

## 目标

- **目标 1**：上传/索引时，前端不仅看到"完成多少"，还能看到"在做什么"（当前 stage 文字）+ "做过什么"（折叠事件日志，最近 ~32 条带时间戳）。
- **目标 2**：进度接口契约保持向后兼容 —— 旧服务器负载（无 `stage` / `events` 字段）仍能渲染，前端做 fallback。
- **目标 3**：新增 `GET /v1/files/tasks/{id}/events?since_id=N` 备用端点，为未来的 live-tail 订阅者预留。
- **不**做：通用 backoff 抽象（仅 openai-compat 用，仍在 G5 收敛状态）；pipeline 重启恢复（任务半途失败不可重启）；SSE / WebSocket 实时流（保留 polling + 备用 `/events`）。

## 范围

### 1. 后端模型与持久化

- `server/app/observability/models.py`：新增 `TaskStage` 枚举（queued / parsing / chunking / embedding / writing / done / failed）、`TaskEvent` 模型、`TaskStatus` 扩展 `stage` + `events`（默认 `[]`）。
- `server/app/observability/task_store.py`：
  - v1 schema 迁移：`ALTER TABLE tasks ADD COLUMN stage TEXT NOT NULL DEFAULT 'queued'`（try/except `OperationalError` 幂等）；新增 `task_events(id PK, task_id FK CASCADE, ts, stage, progress, message)` 表 + `ix_task_events_task_id` 索引；`PRAGMA user_version=1`。
  - 新方法：`add_event(task_id, stage, progress, message)`（写入后 trim 到 32 条）、`list_events(task_id)`（升序）、`list_events_since(task_id, since_id)`（增量分页）、`last_event_id(task_id)`。
  - `update()` 加 `stage` kwarg；`get()` 联表返回 events。

### 2. Pipeline 回调签名升级

- `server/app/pipeline/indexing.py`：`IndexingPipeline.on_progress` 从 `Callable[[float], None]` 升级到 `Callable[[ProgressEvent], None]`。
- 新增 `ProgressEvent(stage, progress, message)` dataclass。
- 4 处边界发事件：
  | 边界 | stage | progress | message |
  |---|---|---|---|
  | 进入 run | `parsing` | 0.05 | `f"parsing {doc.source_path}"` |
  | chunker.split 完成后 | `chunking` | 0.30 | `f"{len(chunks)} chunks"` |
  | 每个 embedding batch 后 | `embedding` | `0.30 + 0.50 * frac` | `f"{done}/{total} chunks embedded"` |
  | datasource.add 完成后 | `writing` | 1.0 | `f"wrote {len(ids)} chunks"` |
- **破坏性变更**：唯一生产调用点 `app/api/files.py::_run_import` 同步更新；pipeline 单测同步更新。

### 3. Files API 接入

- `server/app/api/files.py`：
  - `_run_import` 在每个边界调 `store.update(stage=, progress=)` + `store.add_event(...)` + `log.info("pipeline.stage", task_id=, stage=, progress=, message=)`。
  - `TaskResponse` 增 `stage` + `events`。
  - 新增 `GET /v1/files/tasks/{task_id}/events?since_id=N`：返回 `TaskEventsResponse(events, next_since_id)`；`since_id < 0` → 400；`task_id` 不存在 → 404。

### 4. 前端

- `desktop/src/shared/types.ts` + `desktop/src/main/api-client.ts`：镜像 `TaskStage` type + `TaskEvent` interface + `TaskStatus` 扩展。
- `desktop/src/renderer/lib/state.ts`：`AppState.indexing` 加 `stage` / `events` / `lastMessage` 字段；`onProgress` 监听器同步更新（`t.stage ?? "queued"` / `t.events ?? []` 兼容旧服务器）；`importFile` 初始化默认值。
- `desktop/src/renderer/pages/ImportPage.tsx`：在 `<progress>` 下方新增阶段 tag（不同 stage 不同配色）+ 折叠 `<details>` 事件日志（按时间倒序，含 ts / stage / progress / message）。
- `desktop/src/renderer/styles.css`：新增 `.kb-stage-tag` `.kb-stage-{queued,parsing,chunking,embedding,writing,done,failed}` `.kb-event-log` `.kb-event-ts` `.kb-event-progress` 系列样式。
- **无新增 IPC**：沿用 `kb:progress` 订阅（事件已嵌入 `TaskResponse.events`）。

### 5. 复用

- 沿用 `SettingsPage` toast 模式（仅做错误态，不用于 G6 正常态）。
- 沿用 `pollTask()` 600ms 轮询（`desktop/src/main/index.ts`）。
- 沿用 `DocumentsPage.LoadState` 判别联合风格（虽然 G6 没直接复用）。
- 沿用 `get_logger()` structlog（`server/app/observability/logging.py:44`）。

## 交付物

| 项 | 验证 |
|---|---|
| 后端 `IndexingPipeline` 升级 | `pytest tests/pipeline/test_pipelines.py` 6/6 通过 |
| `TaskStore` v1 schema 迁移 | `pytest tests/test_task_store.py` 15/15 通过（含老库升级用例） |
| `TaskStatus` + `/events` API | `pytest tests/api/test_task_progress_api.py` 5/5 通过 |
| 前端类型 | `npm run check` 0 errors |
| 前端构建 | `npm run build` Vite +1.47 kB |
| 文档 | `docs/API.md` §TaskStatus + `/events`；`docs/RUNBOOK.md` §4a；`docs/goal/01-mapping.md` G6 行；`progress.md` / `session-handoff.md` G6 记录；`feature_list.json` 18/18 |

## 退出标准

1. ✅ `pytest tests/` 113 → **125 passed**（+12 G6 new）。
2. ✅ `npm run verify` test:unit + test:integration 120 → 125 全绿。
3. ✅ `npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite +1.47 kB（远低于 +5 kB 目标）。
4. ✅ 手工 smoke：导入 200 页 PDF → 看到阶段文字从"解析文档"→"切片中"→"Embedding 中"→"写入数据源"→"完成"全程切换 + 事件日志展开 ≥ 4 条；导入损坏 .docx → "失败" 红色 tag + parse error 消息。
5. ✅ 旧 `tasks.db`（缺 stage 列）启动时自动迁移，`user_version` 升到 1，原有任务仍可查询。

## 风险与回滚

- **回调签名破坏性变更**：通过"唯一生产调用点 + 单测同步更新"控制爆炸半径；如需回滚，restore `Callable[[float], None]` + 删除 `ProgressEvent`。
- **schema 迁移幂等**：try/except `OperationalError` 兜底重复添加；如需回滚，老版本会忽略未知 `stage` 列 + 忽略 `task_events` 表（向后兼容：旧代码不读这俩字段）。
- **嵌入 events 体积**：32 条 ≈ 2.5 kB/次 poll；60 s import × 600 ms ≈ 250 kB 总流量，可接受；如未来需要 >100 条再切换到专用 `/events` 流。

## 关联文档

- `docs/API.md` §`GET /v1/files/tasks/{task_id}` + §`GET /v1/files/tasks/{task_id}/events`
- `docs/RUNBOOK.md` §4a "上传进度可观测性"
- `docs/goal/01-mapping.md` G6 行
- `feature_list.json` `feat-goal-upload-progress`
- `progress.md` / `session-handoff.md` G6 段