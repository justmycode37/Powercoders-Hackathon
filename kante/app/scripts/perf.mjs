// Bundle sizes and load timings, measured locally against the mock
// (KANTE_API=http://localhost:8080 npm run perf measures against the real engine).
//   npm run perf
import { gzipSync } from "node:zlib";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { launch, BERN } from "./lib.mjs";
import { OUT, serve } from "./serve.mjs";

const dist = fileURLToPath(new URL(`../${OUT}/`, import.meta.url));
const server = await serve({ build: true });

console.log("bundle (raw / gzip)");
const walk = (d) => readdirSync(d).flatMap((f) => (statSync(d + f).isDirectory() ? walk(d + f + "/") : [d + f]));
let initial = 0;
let lazy = 0;
for (const f of walk(dist).sort()) {
  const buf = readFileSync(f);
  const gz = gzipSync(buf).length;
  const name = f.slice(dist.length);
  const first = name === "index.html" || /assets\/index-.*\.(js|css)$/.test(name);
  if (/maplibre|engine/.test(name) && /\.(js|mjs)$/.test(name)) lazy += gz;
  if (first) initial += gz;
  if (/\.(js|mjs|css|html)$/.test(name)) console.log(`  ${name.padEnd(44)} ${(buf.length / 1024).toFixed(1).padStart(8)} kB ${(gz / 1024).toFixed(1).padStart(7)} kB gzip${first ? "  ← first load" : ""}`);
}
console.log(`  first load (html + js + css), gzip: ${(initial / 1024).toFixed(1)} kB`);
console.log(`  map engine, loaded after the shell has painted, gzip: ${(lazy / 1024).toFixed(1)} kB\n`);

const browser = await launch();
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];

async function measure(label, { throttle = false, sw = false, offline = false, runs = 3 } = {}) {
  const rows = [];
  for (let i = 0; i < runs; i++) {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true,
      serviceWorkers: sw ? "allow" : "block",
    });
    await ctx.addInitScript((p) => localStorage.getItem("kante.sim") ?? localStorage.setItem("kante.sim", JSON.stringify({ ...p, at: 0 })), BERN);
    let page = await ctx.newPage();
    if (sw) {
      // first visit installs the service worker and fills the caches
      await page.goto(server.url + "/");
      await page.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 20000 });
      await page.waitForFunction(() => !!window.__kanteMap && window.__kanteMap.loaded(), null, { timeout: 30000 });
      await page.waitForSelector(".lcard");
      await page.waitForTimeout(800);
      // a fresh tab, like launching the installed app: the first tab's software-GL
      // rendering would otherwise delay the navigation being measured
      await page.close();
      page = await ctx.newPage();
    }
    const cdp = await ctx.newCDPSession(page);
    if (throttle) {
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
      await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
    }
    if (offline) await ctx.setOffline(true);
    await page.goto(server.url + "/", { waitUntil: "commit" });
    await page.waitForSelector(".searchbar-main", { timeout: 30000 });
    const cards = await page.waitForSelector(".lcard", { timeout: 30000 }).then(() => page.evaluate(() => performance.now()), () => null);
    const mapOk = await page.waitForFunction(() => performance.getEntriesByName("kante:map-ready").length > 0, null, { timeout: offline ? 8000 : 60000 }).then(() => true, () => false);
    const m = await page.evaluate(() => {
      const mark = (n) => performance.getEntriesByName(n)[0]?.startTime ?? null;
      return { fp: mark("first-paint"), fcp: mark("first-contentful-paint"), shell: mark("kante:shell"), map: mark("kante:map-ready") };
    });
    rows.push({ ...m, cards, mapOk });
    await ctx.close();
  }
  const pick = (k) => {
    const v = rows.map((r) => r[k]).filter((x) => x !== null);
    return v.length ? Math.round(median(v)) + " ms" : "—";
  };
  console.log(`${label}\n  first paint ${pick("fp")} · shell rendered ${pick("shell")} · nearby departures ${pick("cards")} · map interactive ${pick("map")}`);
}

await measure("cold load, no cache, desktop CPU, localhost");
await measure("cold load, no cache, 4× CPU slowdown + slow 4G (1.6 Mbit/s, 150 ms RTT)", { throttle: true, runs: 2 });
await measure("repeat load from the service worker", { sw: true });
await measure("repeat load from the service worker, 4× CPU + slow 4G", { sw: true, throttle: true, runs: 2 });
await measure("repeat load, offline", { sw: true, offline: true, runs: 2 });

await browser.close();
server.stop();
