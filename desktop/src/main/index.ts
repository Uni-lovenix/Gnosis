/**
 * Electron main process entrypoint.
 *
 * Responsibilities:
 *  - Create BrowserWindow and load the React renderer.
 *  - Spawn and supervise the Python backend (server-manager.ts).
 *  - Persist documents / tasks in SQLite (db.ts).
 *  - Forward IPC requests from the renderer to the backend.
 */
import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";
import fs from "node:fs";

import { ApiClient } from "./api-client";
import { MetaDB } from "./db";
import { createServerManager } from "./server-manager";
import type {
  ActiveDatasourceResponse,
  DatasourceConfig,
  DatasourceConfigRecord,
  DocumentInfo,
  HealthInfo,
  Hit,
  ImportResponse,
  KBAPI,
  TaskStatus,
} from "../shared/types";

const isDev = !app.isPackaged;
const PROJECT_ROOT = path.resolve(__dirname, "..", "..", "..");
const KB_PORT = Number(process.env.KB_PORT ?? 8765);

// KB_DEBUG_RENDER=1 → open devtools + log renderer console messages to stderr.
// Used to diagnose blank-renderer issues without manual mouse input.
if (process.env.KB_DEBUG_RENDER === "1") {
  app.commandLine.appendSwitch("remote-debugging-port", "9223");
  app.commandLine.appendSwitch("remote-allow-origins", "*");
}

let server = createServerManager({ projectRoot: PROJECT_ROOT, port: KB_PORT });
let api: ApiClient | null = null;
let db: MetaDB | null = null;
let mainWindow: BrowserWindow | null = null;

function ensureDirs(): void {
  const dataDir = path.join(app.getPath("userData"), "kb-desktop");
  fs.mkdirSync(dataDir, { recursive: true });
  return void dataDir;
}

function getDataDir(): string {
  return path.join(app.getPath("userData"), "kb-desktop");
}

function attachIpc(): void {
  const handlers: KBAPI = {
    serverUrl: async () => server.baseUrl,
    health: async () => {
      if (!api) throw new Error("server not ready");
      return api.health();
    },
    listDatasources: async () => {
      if (!api) throw new Error("server not ready");
      return api.listDatasources();
    },
    testDatasource: async (cfg: DatasourceConfig) => {
      if (!api) throw new Error("server not ready");
      return api.testDatasource(cfg);
    },
    listDatasourceConfigs: async (): Promise<DatasourceConfigRecord[]> => {
      if (!api) throw new Error("server not ready");
      return api.listDatasourceConfigs();
    },
    saveDatasourceConfig: async (cfg: DatasourceConfig): Promise<DatasourceConfigRecord> => {
      if (!api) throw new Error("server not ready");
      const saved = await api.saveDatasourceConfig(cfg);
      // Mark as tested only if the user has recently verified this exact config.
      // The IPC layer cannot see the prior test step; the renderer signals
      // completion by calling activateDatasourceConfig below.
      return saved;
    },
    deleteDatasourceConfig: async (name: string) => {
      if (!api) throw new Error("server not ready");
      return api.deleteDatasourceConfig(name);
    },
    getActiveDatasource: async (): Promise<ActiveDatasourceResponse> => {
      if (!api) throw new Error("server not ready");
      return api.getActiveDatasource();
    },
    activateDatasourceConfig: async (name: string): Promise<DatasourceConfigRecord> => {
      if (!api) throw new Error("server not ready");
      return api.activateDatasourceConfig(name);
    },
    deactivateDatasource: async () => {
      if (!api) throw new Error("server not ready");
      return api.deactivateDatasource();
    },
    pickFile: async () => {
      if (!mainWindow) return null;
      const r = await dialog.showOpenDialog(mainWindow, {
        properties: ["openFile"],
        filters: [
          { name: "Documents", extensions: ["xlsx", "xls", "docx", "doc", "pdf", "md", "markdown", "txt"] },
          { name: "All", extensions: ["*"] },
        ],
      });
      if (r.canceled || r.filePaths.length === 0) return null;
      return r.filePaths[0] ?? null;
    },
    importFile: async (filePath: string): Promise<ImportResponse> => {
      if (!api) throw new Error("server not ready");
      const result = await api.importFile(filePath);
      // NOTE: do NOT upsert the document here. The initial ``ImportResponse``
      // is a stub — the server fills in the real ``document_id``, ``parser``,
      // and ``chunks`` once the background pipeline finishes. Writing the
      // stub now would (a) collide on the empty ``document_id`` primary key
      // for every import and (b) record zero-chunks / null-parser rows that
      // never get corrected. ``pollTask`` writes the final row from
      // ``TaskStatus.result`` once the task lands in ``done``.
      void pollTask(result.task_id, filePath);
      return result;
    },
    search: async (query: string, opts?: { top_k?: number; datasource?: string }): Promise<Hit[]> => {
      if (!api) throw new Error("server not ready");
      return api.search(query, opts?.top_k ?? 5);
    },
    browseChunks: async (opts: {
      document_id?: string;
      parser?: string;
      offset?: number;
      limit?: number;
    }) => {
      if (!api) throw new Error("server not ready");
      return api.browseChunks(opts);
    },
    getTask: async (taskId: string): Promise<TaskStatus> => {
      if (!api) throw new Error("server not ready");
      return api.getTask(taskId);
    },
    // onProgress is not an IPC handler here — the renderer listens for
    // ``kb:progress`` events directly via preload's ``ipcRenderer.on``. The
    // main process emits events via ``mainWindow.webContents.send`` inside
    // pollTask(). We keep a stub on the KBAPI shape so the type stays satisfied.
    onProgress: (_cb: (t: TaskStatus) => void) => {
      return () => undefined;
    },
    listDocuments: async (): Promise<DocumentInfo[]> => {
      if (!db) throw new Error("metadata db not ready");
      return db.listDocuments();
    },
    getDocument: async (id: string): Promise<DocumentInfo | null> => {
      if (!db) throw new Error("metadata db not ready");
      return db.getDocument(id);
    },
    deleteDocument: async (id: string): Promise<boolean> => {
      if (!db) throw new Error("metadata db not ready");
      return db.deleteDocument(id);
    },
  };

  for (const [name, fn] of Object.entries(handlers)) {
    ipcMain.handle(`kb:${name}`, (_evt, ...args) => (fn as (...a: unknown[]) => unknown)(...args));
  }
}

async function pollTask(taskId: string, filePath?: string): Promise<void> {
  if (!api) return;
  const startedAt = Date.now();
  const maxMs = 5 * 60_000;
  while (Date.now() - startedAt < maxMs) {
    try {
      const t = await api.getTask(taskId);
      // Forward progress to the renderer across the main/renderer boundary.
      // The previous implementation called an in-process listener Set, which
      // never reached the renderer (KB-Desktop-ProgressBridge).
      mainWindow?.webContents.send("kb:progress", t);
      db?.upsertTask({
        task_id: t.task_id,
        kind: t.kind,
        status: t.status,
        progress: t.progress,
        error: t.error,
        result: t.result ? JSON.stringify(t.result) : null,
        created_at: new Date(startedAt).toISOString(),
        updated_at: new Date().toISOString(),
      });
      if (t.status === "done" || t.status === "failed") {
        // Persist the final document row once the server has the real
        // ``document_id``, ``parser``, and ``chunks``. Using the empty
        // stub ``document_id`` from the initial import response would
        // collide on every import (KB-Desktop-ImportHistoryMissingRow).
        if (
          t.status === "done" &&
          t.result &&
          typeof t.result.document_id === "string" &&
          t.result.document_id &&
          filePath
        ) {
          let size = 0;
          try {
            size = fs.statSync(filePath).size;
          } catch {
            // file may have been moved/deleted between import and completion;
            // fall back to whatever the server reported, or 0 if neither has it.
          }
          db?.upsertDocument({
            id: t.result.document_id,
            source_path: filePath,
            parser: typeof t.result.parser === "string" ? t.result.parser : null,
            size: typeof t.result.size === "number" ? t.result.size : size,
            imported_at: new Date().toISOString(),
            chunks: typeof t.result.chunks === "number" ? t.result.chunks : 0,
          });
        }
        return;
      }
    } catch {
      // transient
    }
    await new Promise((r) => setTimeout(r, 600));
  }
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "..", "preload", "index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  if (process.env.KB_DEBUG_RENDER === "1") {
    mainWindow.webContents.on("console-message", (_e, level, msg, line, srcId) => {
      const tag = ["VERBOSE", "INFO", "WARN", "ERROR"][level] ?? `L${level}`;
      // eslint-disable-next-line no-console
      console.error(`[renderer ${tag}] ${msg} (${srcId}:${line})`);
    });
    mainWindow.webContents.on("did-fail-load", (_e, code, desc, url) => {
      // eslint-disable-next-line no-console
      console.error(`[renderer FAIL_LOAD] ${code} ${desc} ${url}`);
    });
    mainWindow.webContents.on("render-process-gone", (_e, details) => {
      // eslint-disable-next-line no-console
      console.error(`[renderer GONE] ${JSON.stringify(details)}`);
    });
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  if (isDev) {
    await mainWindow.loadURL("http://localhost:5173");
  } else {
    await mainWindow.loadFile(path.join(__dirname, "..", "..", "renderer", "index.html"));
  }
}

app.whenReady().then(async () => {
  ensureDirs();
  db = new MetaDB(path.join(getDataDir(), "metadata.db"));
  await server.start();
  api = new ApiClient(server.baseUrl);
  attachIpc();
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) void createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", async () => {
  await server.stop();
  db?.close();
});