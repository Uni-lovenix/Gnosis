/**
 * Smoke test: verify the Electron TS code at least type-checks.
 * Run with: `npx tsc --noEmit -p tsconfig.main.json` and friends.
 *
 * This file is not imported by the app; it just provides a stable entry
 * for lint/typecheck tools.
 */
export const SMOKE_VERSION = "0.1.0";