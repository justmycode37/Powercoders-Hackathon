import { defineConfig, type Plugin } from "vite";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const API = process.env.KANTE_API || "http://localhost:8080";

/** Writes dist/sw.js from src/sw.js with the list of built files to precache. */
function serviceWorker(): Plugin {
  let outDir = "dist";
  return {
    name: "kante-sw",
    apply: "build",
    configResolved(c) {
      outDir = c.build.outDir;
    },
    closeBundle() {
      const files: string[] = [];
      const walk = (dir: string) => {
        for (const f of readdirSync(dir)) {
          const p = join(dir, f);
          if (statSync(p).isDirectory()) walk(p);
          else files.push(relative(outDir, p).replaceAll("\\", "/"));
        }
      };
      walk(outDir);
      const keep = files.filter((f) => f !== "sw.js" && !f.endsWith(".map"));
      const hash = createHash("sha1");
      for (const f of keep.sort()) hash.update(f).update(readFileSync(join(outDir, f)));
      const version = hash.digest("hex").slice(0, 10);
      const src = readFileSync("src/sw.js", "utf8")
        .replace("__VERSION__", version)
        .replace('"__PRECACHE__"', JSON.stringify(keep.map((f) => "/" + f)));
      writeFileSync(join(outDir, "sw.js"), src);
    },
  };
}

export default defineConfig({
  plugins: [serviceWorker()],
  server: {
    host: true,
    port: Number(process.env.PORT) || 5173,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
  preview: {
    host: true,
    port: Number(process.env.PORT) || 4173,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
  build: {
    target: "es2022",
    cssCodeSplit: true,
    chunkSizeWarningLimit: 1500,
  },
});
