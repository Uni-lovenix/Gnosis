# KB Desktop -- Electron + React + TypeScript

桌面端宿主：拉起 Python 后端、持久化元数据、暴露 IPC 与 React UI。

## 目录结构

```
desktop/
├── src/
│   ├── main/          # Electron 主进程
│   │   ├── index.ts         # 入口、窗口、IPC 注册
│   │   ├── server-manager.ts# Python 子进程 + watchdog
│   │   ├── db.ts            # better-sqlite3 元数据
│   │   └── api-client.ts    # FastAPI HTTP 客户端
│   ├── preload/       # contextBridge 暴露 KBAPI
│   │   └── index.ts
│   ├── renderer/      # React + Vite
│   │   ├── main.tsx, App.tsx
│   │   ├── pages/ (Import/Search/Documents/Settings)
│   │   ├── lib/ (kb, state)
│   │   └── styles.css
│   └── shared/types.ts       # 主/preload/渲染共享类型
├── package.json
├── tsconfig.{json,main,preload}.json
└── vite.config.ts
```

## 开发

```bash
cd desktop
npm install
npm run dev      # 同时 watch main / preload / vite
```

## 打包

### 本地运行（dev）

```bash
npm install
npm run build && npx electron .
```

### 跨平台产物（electron-builder）

打包配置见 `desktop/electron-builder.yml`，产物输出到 `desktop/release/`。
Python 后端**不**打包进 Electron 产物；运行时通过 `KB_PYTHON`（默认 `python3`）
解析解释器，由 `server-manager.ts` 拉起。

```bash
npm install                      # 含 electron-builder
npm run pack                     # 仅打包未签名目录到 release/
npm run dist                     # 当前平台默认目标
npm run dist:mac                 # macOS dmg + zip（x64 + arm64）
npm run dist:win                 # Windows NSIS（x64）
npm run dist:linux               # Linux AppImage（x64）
```

> 平台限制：
> - macOS dmg 必须在 macOS 上构建（Apple 工具链）。
> - Windows NSIS 推荐在 Windows 上构建；Linux 可用 `wine` 交叉编译但未验证。
> - 自动更新与签名留待 KI 后续；当前 `publish: null`。

## 架构边界

- 渲染进程**绝不**导入 `electron` 或 `node:*` 模块，只能用 `window.kb`。
- 主进程负责：
  - 创建 BrowserWindow。
  - 拉起并看护 Python 后端（`server-manager.ts`，5s 心跳、3 次失败自动重启）。
  - 持久化 `documents` / `tasks` 到 SQLite。
  - 通过 `ipcMain.handle('kb:xxx', ...)` 转发到 `ApiClient`。
- IPC 路由只在 preload 注册（`src/preload/index.ts`）。

## 状态机（renderer）

`idle → uploading → indexing → idle` 或 `→ error → idle`

进度由 `kb.onProgress(cb)` 推送，订阅在 `useAppState()` 中。

## 手工 e2e（验收脚本）

1. `cd desktop && npm run dev`
2. 等待窗口出现，header 显示 "server ok"。
3. 切到 **Import**：选择样例 `.md` → 进度条从 5% 到 100%。
4. 切到 **Search**：输入 "embedding" → 列出命中。
5. 切到 **Settings**：测试 vector memory backend → "OK latency < 5ms"。

如果 Python 服务不可达，header 变 "server unreachable"，所有按钮在不可用状态下。

## 平台差异

- macOS / Windows / Linux 共享同一份 TS 代码；打包使用 electron-builder（后续迁移）。
- better-sqlite3 需要 node-gyp；CI 上需装 build-essential。
- Python venv 兼容性：通过 `KB_PYTHON` 环境变量指定解释器，默认 `python3`。