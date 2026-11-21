// Screenshots of every screen and state against the REAL engine → shots/
//   npm run shots                 (KANTE_API defaults to http://localhost:8080; builds to .cache/dist-test)
//   KANTE_URL=http://localhost:5173 npm run shots   use an app that is already running
//   npm run shots -- m4 d1        only the shots whose name starts with one of these
// The app's clock is simulated at the next weekday 08:00 so the pictures show a
// busy network whatever the time of day.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { launch, context, mapIdle, placeParam, zurich, BERN_STATION } from "./lib.mjs";
import { nextWeekday, serve } from "./serve.mjs";

if (!process.env.KANTE_API) process.env.KANTE_API = "http://localhost:8080";
const only = process.argv.slice(2);
const dir = fileURLToPath(new URL("../shots/", import.meta.url));
mkdirSync(dir, { recursive: true });
const server = await serve();
const browser = await launch();
const day = nextWeekday("08:00");
const enc = encodeURIComponent;
const place = (name) => placeParam(server.api, name);
const ZH = enc(await place("Zürich HB"));
const OST = enc(await place("Ostermundigen, Rüti"));
const BOARD = (await place("Bern, Bahnhof")).split("~")[0];
const TRIP = `/plan?from=${ZH}&to=${OST}&t=${zurich(day)}`;
const problems = [];

/** One screenshot: open `path`, run `steps(page)`, wait for the map, save. */
async function shot(name, path, steps, opts = {}) {
  if (only.length && !only.some((p) => name.startsWith(p))) return;
  const ctx = await context(browser, { sim: BERN_STATION, clock: day.replace("08:00", opts.at ?? "07:56"), ...opts });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => problems.push(`${name}: ${e.message}`));
  try {
    await page.goto(server.url + path);
    if (steps) await steps(page);
    if (!opts.nomap) await mapIdle(page, 20000);
    await page.screenshot({ path: dir + name + ".png", fullPage: false });
    console.log("  " + name);
  } catch (err) {
    problems.push(`${name}: ${err.message.split("\n")[0]}`);
    await page.screenshot({ path: dir + name + ".png" }).catch(() => undefined);
    console.log("! " + name + ": " + err.message.split("\n")[0]);
  }
  await ctx.close();
}
const expand = async (page) => {
  if ((await page.locator(".sheet").getAttribute("data-detent")) !== "full") await page.locator(".sheet-handle").click();
  await page.waitForTimeout(400);
};
const toMap = async (page) => {
  if ((await page.locator(".sheet").getAttribute("data-detent")) === "full") await page.locator(".sheet-handle").click();
  await page.waitForTimeout(400);
};
const openJourney = async (page, nth = 0) => {
  await page.waitForSelector(".jrow");
  await page.locator(".jrow").nth(nth).click();
  await page.waitForSelector(".tl");
};
const D = { width: 1280, height: 800 };
const map = { storage: { "kante.tripview": '"map"' } };

// ---------------------------------------------------------------- phone, light
await shot("m1-home", "/", (p) => p.waitForSelector(".lcard"), { at: "08:00" });
await shot("m1-home-list", "/", async (p) => {
  await p.waitForSelector(".lcard");
  await p.mouse.wheel(0, 200);
  await p.waitForTimeout(500);
  await p.locator(".sheet-body").evaluate((el) => (el.scrollTop = 420));
}, { at: "08:00" });
await shot("m1-home-no-location", "/", (p) => p.waitForSelector(".banner.locate"), { sim: null, at: "08:00" });
await shot("m2-search-address", "/search?f=from", async (p) => {
  await p.waitForSelector(".search-screen input");
  await p.keyboard.type("bundesgasse 3 bern", { delay: 5 });
  await p.waitForSelector("#search-results .row-wrap");
}, { nomap: true });
await shot("m2-search-station", "/search?f=to", async (p) => {
  await p.waitForSelector(".search-screen input");
  await p.keyboard.type("zürich", { delay: 5 });
  await p.waitForSelector("#search-results .row-wrap");
}, { nomap: true });
await shot("m3-results-list", TRIP, (p) => p.waitForSelector(".jrow"));
await shot("m3-results-map", TRIP, (p) => p.waitForSelector(".jrow"), map);
await shot("m3-results-walk-tab", `/plan?from=${enc(await place("Bundesgasse 3 Bern"))}&to=${enc(await place("Inselspital"))}`, async (p) => {
  await p.waitForSelector(".jrow");
  await p.locator(".tabs [role=tab]").nth(1).click();
  await p.waitForSelector(".walkcard");
}, map);
await shot("m3-results-address-to-place", `/plan?from=${enc(await place("Bundesgasse 3 Bern"))}&to=${enc(await place("Inselspital"))}`, (p) => p.waitForSelector(".jrow"));
await shot("m3-results-arrive-by", `${TRIP.replace(/&t=\d+/, "")}&t=${zurich(day.replace("08:00", "10:00"))}&arr=1`, (p) => p.waitForSelector(".jrow"));
await shot("m3-results-rural", `/plan?from=${enc(await place("Scuol-Tarasp"))}&to=${enc(await place("Zermatt"))}&t=${zurich(day)}`, (p) => p.waitForSelector(".jrow"));
await shot("m3-results-night", `/plan?from=${enc(await place("Scuol-Tarasp"))}&to=${enc(await place("Zermatt"))}&t=${zurich(day.replace("08:00", "23:40"))}`, (p) => p.waitForSelector(".jrow, .empty"), { at: "23:40" });
await shot("m3-results-need-origin", `/plan?from=here&to=${OST}`, (p) => p.waitForSelector(".empty"), { sim: null });
await shot("m4-journey-list", TRIP, (p) => openJourney(p));
await shot("m4-journey-change", TRIP, async (p) => {
  await openJourney(p);
  await p.locator(".tl-walk").first().scrollIntoViewIfNeeded();
  await p.locator(".sheet-body").evaluate((el) => (el.scrollTop += 380));
});
await shot("m4-journey-map", TRIP, (p) => openJourney(p), map);
await shot("m4-journey-step-level", TRIP, async (p) => {
  await openJourney(p);
  await p.locator(".steps .step").nth(3).click();
  await p.waitForSelector(".stepnav");
  await p.waitForTimeout(1800);
});
await shot("m4-journey-where-to-stand", TRIP, async (p) => {
  await openJourney(p);
  await p.locator(".stand .link-btn").nth(1).click();
  await p.waitForTimeout(1800);
});
await shot("m4-journey-stepfree-slow", TRIP + "&o=w3_s2_e0_c1", async (p) => {
  await openJourney(p);
  await p.locator(".tl-walk").first().scrollIntoViewIfNeeded();
  await p.locator(".sheet-body").evaluate((el) => (el.scrollTop += 300));
});
await shot("m4-journey-rural", `/plan?from=${enc(await place("Scuol-Tarasp"))}&to=${enc(await place("Zermatt"))}&t=${zurich(day)}`, (p) => openJourney(p));
await shot("m5-board", `/station?id=${enc(BOARD)}`, async (p) => {
  await p.waitForSelector(".dep");
  await expand(p);
}, { at: "08:00" });
await shot("m5-board-bay", `/station?id=${enc(BOARD)}`, async (p) => {
  await p.waitForSelector(".dep");
  await p.locator(".chip.bay-chip", { hasText: /^L$/ }).click();
  await p.waitForSelector(".stand");
  await p.waitForTimeout(1200);
}, { at: "08:00" });
await shot("m5-board-by-bay", `/station?id=${enc(BOARD)}&by=bay`, async (p) => {
  await p.waitForSelector(".bay");
  await expand(p);
}, { at: "08:00" });
await shot("m5-board-rail", `/station?id=${enc((await place("Bern")).split("~")[0])}`, async (p) => {
  await p.waitForSelector(".dep");
  await expand(p);
}, { at: "08:00" });
await shot("m6-trip", "/", async (p) => {
  await p.waitForSelector(".lcard");
  await p.locator(".lcard").nth(1).click();
  await p.waitForSelector(".calls .tl-row");
}, { at: "08:00" });
await shot("m7-onboard", "/onboard", (p) => p.waitForSelector(".cand, .empty"), { sim: { lat: 46.9479, lon: 7.4435 }, at: "08:01" });
await shot("m7-onboard-journey", "/onboard", async (p) => {
  await p.waitForSelector(".cand");
  await p.locator(".cand").first().click();
  await p.waitForSelector(".search-screen .field.locked");
  await p.keyboard.type("bern wankdorf bahnhof", { delay: 5 });
  await p.waitForSelector("#search-results .row-wrap");
  await p.keyboard.press("Enter");
  await openJourney(p);
}, { sim: { lat: 46.9479, lon: 7.4435 }, at: "08:01" });
const go = (n) => async (p) => {
  await openJourney(p);
  await p.locator("[data-testid=start]").click();
  await p.waitForSelector(".go-say h1");
  for (let i = 0; i < n; i++) await p.locator('[aria-label="Preview the next stage"]').click();
  await p.waitForTimeout(600);
};
await shot("m8-go-stand", TRIP, go(0), { at: "07:58" });
await shot("m8-go-ride", TRIP, go(1), { at: "07:58" });
await shot("m8-go-change-walk", TRIP, go(2), { at: "07:58" });
await shot("m8-go-stand-bay", TRIP, go(3), { at: "07:58" });
await shot("m8-go-leave", `/plan?from=${enc(await place("Bundesgasse 3 Bern"))}&to=${enc(await place("Inselspital"))}`, go(0), { at: "08:00" });
await shot("m8-go-minimised", TRIP, async (p) => {
  await go(0)(p);
  await p.locator('[aria-label="Minimise guidance"]').click();
  await p.waitForSelector(".gstrip");
  await p.goto(server.url + "/");
  await p.waitForSelector(".lcard");
}, { at: "07:58" });
await shot("m9-options", TRIP, async (p) => {
  await p.waitForSelector(".jrow");
  await p.locator('.od [aria-label="Options"]').click();
  await p.waitForSelector(".modal");
}, { nomap: true });
await shot("m9-time", TRIP, async (p) => {
  await p.waitForSelector(".jrow");
  await p.locator(".chip", { hasText: /Leave/ }).first().click();
  await p.waitForSelector(".modal");
}, { nomap: true });
await shot("m9-map-menu", "/", async (p) => {
  await p.waitForSelector(".lcard");
  await mapIdle(p);
  await p.locator(".map").click({ button: "right", position: { x: 230, y: 180 } });
  await p.waitForSelector("[data-testid=sim-here]");
  await p.waitForTimeout(500);
}, { at: "08:00" });
await shot("m10-offline", "/", async (p) => {
  await p.waitForSelector(".lcard");
  await p.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 20000 });
  await mapIdle(p);
  await p.context().setOffline(true);
  await p.reload();
  await p.waitForSelector(".status-line", { timeout: 20000 });
}, { sw: true, at: "08:00" });

// ---------------------------------------------------------------- small phone
await shot("s1-small-results-360", TRIP, (p) => p.waitForSelector(".jrow"), { width: 360, height: 740 });
await shot("s1-small-journey-360", TRIP, (p) => openJourney(p), { width: 360, height: 740 });
await shot("s1-small-home-360", "/", (p) => p.waitForSelector(".lcard"), { width: 360, height: 740, at: "08:00" });

// ---------------------------------------------------------------- phone, dark
await shot("d1-dark-home", "/", (p) => p.waitForSelector(".lcard"), { dark: true, at: "08:00" });
await shot("d1-dark-results", TRIP, (p) => p.waitForSelector(".jrow"), { dark: true });
await shot("d1-dark-journey", TRIP, (p) => openJourney(p), { dark: true });
await shot("d1-dark-journey-step", TRIP, async (p) => {
  await openJourney(p);
  await p.locator(".steps .step").nth(3).click();
  await p.waitForTimeout(1800);
}, { dark: true });
await shot("d1-dark-board", `/station?id=${enc(BOARD)}`, (p) => p.waitForSelector(".dep"), { dark: true, at: "08:00" });
await shot("d1-dark-go", TRIP, go(1), { dark: true, at: "07:58" });

// ---------------------------------------------------------------- desktop
await shot("w1-desktop-home", "/", (p) => p.waitForSelector(".lcard"), { ...D, at: "08:00" });
await shot("w1-desktop-results", TRIP, (p) => p.waitForSelector(".jrow"), D);
await shot("w1-desktop-journey-step", TRIP, async (p) => {
  await openJourney(p);
  await p.locator(".steps .step").nth(1).click();
  await p.waitForTimeout(1800);
}, D);
await shot("w1-desktop-board", `/station?id=${enc(BOARD)}`, (p) => p.waitForSelector(".dep"), { ...D, at: "08:00" });
await shot("w1-desktop-go", TRIP, go(2), { ...D, at: "07:58" });
await shot("w1-desktop-dark-home", "/", (p) => p.waitForSelector(".lcard"), { ...D, dark: true, at: "08:00" });
await shot("w1-desktop-dark-journey", TRIP, (p) => openJourney(p), { ...D, dark: true });

await browser.close();
server.stop();
if (problems.length) console.log("\nproblems:\n  " + problems.join("\n  "));
console.log(`\nscreenshots in shots/ (real engine at ${server.api}, clock ${day})`);
process.exit(problems.length ? 1 : 0);
