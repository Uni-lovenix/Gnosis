# 移交与文档交接（T1）

## 目标

完成最终验收、文档交接与已知问题移交。

## 交付物

| 文档 | 路径 | 说明 |
|---|---|---|
| 顶层 README | `README.md` | 快速开始 + 项目结构 + 验证清单 |
| HTTP API 参考 | `docs/API.md` | 端点、请求、响应、错误码 |
| 运行手册 | `docs/RUNBOOK.md` | 故障、平台差异、回滚 |
| 已知问题 | `docs/KNOWN_ISSUES.md` | KI-01 ~ KI-10 与已缓解项 |
| 进度收尾 | `progress.md` | 全部 `pass` 状态 |
| 跨会话交接 | `session-handoff.md` | 下次会话启动指引 |

## 验收清单

- [x] `bash init.sh` 通过
- [x] `cd server && pytest` 73 passed
- [x] `cd desktop && npx tsc --noEmit -p tsconfig.json` 0 errors
- [x] `cd desktop && node --test scripts/test-server-manager.cjs` 2 passed
- [x] `cd server && PYTHONPATH=. python3 eval/run_eval.py` 9/10 通过
- [x] `feature_list.json` 全部 `pass`

## 结论

- [x] Accept — 全部交付满足 RUP transition 退出标准。
- [ ] Revise
- [ ] Block

## 给下一会话的指引

1. 阅读 `README.md` → `docs/PROCESS.md` → `progress.md`。
2. 看 `docs/KNOWN_ISSUES.md` 与 `docs/RUNBOOK.md`。
3. 选 `feature_list.json` 中下一未完成条目，或针对已知问题新建 `feat-*` 记录。
4. 任何接口变更必须更新 `docs/elaboration/01-architecture-baseline.md` 与对应 API 文档。