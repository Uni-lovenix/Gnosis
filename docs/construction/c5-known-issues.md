# 已知问题修复迭代协议（C5）

> 第二个 RUP 周期的第一个迭代：聚焦 `docs/KNOWN_ISSUES.md` 中已识别但未解决的问题（KI-04 / KI-05 / KI-06）。

## 目标

把遗留的 3 项关键 KI 收敛为可演示的产物：

1. **KI-04** — desktop DocumentsPage 接通真实目录（列表 / 详情 / 删除）。
2. **KI-05** — electron-builder 跨平台打包脚本与 CI 文档。
3. **KI-06** — 真实 BGE-M3 评测可在本机一键复跑（权重下载脚本 + 评测门禁）。

## 范围

### KI-04（桌面端文档目录）

- `desktop/src/main/db.ts`：新增 `getDocument(id)` / `deleteDocument(id)` 方法。
- `desktop/src/shared/types.ts`：`KBAPI` 增加 `listDocuments()` / `getDocument(id)` / `deleteDocument(id)`。
- `desktop/src/main/index.ts`：注册 `kb:listDocuments` / `kb:getDocument` / `kb:deleteDocument` IPC。
- `desktop/src/preload/index.ts`：暴露 3 个新方法。
- `desktop/src/renderer/pages/DocumentsPage.tsx`：替换占位，渲染表格 + 删除按钮 + 错误状态。
- 桌面端类型检查 0 errors。

> **决策**：文档目录以**桌面端 SQLite**为单一来源（已存在），不再新增 Python 侧 `/v1/documents`。原因：Python 服务只关心向量；UI 列表天然属于 Electron 主进程的职责。

### KI-05（electron-builder 打包）

- `desktop/package.json` 增加 `electron-builder` 依赖与 `dist` / `dist:mac` / `dist:win` / `dist:linux` 脚本。
- `desktop/electron-builder.yml`：跨平台产物配置（NSIS / dmg / AppImage）。
- `desktop/README.md`：补充打包章节与平台 note。
- `desktop/scripts/test-server-manager.cjs`：保持 2/2 通过；新增 sanity 校验脚本不强制。

### KI-06（真实 BGE-M3 评测）

- `scripts/download_bge_m3.sh`：本机下载 `BAAI/bge-m3` 到 `server/models/`。
- `server/eval/run_eval.py`：在 `EMBED_BACKEND=bge-m3` 时调用真实模型，保持 mock 路径不变。
- `server/eval/README.md`：补充真实模型下载、显存门槛、门禁阈值（top-1 ≥ 80%）。
- `server/README.md`：注明 `pip install sentence-transformers` 后自动切换。

## 不在范围

- KI-01（OCR）、KI-02（MySQL 性能）、KI-03（重试退避）、KI-07（Milvus 单测）、KI-08（Word 图片/批注）、KI-09（任务表清理）、KI-10（arm64 编译）：保持已知问题记录，下一迭代再处理。
- 自动更新、签名、公网分发。
- BGE-M3 之外的 embedding 模型。

## 交付物

| 交付 | 路径 |
|---|---|
| KI-04 实施 | `desktop/src/main/db.ts` + `desktop/src/main/index.ts` + `desktop/src/preload/index.ts` + `desktop/src/shared/types.ts` + `desktop/src/renderer/pages/DocumentsPage.tsx` |
| KI-05 实施 | `desktop/electron-builder.yml` + `desktop/package.json` + `desktop/README.md` |
| KI-06 实施 | `scripts/download_bge_m3.sh` + `server/eval/run_eval.py` + `server/eval/README.md` + `server/README.md` |
| 验证证据 | `docs/construction/c5-evaluation.md`（评估者产出） |
| 状态更新 | `feature_list.json`、`progress.md`、`session-handoff.md`、`docs/KNOWN_ISSUES.md` |

## 退出标准

- `desktop npm run check` 0 errors；`desktop npm run build` 成功。
- `desktop node --test scripts/test-server-manager.cjs` 2/2 通过。
- `server pytest` 73+ passed（不回归）。
- `server PYTHONPATH=. python3 eval/run_eval.py` mock 9/10；真实 BGE-M3 评测在本机可重跑（产物可选）。
- `bash init.sh` 通过。
- `feature_list.json` 三个新条目 `pass`。

## 风险

- **R-C5-1**：electron-builder 跨平台产物只在 macOS 开发机验证；Windows / Linux 产物 CI 留 placeholder。
- **R-C5-2**：真实 BGE-M3 模型权重 ~2.4GB，CI 不下载；默认仍走 mock 路径。
- **R-C5-3**：删除文档只清理本地 SQLite 元数据，不下钻数据源中的向量（与现状一致，文档化即可）。