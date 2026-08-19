# H4 ATAM 优化方案（灵知 Gnosis）

> 类别：H（harness / 文档迭代）。本迭代只产出分析与优化方案，**零生产代码改动**；方案作为后续实现迭代的输入。

## 1. 迭代协议

### 1.1 目标

在 H3 SAAM UX/UI 分析（`docs/construction/h3-saam-ux-analysis-report.md`）基础上，使用 ATAM（Architecture Tradeoff Analysis Method）系统方法，从**架构权衡**角度整理出可执行的优化方案：

1. 建立质量属性效用树，明确优化优先级。
2. 列出当前已采用的架构方法（Architectural Approaches）。
3. 识别敏感点（Sensitivity Points）与权衡点（Tradeoff Points）。
4. 输出风险 / 非风险清单。
5. 按 P0 / P1 / P2 给出优化方案，每项包含目标架构元素、改动方向、保留/放弃的权衡与验收标准。

### 1.2 范围

- 输入：H3 报告、`desktop/src/renderer/*`、`desktop/src/main/*`、`server/app/api/*`、`server/app/blackboard/*`、`server/app/config/*`、`server/app/observability/*`。
- 在范围内：可用性、性能、可用性/可靠性、可修改性、安全性、可部署性、可测试性、可访问性之间的权衡。
- 不在范围内：本轮不实施代码修复；不新增公共 API / schema 迁移 / 安全边界改动。

### 1.3 方法

ATAM 标准步骤的轻量化落地：

1. 梳理业务驱动与质量属性效用树。
2. 将 H3 场景映射为 ATAM 场景（用例 + 质量属性 + 优先级）。
3. 列出当前架构方法，标注“支持哪些质量属性”。
4. 识别敏感点：某个架构决策对属性敏感、变化会放大影响的位置。
5. 识别权衡点：两个或多个质量属性在同一架构决策上互斥的位置。
6. 输出风险 / 非风险与优化方案。

### 1.4 交付物与退出标准

- 本文件即协议 + ATAM 分析 + 优化方案。
- `feature_list.json` 新增 `feat-h4-atam-optimization-plan`（pass + 非空 evidence）。
- `progress.md` / `evaluator-rubric.md` / `session-handoff.md` 同步。
- 退出标准：优化方案每个 P0/P1/P2 项都包含目标架构元素、改动方向、权衡说明与验收标准；无生产代码变更；`git status` 不含计划外改动。

## 2. 业务驱动与质量属性效用树

### 2.1 业务驱动

| 驱动 | 描述 |
|---|---|
| 本地知识库 | 灵知（Gnosis）面向“本地部署属于自己的知识库”，数据与配置本地优先 |
| 混合用户 | 日常知识管理与配置/运维操作并存，权重均衡 |
| 低摩擦启动 | 首次启动应能判断依赖状态并知道下一步 |
| 稳定可用 | 导入/检索/浏览/备份/failover 闭环必须可靠且可观察 |
| 增量演进 | RUP 迭代交付，C/G/H 系列持续扩展，架构必须可扩展 |

### 2.2 质量属性效用树

| 质量属性 | 优先级 (L/M/H) | 关键场景 |
|---|---|---|
| 可用性 Usability | H | U1 首启 30s 内可知状态与下一步；U2 非技术用户可完成数据源配置；U3 检索有空/加载/无结果/错误四态 |
| 性能 Performance | H | P1 导入/检索不阻塞 UI；健康轮询与探活不显著消耗远端资源 |
| 可用性/可靠性 Availability | H | A1 服务崩溃自动重启且 UI 反映状态；A2 备份/恢复/failover 可观察、可回退 |
| 可修改性 Modifiability | H | M1 新增数据源/解析器/embedder 不破坏既有契约；M2 新增页面不破坏 IPC |
| 安全性 Security | M | S1 凭证不意外出现在 UI/日志/导出；S2 破坏性操作有确认与回退 |
| 可部署性 Deployability | M | D1 一键启动；D2 打包产物可在目标平台运行 |
| 可测试性 Testability | M | T1 UI 关键路径可自动化；原生 dialog 不阻塞测试 |
| 可访问性 Accessibility | L/M | A11 键盘、ARIA、响应式布局 |

### 2.3 ATAM 场景（H3 场景映射）

| 编号 | 质量属性 | 场景 | 优先级 (属性重要性, 场景重要性) |
|---|---|---|---|
| AT-U1 | Usability | 首次启动，后端/Ollama 未就绪，用户能在 30s 内得到可操作指引 | (H,H) |
| AT-U2 | Usability | 混合用户完成一次数据源“新增-测试-保存-激活/热切换”，无需手写 JSON | (H,H) |
| AT-U3 | Usability | 搜索无结果时用户能区分“无数据/无匹配/加载中”，并看到结果来源 | (H,H) |
| AT-P1 | Performance | 长导入期间 UI 可切换页面；进度由事件流推送而非整页刷新 | (H,H) |
| AT-A1 | Availability | Python 服务崩溃后 3 次心跳失败自动重启，UI 在 30s 内显示恢复 | (H,H) |
| AT-M1 | Modifiability | 新增 `chunk_list` 之外的 capability 时，不强制改 UI 主流程 | (H,M) |
| AT-S1 | Security | 数据源凭证只在本地配置与备份中存在，UI/日志不打印明文 | (M,M) |
| AT-D1 | Deployability | 用户不装 Python 也能启动打包应用，或至少得到清晰预检 | (M,M) |
| AT-T1 | Testability | UI 自动化可驱动 tab、表单、确认与错误态，无需人工点击原生 dialog | (M,M) |

## 3. 当前架构方法与属性覆盖

| 架构方法 | 位置 | 支持的属性 | 已观测成本 |
|---|---|---|---|
| Electron main/renderer + contextBridge | `main/index.ts`、`preload/index.ts` | 安全、可修改性、可测试性 | IPC 类型需三处同步（共享 types 已缓解） |
| React 全局状态机 | `state.ts` | 简单性、可维护性 | 错误上下文互相覆盖，U3/A1 受影响 |
| FastAPI + 黑板控制器 | `main.py`、`blackboard/control.py` | 可扩展性、并发安全 | 首次理解成本较高，但契约稳定 |
| JSON 配置存储（原子写 + 损坏自愈） | `datasource_store.py` | 可移植性、可恢复性 | options 无 schema 校验，U2 成本高 |
| 健康检查 + readiness + 监控 | `health.py`、`main.py` | 可用性、可观察性 | 轮询频率与远端探活负载需权衡 |
| capability 声明 + 501 | `datasources/base.py`、`chunks.py`、`BrowsePage.tsx` | 可扩展性、诚实反馈 | 默认数据源下 UX 不友好 |
| server-manager watchdog | `server-manager.ts` | 可用性 | 自动重启可能掩盖用户可见的启动失败 |
| 结构化日志 + request_id | `middleware.py`、`logging.py` | 可观察性、可测试性 | 无显著成本 |
| mock embedder fallback | `main.py`、`embedding/factory.py` | 可用性、可部署性 | 用户可能不知道自己在用 mock |

## 4. 敏感点

| 敏感点 | 描述 | 放大因素 |
|---|---|---|
| SP1 | 首次启动体验对 embedder 默认值（Ollama）与健康状态文案敏感 | 缺依赖时只有日志 hint，UI 文案未透出 |
| SP2 | 配置可用性对 options 表示方式（JSON vs 表单）敏感 | 新增 adapter 只需 JSON 就能工作，但也放大了用户出错面 |
| SP3 | 错误反馈对全局 AppState 的 `kind` 字段敏感 | 搜索/导入/健康任一错误都会覆盖其他上下文 |
| SP4 | Browse 可用性对 capability 声明敏感 | 无 `chunk_list` 时用户只能看到 501 文案 |
| SP5 | 性能对健康轮询/探活频率敏感 | 每 5s 心跳 + 每 30s 探活 + 15s 桌面轮询会放大远端负载 |
| SP6 | 安全对“配置可编辑 + 备份含凭证”敏感 | UI 明文 textarea、备份含 `datasources.json` |
| SP7 | 可测试性对原生 `window.confirm` 敏感 | 弹窗阻塞渲染线程，CDP/自动化无法截屏或继续执行 |

## 5. 权衡点（Tradeoff Points）

| 权衡点 | 方案 A | 方案 B | 取舍 | ATAM 建议 |
|---|---|---|---|---|
| TP1 配置表示 | 自由 JSON（当前） | 按类型表单模板 | A 可扩展、B 可学习 | 混合：per-type schema 表单 + 高级 JSON 模式，保留 A 的扩展性，获得 B 的可用性 |
| TP2 错误状态 | 单一全局 state（当前） | 按上下文拆分 | A 简单、B 可隔离 | 保留全局健康/导航，拆分页面级错误上下文，IPC 契约不变 |
| TP3 能力缺失反馈 | 501 + warning 横幅（当前） | 应用内迁移向导 | A 诚实、B 可操作 | capability 声明不变，UI 增加“迁移路径/该数据源可用能力”面板 |
| TP4 健康感知 | 定时轮询（当前） | 事件推送/自适应轮询 | A 实现简单、B 精确且省资源 | 保持轮询基线，降级时提速、恢复时降频；后续可加 SSE/WS |
| TP5 破坏性操作 | 原生 confirm（当前） | 应用内确认对话框 | A 简单安全、B 一致可测 | 替换为应用内 typed-confirm，保留“明确回退”语义 |
| TP6 打包 | 不捆绑 Python（当前） | 捆绑运行时 | A 产物小、B 开箱即用 | 不急于捆绑；先补启动预检/安装说明，再评估 PyInstaller/conda-pack |
| TP7 凭证暴露 | 明文 JSON（当前） | 加密存储 | A 本地可移植、B 更安全 | 维持本地明文 + 权限保护；UI 掩码 + 导出/日志脱敏 + 备份权限提示 |
| TP8 自动重启 | server-manager 自动重启（当前） | 用户确认后重启 | A 可用性高、B 可预期 | 保留自动重启，增加“重启状态/原因”可见事件与手动重启入口 |

## 6. 风险与非风险

### 6.1 风险

| 风险 | 等级 | 描述 | 关联权衡点 |
|---|---|---|---|
| R1 配置错误高发 | 高 | 自由 JSON + 无校验，混合用户容易写坏数据源 | TP1 |
| R2 错误上下文丢失 | 高 | 全局状态机覆盖搜索/导入/健康错误 | TP2 |
| R3 检索反馈缺失 | 高 | 无结果/加载/空数据不区分，用户误判 | TP2、U3 |
| R4 原生 dialog 阻塞 | 中 | 自动化与可访问性受阻，误操作风险 | TP5 |
| R5 远端探活负载 | 中 | 多层轮询叠加，对远端 ES/PG 不友好 | TP4 |
| R6 凭证暴露 | 中 | UI 明文 textarea、备份含密码 | TP7 |
| R7 语言/响应式不一致 | 中 | 品牌与可用性受损 | — |

### 6.2 非风险

- 渲染层不直接导入 Node/Electron，安全边界清晰。
- IPC 契约集中在 `shared/types.ts`，类型漂移风险已被 MI-03 缓解。
- 黑板控制器与 capability 机制为新增数据源/能力提供稳定扩展点。
- 备份/恢复/failover/热切换已有测试与运行时日志闭环。
- mock embedder fallback 保证服务在缺依赖时仍可启动。

## 7. 优化方案

### P0（下一实现迭代优先，低风险、高可见收益）

#### P0-1 检索四态与结果来源

- 目标元素：`SearchPage.tsx`、`state.ts`、`shared/types.ts`（Hit 可选扩展）。
- 改动方向：空查询 / loading / 无结果 / 错误四态；结果项展示来源文档名、parser、导入时间或 metadata 摘要。
- 权衡：结果字段增加轻微 IPC 负载，换取用户可判断性与信任。
- 验收：无结果时显示“无匹配，检查是否已导入”；加载中不闪烁空列表；结果项含来源信息；现有 IPC 不破坏。

#### P0-2 可操作错误文案

- 目标元素：`App.tsx`、`state.ts`、错误映射层。
- 改动方向：把 `fetch failed`、`unsupported file type`、501 等原始错误映射为用户可读文案 + 下一步指引（启动 Ollama / 检查端口 / 查看 RUNBOOK / 更换数据源）。
- 权衡：新增错误映射表，换取反馈可理解性；日志仍保留原始错误。
- 验收：服务不可达、导入失败、Browse 501 三种场景均显示“原因 + 下一步”，不再暴露内部错误字符串。

#### P0-3 导入失败保留上下文

- 目标元素：`ImportPage.tsx`、`state.ts`。
- 改动方向：导入失败改为 Import 页面内错误卡片 + 失败事件记录，而不是只依赖全局 banner；全局 banner 仅保留“服务不可达”。
- 权衡：状态机增加 terminal failed 分支，换取跨页面可追溯。
- 验收：失败后切页再回来仍能看到失败文件、原因与重试入口；事件日志记录 failed 事件。

### P1（架构调整，additive，不破坏既有契约）

#### P1-1 per-type 数据源表单模板

- 目标元素：`SettingsPage.tsx`、`api/datasources.py`（可加 `GET /v1/datasources/schemas`）、adapter 元数据。
- 改动方向：每个 adapter 声明 `options_schema`（字段、必填、类型、敏感标记）；UI 用表单渲染，同时保留“高级 JSON”模式；接通 `mark_tested` 并在保存列表显示 `last_tested_at`。
- 权衡：新增只读 schema 端点（additive）换取 U2 可用性；老配置 JSON 仍可编辑。
- 验收：新增 schema 后无需改 Settings 主流程；表单可生成合法 options；测试连接成功后 `last_tested_at` 被写入。

#### P1-2 页面级错误上下文

- 目标元素：`state.ts`、`App.tsx`、页面 props。
- 改动方向：全局状态只保留导航/健康/服务状态；导入、搜索、浏览各自持有页面级状态与错误；共享 error banner 组件。
- 权衡：状态机稍微复杂，换取错误隔离与上下文连续性。
- 验收：搜索失败不影响导入进度；健康失败不覆盖页面内容；IPC 契约不变。

#### P1-3 应用内确认与操作反馈

- 目标元素：新增 `ConfirmDialog` 组件、`DocumentsPage.tsx`、`SettingsPage.tsx`。
- 改动方向：删除/恢复改为应用内 typed-confirm（输入配置名/文档名确认）；恢复过程显示进度与完成/失败结果。
- 权衡：自定义组件替代原生 dialog，换取一致性、可访问性与自动化可行性。
- 验收：无 `window.confirm` 残留；确认按钮在输入不匹配时禁用；恢复中按钮显示 busy。

#### P1-4 Browse 能力面板

- 目标元素：`BrowsePage.tsx`、`shared/types.ts`（可选）。
- 改动方向：当前数据源支持/不支持的能力以清单展示，不支持项给“迁移路径”（RUNBOOK 链接或摘要）；document_id 增加下拉选择。
- 权衡：页面增加一个信息面板，换取 S5 场景可操作性与“该数据源能做什么”的透明度。
- 验收：默认 memory/vector 下显示“不支持浏览，建议迁移到 ES”；ES 下显示 chunk_list 可用。

#### P1-5 语言一致性

- 目标元素：所有页面文案。
- 改动方向：以中文为主，技术名词保留英文；统一 tab 标签（中文短标签 + aria-label）。
- 权衡：纯文案改动，成本低。
- 验收：页面内不再出现“Search / server ok / Imported documents”等孤立英文标题；tab 名称与页面标题一致。

### P2（体验打磨与平台能力）

#### P2-1 自适应健康感知

- 目标元素：`App.tsx`、`state.ts`、可选 `health` 端点。
- 改动方向：健康轮询在 degraded 时 5s、正常时 30s；或通过事件推送（SSE/WebSocket）替代轮询。
- 权衡：推送实现成本高于轮询，但降低远端探活负载并缩短感知延迟。
- 验收：模拟后端停止/恢复，UI 在目标时间内反映状态；远端探活频率可配。

#### P2-2 无障碍与响应式

- 目标元素：`App.tsx`、页面组件、`styles.css`。
- 改动方向：nav 增加 `aria-current`/`aria-label`，表单错误 `aria-describedby`，焦点样式齐全；增加 `@media` 断点与小屏布局。
- 验收：Tab 键可完成核心流程；320px 宽下无横向溢出；`axe` 扫描无阻塞错误。

#### P2-3 效率型交互

- 目标元素：各页面。
- 改动方向：拖放/批量导入、搜索历史、快捷跳转（导入后可直接去 Search）、浏览过滤条件持久化。
- 验收：高频路径（导入→检索→浏览）点击次数显著下降；可提交自动化用例。

#### P2-4 Settings 分区与 HA 可编辑

- 目标元素：`SettingsPage.tsx`、`ha.py`（可选）。
- 改动方向：Settings 分区/折叠导航；HA 参数从只读升级为可编辑持久化（需新增 schema，作为独立 C/G 迭代处理）。
- 验收：长页面可导航；HA 修改后重启生效并显示在总览。

#### P2-5 打包预检与自动化

- 目标元素：`server-manager.ts`、`desktop/README.md`、electron-builder。
- 改动方向：启动前预检 Python/Ollama/端口并给出诊断；为打包产物增加运行时检测；用 Electron 自动化（如 Playwright for Electron）覆盖核心流程。
- 验收：无 Python 环境时给出可操作安装指引；CI 可跑核心 UI 冒烟。

## 8. 实施顺序建议

1. P0-1/P0-2/P0-3 作为“UX 可读性”迭代（建议独立 G 类）。
2. P1-1/P1-2/P1-3/P1-4/P1-5 作为“配置与反馈架构”迭代（涉及新增 schema 端点/状态机拆分，建议独立 C 类并出具评估报告）。
3. P2 项按需求热度分批：P2-2/P2-3 可并行；P2-4 涉及 schema 变更必须按 `docs/PROCESS.md` 升级条件评估；P2-5 属工程化能力。

## 9. 验收对照

- [x] 质量属性效用树含 L/M/H 优先级与 ATAM 场景
- [x] 当前架构方法清单标注属性覆盖
- [x] 敏感点 7 项、权衡点 8 项、风险 7 项、非风险 5 项
- [x] P0/P1/P2 每项含目标元素、改动方向、权衡、验收
- [x] 零生产代码改动；feature/progress/evaluator/session-handoff 同步
