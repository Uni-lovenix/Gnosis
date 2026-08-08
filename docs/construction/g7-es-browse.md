# ES 数据浏览页迭代协议（G7 / goal-es-browse）

> 第二轮 Goal 段第七个迭代：让用户能"看见"导入到 ES 里的数据 —— chunk 列表 + 文档聚合 + 过滤 + 分页。

## 目标

- **目标 1**：新增 `BrowsePage`，列出当前 active 数据源里存储的 chunks；按 `document_id` 聚合展示同一文件的 chunk 数 + parser 分布 + sample text；按 parser 下拉 / `document_id` 输入过滤；分页（默认 20/页）。
- **目标 2**：仅 ES 适配器实现 browse 能力（通过新增 `chunk_list` capability 声明），其它 adapter 维持默认 `NotSupportedError` 并由端点统一转 501；前端展示永久警告横幅。
- **目标 3**：Browse 端点读**当前启动期绑定的 active DataSource 实例**（与 import pipeline 同一份），遵循 G2 "active 切换只在下次启动生效"。
- **不**做：跨数据源浏览；写入/删除 chunks；SSE / WebSocket 实时流；权限/多用户。

## 范围

### 1. 后端模型

- `server/app/observability/models.py`：新增 `ChunkSummary(chunk_id, document_id, text, text_length, metadata)` + `DocumentSummary(document_id, chunk_count, parsers, first_chunk_id, sample_text)`。

### 2. DataSource 基类扩展

- `server/app/datasources/base.py`：
  - 新增 `NotSupportedError(DatasourceError)`。
  - `DataSource.list_chunks(*, document_id, parser, offset, limit) -> tuple[list[ChunkSummary], int]`：默认抛 `NotSupportedError`。
  - `DataSource.aggregate_by_document() -> dict[str, DocumentSummary]`：默认抛 `NotSupportedError`。

### 3. ES 适配器实现

- `server/app/datasources/elasticsearch_adapter.py`：
  - `capabilities()` 增 `"chunk_list"`。
  - `_truncate(text)` 静态辅助：截到 240 字加 `…`。
  - `list_chunks`：
    - ES `match_all` + bool filter（按 `document_id` / `metadata.parser`）。
    - `from` / `size` 分页（size 限 1–100，default 20）。
    - `sort` `(document_id asc, chunk_id asc)` 让同 doc 的 chunks 聚在一起。
    - `_source` 限定 `[chunk_id, document_id, text, metadata]`（不返回 `vector`，体积过大）。
    - text 服务端截到 240 字；`text_length` 报原始长度。
    - 返回 `(summaries, total)`。
  - `aggregate_by_document`：
    - ES `terms` agg on `document_id`（size 1000）+ 嵌套 `terms` on `metadata.parser`（size 10）+ `top_hits`（size 1）取 sample text。
    - ES 异常降级为 `{}` 而不是 500（ES 动态 mapping 缺字段时偶发）。
    - 返回 `dict[document_id, DocumentSummary]`。

### 4. Browse 端点

- `server/app/api/chunks.py`（新）：
  - 模块级 `_active_datasource` 句柄 + `set_active_datasource(ds)` / `get_active_datasource()`（参考现有 `app/api/files.py::set_pipeline` 模式）。
  - `GET /v1/chunks?document_id&parser&offset&limit`：
    - `offset ≥ 0`，`limit ∈ [1, 100]`（FastAPI Query 校验 → 422；处理器内手动校验 → 400）。
    - 读 `_active_datasource`；503 if None。
    - 检查 `"chunk_list" in caps`；501 with message 否则。
    - 调 `list_chunks` + `aggregate_by_document`，返回 `BrowseResponse {chunks, total, aggregations}`。
    - `NotSupportedError` 异常 → 501；其它异常 → 500。
    - 打 `chunks.browse` info 事件（document_id / parser / offset / limit / returned / total / aggregations 字段）。
- `server/app/main.py`：`_build_default_components()` 成功后调 `chunks_api.set_active_datasource(ds)`；`app.include_router(chunks_api.router)`。

### 5. 前端

- `desktop/src/shared/types.ts` + `desktop/src/main/api-client.ts`：镜像 `ChunkSummary` / `DocumentSummary` / `BrowseResponse` / `BrowseOpts` + `ApiClient.browseChunks(opts)`（GET with URLSearchParams）。
- `desktop/src/preload/index.ts` + `desktop/src/main/index.ts`：加 `browseChunks` IPC handler。
- `desktop/src/renderer/App.tsx`：Tab union 加 `"browse"`，nav 顺序调整为 `import | search | browse | documents | settings`。
- `desktop/src/renderer/pages/BrowsePage.tsx`（新）：
  - 头部：active ds 角标（`Browsing es-prod`）、refresh 按钮。
  - 永久警告横幅 `.kb-banner-warn`：ds 不支持 `chunk_list` 时显示 + RUNBOOK §3 迁移提示。
  - 过滤栏：parser 下拉（seed `[excel, word, pdf, markdown, text]` ∪ 实际见过的值）+ `document_id` 输入（250ms debounce）+ refresh。
  - 聚合面板：`<table class="kb-agg-table">`，每行显示 `document_id` / parsers / chunk_count / sample_text；点击行 = 应用 `document_id` 过滤。
  - chunk 列表：`<ul class="kb-chunks">`，每条 `<li>`：preview + `<details>` 折叠 JSON metadata + chunk_id / document_id / "240 / 1380 chars" 提示。
  - 分页：prev / next + `offset / limit` + total 状态条。
  - 错误：toast 模式（`SettingsPage` 同款）；501 / 不支持 capability → 切到永久 banner。
  - 复用 `LoadState` 判别联合 + `Toast` 模式。
- `desktop/src/renderer/styles.css`：新增 `.kb-chunks` `.kb-chunks details summary` `.kb-chunks pre` `.kb-agg-table` `.kb-banner-warn` `.kb-browse-filters` `.kb-pagination` 系列样式。

### 6. 复用与可观测性

- 沿用 `SettingsPage` 的 toast 模式 + `DocumentsPage` 的 `LoadState` 判别联合。
- 沿用 `App.tsx` nav map（顺序调整 + 1 项新增）。
- 复用 `get_logger()` structlog，`chunks.browse` info 事件。

## 交付物

| 项 | 验证 |
|---|---|
| 后端 ES adapter 实现 | `pytest tests/datasources/test_elasticsearch_adapter.py` 9/9 通过 |
| Browse 端点 | `pytest tests/api/test_chunks_api.py` 7/7 通过 |
| 前端类型 | `npm run check` 0 errors |
| 前端构建 | `npm run build` Vite 158.61 kB（+4.87 kB vs G6 的 153.74） |
| 文档 | `docs/API.md` §浏览；`docs/RUNBOOK.md` §4b + §3 capability；`docs/goal/01-mapping.md` G7 行；`progress.md` / `session-handoff.md` G7 记录；`feature_list.json` 19/19 |

## 退出标准

1. ✅ `pytest tests/` 125 → **136 passed**（+11 G7 new）。
2. ✅ `npm run verify` test:unit + test:integration 125 → 136 全绿。
3. ✅ `npm run check` 0 errors；`npm run lint` 0 errors；`npm run build` Vite +4.87 kB。
4. ✅ 手工 smoke（ES 9.5.0 + G4 留下的 8 chunks）：browse tab → 8 chunks + 聚合 1 行；filter `parser=markdown` → 只 README chunks；filter `document_id=<id>` → 聚合坍缩到 1 行；点聚合行 → 自动应用 document_id 过滤；切 active 到 vector 重启 → 永久 banner 显示 "datasource 'vector' does not support chunk_list"。
5. ✅ 旧服务器负载兼容（前端类型定义独立，BrowsePage 内部正常处理空数据 / 不支持的 ds）。

## 风险与回滚

- **ES `metadata.parser` 动态 mapping**：若首个 doc 无 parser 字段，terms agg 会失败；`aggregate_by_document` 捕获异常返回 `{}` 而不是 500，前端聚合面板显示为空（仍有 chunk 列表）。
- **active 切换热生效**：遵循 G2 决策，**不**做；BrowsePage 顶部明确告知"显示当前启动期绑定的数据源"。
- **MySQL / Postgres / Vector / Milvus 不支持 browse**：501 with message + RUNBOOK §3 链接；这是**设计如此**，符合 "minimum capability set + per-adapter extensions" 原则。
- **跨数据源浏览**：单一 active 数据源；多数据源浏览（如同时看 ES + Milvus）超出本迭代范围，留作未来扩展。
- **回滚**：删除 `app/api/chunks.py` 路由 + ES 适配器中 `list_chunks` / `aggregate_by_document` 实现；前端 BrowsePage 入口可注释掉 `App.tsx` 的 render 分支。

## 关联文档

- `docs/API.md` §`GET /v1/chunks`
- `docs/RUNBOOK.md` §4b "ES 数据浏览" + §3 capability 列表
- `docs/goal/01-mapping.md` G7 行 + 已完成段
- `feature_list.json` `feat-goal-es-browse`
- `progress.md` / `session-handoff.md` G7 段