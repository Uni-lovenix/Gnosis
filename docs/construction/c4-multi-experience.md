# 多端体验迭代交付（C4）

> 构造阶段第四个迭代的交付物说明。

## 模块清单

| 模块 | 文件 | 说明 |
|---|---|---|
| 共享类型 | `desktop/src/shared/types.ts` | `KBAPI`、`Hit`、`HealthInfo`、`ImportResponse`、`TaskStatus`、`DatasourceConfig` |
| 主进程入口 | `desktop/src/main/index.ts` | BrowserWindow、IPC 注册、生命周期 |
| 子进程管理 | `desktop/src/main/server-manager.ts` | 拉起 Python 子进程 + 5s 心跳 + 3 次失败自动重启 |
| HTTP 客户端 | `desktop/src/main/api-client.ts` | FastAPI fetch 客户端（multipart 上传、JSON） |
| 元数据存储 | `desktop/src/main/db.ts` | better-sqlite3，documents + tasks 两表 |
| preload | `desktop/src/preload/index.ts` | contextBridge 暴露 `window.kb` |
| 渲染层入口 | `desktop/src/renderer/main.tsx` + `App.tsx` | React 18 + TS + Vite |
| 状态机 | `desktop/src/renderer/lib/state.ts` | `idle / uploading / indexing / searching / error` |
| 4 个页面 | `desktop/src/renderer/pages/{Import,Search,Documents,Settings}.tsx` | 最小可用 |
| 样式 | `desktop/src/renderer/styles.css` | 深色主题 |
| 构建配置 | `desktop/package.json` + 3 个 `tsconfig*.json` + `vite.config.ts` | 多入口构建 |
| 单元测试 | `desktop/scripts/test-server-manager.cjs` | Node test runner |
| README | `desktop/README.md` | dev / build / e2e |

## 架构边界（满足协议）

- **渲染进程** 只用 `window.kb`，**未** 导入 `electron` 或 `node:*`。
- **preload** 是唯一把 IPC 通道暴露到渲染层的位置。
- **主进程** 只做窗口、子进程、SQLite、转发；不持有 UI 状态。
- **文件系统/对话框** 仅主进程持有；渲染层通过 IPC 调用。

## 状态机

```
idle → uploading → indexing → idle
                    ↓
                   error → idle
```

进度由 `kb.onProgress(cb)` 推送到渲染层；订阅在 `useAppState()` 中注册。

## 验证证据

```bash
$ npx tsc --noEmit -p tsconfig.main.json    # 0 errors
$ npx tsc --noEmit -p tsconfig.preload.json # 0 errors
$ npx tsc --noEmit -p tsconfig.json         # 0 errors
$ npx vite build
... 37 modules transformed, 147.73 kB JS gzip 47.57 kB ...
✓ built in 391ms

$ npx tsc -p tsconfig.main.json && npx tsc -p tsconfig.preload.json
# dist/main/{index,server-manager,db,api-client}.js + dist/preload/index.js

$ node --test scripts/test-server-manager.cjs
ℹ tests 2  ℹ pass 2  ℹ fail 0
```

## 手工 e2e 步骤（README 已记录）

1. `cd desktop && npm run dev`
2. 等待窗口出现，header 显示 "server ok"。
3. 切到 **Import**：选 `.md` → 进度条 5% → 100%。
4. 切到 **Search**：输入 "embedding" → 列出命中。
5. 切到 **Settings**：测试 vector memory backend → "OK latency < 5ms"。

服务不可达时 header 显 "server unreachable"，所有按钮进入不可用态。

## 不在范围内（按协议 C4）

- 自动更新、签名、公网分发。
- 移动端。
- 多用户。

## 已知缺口

- DocumentsPage 暂未拉真实列表（需要 main 侧加 `kb:listDocuments` IPC + server 侧 `/v1/documents` 端点）。接口预留，迁移到 transition 阶段补。
- electron-builder 打包脚本未提供（CI 阶段）。
- 跨进程 IPC mock 测试未做（依赖 Electron 运行时）。