# 灵知 (Gnosis) — 本地知识库

> 帮助人们在本地部署属于自己的知识库：解析多种格式的文件 → 切片 →
> embedding → 持久化到可插拔的数据源 → 自然语言检索。

## 功能

- **多数据源**：Elasticsearch / PostgreSQL (pgvector) / MySQL (JSON 列) / 向量数据库（in-memory 或 Milvus），抽象为统一接口，可热插拔。
- **文件导入**：Excel / Word / PDF / Markdown，自动解析为统一 `Document`。
- **embedding**：默认走 **本地 Ollama bge-m3**（OpenAI 兼容接口 1024-dim 真模型）；mock 仅留作测试与离线降级。
- **检索**：余弦相似度 top-k，可按元数据过滤。
- **桌面端**：Electron + React + TypeScript，主进程拉起 Python 后端、暴露最小 IPC。
- **评测**：10 条 fixture 检索集 + 命中率门槛。

## 快速开始

> **生产默认 = Ollama + bge-m3**。CI 默认 = mock（pytest 强制 conftest 覆写）。
> 详见 `docs/RUNBOOK.md` §"Embedder 默认"。

### 1. 启动 Python 服务（生产：Ollama bge-m3）

```bash
# 前置：装 Ollama 与 bge-m3（一次性）
ollama pull bge-m3                           # 1024-dim, ~580 MB
ollama list                                  # 看到 bge-m3:latest

# 一键起服务（自动设 KB_EMBED_BACKEND=openai-compat + Ollama 路径）
bash scripts/start_server_ollama.sh          # ← 生产路径
# 或在 server/ 目录手动设 env：
# KB_EMBED_BACKEND=openai-compat \
# KB_OPENAI_BASE_URL=http://127.0.0.1:11434/v1 \
# KB_OPENAI_MODEL=bge-m3 \
#   PYTHONPATH=. uvicorn app.main:app --port 8765
```

### 1b. 离线 / 测试场景（mock 降级）

```bash
cd server
KB_EMBED_BACKEND=mock-hash PYTHONPATH=. uvicorn app.main:app --port 8765
# 启动期会打 embedder.fallback_to_mock 日志并给出 hint
```

### 2. 启动桌面端

```bash
cd ../desktop
npm install
npm run dev   # 自动拉起 Python 子进程
```

桌面端会自动拉起 Python 子进程并通过 `http://127.0.0.1:8765` 与之通信。

## 项目结构

```
.
├── AGENTS.md / CLAUDE.md        # 规则入口
├── agents/                      # 角色规则
├── docs/
│   ├── PROCESS.md               # RUP 流程
│   ├── inception/               # 启动阶段交付
│   ├── elaboration/             # 细化阶段交付
│   ├── construction/            # 构建阶段交付（C1-C8 + G1/G2/G3）
│   └── transition/              # 移交阶段交付
├── server/                      # Python FastAPI 服务
│   ├── app/{api,datasources,embedding,parsers,chunking,pipeline,observability,config}
│   ├── tests/
│   └── eval/
├── desktop/                     # Electron + React + TS 桌面端
│   └── src/{main,preload,renderer,shared}
└── scripts/                     # harness + bench + start_server_ollama
```

## 详细文档

- 架构基线：[`docs/elaboration/01-architecture-baseline.md`](docs/elaboration/01-architecture-baseline.md)
- 数据源能力矩阵：[`docs/construction/c1-data-sources.md`](docs/construction/c1-data-sources.md)
- 文件解析：[`docs/construction/c2-files-and-sync.md`](docs/construction/c2-files-and-sync.md)
- Embedding / 检索：[`docs/construction/c3-ai-embedding.md`](docs/construction/c3-ai-embedding.md)
- 桌面端：[`docs/construction/c4-multi-experience.md`](docs/construction/c4-multi-experience.md)
- HTTP API：[`docs/API.md`](docs/API.md)
- 运行手册（含 Ollama 排错）：[`docs/RUNBOOK.md`](docs/RUNBOOK.md)
- 已知问题：[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md)
- goal.md 映射：[`docs/goal/01-mapping.md`](docs/goal/01-mapping.md)

## 验证

```bash
bash init.sh                       # harness 完整
npm run verify                     # check + lint + 113 pytest
npm run eval                       # 默认走 Ollama bge-m3（10/10 = 100%）
npm run eval:mock                  # 离线 mock 9/10 = 90%
npm run eval:bgem3                 # local snapshot 路径
cd ../desktop && npx tsc --noEmit -p tsconfig.json
cd ../desktop && node --test scripts/test-server-manager.cjs
```
