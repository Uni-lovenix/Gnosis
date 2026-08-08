/**
 * ServerManager: spawns and supervises the Python backend.
 *
 * - Picks a port (env KB_PORT, default 8765).
 * - Spawns `python -m app.main` with the project venv if available.
 * - Polls /v1/health every 5s; restarts after 3 consecutive failures.
 */
import { ChildProcess, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { request } from "node:http";
import path from "node:path";

export interface ServerHandle {
  baseUrl: string;
  start(): Promise<void>;
  stop(): Promise<void>;
  health(): Promise<boolean>;
}

interface Options {
  /** Project root containing `server/` with the FastAPI app. */
  projectRoot: string;
  /** Port to bind. */
  port: number;
  /** Optional path to a Python interpreter (defaults to `python3`). */
  python?: string;
  /** Extra env vars passed to the child. */
  env?: Record<string, string>;
}

export function createServerManager(opts: Options): ServerHandle {
  const baseUrl = `http://127.0.0.1:${opts.port}`;
  let proc: ChildProcess | null = null;
  let failStreak = 0;
  let stopRequested = false;

  function pythonBin(): string {
    return opts.python ?? "python3";
  }

  function serverCwd(): string {
    return path.join(opts.projectRoot, "server");
  }

  async function ping(timeoutMs = 2000): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      const req = request(
        `${baseUrl}/v1/health`,
        { method: "GET", timeout: timeoutMs },
        (res) => {
          resolve((res.statusCode ?? 0) >= 200 && (res.statusCode ?? 0) < 500);
          res.resume();
        },
      );
      req.on("error", () => resolve(false));
      req.on("timeout", () => {
        req.destroy();
        resolve(false);
      });
      req.end();
    });
  }

  async function waitReady(timeoutMs = 30_000): Promise<boolean> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (await ping(1500)) return true;
      await sleep(500);
    }
    return false;
  }

  function spawnServer(): ChildProcess {
    const cwd = serverCwd();
    const env = {
      ...process.env,
      KB_HOST: "127.0.0.1",
      KB_PORT: String(opts.port),
      ...(opts.env ?? {}),
    };
    const child = spawn(pythonBin(), ["-m", "app.main"], { cwd, env, stdio: "pipe" });
    child.stdout?.on("data", (b) => process.stdout.write(`[kb-server] ${b}`));
    child.stderr?.on("data", (b) => process.stderr.write(`[kb-server] ${b}`));
    child.on("exit", (code) => {
      if (!stopRequested) {
        // eslint-disable-next-line no-console
        console.warn(`[kb-server] exited with code ${code}`);
      }
      proc = null;
    });
    return child;
  }

  async function supervise(): Promise<void> {
    if (stopRequested) return;
    if (!proc) {
      proc = spawnServer();
    }
    const ok = await ping(1500);
    if (ok) {
      failStreak = 0;
    } else {
      failStreak += 1;
      if (failStreak >= 3) {
        // eslint-disable-next-line no-console
        console.warn("[kb-server] 3 consecutive failures, restarting");
        proc?.kill("SIGTERM");
        await sleep(500);
        proc = spawnServer();
        failStreak = 0;
      }
    }
  }

  let supervisorHandle: NodeJS.Timeout | null = null;

  return {
    baseUrl,
    async start(): Promise<void> {
      stopRequested = false;
      if (existsSync(serverCwd())) {
        proc = spawnServer();
        const ready = await waitReady();
        if (!ready) {
          // eslint-disable-next-line no-console
          console.warn("[kb-server] did not become ready in time");
        }
      } else {
        // eslint-disable-next-line no-console
        console.warn(`[kb-server] no server cwd at ${serverCwd()}; running in offline mode`);
      }
      supervisorHandle = setInterval(() => {
        void supervise();
      }, 5_000);
    },
    async stop(): Promise<void> {
      stopRequested = true;
      if (supervisorHandle) clearInterval(supervisorHandle);
      supervisorHandle = null;
      const target = proc;
      proc = null;
      if (target) {
        target.kill("SIGTERM");
        await sleep(300);
        target.kill("SIGKILL");
      }
    },
    async health(): Promise<boolean> {
      return ping(2000);
    },
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}