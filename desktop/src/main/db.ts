/**
 * SQLite metadata store for the desktop host.
 *
 * Two tables:
 *   documents(id, source_path, parser, size, imported_at, chunks)
 *   tasks(task_id, kind, status, progress, error, result, created_at, updated_at)
 *
 * The on-disk file lives under `app.getPath('userData')`.
 */
import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";

export interface DocumentRow {
  id: string;
  source_path: string;
  parser: string | null;
  size: number;
  imported_at: string;
  chunks: number;
}

export interface TaskRow {
  task_id: string;
  kind: string;
  status: string;
  progress: number;
  error: string | null;
  result: string | null;
  created_at: string;
  updated_at: string;
}

export class MetaDB {
  private db: Database.Database;

  constructor(file: string) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    this.db = new Database(file);
    this.db.pragma("journal_mode = WAL");
    this.init();
  }

  private init(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        source_path TEXT NOT NULL,
        parser TEXT,
        size INTEGER NOT NULL,
        imported_at TEXT NOT NULL,
        chunks INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,
        progress REAL NOT NULL DEFAULT 0,
        error TEXT,
        result TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  upsertDocument(d: DocumentRow): void {
    this.db
      .prepare(
        `INSERT INTO documents(id, source_path, parser, size, imported_at, chunks)
         VALUES(?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           source_path = excluded.source_path,
           parser = excluded.parser,
           size = excluded.size,
           imported_at = excluded.imported_at,
           chunks = excluded.chunks`,
      )
      .run(d.id, d.source_path, d.parser, d.size, d.imported_at, d.chunks);
  }

  listDocuments(): DocumentRow[] {
    return this.db
      .prepare(
        "SELECT id, source_path, parser, size, imported_at, chunks FROM documents ORDER BY imported_at DESC",
      )
      .all() as DocumentRow[];
  }

  getDocument(id: string): DocumentRow | null {
    const row = this.db
      .prepare(
        "SELECT id, source_path, parser, size, imported_at, chunks FROM documents WHERE id = ?",
      )
      .get(id) as DocumentRow | undefined;
    return row ?? null;
  }

  deleteDocument(id: string): boolean {
    const info = this.db.prepare("DELETE FROM documents WHERE id = ?").run(id);
    return info.changes > 0;
  }

  upsertTask(t: TaskRow): void {
    this.db
      .prepare(
        `INSERT INTO tasks(task_id, kind, status, progress, error, result, created_at, updated_at)
         VALUES(?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(task_id) DO UPDATE SET
           status = excluded.status,
           progress = excluded.progress,
           error = excluded.error,
           result = excluded.result,
           updated_at = excluded.updated_at`,
      )
      .run(
        t.task_id,
        t.kind,
        t.status,
        t.progress,
        t.error,
        t.result,
        t.created_at,
        t.updated_at,
      );
  }

  close(): void {
    this.db.close();
  }
}