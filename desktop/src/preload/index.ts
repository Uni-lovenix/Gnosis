/**
 * Preload script — exposes a minimal, typed KBAPI to the renderer via
 * contextBridge. The renderer NEVER imports node or electron modules directly.
 */
import { contextBridge, ipcRenderer } from "electron";
import type { KBAPI } from "../shared/types";

const api: KBAPI = {
  serverUrl: () => ipcRenderer.invoke("kb:serverUrl"),
  health: () => ipcRenderer.invoke("kb:health"),
  getHaSettings: () => ipcRenderer.invoke("kb:getHaSettings"),
  listBackups: () => ipcRenderer.invoke("kb:listBackups"),
  createBackup: () => ipcRenderer.invoke("kb:createBackup"),
  restoreBackup: (name) => ipcRenderer.invoke("kb:restoreBackup", name),
  listDatasources: () => ipcRenderer.invoke("kb:listDatasources"),
  testDatasource: (cfg) => ipcRenderer.invoke("kb:testDatasource", cfg),
  listDatasourceConfigs: () => ipcRenderer.invoke("kb:listDatasourceConfigs"),
  saveDatasourceConfig: (cfg) => ipcRenderer.invoke("kb:saveDatasourceConfig", cfg),
  deleteDatasourceConfig: (name) => ipcRenderer.invoke("kb:deleteDatasourceConfig", name),
  getActiveDatasource: () => ipcRenderer.invoke("kb:getActiveDatasource"),
  activateDatasourceConfig: (name) => ipcRenderer.invoke("kb:activateDatasourceConfig", name),
  switchDatasourceConfig: (name) => ipcRenderer.invoke("kb:switchDatasourceConfig", name),
  listFailover: () => ipcRenderer.invoke("kb:listFailover"),
  setFailover: (names) => ipcRenderer.invoke("kb:setFailover", names),
  clearFailover: () => ipcRenderer.invoke("kb:clearFailover"),
  deactivateDatasource: () => ipcRenderer.invoke("kb:deactivateDatasource"),
  pickFile: () => ipcRenderer.invoke("kb:pickFile"),
  importFile: (path) => ipcRenderer.invoke("kb:importFile", path),
  search: (query, opts) => ipcRenderer.invoke("kb:search", query, opts),
  browseChunks: (opts) => ipcRenderer.invoke("kb:browseChunks", opts),
  getTask: (taskId) => ipcRenderer.invoke("kb:getTask", taskId),
  listDocuments: () => ipcRenderer.invoke("kb:listDocuments"),
  getDocument: (id) => ipcRenderer.invoke("kb:getDocument", id),
  deleteDocument: (id) => ipcRenderer.invoke("kb:deleteDocument", id),
  onProgress: (cb) => {
    const listener = (_evt: unknown, task: unknown) => cb(task as Parameters<typeof cb>[0]);
    ipcRenderer.on("kb:progress", listener);
    return () => ipcRenderer.removeListener("kb:progress", listener);
  },
};

contextBridge.exposeInMainWorld("kb", api);

export type { KBAPI };
