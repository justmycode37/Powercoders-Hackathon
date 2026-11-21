// Starts the mock engine and Vite together: `npm run dev:mock`.
import { spawn } from "node:child_process";

const mockPort = process.env.KANTE_MOCK_PORT || "8080";
const env = { ...process.env, KANTE_API: `http://localhost:${mockPort}` };
const procs = [
  spawn(process.execPath, ["mock/server.mjs"], { stdio: "inherit", env: { ...env, PORT: mockPort } }),
  spawn(process.execPath, ["node_modules/vite/bin/vite.js", ...process.argv.slice(2)], { stdio: "inherit", env }),
];
const stop = () => procs.forEach((p) => p.kill());
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
procs.forEach((p) => p.on("exit", (code) => { stop(); process.exitCode = code ?? 0; }));
