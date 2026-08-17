# 评审评分表 -- 灵知 (Gnosis)

## 当前评审上下文

- 当前 RUP 阶段：移交后增量（transition 已通过）
- 当前评审对象：G1-G18 goal 迭代 + H1-H2 harness 同步 + C9-C17 高可用基础能力 + **G18 HA 配置总览**，累计状态
- 评估者：评估者
- 评审时间：2026-08-18T00:00:00.000Z
- 取证方式：所有数值均为实测（`pytest` / `tsc` / `vite build` / `node --test` / 仓库 grep），非历史抄录
- 修订记录：H1 轮补齐自 T1 悬空 7 轮的双层可观测性评分；H2 轮在过程政策确立后重评过程可观测性维度；C10 轮运行时可观测性 4 → 5；C11-C17 补齐备份/恢复/热切换/自动备份/健康监控/failover/回切/迁移；G18 轮首次实践 H2 自验政策，过程可观测性 4 → 5

## 评分规则

- **5 分**：满足全部验收证据，无需修订。
- **4 分**：核心满足，仅存在少量非阻塞打磨项。
- **3 分**：核心基本满足，需要计划内修订并复审。
- **2 分**：存在明显缺口，验收前必须修订。
- **1 分**：存在阻塞问题，当前不可验收。

## 评分维度

| 维度 | 问题 | 分数 (1-5) | 备注 |
| --- | --- | --- | --- |
| 正确性 | 实现行为是否符合目标 + 协议？ | 5 | 全部 4 个需求（多数据源 / 文件导入 / embedding / 持久化检索）落地；G4 真实 ES 9.5 + G3 真实 bge-m3 端到端可跑 |
| 验证 | 要求的检查是否真的跑过 + 留证？ | 5 | 实测 pytest **193 passed**；tsc 0 errors；Vite build 167.56 kB；eval:mock 9/10；desktop node --test 2 passed |
| 范围纪律 | 各轮是否基本保持在选定功能范围？ | 5 | C1-C17 + G1-G18 + H1-H2 全部单一主题，未越界 |
| 可靠性 | 重启或重跑后是否继续工作？ | 5 | SQLite 幂等 + v1 schema 自动迁移（老库不丢数据）；mock embedder 自动降级；子进程 watchdog；一致性备份 + restore + `.pre-restore` 回退；active 热切换；自动备份；运行期健康监控；健康驱动自动 failover + 恢复回切；数据源迁移 dump/load |
| 可维护性 | 代码与文档是否清楚到下一会话可继续？ | 5 | 模块边界清晰；README/API/RUNBOOK/KNOWN_ISSUES 完整 |
| 交接准备度 | 新会话只靠仓库工件能继续推进？ | 5 | `session-handoff.md` 给出精确 next steps；H1 修复了滞后 6 轮的三份 harness 文件，H2 修复了停在 `inception` 的 `docs/PROCESS.md`，新会话读到的基线已与实测一致 |
| **运行时可观测性** | 关键路径的日志 / 追踪 / 进程事件 / 健康检查是否齐备并留证，回答"系统做了什么"？ | **5** | 详见下方取证 |
| **过程可观测性** | 本轮迭代的计划 / 评分标准 / 验收条件是否对齐且可追溯，回答"为什么这个变更应该被接受"？ | **5**（H1 时 3，H2 政策确立后 4，G18 实践后 5） | 详见下方取证 |

## 双层可观测性取证（本轮补分依据）

这两个维度自 T1 起标注"新增，待下一轮迭代评分"，此后 G1-G7 七轮均未补。本轮基于仓库实测补分。

### 运行时可观测性 = 5 / 5（C10 轮 4 → 5）

按 `CLAUDE.md` 定义的四项子能力逐条核对：

| 子能力 | 状态 | 证据 |
| --- | --- | --- |
| 日志 | ✅ 强 | structlog JSON（timestamp/level/event/message）；19 类结构化事件 + C10 新增 `http.request` / `http.request_failed` / `health.readiness_degraded` 在 `server/app/` 下 grep 命中 |
| 健康检查 | ✅ 强 | `/v1/health` 返回 `degraded / embedder_backend / embedder_fallback / active_datasource / uptime_seconds`；`/v1/health/ready` 带 15s TTL 探活 datasource + embedder（`tests/api/test_health_api.py` 4 项） |
| 进程事件 | ✅ | desktop `server-manager.ts` 5s 心跳 + 3 次 ping 失败自动重启；`node --test scripts/test-server-manager.cjs` 2 passed（实测 30.8s，含真实重启等待） |
| 追踪 | ✅ 强 | `server/app/api/middleware.py` 生成/透传 `X-Request-Id`，structlog contextvars 绑定 `request_id / method / path`，所有响应头回写；`http.request` 日志与业务日志共享同一 id（`tests/test_request_context.py` 2 项）；所有 API 路径（health / datasource / files / search / chunks）都经过中间件，不再只覆盖 import |

**给 5 分的理由**：四项子能力（日志 / 健康检查 / 进程事件 / 追踪）全部有实现、有测试、有留证；健康检查从“存活”扩展为“存活 + 降级快照 + 依赖就绪”，追踪不再为零。C10 还补了数据目录一致性备份（`tests/test_backup.py` 3 项），把“可恢复”从口头能力变成可执行命令。

### 过程可观测性 = 4 / 5（H1 评 3，H2 政策确立后重评）

**H1 时评 3 分的两条依据**：`docs/construction/` 有 c1-c7 评估报告 7 份但 **G1-G7 零评估报告**；迭代协议只有 c1-c7 + g5/g6/g7 共 10 份，**G1-G4 四轮缺失**。当时判定"这不是打磨项，是流程环节缺失"。

**H2 的处理**：根因不是"忘了写"，而是 `docs/PROCESS.md` **从未规定过 goal 系列要不要写**——它只说"每个迭代开始前必须制定迭代协议"，对评估报告的适用范围只字未提，且自身停在 `当前阶段：inception`。H2 确立明文政策而非回溯补文档（用户决策）。

| 子能力 | H1 状态 | H2 后状态 | 证据 |
| --- | --- | --- | --- |
| 验收条件 | ✅ | ✅ | `feature_list.json` 31/31 条目 `evidence` 均非空（H2 修复了 5 处因重复键而失效的 evidence，见下方偏差表）；`progress.md` 每轮留可复核数值 |
| 计划（迭代协议） | ⚠️ G1-G4 缺失 | ✅ 规则明确 | `docs/PROCESS.md` §迭代分类：三类迭代**均必须**有协议；G1-G4 显式追认、不回溯；H2 自身已产出协议 |
| 评分标准（评估报告） | ❌ G1-G7 全缺 | ✅ 规则明确 | C 类必须、G/H 类免除并写明论据；四条**客观可判定**的升级触发条件（破坏性接口变更 / schema 迁移 / 新增数据源或 embedder 后端 / 安全边界） |
| 评分表自身时效 | ❌ 滞后 6 轮 | ✅ 已修复 + 立规 | H1 同步到 G7；H2 立"连续两轮未同步即判不合格""新增维度不得长期挂待评分"两条约定；C10 轮已同步 |
| 记录口径 | ❌ 136 vs 144 漂移 | ✅ 已固化 | `docs/PROCESS.md` §记录口径约定：测试数以 `npm run test:unit` 为准（带 Milvus Lite URI）；包体积带前值与差值 |

**给 4 分而非 5 分的理由**（两条，均为事实而非保守）：

1. **政策尚未被实践检验**。H2 确立的"自验四项最低要求"和四条升级触发条件，至今没有任何一轮 G 类迭代在其约束下跑过。规则写得清楚 ≠ 规则可执行——下一轮 G 类迭代收尾时才能验证它是否真的可判定。
2. **G1-G4 协议与 G1-G7 评估报告仍然不存在**。追认是一个**有记录、有论据的主动选择**（不是遗漏），但工件本身确实缺失；若日后需要回溯审计 G2 的数据源 CRUD 为何那样设计，只能读 `progress.md` 的自述，没有第二方视角。

**不再判 3 分的理由**：3 分的定义是"需要计划内修订并复审"。修订已完成——规则缺位这个根因已被消除，且消除方式经过论证（免除项写明了为什么 G 类的可执行断言比追述性报告更难造假）、边界清晰（四条升级条件把高风险改动挡在自验之外）、不留隐性欠账（G6 命中升级条件这一事实已留档为判例）。

## 本轮实测与既有记录的偏差

| 项 | 记录值 | 实测值 | 判定 |
| --- | --- | --- | --- |
| pytest | 136 passed（G7 记录） | **144 passed** | 记录偏低 8。差值恰等于 `tests/datasources/test_milvus_adapter.py` 的 8 项——记录时该文件应处于 skip 状态（conftest 在 Milvus 不可达时 skip），本轮 Lite 路径全跑。非回归，已在 `progress.md` / `session-handoff.md` 注明，并在 H2 固化为记录口径约定 |
| `docs/PROCESS.md` 阶段状态 | `当前阶段：inception`；细化/构建/移交均 `待进入` | 实际已全部通过，且在增量段 | H1 未覆盖到该文件（只查了 4 份根级 harness 文件），H2 修正。这是本次整理中**滞后最严重**的一份 |
| `feature_list.json` 的 5 处 evidence | 原始文件中 `feat-construction-1`…`-4` 与 `feat-transition-handoff` 各有**两个 `evidence` 键**：真实内容在前、空字符串在后 | 按 JSON 语义后者覆盖前者，这 5 项的 evidence 对**任何标准解析器**都是空 | **H2 新发现的潜在缺陷**。此前所有"evidence 齐备"的判断都是基于肉眼看原始文本，而工具链读到的是空值——过程可观测性的证据链在这 5 项上实际是断的。H2 已去重并保留真实内容，21/21 条目 evidence 均非空且可被解析器读到 |
| 其余（tsc / build / eval / 19 类日志事件） | — | 全部对上 | 无偏差 |

## 总体评分

**Overall: 5 / 5**（8 个维度全 5 = 40/40）

功能与验证维度满分且实测可复现；运行时扣分由 C10-C17 关闭，过程政策经 G18 首次实践验证，两个 4 分项全部消除。

## Harness 文件评估

| 文件 | Present | Quality | Notes |
| --- | --- | --- | --- |
| `AGENTS.team.md` | 是 | 5 | 团队规则完整 |
| `agents.json` | 是 | 5 | schema v3 |
| `AGENTS.md` | 是 | 5 | 规则入口 |
| `CLAUDE.md` | 是 | 5 | 规则入口 |
| `feature_list.json` | 是 | 5 | **31/31** = pass（G18 新增 `feat-ha-settings-overview`，evidence 非空） |
| `progress.md` | 是 | 5 | 当前 RUP 状态与下一步；H1 修正 136→144，G18 更新 193 passed / 167.56 kB |
| `session-handoff.md` | 是 | 5 | 完整交接；H1 修正 136→144，G18 更新 Recommended Next Step |
| `quality-document.md` | 是 | 5 | H1 从 G1 基线同步到 G7 实测；G18 更新 HA 配置总览维度 |
| `evaluator-rubric.md` | 是 | 5 | 本表；H1 补齐双层可观测性评分，H2 政策确立后重评过程维度 3 → 4 |
| `clean-state-checklist.md` | 是 | 5 | H1 同步到 G7 实测并暴露 2 项欠账；H2 后两项已由政策解除 |
| `init.sh` | 是 | 5 | 通过 |
| `docs/PROCESS.md` | 是 | 5 | **H2 重写**：新增迭代分类与评估策略 + 记录口径约定；修正此前停在 `inception` 的陈旧状态 |
| `docs/construction/h2-process-policy.md` | 是 | 5 | H2 迭代协议，含 H1 协议补记 |
| `agents/<角色文件>` | 是（7） | 5 | 每角色一文件 |

## 结论

- [x] Accept
- [ ] Revise
- [ ] Block

H1 提出的 Revise 项（过程工件欠账）已由 H2 以确立明文政策的方式关闭；C10-C17 关闭运行时与数据可靠性缺口；G18 作为 H2 政策生效后首个 G 类迭代，验证四项自验要求可判定，过程可观测性 4 → 5。无剩余扣分项。

## Summary

inception / elaboration / construction(×4) / transition 四阶段 + C5-C8 补充收敛 + G1-G18 goal 迭代 + H1-H2 harness 迭代 + C9-C17 高可用基础能力全部闭环。实测 193 passed / tsc 0 errors / Vite 167.56 kB / eval:mock 9/10 / desktop node --test 2 passed，`feature_list.json` 31/31 pass。

H1 补齐了自 T1 悬空 7 轮的双层可观测性评分，H2 确立迭代分类与评估策略并修复 `feature_list.json` 重复键，C9-C17 补齐黑板体系与高可用能力，G18 首次实践 G 类自验并展示 HA 配置总览。总分 **5/5**。

## 后续动作

- 缺失证据：无（偏差项已全部核实并注明）。
- 必须补的修复：无阻塞项。
- 已关闭（H2）：~~为 G1-G7 补评估报告或明确政策~~ → 已在 `docs/PROCESS.md` §迭代分类与评估策略 显式选定"G/H 类走自验"并写明论据；~~约定评分表每轮同步~~ → 已立"连续两轮未同步即判不合格"。
- 待验证（下一轮 G 类迭代收尾时）：H2 的"自验四项最低要求"与四条升级触发条件是否真的可判定。这是过程可观测性从 4 升 5 的唯一前置条件。
- 已关闭（C10）：~~引入 `request_id` 并 `bind_contextvars`~~ → `server/app/api/middleware.py` + `health.readiness_degraded` + `/v1/health/ready` + 备份 CLI 已闭环，运行时可观测性 4 → 5。
- 已关闭（C11）：~~备份只有 CLI 无恢复入口~~ → `restore_backup` + `list_backups` + `/v1/backups` + 桌面 Backup & Restore（停服 → restore → 重启）已闭环。
- 已关闭（C12）：~~active 切换需重启~~ → `POST /v1/datasources/active/{name}/switch` + Settings “Switch now” 已闭环。
- 已关闭（C13）：~~备份依赖手动执行~~ → 服务启动即检查 + 每小时 `backup_if_due` 自动快照已闭环（`KB_BACKUP_AUTO=false` 可关）。
- 已关闭（C14）：~~运行期降级不反映到 /v1/health~~ → 后台探活 + 健康快照 + 桌面 15s 轮询已闭环。
- 已关闭（C15）：~~数据源故障只能手动切换~~ → failover 顺序 + 连续失败自动热切换已闭环。
- 已关闭（C16）：~~failover 后不会自动切回主数据源~~ → 主库恢复连续健康自动回切已闭环。
- 已关闭（C17）：~~数据无法跨数据源复制~~ → `dump_all` + migrate CLI 已闭环（memory / ES）。
- 已关闭（G18）：~~过程政策待实践检验~~ → G18 完成首次 G 类自验，过程可观测性 4 → 5。
- 下次复审触发条件：下一个功能迭代收尾时（届时同步验证 H2 政策的可执行性）。
