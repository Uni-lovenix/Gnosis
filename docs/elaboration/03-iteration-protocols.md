# 构建迭代协议 -- 个人知识库

> 细化阶段交付物 3/3：为 4 个 construction 迭代与 transition 迭代制定协议。

## 通用约定

- 分支：`feature/<责任区块名>`
- 每个迭代结束更新 `feature_list.json` 与 `progress.md`
- 评估者按"正确性/验证/范围/可靠/可维护/交接"打分（`evaluator-rubric.md`）
- 通过条件：6 项维度均 ≥ 4 分且关键证据落盘
- 类型检查与单测必须可重跑：`bash init.sh` 视为冒烟门禁

---

## C1: 数据与报表开发迭代

### 目标

`DataSource` 抽象稳定 + 4 类适配器可工作 + 接口契约文档化。

### 范围

- `server/datasources/base.py`：抽象与最小能力集。
- `server/datasources/elasticsearch_adapter.py`：ES 8+ dense_vector。
- `server/datasources/postgres_adapter.py`：pgvector 扩展。
- `server/datasources/mysql_adapter.py`：JSON 列向量方案（含 limit 说明）。
- `server/datasources/vector_db_adapter.py`：抽象 Milvus / Qdrant / Chroma 之一为默认实现，其余以占位与 TODO 标注。
- 单元测试：4 个适配器各自的 add/search/delete/health 烟囱测试，使用测试容器或本地 mock（取决于环境）。
- API：`/v1/datasources` 列表 + `/v1/datasources/test` 联通性测试。

### 不在范围

- 解析器与 embedding（本迭代只读 mock）。
- 桌面端集成。

### 交付物

- 上述模块代码 + 单测 + 接口契约文档。
- `docs/construction/data-sources.md`：能力矩阵与使用说明。

### 退出标准

- `pytest server/tests/datasources` 通过。
- 4 类适配器均能在 mock 或测试容器下完成 add → search → delete 闭环。
- 接口变更同步到 `docs/elaboration/01-architecture-baseline.md`。

---

## C2: 文件与同步开发迭代

### 目标

4 类文件解析器 + 切片器 + 任务队列与持久化。

### 范围

- `server/parsers/excel.py`：`openpyxl` → `Document`。
- `server/parsers/word.py`：`python-docx` → `Document`。
- `server/parsers/pdf.py`：`pdfplumber` → `Document`（仅文本层）。
- `server/parsers/markdown.py`：`markdown-it-py` → `Document`（保留结构）。
- `server/chunking/text_chunker.py`：按 token/字符切分 + overlap。
- `server/observability/task_store.py`：SQLite 任务表。
- `server/api/files.py`：`POST /v1/files/import` + `GET /v1/tasks/{id}`。
- 单元测试：4 个解析器样例 + 切片器边界。

### 不在范围

- embedding（用占位 mock）。
- 桌面端集成。

### 交付物

- 上述模块代码 + 单测。
- `docs/construction/files-and-sync.md`：解析能力、失败语义、重试策略。

### 退出标准

- `pytest server/tests/parsers server/tests/chunking` 通过。
- 4 类样例文件（excel/word/pdf/markdown）可解析为非空 Document。
- 切片器对长文档给出重叠切片且无丢失。

---

## C3: AI 与智能体开发迭代

### 目标

embedding 服务 + 端到端流水线 + 检索能力。

### 范围

- `server/embedding/base.py`：`Embedder` 抽象。
- `server/embedding/bge_m3.py`：sentence-transformers 实现（含懒加载）。
- `server/embedding/openai_compat.py`：远端 OpenAI 兼容实现。
- `server/pipeline/indexing.py`：解析 → 切片 → embedding → 入库。
- `server/pipeline/retrieval.py`：embedding(query) → DataSource.search。
- `server/api/search.py`：`POST /v1/search`。
- 评测集：`server/eval/fixtures/` 10 条检索样本 + 期望片段。
- 单元测试：embedding 接口 mock；端到端使用 mock 适配器。

### 不在范围

- 桌面端集成。
- 多模态 embedding。

### 交付物

- 上述模块代码 + 单测。
- `docs/construction/ai-embedding.md`：模型、维度、限流、回退。
- `server/eval/README.md`：评测方法与通过阈值。

### 退出标准

- `pytest server/tests/embedding server/tests/pipeline` 通过。
- 端到端索引 → 检索 demo 脚本可重跑。
- 评测集 10 条检索：top-1 命中率 ≥ 60%（占位阈值，正式评估由评估者覆盖）。

---

## C4: 多端体验开发迭代

### 目标

Electron 主进程 + React 渲染层 + IPC + 状态机，桌面端可启动、可上传、可检索。

### 范围

- `desktop/src/main/index.ts`：窗口、子进程 watchdog、SQLite。
- `desktop/src/preload/index.ts`：contextBridge 暴露 KBAPI。
- `desktop/src/renderer/`：上传、列表、检索、配置 4 个最小页面。
- 状态机：`useAppState`（idle/uploading/indexing/searching/error）。
- 桌面端 e2e：手工启动 → 上传样例 → 检索命中。
- `desktop/README.md`：dev/build/运行说明。

### 不在范围

- 自动更新、签名。
- 移动端。

### 交付物

- 上述模块代码 + 启动说明。
- `docs/construction/multi-experience.md`：UI 流程图、平台差异清单。

### 退出标准

- `npm run check` 类型检查通过。
- `npm run build` 打包可生成产物（macOS dev 模式可启动）。
- 手工 e2e 通过：上传 → 检索 → 配置数据源联通。
- 桌面端在 Python 服务不可达时给出清晰错误而非崩溃。

---

## T1: 移交与文档交接

### 目标

最终验收 + 完整文档 + 已知问题清单。

### 范围

- `README.md`：快速开始（启动 Python 服务 + 桌面端）。
- `docs/RUNBOOK.md`：常见问题、平台差异、回滚。
- `docs/API.md`：HTTP API 参考。
- `docs/KNOWN_ISSUES.md`：已知问题与绕行方案。
- `progress.md` / `session-handoff.md` 收尾。

### 退出标准

- 新会话只读仓库可继续推进。
- `bash init.sh` 通过。
- `feature_list.json` 全部 `pass`。