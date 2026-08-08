/**
 * HTTP client that talks to the Python backend over plain fetch.
 * Lives in the main process; preload proxies requests via IPC.
 */
import fs from "node:fs";
import path from "node:path";

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

export type TaskStage =
  | "queued"
  | "parsing"
  | "chunking"
  | "embedding"
  | "writing"
  | "done"
  | "failed";

export interface TaskEvent {
  ts: string;
  stage: TaskStage;
  progress: number;
  message: string;
}

export interface TaskStatus {
  task_id: string;
  kind: string;
  status: string;
  progress: number;
  stage: TaskStage;
  events: TaskEvent[];
  error: string | null;
  result: Record<string, unknown> | null;
}

export class ApiClient {
  constructor(private baseUrl: string) {}

  async health(): Promise<HealthInfo> {
    return this.json("GET", "/v1/health");
  }

  async listDatasources(): Promise<Array<{ name: string; type: string; capabilities: string[] }>> {
    return this.json("GET", "/v1/datasources");
  }

  async testDatasource(cfg: { name: string; type: string; options?: Record<string, unknown> }): Promise<{
    ok: boolean;
    latency_ms: number | null;
    message: string | null;
  }> {
    return this.json("POST", "/v1/datasources/test", cfg);
  }

  async listDatasourceConfigs(): Promise<
    Array<{
      name: string;
      type: string;
      options: Record<string, unknown>;
      saved_at: string;
      last_tested_at: string | null;
    }>
  > {
    return this.json("GET", "/v1/datasources/configs");
  }

  async saveDatasourceConfig(cfg: {
    name: string;
    type: string;
    options?: Record<string, unknown>;
  }): Promise<{
    name: string;
    type: string;
    options: Record<string, unknown>;
    saved_at: string;
    last_tested_at: string | null;
  }> {
    return this.json("POST", "/v1/datasources/configs", cfg);
  }

  async deleteDatasourceConfig(name: string): Promise<{ name: string; deleted: boolean }> {
    return this.json("DELETE", `/v1/datasources/configs/${encodeURIComponent(name)}`);
  }

  async getActiveDatasource(): Promise<{
    name: string | null;
    config:
      | {
          name: string;
          type: string;
          options: Record<string, unknown>;
          saved_at: string;
          last_tested_at: string | null;
        }
      | null;
  }> {
    return this.json("GET", "/v1/datasources/active");
  }

  async activateDatasourceConfig(name: string): Promise<{
    name: string;
    type: string;
    options: Record<string, unknown>;
    saved_at: string;
    last_tested_at: string | null;
  }> {
    return this.json("PUT", `/v1/datasources/active/${encodeURIComponent(name)}`);
  }

  async deactivateDatasource(): Promise<{ name: null; deleted: boolean }> {
    return this.json("DELETE", "/v1/datasources/active");
  }

  async importFile(filePath: string): Promise<ImportResponse> {
    const buf = fs.readFileSync(filePath);
    const filename = path.basename(filePath);
    // Build a multipart body using Node 20's built-in FormData / Blob.
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(buf)]), filename);
    const r = await fetch(`${this.baseUrl}/v1/files/import`, { method: "POST", body: form });
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`import failed ${r.status}: ${txt.slice(0, 200)}`);
    }
    return (await r.json()) as ImportResponse;
  }

  async search(query: string, topK = 5): Promise<Hit[]> {
    const body = { query, top_k: topK };
    const r = await fetch(`${this.baseUrl}/v1/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`search failed ${r.status}: ${txt.slice(0, 200)}`);
    }
    const j = (await r.json()) as { hits: Hit[] };
    return j.hits;
  }

  async browseChunks(opts: {
    document_id?: string;
    parser?: string;
    offset?: number;
    limit?: number;
  }): Promise<{
    chunks: Array<{
      chunk_id: string;
      document_id: string;
      text: string;
      text_length: number;
      metadata: Record<string, unknown>;
    }>;
    total: number;
    aggregations: Record<
      string,
      {
        document_id: string;
        chunk_count: number;
        parsers: string[];
        first_chunk_id: string | null;
        sample_text: string;
      }
    >;
  }> {
    const qs = new URLSearchParams();
    if (opts.document_id) qs.set("document_id", opts.document_id);
    if (opts.parser) qs.set("parser", opts.parser);
    if (opts.offset !== undefined && opts.offset !== 0) qs.set("offset", String(opts.offset));
    qs.set("limit", String(opts.limit ?? 20));
    return this.json("GET", `/v1/chunks?${qs.toString()}`);
  }

  async getTask(taskId: string): Promise<TaskStatus> {
    return this.json("GET", `/v1/files/tasks/${encodeURIComponent(taskId)}`);
  }

  private async json<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
    const init: RequestInit = { method };
    if (body !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    const r = await fetch(`${this.baseUrl}${path}`, init);
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`${method} ${path} ${r.status}: ${txt.slice(0, 200)}`);
    }
    return (await r.json()) as T;
  }
}