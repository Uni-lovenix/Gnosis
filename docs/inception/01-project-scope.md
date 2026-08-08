# 项目范围说明 -- 个人知识库

> 启动阶段交付物 1/3：项目边界、核心目标、关键约束。

## 1. 核心需求（来自 `feature_list.json`）

1. **多数据源适配**：支持 Elasticsearch、PostgreSQL、MySQL 以及向量数据库（Milvus / Qdrant / pgvector 等）的可插拔适配层。
2. **文件导入**：支持 Excel、Word、PDF、Markdown 等格式的解析与结构化抽取。
3. **向量化能力**：支持 embedding 模型（BGE-M3）的接入、推理、缓存与回退。
4. **数据存储**：向量化结果持久化到所选数据库，并支持检索与回查。

## 2. 项目边界

### In-Scope（本次必须交付）

- 单机桌面端：Electron + React + TypeScript 主进程 + 渲染进程。
- 本地后端服务：Python（FastAPI），提供 embedding 推理、文件解析、向量存储协调。
- 数据源适配层：统一抽象 `DataSource` 接口，至少 4 类适配实现。
- embedding 模型：BGE-M3，可选本地或远端推理。
- 端到端最小闭环：文件 → 解析 → 切片 → embedding → 入库 → 检索。

### Out-of-Scope（本次不交付）

- 多用户协同编辑、权限分级、企业级账号体系。
- 公网部署与 SaaS 化运营。
- 模型微调与训练流水线。
- 移动端原生应用（仅保留接口预留）。
- 商业向量化数据库的私有协议实现。

## 3. 核心目标

| 目标 ID | 描述 | 度量 |
|---|---|---|
| G1 | 个人可在本地搭建并使用统一知识库 | 桌面端可启动、可上传、可检索 |
| G2 | 文件导入可解析 ≥4 种主流格式 | excel/word/pdf/markdown 解析单元测试均通过 |
| G3 | embedding 可调用 BGE-M3 | embedding 服务可达、批量调用 < 2s/段 |
| G4 | 向量与元数据可持久化到至少 4 类数据源 | Elasticsearch / PostgreSQL / MySQL / 向量数据库均可接入 |
| G5 | 检索结果可解释 | 返回 top-k 与命中文档片段 |

## 4. 关键约束

- **运行平台**：开发机 macOS（Darwin 25.5.0），要求跨平台可构建（macOS / Windows / Linux）。
- **技术栈**：React、Electron、TypeScript、Python（≥3.10）、Elasticsearch 8+。
- **可观测性**：结构化 JSON 日志（timestamp、level、service、message）。
- **可测试性**：类型检查、单测与 e2e 必须可复跑。
- **代码可交接**：新会话仅靠仓库工件即可继续推进。

## 5. 角色映射

| 需求区块 | 负责角色 | 交付形式 |
|---|---|---|
| 多数据源 + 检索 | 数据与报表开发者 | `DataSource` 抽象与 4 类适配实现 |
| 文件解析 + 同步 | 文件与同步开发者 | 解析器、切片器、同步队列 |
| embedding + Agent | AI 与智能体开发者 | embedding 服务 + 检索 Agent |
| Electron + React UI | 多端体验开发者 | 桌面端与 IPC 集成 |
| 文档与交接 | 文档与交接负责人 | README、API、运行说明、已知问题 |

## 6. 退出标准

- [x] 范围与目标已确认（本文件）。
- [x] 初始风险已列出（见 `02-initial-risks.md`）。
- [x] 首个迭代已计划（见 `03-initial-iteration-plan.md`）。