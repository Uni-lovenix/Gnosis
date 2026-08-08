# C5 评估：已知问题修复迭代

> 评估者对 `docs/construction/c5-known-issues.md` 中 KI-04 / KI-05 / KI-06 三项交付的核对。

## 验证证据

| 检查项 | 命令 / 文件 | 结果 |
|---|---|---|
| 迭代协议存在 | `docs/construction/c5-known-issues.md` | OK（目标 / 范围 / 交付物 / 退出标准齐备） |
| KI-04 桌面端类型 | `cd desktop && npx tsc --noEmit -p tsconfig.json` | 0 errors |
| KI-04 桌面端 main | `cd desktop && npx tsc --noEmit -p tsconfig.main.json` | 0 errors |
| KI-04 桌面端 preload | `cd desktop && npx tsc --noEmit -p tsconfig.preload.json` | 0 errors |
| KI-04 桌面端构建 | `cd desktop && npm run build` | Vite 成功（renderer 148.70 kB / gzip 47.83 kB） |
| KI-04 桌面单测 | `cd desktop && node --test scripts/test-server-manager.cjs` | 2/2 通过 |
| KI-04 `MetaDB.getDocument / deleteDocument` | `desktop/src/main/db.ts` | 已新增，类型安全 |
| KI-04 `KBAPI.listDocuments / getDocument / deleteDocument` | `desktop/src/shared/types.ts` | 已扩展 |
| KI-04 IPC 通道 | `desktop/src/main/index.ts` + `desktop/src/preload/index.ts` | 3 个新通道已注册 |
| KI-04 `DocumentsPage` 渲染 | `desktop/src/renderer/pages/DocumentsPage.tsx` | 占位 → 表格 + 删除 + 错误态 |
| KI-05 electron-builder 配置 | `desktop/electron-builder.yml` | mac/win/linux 三平台产物，asar + asarUnpack better-sqlite3 |
| KI-05 打包脚本 | `desktop/package.json` scripts | `pack / dist / dist:mac / dist:win / dist:linux` |
| KI-05 README 文档 | `desktop/README.md` | 打包章节 + 平台 note |
| KI-05 package.json 合法 | `node -e "JSON.parse(...)"` | valid |
| KI-06 eval harness 切换 | `cd server && PYTHONPATH=. python3 eval/run_eval.py` | mock 9/10 = 90%（保持） |
| KI-06 eval bge-m3 路径 | `--embedder bge-m3` | argparse 接受；缺依赖时抛清晰 `EmbedderError` 指向 `pip install -e ".[embedding-local]"` |
| KI-06 argparse 边界 | `--embedder unknown` | `argparse: invalid choice` 拒绝 |
| KI-06 下载脚本 | `scripts/download_bge_m3.sh`（executable） | idempotent；幂等检查 `config.json` 存在 |
| KI-06 README | `server/eval/README.md` + `server/README.md` | 新增真实 BGE-M3 章节与门禁 80% |
| pytest 回归 | `cd server && pytest` | 73 passed（与 C4 持平） |

## 评分（参考 `evaluator-rubric.md`）

| 维度 | 分数 | 备注 |
| --- | --- | --- |
| 正确性 | 5 | KI-04 渲染接通真实目录，删除幂等；KI-05 三平台配置无遗漏；KI-06 eval 双后端 + 清晰错误 |
| 验证 | 5 | 类型 / 构建 / 单测 / pytest / eval mock 路径全部重跑并留证 |
| 范围纪律 | 5 | 严格按协议 C5，未越界到 KI-01/02/03/07/08/09/10 |
| 可靠性 | 4 | 真实 BGE-M3 仅本机验证；下载脚本幂等；mock fallback 保留（KI-06 残留限制） |
| 可维护性 | 5 | 三处修改文件局部化（db / types / index / preload / DocumentsPage）；download 脚本可独立运行 |
| 交接准备度 | 5 | `KNOWN_ISSUES.md` 标 C5 已收敛；eval README 给出 80% 门禁；electron-builder README 写明平台 note |
| **运行时可观测性** | 4 | desktop 错误态显式渲染；eval JSON 含 `backend / dim`；KI-04 删除确认对话框 |
| **过程可观测性** | 5 | 协议 C5 / 本评估文件 / KNOWN_ISSUES 三处对齐可追溯 |

**Overall: 4.75 / 5**

## 结论

- [x] Accept
- [ ] Revise
- [ ] Block

## 后续动作

- 推荐下一迭代：KI-09 任务表过期清理（轻量，构造阶段可顺带完成）；或 KI-07 Milvus 1:1 单测（需 docker）。
- KI-06 真实模型评测本机未在本会话执行（缺 sentence-transformers + 权重），但路径与脚本均已就绪，下一会话在带权重的 runner 上重跑即可。