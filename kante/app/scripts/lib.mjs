// Shared helpers for the smoke test and the screenshot run.
import { chromium } from "playwright";

export const BERN = { lat: 46.9479, lon: 7.4405 };
/** In front of Bern station (the brief's test position). */
export const BERN_STATION = { lat: 46.9482, lon: 7.4398 };

export async function launch() {
  return chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"] });
}

/** A phone-like (or desktop) context with a simulated position in Bern. */
export async function context(browser, { width = 390, height = 844, dark = false, sim = BERN, storage = {}, clock = undefined, sw = false } = {}) {
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: width < 600 ? 2.5 : 1,
    isMobile: width < 600,
    hasTouch: width < 600,
    colorScheme: dark ? "dark" : "light",
    locale: "en-GB",
    timezoneId: "Europe/Zurich",
    serviceWorkers: sw ? "allow" : "block",
  });
  const init = { ...storage };
  if (sim) init["kante.sim"] = JSON.stringify({ ...sim, at: 0 });
  await ctx.addInitScript(
    ({ items, clock }) => {
      for (const [k, v] of Object.entries(items)) if (localStorage.getItem(k) === null) localStorage.setItem(k, v);
      // a simulated clock for the tab ("2026-11-23T08:00" Swiss time, CET): the app sends it with its requests
      if (clock && sessionStorage.getItem("kante.clock") === null) sessionStorage.setItem("kante.clock", String(Date.parse(clock.length <= 16 ? clock + ":00+01:00" : clock) - Date.now()));
    },
    { items: init, clock },
  );
  return ctx;
}

/** Collects console errors and failed requests of a page. */
export function watch(page) {
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push("console: " + m.text());
  });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("response", (r) => {
    if (r.status() >= 400 && r.url().includes("/api/")) errors.push(`http ${r.status()}: ${r.url()}`);
  });
  page.on("requestfailed", (r) => {
    // aborted requests are the app superseding its own calls
    if (r.url().includes("/api/") && !/ERR_ABORTED/.test(r.failure()?.errorText ?? "")) errors.push(`failed: ${r.url()} ${r.failure()?.errorText}`);
  });
  return errors;
}

export async function mapIdle(page, timeout = 20000) {
  await page.waitForFunction(() => !!window.__kanteMap && window.__kanteMap.loaded() && !window.__kanteMap.isMoving(), null, { timeout }).catch(() => undefined);
  await page.waitForTimeout(700);
}

/** "id~name~lat,lon~k" for the first search hit of `text`: a place as the app's URLs carry it. */
export async function placeParam(api, text) {
  const r = await (await fetch(`${api}/api/search?q=${encodeURIComponent(text)}&limit=1`)).json();
  const p = r.results[0];
  if (!p) throw new Error("no search hit for " + text);
  return `${p.id}~${p.name.replace(/[~|]/g, " ")}~${p.lat.toFixed(5)},${p.lon.toFixed(5)}~${p.kind[0]}`;
}
/** Unix seconds of a Swiss wall-clock time in winter ("2026-11-23T08:00"). */
export const zurich = (local) => Math.floor(Date.parse(local + ":00+01:00") / 1000);
/** Replaces {place:Name} and {t:2026-11-23T08:00} in a path. */
export async function expand(api, path) {
  let out = path;
  for (const m of path.matchAll(/\{place:([^}]+)\}/g)) out = out.replace(m[0], encodeURIComponent(await placeParam(api, m[1])));
  for (const m of path.matchAll(/\{t:([^}]+)\}/g)) out = out.replace(m[0], String(zurich(m[1])));
  return out;
}
