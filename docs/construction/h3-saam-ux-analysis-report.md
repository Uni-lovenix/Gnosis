# H3 SAAM UX/UI 分析报告（灵知 Gnosis）

> 类别：H（harness / 文档迭代）。本报告只做评审，不实施 UI 修复；建议作为后续迭代输入。

## 1. 方法与范围

### 1.1 方法：UX 化 SAAM

沿用经典 SAAM（Scenario-based Architecture Analysis Method）的场景驱动结构，把评审对象从“整体软件架构”收窄为 **UI/UX 架构元素**：

1. 定义场景集（已协商为全流程基线 7 场景）。
2. 判定每个场景的当前支持方式：**直接支持 / 间接支持 / 未支持**。
3. 将场景映射到架构元素，并记录代码引用与运行时证据。
4. 分析场景交互与共享资源（全局状态机、健康轮询、确认对话框、toast 等）。
5. 按质量属性评估：可用性（有效性/效率/可学习性/错误恢复）、体验（满意度/信任/反馈及时性）、界面（清晰/一致/可达性/响应式）。
6. 输出问题、风险、P0/P1/P2 建议与结论。

### 1.2 范围与目标用户

- 范围：`desktop/` 渲染层、状态机、IPC/API、相关后端端点与进程；不改生产代码。
- 目标用户画像：混合用户（个人知识库日常使用 + 配置/运维操作），权重均衡。
- 质量属性权重：S1-S5 更看重日常可用性与反馈及时性；S6-S7 更看重配置/运维效率与状态可见性。

## 2. 架构元素清单

| 元素 | 位置 | 说明 |
|---|---|---|
| 应用外壳 | `desktop/src/renderer/App.tsx:46-93` | header、状态点、5 个 tab、降级横幅、全局错误层 |
| 全局状态机 | `desktop/src/renderer/lib/state.ts:15-157` | idle/uploading/indexing/completed/searching/error；健康轮询与进度订阅 |
| 页面 | `desktop/src/renderer/pages/*.tsx` | Import / Search / Browse / Documents / Settings |
| IPC/API | `desktop/src/preload/index.ts:8-42`、`desktop/src/main/index.ts:225-286`、`desktop/src/main/api-client.ts` | KBAPI、ipcMain.handle、pollTask 进度桥 |
| 进程生命周期 | `desktop/src/main/server-manager.ts` | 拉起 Python 子进程、5s 心跳、3 次失败重启 |
| 样式系统 | `desktop/src/renderer/styles.css` | 深色主题、按钮/表格/toast/进度/阶段标签；无 `@media` 响应式规则 |
| 后端契约 | `server/app/api/*` | health、files/tasks、search、chunks、datasources、backups、failover、settings/ha |

## 3. 运行时取证说明

### 3.1 隔离环境

```bash
KB_DATA_DIR=/tmp/gnosis-saam-data
KB_BACKUP_DIR=/tmp/gnosis-saam-backups
KB_EMBED_BACKEND=mock-hash
KB_BACKUP_AUTO=false
KB_HEALTH_MONITOR=false
HOME=/tmp/gnosis-saam-home
KB_DEBUG_RENDER=1
```

先 `npm --prefix desktop run build`，再启动 Vite dev server 与 Electron；通过 CDP（端口 9223）驱动页面并截图。样例数据：`README.md`（5 chunks）、`/tmp/gnosis-saam-large.md`（1391 chunks）、`/tmp/gnosis-saam-bad.xyz`（触发 415 失败）。

### 3.2 证据清单

截图存放于 `/tmp/gnosis-saam-evidence/`，未提交到仓库：

| 文件 | 场景/状态 |
|---|---|
| `01-search-empty.png` | 默认 Search 空状态 |
| `02-import-idle.png` | Import 空闲 |
| `03-import-history.png` | 导入历史 |
| `04-documents-list.png` | Documents 列表 |
| `05-search-results.png` | 检索有结果 |
| `06-search-no-results.png` | 检索无结果（无提示文案） |
| `07-browse-overview.png` / `08-browse-filtered.png` / `09-browse-metadata.png` | Browse 总览/过滤/元数据 |
| `10-settings-top.png` / `11-settings-test.png` / `12-settings-saved-active.png` | Settings 表单/测试/保存与 active |
| `13-settings-ha.png` / `14-settings-failover.png` / `15-settings-backup.png` | HA/failover/backup |
| `16-import-progress-01-排队中.png` / `16-import-progress-02-完成.png` | 导入进行中与完成（事件日志展开） |
| `17-import-failed-banner.png` | 导入失败全局错误横幅 |
| `19-server-unreachable.png` | 后端不可达首屏 |

运行时观察记录：

- 导入 2.8MB Markdown：`排队中 (10%) → 完成 (100%)`，事件日志含 parsing/chunking/embedding/writing/done 共 7 条，最终 “indexed 1391 chunks”。
- 导入 `.xyz`：服务端返回 `415 unsupported file type: .xyz`，渲染层显示全局错误横幅 “Import failed: ... unsupported file type: .xyz” + dismiss。
- 删除确认：CDP 捕获到 `Delete document b206a3aaf6f8498b? This removes the local catalog entry only.`。受 macOS 屏幕录制权限限制，原生 confirm 弹窗本身无法截屏，报告以 CDP 弹窗文案 + `04-documents-list.png` 作为证据。
- Browse 在默认 memory/vector 数据源下返回 `501 chunk_list`，页面显示永久 warning 横幅；React StrictMode 导致同一次挂载重复请求并产生重复 error toast（运行日志可见两次 501）。
- 后端停止后重载渲染页：header 变 `server unreachable`，顶部出现 `Server unreachable: Error: Error invoking remote method 'kb:health': TypeError: fetch failed` + dismiss。

## 4. 场景分析

### S1 首次启动与降级识别

**场景描述**：用户第一次打开应用，后端/Ollama/数据源可能未就绪；需要在 30 秒内理解当前状态并知道下一步。

**前置条件**：全新环境或依赖缺失。

**操作路径**：启动应用 → 观察 header/横幅 → 判断 server/embedder/datasource 状态 → 采取措施。

**成功标准**：30 秒内能判断状态并知道下一步（启动 Ollama、配数据源等）。

**支持方式**：直接支持（header 状态 + 降级横幅 + 错误横幅 + server-manager watchdog）。

**架构元素映射**：`App.tsx:46-79`（状态点、横幅、错误层）、`state.ts:90-100`（健康检查）、`server-manager.ts`（自动重启）。

**证据**：`19-server-unreachable.png`；`App.tsx:59-74`（degraded 文案）；`App.tsx:48-50`（server ok/unreachable）。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P1 | 不可达文案是原始 IPC 错误（`Error invoking remote method 'kb:health': TypeError: fetch failed`），混合用户无法理解，也没有“启动 Ollama / 检查端口 / 看 RUNBOOK”等下一步指引 | `state.ts:98`；运行时 19 截图 |
| P1 | 首次启动无 onboarding/引导，用户不知道要先配数据源、先启动 Ollama、或哪些能力是可选 | `App.tsx:46-93` 无引导元素 |
| P2 | degraded 横幅是嵌套条件文案，可能显示 “dependencies degraded” 或 “no active datasource”，仍缺“怎么修” | `App.tsx:63-71` |
| P2 | 健康轮询间隔 15s，状态感知有延迟；服务恢复后错误横幅不会自动消失（成功分支不清除 error state） | `App.tsx:40`；`state.ts:90-100` |

### S2 数据源配置与激活

**场景描述**：新增/编辑/测试/保存/激活/热切换数据源（memory/ES/PG/MySQL/Milvus），options 以 JSON 编辑。

**前置条件**：打开 Settings 页。

**操作路径**：填写 name/type → 编辑 options JSON → Test connection → Save as new config → Activate 或 Switch now。

**成功标准**：不查文档也能完成一次连接测试与激活；错误信息可操作。

**支持方式**：直接支持（完整 CRUD + test + activate + switch）。

**架构元素映射**：`SettingsPage.tsx:26-350`、`preload/index.ts:15-22`、`api-client.ts:114-205`、`datasources.py` CRUD/active/switch。

**证据**：`10-settings-top.png`、`11-settings-test.png`、`12-settings-saved-active.png`；运行中成功保存 `vec-local`、激活、热切换数据源配置。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P1 | options 必须手写 JSON，无 per-type 模板/字段校验；JSON 非法只提示 “options JSON is invalid”，不指出字段问题 | `SettingsPage.tsx:26, 84-91, 111-112, 128-129` |
| P1 | 配置表单直接暴露密码等敏感值（textarea 明文），本地应用场景下仍有误触与泄露风险 | `SettingsPage.tsx:282-290` |
| P2 | Test connection 结果是无结构文本（`OK latency=0.61ms`），且 `mark_tested` 后端实现无 UI 调用方，`last_tested_at` 永远为空 | `SettingsPage.tsx:121`；`session-handoff.md` 已记录该死代码 |
| P2 | Activate（下次启动生效）与 Switch now（立即热切换）语义容易混淆，仅靠一小段 help 解释 | `SettingsPage.tsx:153-175, 304-309` |

### S3 文件导入与进度反馈

**场景描述**：导入 Excel/Word/PDF/Markdown，看到阶段进度与事件日志，成功/失败可判断。

**前置条件**：后端与数据源就绪。

**操作路径**：Import tab → 选择文件 → 观察进度条/阶段 tag/事件日志 → 确认完成或失败。

**成功标准**：清楚看到阶段进度、成功或失败原因，失败后可恢复。

**支持方式**：直接支持（进度条 + 7 阶段 + 事件日志 + 失败保留）。

**架构元素映射**：`ImportPage.tsx:142-186`、`state.ts:52-125`、`main/index.ts:230-286`（pollTask 进度桥）、`styles.css:467-512`（进度/阶段样式）。

**证据**：`16-import-progress-01-排队中.png`、`16-import-progress-02-完成.png`、`17-import-failed-banner.png`；运行时导入 1391 chunks 的事件链完整。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P1 | 导入失败显示在**全局错误横幅**（`Import failed: ...`），而非导入上下文内；用户切页后丢失失败上下文，事件日志也不展示失败事件 | `state.ts:122-123`；`17-import-failed-banner.png` |
| P2 | 同一时间只能导入一个文件，按钮禁用但没有队列或“等待原因”说明 | `ImportPage.tsx:118-121` |
| P2 | 小文件/快速流水线时中间阶段一闪而过，用户主要靠事件日志补看；无动画或阶段时间线 | 运行时仅捕获到 queued→done 两帧 |
| P2 | 文件选择器允许 `doc`，但解析器实际覆盖未验证；无“支持格式”交互式引导 | `main/index.ts` 的 `pickFile` filters |

### S4 知识检索

**场景描述**：输入问题，查看命中、评分、可读文本；空查询/无结果有合理反馈。

**前置条件**：已导入知识。

**操作路径**：Search tab → 输入 → 提交 → 查看结果。

**成功标准**：3 次尝试内找到目标知识，能理解相关性并知道下一步。

**支持方式**：直接支持（基础检索与结果列表）。

**架构元素映射**：`SearchPage.tsx:9-35`、`state.ts:127-140`、`api-client.ts:221-234`。

**证据**：`05-search-results.png`、`06-search-no-results.png`（无结果时页面只有输入框，无提示）。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P1 | 无结果/空状态没有任何提示，用户无法区分“没有数据”“没有匹配”“还在加载” | `SearchPage.tsx:28-35`；`06-search-no-results.png` |
| P1 | 结果只展示 score + 400 字文本，无文档名、来源、时间、metadata；用户难以判断结果来自哪里 | `SearchPage.tsx:29-34`；`shared/types.ts` Hit 字段 |
| P2 | 页面标题与 placeholder 为英文（`Search`、`Ask your knowledge base...`），与 Import/Documents 等页面中文标题混用 | `SearchPage.tsx:13, 23` |
| P2 | 检索错误走全局横幅，Search 页内无错误态；结果不会因切换 tab 清空，状态语义不透明 | `state.ts:137-138` |
| P2 | 无 query highlighting、无分页、无二次筛选；大量结果时效率低 | `SearchPage.tsx:28-35` |

### S5 数据浏览与排查

**场景描述**：按文档/解析器浏览 chunks、查看元数据，理解 active 数据源能力限制。

**前置条件**：active 数据源支持 `chunk_list`；否则应明确告知并给迁移路径。

**操作路径**：Browse tab → 看 active 数据源与 capability → parser/document_id 过滤 → 聚合表 → 分页 → 展开 metadata。

**成功标准**：能定位指定数据，识别 active 数据源能力限制。

**支持方式**：直接支持（capability-gated）；默认 memory/vector 下实际为“能力缺失 + warning 横幅”。

**架构元素映射**：`BrowsePage.tsx:143-275`、`api-client.ts:236-260`、`chunks.py`、`datasources/base.py` capabilities。

**证据**：`07-browse-overview.png`、`08-browse-filtered.png`、`09-browse-metadata.png`；运行时日志确认 memory/vector 返回 501 并重复触发错误 toast。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P2 | 默认 memory/vector 数据源下 Browse 永久显示 “does not support chunk_list; see RUNBOOK §3”，但应用内没有迁移指引 | `BrowsePage.tsx:155-161`；运行时 501 日志 |
| P2 | document_id 过滤需要用户手输不透明 ID；聚合表点击可缓解，但无文档列表选择器 | `BrowsePage.tsx:129-133, 181-189` |
| P2 | metadata 以 JSON 原样展示，普通用户可读性差；无搜索/高亮 | `BrowsePage.tsx:267-270` |
| P2 | 页面提示“restart the desktop after changing active datasource”，与 Settings 的 Switch now 语义并存，容易造成困惑 | `BrowsePage.tsx:143-147` |

### S6 运维与故障恢复

**场景描述**：备份、恢复、failover、健康监控、HA 参数查看；破坏性操作有确认，过程有状态反馈。

**前置条件**：Settings 页可用，后端已配置。

**操作路径**：Settings → Backup & Restore / Failover order / HA Configuration / Saved configs。

**成功标准**：破坏性操作有确认，操作过程有状态反馈，失败可诊断。

**支持方式**：直接支持（toast + confirm + 只读 HA 表 + 备份/恢复 + failover）。

**架构元素映射**：`SettingsPage.tsx:187-248, 352-437`、`api-client.ts:106-205`、backups/failover/ha 端点。

**证据**：`13-settings-ha.png`、`14-settings-failover.png`、`15-settings-backup.png`；运行时创建备份成功并列出快照。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P1/P2 | 删除/恢复使用原生 `window.confirm`，样式与页面不一致、阻塞渲染进程且难以自动化/可访问性差；恢复提示虽说明“server will stop and restart”，但无进度指示 | `DocumentsPage.tsx:31`；`SettingsPage.tsx:188, 213`；删除弹窗 CDP 文案 |
| P2 | HA 参数只读，用户看到参数后不知道如何修改（需 `KB_*` env 并重启） | `SettingsPage.tsx:352-375` |
| P2 | failover 顺序是逗号分隔自由文本，无下拉选择/校验；保存后自动过滤无效名，用户可能没意识到 | `SettingsPage.tsx:229-238, 383-396` |
| P2 | 备份恢复成功信息是技术路径（`pre-restore kept at ...`），缺少“数据已恢复，可检查检索”的下一步 | `SettingsPage.tsx:216-220` |

### S7 长期使用效率

**场景描述**：高频用户快速完成导入→检索→浏览，状态保留合理、信息密度一致。

**前置条件**：已熟悉基本操作。

**操作路径**：反复在 5 个 tab 间切换，重复导入、检索、过滤、配置。

**成功标准**：重复任务步骤少、状态保留合理、信息密度与一致性可接受。

**支持方式**：间接支持（核心流程可用，但需要多次点击与手工操作，缺少效率型交互）。

**架构元素映射**：`App.tsx:28-92`（tab 切换）、各页面表单、`styles.css`（无响应式媒体查询）。

**证据**：`01-15` 各页面截图；`styles.css` 中无 `@media`；nav 为纯文本小按钮。

**问题**：

| 严重度 | 问题 | 依据 |
|---|---|---|
| P2 | 无键盘快捷键、无拖放导入、无批量导入、无搜索历史；高频重复任务步骤多 | `ImportPage.tsx:118-141`；`SearchPage.tsx:9-35` |
| P2 | tab 标签用英文小写（import/search/...），页面标题中英混用；界面语言一致性差 | `App.tsx:52-56`；各页面标题 |
| P2 | 窗口固定 1100x760，样式无 `@media` 响应式规则；小屏/缩放场景可能出现溢出或挤压 | `main/index.ts:289-299`；`styles.css` |
| P2 | Settings 页是超长单页，表单/表格/HA/failover/backup 无分组导航或折叠 | `SettingsPage.tsx:250-447` |
| P2 | 可访问性缺口：nav 按钮无 aria-label/aria-current，图标按钮无 tooltip，表单错误无 aria-describedby | `App.tsx:51-57`；`styles.css` |

## 5. 场景交互与共享资源分析

1. **全局单状态机覆盖**：`AppState` 只有一个 `kind` 字段，搜索错误、导入错误、健康错误会互相覆盖；例如健康失败会清掉搜索上下文（`state.ts:15-41, 90-100, 127-140`）。导入失败状态也无法与全局错误共存，切页即丢失（`ImportPage.tsx:95-107`）。
2. **健康轮询与页面加载并发**：App 启动同时触发 health + listDatasources，Settings 挂载又并行 4 个请求，Browse 挂载再并行 active + catalog；错误分别落在全局 banner / 页面 toast，无统一错误聚合（`App.tsx:31-42`、`SettingsPage.tsx:40-82`、`BrowsePage.tsx:50-66`）。
3. **React StrictMode 双重副作用**：开发模式挂载两次导致 Browse 首次请求重复，501 错误 toast 出现两次（运行日志实测），用户会看到重复错误。
4. **原生 confirm 阻塞**：`window.confirm` 同步阻塞渲染进程，CDP 无法在弹窗打开时截图；对自动化测试与无障碍都是障碍。
5. **状态保留策略不一致**：Search 结果保留在全局 state，Browse 过滤条件保留在页面内，Settings 表单在切页后重置；没有统一的状态恢复规则。

## 6. 风险评估

| 风险 | 等级 | 描述 |
|---|---|---|
| 配置错误高发 | 高 | options 自由 JSON + 无模板校验，混合用户容易写错导致数据源不可用 |
| 检索反馈缺失 | 高 | 无结果/加载/空数据无区分，用户可能误判“知识库坏了” |
| 误操作破坏数据 | 中 | 删除/恢复用原生 confirm，技术文案 + 阻塞交互，存在误恢复/误删风险 |
| 错误上下文丢失 | 中 | 导入/搜索/健康错误共用全局 banner，跨页面不可追溯 |
| 能力缺口不透明 | 中 | Browse 对默认数据源 501，用户只能看 RUNBOOK 再理解迁移路径 |
| 品牌与信任 | 中 | 中英文混用、无响应式、无引导，影响“本地个人知识库”定位的完成度 |
| 可访问性/自动化 | 低-中 | 无 aria、无键盘快捷键、原生 dialog 不可自动化，阻碍后续验收与辅助技术使用 |

## 7. 建议（后续迭代输入）

### P0（体验验收前应处理）

1. Search 补齐空查询/加载/无结果/错误四态，结果项展示来源文档与 metadata。
2. 服务不可达与导入失败改为用户可读文案，并给下一步指引（启动 Ollama、检查端口、查看 RUNBOOK、重试）。
3. 导入失败保留在 Import 页面上下文内，事件日志记录失败事件，而非只靠全局 banner。

### P1（下个 UX 迭代）

4. 数据源配置改为 per-type 表单模板 + 字段校验，保留高级 JSON 编辑；接通 `mark_tested` 并结构化展示测试结果。
5. 删除/恢复改为应用内确认对话框，恢复过程给进度与结果反馈。
6. Browse 能力缺失时给应用内迁移指引（RUNBOOK 章节链接或摘要），document_id 提供下拉/选择器。
7. 全界面语言一致性整理：中文为主，技术名词保留英文。

### P2（体验打磨）

8. 键盘快捷键、拖放/批量导入、搜索历史、过滤条件持久化。
9. 响应式布局与可访问性（aria-label、aria-current、焦点样式、图标 tooltip）。
10. Settings 分区折叠/导航，HA 参数后续做成可编辑持久化。
11. 健康状态文案简化，错误横幅提供“如何恢复”而非纯状态描述。

## 8. 结论

当前桌面端具备完整功能闭环（导入、检索、浏览、配置、运维），架构边界清晰，状态与反馈机制已经“有”；但按混合用户视角，UX/UI 仍处于**功能优先、体验未收口**状态：错误文案偏技术、自由 JSON 门槛高、搜索缺状态、语言不一致、无响应式与可访问性设计。

SAAM 分类结果：S1-S6 均为直接支持，S7 为间接支持；不存在完全未支持的场景。主要风险集中在**反馈可理解性、配置可学习性、错误上下文连续性**三个维度，属于可在现有架构内通过 UI 迭代收敛的问题，不涉及破坏性接口变更。

## 9. 验收对照

- [x] 7 个场景均含描述、前置、路径、成功标准、支持分类、映射、证据、问题与严重度
- [x] 代码引用可 grep 命中；截图非空且记录于 `/tmp/gnosis-saam-evidence/`
- [x] 运行时观察含实际命令与结果（隔离 env、CDP、导入/失败/不可达）
- [x] 未修改生产代码、公共 API、类型或 schema
- [x] 删除确认原生弹窗无法截屏，已如实记录限制并保留 CDP 弹窗文案证据
