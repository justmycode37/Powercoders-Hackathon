// Serves the app for the test scripts on private ports.
//   default            mock engine (:8097, clock fixed) + `vite preview`
//   KANTE_API=http://… the real engine at that address instead of the mock
//   KANTE_URL=http://… use an app that is already running (nothing is started)
// The build goes to .cache/dist-test, never to dist/: the engine serves dist/ live.
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
export const OUT = ".cache/dist-test";
export const REAL = process.env.KANTE_API || "";

async function waitFor(url, ms = 15000) {
  const end = Date.now() + ms;
  for (;;) {
    try {
      const r = await fetch(url);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    if (Date.now() > end) throw new Error("timeout waiting for " + url);
    await new Promise((r) => setTimeout(r, 150));
  }
}

/** @returns {Promise<{ url: string, api: string, real: boolean, stop: () => void }>} */
export async function serve({ mockPort = 8097, webPort = REAL ? 4198 : 4197, now = "2026-11-23T14:02:00+01:00", build = true } = {}) {
  const api = REAL || `http://localhost:${mockPort}`;
  if (process.env.KANTE_URL) return { url: process.env.KANTE_URL, api, real: !!REAL, stop() {} };
  if (build) {
    const r = spawnSync(process.execPath, ["node_modules/vite/bin/vite.js", "build", "--outDir", OUT, "--emptyOutDir", "--logLevel", "warn"], { cwd: root, stdio: "inherit" });
    if (r.status !== 0) throw new Error("build failed");
  }
  const env = { ...process.env, KANTE_API: api };
  const procs = [spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--strictPort", "--outDir", OUT], { cwd: root, stdio: "ignore", env: { ...env, PORT: String(webPort) } })];
  if (!REAL) procs.push(spawn(process.execPath, ["mock/server.mjs"], { cwd: root, stdio: "ignore", env: { ...env, PORT: String(mockPort), KANTE_MOCK_NOW: now } }));
  const stop = () => procs.forEach((p) => p.kill());
  process.on("exit", stop);
  try {
    await waitFor(`${api}/api/meta`);
    await waitFor(`http://localhost:${webPort}/`);
  } catch (err) {
    stop();
    throw err;
  }
  return { url: `http://localhost:${webPort}`, api, real: !!REAL, stop };
}

/** The next weekday at `hhmm` Swiss time as "YYYY-MM-DDTHH:MM" — a busy moment that is always inside the timetable. */
export function nextWeekday(hhmm = "08:00") {
  const d = new Date(Date.now() + 86400000);
  while ([0, 6].includes(d.getUTCDay())) d.setUTCDate(d.getUTCDate() + 1);
  return `${d.toISOString().slice(0, 10)}T${hhmm}`;
}
