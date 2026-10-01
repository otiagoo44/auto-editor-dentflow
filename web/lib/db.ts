import { mkdirSync } from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import postgres from "postgres";
import { AsyncLocalStorage } from "node:async_hooks";
import { dataDir, remote } from "./config";

type Row = Record<string, unknown>;
let sqlite: DatabaseSync | undefined;
let pg: ReturnType<typeof postgres> | undefined;
let initialized: Promise<void> | undefined;
type Query = (sql: string, params?: unknown[]) => Promise<Row[]>;
const context = new AsyncLocalStorage<Query>();
let localQueue = Promise.resolve();
async function exclusive<T>(action: () => Promise<T>): Promise<T> {
  const previous = localQueue;
  let release!: () => void;
  localQueue = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    return await action();
  } finally {
    release();
  }
}

// The same migration runs on SQLite locally and PostgreSQL remotely.
export const migration = [
  "CREATE TABLE IF NOT EXISTS content_items (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, source_version TEXT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS content_versions (id TEXT PRIMARY KEY, content_id TEXT NOT NULL, owner_id TEXT NOT NULL, created_at BIGINT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, status TEXT NOT NULL, created_at BIGINT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, content_id TEXT, created_at BIGINT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, project_id TEXT NOT NULL, status TEXT NOT NULL, created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL, intent_key TEXT NOT NULL, settings_hash TEXT NOT NULL, lease_hash TEXT, lease_until BIGINT, worker_id TEXT, attempt INTEGER NOT NULL DEFAULT 0, data TEXT NOT NULL, UNIQUE(owner_id,intent_key))",
  "CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status,created_at)",
  "CREATE INDEX IF NOT EXISTS jobs_owner ON jobs(owner_id,project_id,created_at)",
  "CREATE TABLE IF NOT EXISTS job_events (id TEXT PRIMARY KEY, job_id TEXT NOT NULL, created_at BIGINT NOT NULL, phase TEXT NOT NULL)",
  "CREATE INDEX IF NOT EXISTS events_job ON job_events(job_id,created_at)",
  "CREATE TABLE IF NOT EXISTS outputs (id TEXT PRIMARY KEY, job_id TEXT NOT NULL, owner_id TEXT NOT NULL, kind TEXT NOT NULL, created_at BIGINT NOT NULL, data TEXT NOT NULL, UNIQUE(job_id,kind))",
  "CREATE INDEX IF NOT EXISTS outputs_owner ON outputs(owner_id,job_id)",
  "CREATE TABLE IF NOT EXISTS editorial_plans (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, job_id TEXT NOT NULL, owner_id TEXT NOT NULL, created_at BIGINT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS workers (id TEXT PRIMARY KEY, last_seen BIGINT NOT NULL, data TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS rate_limits (id TEXT PRIMARY KEY, window_start BIGINT NOT NULL, count INTEGER NOT NULL)",
];

async function execute(sql: string, params: unknown[] = []): Promise<Row[]> {
  if (remote()) {
    if (!process.env.DATABASE_URL) throw new Error("Falta DATABASE_URL");
    pg ||= postgres(process.env.DATABASE_URL, { max: 3, prepare: false });
    return (await pg.unsafe(sql, params as never[])) as unknown as Row[];
  }
  if (!sqlite) {
    mkdirSync(dataDir(), { recursive: true });
    sqlite = new DatabaseSync(path.join(dataDir(), "studio.sqlite"));
    sqlite.exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;");
  }
  const values: unknown[] = [];
  const query = sql.replace(/\$(\d+)/g, (_, n) => {
    values.push(params[Number(n) - 1]);
    return "?";
  });
  return sqlite
    .prepare(query)
    .all(...(values as (string | number | null)[])) as Row[];
}
async function initialize() {
  initialized ||= (async () => {
    for (const stmt of migration) await execute(stmt);
  })().catch((error) => {
    initialized = undefined;
    throw error;
  });
  await initialized;
}
export async function db(sql: string, params: unknown[] = []): Promise<Row[]> {
  const query = context.getStore();
  if (query) return query(sql, params);
  await initialize();
  return remote()
    ? execute(sql, params)
    : exclusive(() => execute(sql, params));
}
export async function transaction<T>(action: () => Promise<T>): Promise<T> {
  if (context.getStore()) return action();
  await initialize();
  if (remote()) {
    return (await pg!.begin(async (sql) =>
      context.run(
        async (query, params = []) =>
          (await sql.unsafe(query, params as never[])) as unknown as Row[],
        action,
      ),
    )) as T;
  }
  return exclusive(async () => {
    sqlite!.exec("BEGIN IMMEDIATE");
    try {
      const result = await context.run(execute, action);
      sqlite!.exec("COMMIT");
      return result;
    } catch (error) {
      sqlite!.exec("ROLLBACK");
      throw error;
    }
  });
}
export async function one(sql: string, params: unknown[] = []) {
  return (await db(sql, params))[0];
}
export const unpack = <T>(row: Row): T => JSON.parse(String(row.data));
