/**
 * Shared types between main, preload, and renderer.
 * Keep this file dependency-free.
 */

export interface DatasourceInfo {
  name: string;
  type: string;
  capabilities: string[];
}

export interface DatasourceConfig {
  name: string;
  type: string;
  options?: Record<string, unknown>;
}

/**
 * A user-saved named datasource connection config. Persisted on the server
 * side at ``~/.kb-server/datasources.json``. UI calls ``listDatasourceConfigs``
 * to render the saved-list, then ``saveDatasourceConfig`` to upsert by name
 * and ``activateDatasourceConfig`` to mark the entry used on next server start.
 */
export interface DatasourceConfigRecord {
  name: string;
  type: string;
  options: Record<string, unknown>;
  saved_at: string;
  last_tested_at: string | null;
}

export interface ActiveDatasourceResponse {
  name: string | null;
  config: DatasourceConfigRecord | null;
}

export interface HealthInfo {
  status: string;
  version: string;
  embed_backend: string;
  embed_dim: number;
  datasources: string[];
}

export interface Hit {
  id: string;
  score: number;
  text: string;
  metadata: Record<string, unknown>;
}

export interface ImportResponse {
  task_id: string;
  document_id: string;
  chunks: number;
  parser: string | null;
  mime: string | null;
  size: number;
}

/**
 * Pipeline stage labels emitted by the server's import pipeline.
 * Kept in sync with ``TaskStage`` in ``server/app/observability/models.py``.
 */
export type TaskStage =
  | "queued"
  | "parsing"
  | "chunking"
  | "embedding"
  | "writing"
  | "done"
  | "failed";

/**
 * One entry in the per-task rolling event log. The server keeps the most
 * recent ~32 events so the UI can show "what happened" alongside the
 * progress bar without unbounded memory growth.
 */
export interface TaskEvent {
  ts: string;          // ISO-8601 UTC
  stage: TaskStage;
  progress: number;
  message: string;
}

export interface TaskStatus {
  task_id: string;
  kind: string;
  status: string;
  progress: number;
  /** Latest pipeline stage label. Defaults to "queued" if the server is older. */
  stage: TaskStage;
  /** Most recent ~32 events for this task (oldest first). Defaults to []. */
  events: TaskEvent[];
  error: string | null;
  result: Record<string, unknown> | null;
}

/**
 * A locally catalogued document. Backed by MetaDB on the main side.
 */
export interface DocumentInfo {
  id: string;
  source_path: string;
  parser: string | null;
  size: number;
  imported_at: string;
  chunks: number;
}

/**
 * A chunk as returned by `GET /v1/chunks` (G7 browse UI).
 * `text` is server-side truncated to ~240 chars; `text_length` is the full
 * size. `metadata` is the same object the import pipeline wrote.
 */
export interface ChunkSummary {
  chunk_id: string;
  document_id: string;
  text: string;
  text_length: number;
  metadata: Record<string, unknown>;
}

/**
 * Per-document rollup returned alongside the chunk list. Drives the
 * aggregation panel in the browse UI.
 */
export interface DocumentSummary {
  document_id: string;
  chunk_count: number;
  parsers: string[];
  first_chunk_id: string | null;
  sample_text: string;
}

/**
 * Response shape for `GET /v1/chunks`.
 */
export interface BrowseResponse {
  chunks: ChunkSummary[];
  total: number;
  aggregations: Record<string, DocumentSummary>;
}

export interface BrowseOpts {
  document_id?: string;
  parser?: string;
  offset?: number;
  limit?: number;
}

/**
 * The minimal API exposed by preload's contextBridge to the renderer.
 */
export interface KBAPI {
  health(): Promise<HealthInfo>;
  listDatasources(): Promise<DatasourceInfo[]>;
  testDatasource(cfg: DatasourceConfig): Promise<{ ok: boolean; latency_ms: number | null; message: string | null }>;
  listDatasourceConfigs(): Promise<DatasourceConfigRecord[]>;
  saveDatasourceConfig(cfg: DatasourceConfig): Promise<DatasourceConfigRecord>;
  deleteDatasourceConfig(name: string): Promise<{ name: string; deleted: boolean }>;
  getActiveDatasource(): Promise<ActiveDatasourceResponse>;
  activateDatasourceConfig(name: string): Promise<DatasourceConfigRecord>;
  deactivateDatasource(): Promise<{ name: null; deleted: boolean }>;
  importFile(path: string): Promise<ImportResponse>;
  search(query: string, opts?: { top_k?: number; datasource?: string }): Promise<Hit[]>;
  browseChunks(opts: BrowseOpts): Promise<BrowseResponse>;
  getTask(taskId: string): Promise<TaskStatus>;
  pickFile(): Promise<string | null>;
  onProgress(cb: (task: TaskStatus) => void): () => void;
  serverUrl(): Promise<string>;
  listDocuments(): Promise<DocumentInfo[]>;
  getDocument(id: string): Promise<DocumentInfo | null>;
  deleteDocument(id: string): Promise<boolean>;
}