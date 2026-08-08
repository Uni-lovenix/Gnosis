# Goal Loop 目标描述模板 — 灵知 (Gnosis)

> 本目标用于执行 **灵知 (Gnosis)** —— 本地知识库应用的核心功能开发，请严格遵循验收标准与范围限制。

## 目标

实现本地知识库的数据导入与向量化存储功能，让用户可以本地部署属于自己的知识库，具体包括：
- 支持配置至少四种数据源：Elasticsearch、PostgreSQL、MySQL、向量数据库（如Milvus或Pgvector）。
- 支持上传并解析 Excel（.xlsx）、Word（.docx）、PDF（.pdf）、Markdown（.md）文件。
- 使用 bge-m3 模型对解析后的文本内容进行向量化，并将向量连同元数据存入配置的目标数据库（优先存入 Elasticsearch 8+）。

## 验收标准

所有验收项须通过，每条均可通过自动脚本或人工验证方式确认：

- [ ] **配置管理**：提供图形界面或配置文件，允许用户添加/编辑/删除数据源连接信息（主机、端口、认证等），并测试连接成功。
- [ ] **文件导入**：前端提供文件上传按钮，支持批量上传上述四种格式文件；后端能够解析文件并提取纯文本内容（保留基本段落结构）。
- [ ] **向量化**：调用 bge-m3 模型（可通过本地 Ollama 或 HuggingFace 接口）为每个文本块生成 1024 维向量，并关联文件名、上传时间、原始文件路径等元数据。
- [ ] **数据存储**：向量及元数据成功写入 Elasticsearch 索引（若配置为其他目标数据库，则按对应驱动写入），写入后可通过查询接口验证数据存在。
- [ ] **集成测试**：运行 `npm run test:integration`（自定义脚本）覆盖完整导入流程（上传→解析→向量化→存储），所有测试通过。
- [ ] **代码质量**：TypeScript 类型检查通过（`npx tsc --noEmit`），ESLint 零错误（`npm run lint`）。
- [ ] **前端反馈**：导入过程中显示进度条或状态提示，完成时给出成功/失败通知。

## 范围

### 可以改的

- `src/backend/` 下的所有模块（控制器、服务、模型、数据源适配器）
- `src/frontend/src/components/` 中的上传组件和配置页面
- `src/frontend/src/api/` 中的 API 调用封装
- `src/shared/types/` 类型定义
- `scripts/` 中的测试和初始化脚本
- `docker-compose.yml`（如需新增服务如 Milvus）
- `package.json`（允许新增必要的依赖包，如 `xlsx`, `pdf-parse`, `mammoth`, `markdown-it`, `@elastic/elasticsearch`, `pg`, `mysql2` 等）

### 不能改的

- `src/main.ts`（Electron 主进程入口，除非必要且经确认）
- 现有数据库迁移文件（`migrations/` 下的文件版本号不可修改）
- `package.json` 中的 `engines` 和 `scripts` 已有字段（`start`, `build` 等不可变更）
- `.github/workflows/` 下的 CI 配置
- `public/` 目录下的静态资源（图标、HTML 模板）

## 验证方式

每一轮实现后必须按以下顺序执行检查，任何失败立即修复：

1. `npx tsc --noEmit` — 检查 TypeScript 类型。
2. `npm run lint` — 检查代码风格。
3. `npm run test:unit` — 运行单元测试（覆盖解析器、向量化服务、数据源适配器）。
4. `npm run test:integration` — 运行端到端导入流程测试（需启动测试数据库和模型服务）。
5. 若全部通过，启动应用（`npm run dev`）进行手动验证：
   - 打开配置页面，添加 Elasticsearch 连接，测试连通性。
   - 上传一个示例 `.md` 文件，观察向量生成及存储，查询返回结果。
   - 重复测试其他格式文件。
6. 启动GUI对功能进行验证。

## 停止条件

- 所有验收标准全部通过 ✅
- 达到最大回合数：20 轮
- 连续 3 轮没有进展（同样的错误反复出现）
- 遇到无法自行解决的阻塞问题（比如需要的依赖不存在、环境问题）

## 工作方式

1. 先读 `AGENTS.md` 和 `feature_list.json`，理解项目结构和现有功能。
2. 先写设计思路，再动手改代码，设计遵循第一性原理，避免过度设计。
3. 每完成一个子任务就验证一次。
4. 遇到卡住超过 2 轮，换个思路或简化方案。
5. 每一轮结束后更新进度。
