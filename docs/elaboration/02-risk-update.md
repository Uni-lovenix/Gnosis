# 风险更新清单 -- 个人知识库

> 细化阶段交付物 2/3：在启动阶段基础上加入架构缓解与新风险。

## 风险矩阵（更新）

| ID | 风险 | 影响 | 概率 | 缓解策略（架构化） | 状态 |
|---|---|---|---|---|---|
| R1 | BGE-M3 本地部署门槛高 | 启动慢、体积大 | 高 | 默认本地懒加载 + 提供 `EMBED_BACKEND=remote` 切换；模型缺失时返回清晰错误 | 已纳入架构 |
| R2 | 多数据源协议差异 | 性能/特性折损 | 中 | 接口收敛最小能力集；特性能力按适配器扩展（`capabilities()` 字段） | 已纳入架构 |
| R3 | 文件解析复杂度 | 解析失败 | 中 | 仅承诺结构化文本；扫描件 OCR 留接口；解析器单测覆盖 4 类样例 | 已纳入测试 |
| R4 | Python 进程崩溃 | 桌面端不可用 | 中 | 主进程 watchdog + 任务状态机 + 失败重试 | 已纳入架构 |
| R5 | 数据源切换丢数据 | 业务受损 | 中 | SQLite 双写元数据；切源时强制导出/迁移 | 已纳入架构 |
| R6 | embedding 限流 | 失败率上升 | 中 | 分批 + 指数退避 + 持久化任务队列 | 已纳入架构 |
| R7 | Electron 与 Python 环境不匹配 | 打包失败 | 中 | `init.sh` 自检 + Python venv 文档化 | 部分缓解 |
| R8 | 评估主观 | 难以客观评分 | 中 | 10 条 fixture 检索集 + 期望片段 + 类型检查/单测硬指标 | 已纳入评估 |
| R9 | 缺乏 CI | 回归风险 | 中 | 类型检查 + 单测可重跑；`bash init.sh` 校验 | 已纳入工程约定 |
| R10 | 多端同步冲突 | 数据丢失 | 低 | 单设备单用户；保留版本号接口 | 已降级 |

## 新识别风险（细化阶段）

| ID | 风险 | 影响 | 概率 | 缓解策略 |
|---|---|---|---|---|
| R11 | sentence-transformers 在 macOS arm64 安装报错 | 模型加载失败 | 中 | 提供 CPU/MPS 双路径；README 写明 platform note |
| R12 | pgvector / Milvus / ChromaDB 安装复杂 | 数据源可启动性差 | 中 | 适配器提供 `health()` 失败时降级提示；README 给出 docker-compose |
| R13 | Electron preload 类型与 Python 模型不对齐 | 端到端断链 | 中 | 用 TypeScript zod schema 与 pydantic v2 双向校验 |
| R14 | MySQL 适配器使用 JSON 列装向量导致大库慢 | 性能问题 | 中 | 文档化"小规模 OK，大规模建议换向量库"；提供 limit |
| R15 | 跨平台路径与编码差异 | 文件读不到 | 中 | 全部走 pathlib；解析前统一 UTF-8 normalize |

## 依赖排序（细化版）

1. Python 服务骨架 + 健康检查 + 日志 → Electron 主进程能拉起。
2. `DataSource` 接口 + ES 适配器 + 单元测试 → 端到端可跑通。
3. `Embedding` 接口 + 本地 BGE-M3 适配器 + 单元测试。
4. 文件解析器（excel/word/pdf/markdown）+ 切片器 + 单测。
5. 流水线：解析 → 切片 → embedding → 入库。
6. 检索 API + 评估 fixture。
7. PostgreSQL / MySQL / VectorDB 适配器。
8. Electron 主进程 + preload + IPC + SQLite。
9. React 渲染层：上传 / 列表 / 检索 / 配置。
10. 打包脚本 + 跨平台说明 + 文档。

## 不在本迭代范围

- 多用户协同、权限分级。
- 模型训练/微调。
- 公网 SaaS 部署。