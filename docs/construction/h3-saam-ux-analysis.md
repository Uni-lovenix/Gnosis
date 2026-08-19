# H3 SAAM UX/UI 分析（迭代协议）

> 类别：H（harness / 文档迭代）。只产出过程工件与文档，**零生产代码改动**。

## 迭代目标

用 UX 化 SAAM（Scenario-based Architecture Analysis Method，场景驱动架构分析方法）对当前桌面端做一次系统性评审，覆盖**可用性（usability）、用户体验（UX）、用户界面（UI）**三个维度，输出可复核、可落盘、可驱动后续迭代的分析报告。

## 当前上下文

- 当前 RUP 阶段：移交后增量（transition 已通过）
- 当前迭代：G18 HA 配置总览（已收尾）→ 本轮 H3
- 分析对象：`desktop/` 渲染层、状态机、IPC/API、相关后端端点与进程
- 目标用户画像：混合用户（个人知识库日常使用 + 配置/运维操作），权重均衡

## 范围

### 在范围内

- 桌面端 5 个页面：Import / Search / Browse / Documents / Settings
- `App.tsx` 导航、健康状态、降级横幅、错误层
- `useAppState` 全局状态机与进度/事件反馈
- `KBAPI` / preload / main / `ApiClient` / `server-manager`
- `styles.css` 与 `shared/types.ts` 承载的界面契约
- 与 UI 协作的后端契约：`/v1/health`、files/tasks、search、chunks、datasources、backups、failover、settings/ha
- 静态代码/文档取证 + 实际启动 Electron 的运行时截图与走查

### 不在范围内

- 不改任何生产代码、接口、类型、schema 或配置
- 不评估后端检索算法、embedding 模型质量、数据源内部实现
- 不实施 UI 修复；建议仅作为后续迭代输入

## 场景集（已与用户协商为全流程基线 7 场景）

| 编号 | 场景 | 用户目标 | 成功标准 |
|---|---|---|---|
| S1 | 首次启动与降级识别 | 第一次打开应用，理解服务/数据源是否就绪 | 30 秒内能判断状态并知道下一步（启动 Ollama、配数据源等） |
| S2 | 数据源配置与激活 | 新增/编辑/测试/保存/激活/热切换数据源 | 不查文档也能完成一次连接测试与激活；错误信息可操作 |
| S3 | 文件导入与进度反馈 | 导入 Excel/Word/PDF/Markdown 并确认结果 | 清楚看到阶段进度、成功或失败原因，失败后可恢复 |
| S4 | 知识检索 | 输入问题并找到相关知识 | 3 次尝试内找到目标知识，能理解相关性并知道下一步 |
| S5 | 数据浏览与排查 | 按文档/解析器浏览 chunks、查看元数据 | 能定位指定数据，识别 active 数据源能力限制 |
| S6 | 运维与故障恢复 | 备份、恢复、failover、健康监控、HA 参数查看 | 破坏性操作有确认，操作过程有状态反馈，失败可诊断 |
| S7 | 长期使用效率 | 高频用户快速完成导入→检索→浏览 | 重复任务步骤少、状态保留合理、信息密度与一致性可接受 |

## 方法：UX 化 SAAM

1. 建立 UI/UX 架构元素清单（页面、导航、状态机、IPC/API、反馈机制、样式系统、进程生命周期）。
2. 对每个场景判定支持方式：
   - **直接支持**：现有架构元素直接满足；
   - **间接支持**：需要多个元素组合或少量界面调整；
   - **未支持**：当前缺少能力，需要新增元素或改动契约。
3. 将场景映射到架构元素，记录证据（文件:行号或运行时截图）。
4. 分析场景交互与共享资源（例如全局状态机、健康轮询、确认对话框、toast 的并发与覆盖关系）。
5. 按质量属性评估：可用性（有效性/效率/可学习性/错误恢复）、体验（满意度/信任/反馈及时性）、界面（清晰/一致/可达性/响应式）。
6. 输出问题（带严重度）、风险、P0/P1/P2 建议与结论。

## 取证方式

### 静态取证

- 逐文件核对 `desktop/src/renderer/`、`desktop/src/main/`、`desktop/src/preload/`、`desktop/src/shared/types.ts`
- 核对 `docs/RUNBOOK.md`、`docs/API.md`、`docs/construction/c4-multi-experience.md` 等文档与实现的一致性
- 代码引用统一用 `文件:行号`，保证可 grep 复核

### 运行时取证

- 使用隔离环境：临时 `KB_DATA_DIR` / `KB_BACKUP_DIR`、`KB_EMBED_BACKEND=mock-hash`、`KB_BACKUP_AUTO=false`
- 准备样例文件并导入，使 Search / Browse / Documents 有真实数据
- `KB_DEBUG_RENDER=1` 启动桌面端，通过 CDP（Node 内置 WebSocket）驱动标签页与输入并截图；必要时回退 `osascript` + `screencapture -l`
- 截图保存到 `/tmp/gnosis-saam-evidence/`，报告引用路径但不提交二进制
- 覆盖：5 个标签页、降级横幅、导入进行中/完成/失败、检索有结果/无结果、浏览过滤与分页、删除确认、Settings 表单/保存列表/HA/failover/backup
- 结束后清理临时目录与进程，不污染真实用户数据目录

## 交付物

- `docs/construction/h3-saam-ux-analysis-report.md`：完整分析报告
- `feature_list.json`：新增 `feat-h3-saam-ux-analysis`（pass + 非空 evidence）
- `progress.md`：H3 记录与可复核基线
- `evaluator-rubric.md`：H 类迭代要求刷新，补充 H3 评审上下文
- `session-handoff.md`：H3 交接记录

## 退出标准

- [x] 迭代协议先于分析落盘（本文件）
- [x] 7 个场景每个均含：场景描述、前置条件、操作路径、成功标准、直接/间接/未支持分类、架构元素映射、证据、问题与严重度
- [x] 报告可复核：代码引用可 grep 命中，截图文件存在且非空，运行时观察含实际命令与结果
- [x] feature_list 新增条目 evidence 非空；progress / evaluator-rubric / session-handoff 已同步
- [x] 除文档与过程工件外无生产代码变更；`git status` 不含计划外改动

## 决策记录

- 7 个场景为最终基线，执行阶段不新增场景。
- 运行取证默认 mock embedder；Ollama 未启动不影响 UI/UX 分析。
- 报告使用中文，技术术语保留英文原名。
- 本迭代只产出分析报告与过程工件，不实施 UI 修复。
