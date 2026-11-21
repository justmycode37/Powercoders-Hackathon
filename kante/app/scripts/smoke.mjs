// Smoke test: walks the main flows in headless Chromium and fails on any
// console error, page error or failed API call.
//   npm run smoke          against the mock engine (clock fixed at Mon 23 Nov 2026 14:02)
//   npm run smoke:real     against the real engine (KANTE_API, default http://localhost:8080),
//                          with the app's clock simulated at the next weekday 08:00
//   KANTE_URL=http://localhost:5173 npm run smoke   use an app that is already running
import { launch, context, watch, placeParam, zurich, BERN, BERN_STATION } from "./lib.mjs";
import { nextWeekday, serve } from "./serve.mjs";

const server = await serve();
const REAL = server.real;
const day = nextWeekday("08:00");
// what differs between the synthetic network and the national one
const D = REAL
  ? {
      sim: BERN_STATION, clock: day, search: "zürich hb", first: "Zürich HB", from: "Zürich HB", to: "Ostermundigen, Rüti",
      board: await stationId("Bern, Bahnhof"), bay: "L", onboardNear: { lat: 46.9479, lon: 7.4435 }, onboardTo: "bern wankdorf bahnhof",
      shared: [await placeParam(server.api, "Bern, Zytglogge"), await placeParam(server.api, "Zürich HB")],
    }
  : {
      sim: BERN, clock: undefined, search: "zürich h", first: "Zürich HB", from: null, to: null,
      board: "st:8576646", bay: "K1", onboardNear: BERN, onboardTo: "bern bahnhof",
      shared: ["st:8507152~Bern, Zytglogge~46.94795,7.44770~s", "st:8503000~Zürich HB~47.37790,8.54030~s"],
    };
async function stationId(name) {
  return (await placeParam(server.api, name)).split("~")[0];
}

const browser = await launch();
const ctx = await context(browser, { width: 390, height: 844, sim: D.sim, clock: D.clock });
const page = await ctx.newPage();
const errors = watch(page);
const plans = [];
page.on("request", (r) => {
  if (r.url().endsWith("/api/plan")) plans.push(JSON.parse(r.postData() ?? "{}"));
});
let failed = false;
const skipped = [];
const step = async (name, fn) => {
  const t = Date.now();
  try {
    const note = await fn();
    console.log(`  ok  ${name} (${Date.now() - t} ms)${note ? " — " + note : ""}`);
  } catch (err) {
    failed = true;
    console.log(`FAIL  ${name}: ${err.message.split("\n")[0]}`);
    await page.screenshot({ path: new URL("../shots/smoke-fail.png", import.meta.url).pathname }).catch(() => undefined);
  }
};
const expect = (cond, msg) => {
  if (!cond) throw new Error(msg);
};
const mapZoom = () => page.evaluate(() => window.__kanteMap?.getZoom() ?? null);
const count = (sel) => page.locator(sel).count();
const text = (sel) => page.locator(sel).first().innerText();
const settled = () => page.waitForFunction(() => document.querySelectorAll(".jrow").length > 0 && !document.querySelector(".results.refreshing"));
const enc = encodeURIComponent;
/** Content below the fold is reached by expanding the sheet, as a thumb would. */
const expandSheet = async () => {
  if ((await page.locator(".sheet").getAttribute("data-detent")) !== "full") await page.locator(".sheet-handle").click();
  await page.waitForSelector('.sheet[data-detent="full"]');
};
const planUrl = async (from, to, extra = "") => `${server.url}/plan?from=${enc(await placeParam(server.api, from))}&to=${enc(await placeParam(server.api, to))}${extra}`;

await step("home: line-coloured cards with boarding point, walk and a live/timetable label", async () => {
  await page.goto(server.url + "/");
  await page.waitForSelector(".searchbar-main");
  await page.waitForSelector(".lcard");
  expect((await count(".lcard-stop b")) > 0, "no boarding point on the nearby cards");
  expect((await count(".lcard-walk")) > 0, "no walking time on the nearby cards");
  expect(/Live|Timetable/.test(await text(".lcard-live")), "no live/timetable label");
  const box = await page.locator(".searchbar").boundingBox();
  expect(box && box.y > 250 && box.y < 500, "search bar is not on the seam between map and list");
});

await step("a card opens its trip, with where to stand at that stop", async () => {
  await page.locator(".lcard").first().click();
  await page.waitForSelector(".calls .tl-row");
  expect((await count(".calls .at")) === 1, "the stop the card was for is not marked");
  await page.locator(".round-btn[aria-label=Close]").click();
  await page.waitForSelector(".lcard");
});

await step("search: type-ahead, Enter picks the first result", async () => {
  await page.locator(".searchbar-main").click();
  await page.waitForSelector(".search-screen input");
  await page.keyboard.type(D.search, { delay: 15 });
  await page.waitForFunction((want) => document.querySelector("#search-results .row-wrap")?.textContent.includes(want), D.first);
  await page.keyboard.press("Enter");
  await page.waitForSelector(".jrow, .empty");
  expect(new URL(page.url()).pathname === "/plan", "not on the results page");
});

await step("results: rows with every leg's badge, the time bar, first platform and countdown", async () => {
  if (REAL) await page.goto(await planUrl(D.from, D.to));
  await page.waitForSelector(".jrow");
  expect((await count(".jrow")) >= 2, "fewer than two journeys");
  expect((await count(".jrow .chain .badge")) >= 2, "leg badges missing");
  expect((await count(".jrow .tbar-ride")) >= 2, "no ride segments in the time bar");
  expect((await count(".jrow-plat .plat")) >= 1, "no first boarding point in the rows");
  expect(/Leaves? (in|now)/.test(await page.locator(".jrow-act").first().innerText()), "no countdown");
  return (await text(".jrow-l1")).replace(/\s+/g, " ") + " · " + (await text(".jrow-l3")).replace(/\s+/g, " ");
});

await step("walking speed changes the plan in two taps", async () => {
  const before = plans.length;
  await page.locator(".chip", { hasText: "km/h" }).click();
  await page.locator(".speed-opt", { hasText: "Slow" }).click();
  await page.waitForFunction(() => !document.querySelector(".modal"));
  await settled();
  expect(plans.length > before, "no new plan request");
  expect(Math.abs(plans[plans.length - 1].options.walkSpeed - 3 / 3.6) < 0.01, "walkSpeed not sent as m/s");
  await page.locator(".chip", { hasText: "km/h" }).click();
  await page.locator(".speed-opt", { hasText: "Normal" }).click();
  await settled();
});

await step("earlier and later journeys page in", async () => {
  const n = await count(".jrow");
  await page.locator(".more", { hasText: "Later" }).click();
  await page.waitForFunction((k) => document.querySelectorAll(".jrow").length > k, n);
  const m = await count(".jrow");
  if (await count(".more:has-text('Earlier')")) {
    await page.locator(".more", { hasText: "Earlier" }).click();
    await page.waitForFunction((k) => document.querySelectorAll(".jrow").length > k || !document.querySelector(".more:disabled"), m);
  }
});

await step("journey detail: timeline on the grid, where-to-stand card, map close-up", async () => {
  // a journey that has not left yet (paging in earlier ones put past journeys first), with a change if there is one
  const rows = page.locator(".jrow:not(.gone)");
  const withChange = rows.filter({ hasText: /\d changes?/ });
  const changing = (await withChange.count()) > 0;
  await (changing ? withChange : rows).first().click();
  await page.waitForSelector(".tl");
  expect((await count(".stand")) >= 1, "no where-to-stand card");
  expect((await count(".tl-row.board .plat")) >= 1, "no platform in the boarding row");
  if (changing) expect((await count(".steps .step")) >= 2, "written directions are not shown at the change");
  else await page.locator(".expander", { hasText: "Walking directions" }).first().click();
  await page.waitForSelector(".steps .step");
  await page.locator(".stand .link-btn").first().click();
  await page.waitForFunction(() => !window.__kanteMap || window.__kanteMap.getZoom() > 18, null, { timeout: 15000 });
});

await step("walking directions: stepping follows the route and its level", async () => {
  await page.locator(".steps .step").nth(1).click();
  await page.waitForSelector(".stepnav");
  const at = () => text(".stepnav-text small").then((t) => parseInt(t, 10));
  const before = await at();
  await page.locator('.stepnav [aria-label="Next direction"]').click();
  expect((await at()) === before + 1, "step navigation did not advance");
  let note = "";
  // a walk through several levels: the level switcher follows the step
  if (await count(".steps .step:has(.tag.lvl)")) {
    await page.locator(".steps .step:has(.tag.lvl)").first().click();
    await page.waitForSelector(".levels .on", { timeout: 15000 });
    note = `${(await text(".stepnav-text strong")).trim()} → level ${(await text(".levels .on")).trim()} selected`;
  }
  await page.locator('.stepnav [aria-label="Back to the whole journey"]').click();
  await page.waitForSelector(".jhead");
  return note;
});

await step("reload keeps the journey; Back returns to the results", async () => {
  await page.reload();
  await page.waitForSelector(".tl");
  await page.goBack();
  await page.waitForSelector(".jrow");
  await page.goForward();
  await page.waitForSelector(".tl");
});

await step("guidance: one sentence per stage, through a walk and a ride; closing minimises to a strip", async () => {
  await page.locator("[data-testid=start]").click();
  await page.waitForSelector(".go-say h1");
  const said = [await text(".go-say h1")];
  for (let i = 0; i < 4 && !(await page.locator('[aria-label="Preview the next stage"]').isDisabled()); i++) {
    await page.locator('[aria-label="Preview the next stage"]').click();
    await page.waitForTimeout(120);
    said.push(await text(".go-say h1"));
  }
  expect(said.some((s) => /^(Stand at|Wait at|Board)/.test(s)), "no boarding stage: " + said.join(" | "));
  expect(said.some((s) => /^(Get off in|Get off at the next stop|Your stop is next|This is your stop)/.test(s)), "no riding stage: " + said.join(" | "));
  expect(said.some((s) => /^(Change to|Walk to|Leave|Hurry)/.test(s)), "no walking stage: " + said.join(" | "));
  expect((await count(".pbar-puck")) === 1, "no position puck");
  await page.locator('[aria-label="Minimise guidance"]').click();
  await page.waitForSelector(".gstrip");
  await page.locator(".gstrip").click();
  await page.waitForSelector(".go-say h1");
  await page.locator(".pill-btn.danger, .pill-btn.start").first().click();
  if (await count(".pill-btn.danger")) await page.locator(".pill-btn.danger").click();
  await page.waitForFunction(() => !document.querySelector(".gstrip") && !document.querySelector(".go-say"));
  return said.join(" → ");
});

await step("step-free re-plans with stairs: never and says so", async () => {
  await page.goto(page.url().replace("/journey?", "/plan?").replace(/&j=[^&]+/, ""));
  await settled();
  const before = plans.length;
  await page.locator('.od [aria-label="Options"]').click();
  await page.locator(".toggle", { hasText: "Step-free" }).first().click();
  await page.locator('.modal [aria-label="Close"]').click();
  await page.waitForFunction(() => !document.querySelector(".modal"));
  await page.waitForSelector(".chip.on:has-text('Step-free')");
  expect(plans.length > before && plans[plans.length - 1].options.stairs === "never" && plans[plans.length - 1].options.escalators === false, "step-free options not sent");
  await page.waitForSelector(".jrow, .empty");
  const note = (await count(".jrow")) ? "journeys found" : await text(".empty strong");
  await page.locator(".chip.on:has-text('Step-free')").click();
  await page.locator(".toggle", { hasText: "Step-free" }).first().click();
  await page.locator('.modal [aria-label="Close"]').click();
  await settled();
  return note;
});

await step("arrive by: the request carries arriveBy and the chip says so", async () => {
  const before = plans.length;
  await page.locator(".chip", { hasText: /Leave/ }).first().click();
  await page.locator(".segmented button", { hasText: "Arrive by" }).click();
  await page.locator(".chip", { hasText: "+1 h" }).click();
  await page.locator("[data-testid=time-apply]").click();
  await page.waitForSelector(".chip.on:has-text('Arrive by')");
  await page.waitForSelector(".jrow, .empty");
  for (let i = 0; i < 50 && plans.length === before; i++) await page.waitForTimeout(100);
  expect(plans[plans.length - 1].arriveBy === true && typeof plans[plans.length - 1].time === "number", "arriveBy not sent");
});

await step("departure board: minutes to go, platform slot, filter and grouping by bay", async () => {
  await page.goto(server.url + "/station?id=" + enc(D.board));
  await page.waitForSelector(".dep");
  expect((await count(".dep-count b")) > 0, "no minutes-to-go on the board");
  expect((await count(".dep-plat .plat")) > 0, "no platform slot on the board");
  await page.locator(".chip.bay-chip", { hasText: new RegExp(`^${D.bay}$`) }).click();
  await page.waitForFunction((bay) => {
    const rows = [...document.querySelectorAll(".dep")];
    return rows.length > 0 && rows.every((r) => r.querySelector(".dep-plat b")?.textContent === bay);
  }, D.bay);
  await page.waitForSelector(".stand");
  await page.locator(".chip", { hasText: /^By (bay|platform)$/ }).click();
  await page.waitForSelector(".bay .bay-row");
  await page.locator(".chip", { hasText: "By time" }).click();
  await expandSheet();
  const n = await count(".dep");
  await page.locator(".more", { hasText: "Later departures" }).click();
  await page.waitForFunction((k) => document.querySelectorAll(".dep").length > k, n);
});

await step("trip → I'm on this one → on-board plan", async () => {
  await page.locator(".dep:not(.cancelled)").nth(2).click();
  await page.waitForSelector(".calls .tl-row");
  await page.waitForSelector("[data-testid=im-on-this]", { timeout: 8000 }).catch(() => {
    throw new Error("no “I'm on this one” on " + page.url());
  });
  await page.locator("[data-testid=im-on-this]").click();
  await page.waitForSelector(".search-screen .field.locked");
  await page.keyboard.type(D.onboardTo, { delay: 10 });
  await page.waitForSelector("#search-results .row-wrap");
  await page.keyboard.press("Enter");
  await page.waitForSelector(".jrow, .empty");
  expect(plans[plans.length - 1].onboard?.tripId, "plan request carries no onboard trip");
  if (await count(".jrow")) {
    await page.locator(".jrow").first().click();
    await page.waitForSelector(".tl");
    expect((await text(".tl")).includes("You're on"), "the journey does not start on board");
  }
});

await step("I'm on board: line and direction cards near the location", async () => {
  await ctx.addInitScript((p) => localStorage.setItem("kante.sim", JSON.stringify({ ...p, at: 0 })), D.onboardNear);
  await page.goto(server.url + "/onboard");
  await page.waitForSelector(".cand, .empty");
  const n = await count(".cand");
  expect(n <= 5, "more than five candidates offered");
  let note = `${n} candidates`;
  if (n) {
    const label = (await text(".cand-line")).trim();
    await page.locator(".filter input").fill(label);
    await page.waitForFunction((want) => {
      const c = [...document.querySelectorAll(".cand-line")];
      return c.length > 0 && c.every((x) => x.textContent.replace(/\s/g, "").includes(want.replace(/\s/g, "")));
    }, label);
    note += `, filtered to ${label}: ${(await text(".cand-main")).replace(/\s+/g, " ")}`;
    await page.locator(".cand").first().click();
    await page.waitForSelector(".search-screen .field.locked");
    await page.goBack();
  }
  await ctx.addInitScript((p) => localStorage.setItem("kante.sim", JSON.stringify({ ...p, at: 0 })), D.sim);
  return note;
});

await step("long-press menu names the place and sets a simulated location", async () => {
  await page.goto(server.url + "/");
  await page.waitForFunction(() => !!window.__kanteMap && window.__kanteMap.loaded(), null, { timeout: 30000 });
  await page.locator(".map").click({ button: "right", position: { x: 200, y: 200 } });
  await page.waitForSelector("[data-testid=sim-here]");
  if (REAL) await page.waitForFunction(() => document.querySelector(".modal h2")?.textContent !== "Map location", null, { timeout: 5000 });
  const title = await text(".modal h2");
  await page.locator("[data-testid=sim-here]").click();
  await page.waitForSelector(".sim-chip");
  expect((await mapZoom()) !== null, "map did not start");
  return title;
});

await step("a tap on a stop on any screen offers departures and directions", async () => {
  await page.waitForFunction(() => window.__kanteMap.loaded() && !window.__kanteMap.isMoving());
  const q = await page.evaluate(() => {
    const map = window.__kanteMap;
    // a boarding point in the free part of the map: clear of the chips at the top and of the sheet
    const sheetTop = document.querySelector(".sheet").getBoundingClientRect().top;
    for (const f of map.queryRenderedFeatures({ layers: ["k-signs"] })) {
      const p = map.project(f.geometry.coordinates);
      if (p.x > 40 && p.x < innerWidth - 90 && p.y > 150 && p.y < sheetTop - 140) return { x: p.x, y: p.y };
    }
    return null;
  });
  if (!q) return "no boarding point on screen — skipped";
  await page.locator(".map").click({ position: { x: Math.round(q.x), y: Math.round(q.y) } });
  await page.waitForSelector(".dep, .empty", { timeout: 10000 });
  expect(new URL(page.url()).pathname === "/station", "the boarding point did not open its board");
});

await step("shared link applies its options", async () => {
  await page.goto(`${server.url}/plan?from=${enc(D.shared[0])}&to=${enc(D.shared[1])}&o=w6.5_s1`);
  await page.waitForSelector(".jrow");
  const o = plans[plans.length - 1].options;
  expect(Math.abs(o.walkSpeed - 6.5 / 3.6) < 0.01 && o.stairs === "avoid", "options from the link were not used");
});

await step("real geolocation: the browser's position drives the home list, no simulated location", async () => {
  const c2 = await browser.newContext({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: "en-GB", timezoneId: "Europe/Zurich", serviceWorkers: "block",
    geolocation: { latitude: D.sim.lat, longitude: D.sim.lon, accuracy: 18 }, permissions: ["geolocation"],
  });
  if (D.clock) await c2.addInitScript((clock) => sessionStorage.setItem("kante.clock", String(Date.parse(clock + ":00+01:00") - Date.now())), D.clock);
  const p2 = await c2.newPage();
  const e2 = watch(p2);
  try {
    await p2.goto(server.url + "/");
    await p2.waitForSelector(".lcard-walk");
    expect((await p2.locator(".banner.locate").count()) === 0, "still asking for a location");
    expect((await p2.locator(".sim-chip", { hasText: "Simulated location" }).count()) === 0, "a simulated location is on");
    expect(e2.length === 0, e2.join("; "));
  } finally {
    await c2.close();
  }
});

if (REAL) {
  await step("address to place: Bundesgasse 3 → Inselspital, with walking as a tab", async () => {
    await page.goto(server.url + "/search?f=from");
    await page.waitForSelector(".search-screen input");
    await page.keyboard.type("bundesgasse 3 bern", { delay: 8 });
    await page.waitForFunction(() => document.querySelector("#search-results .row-wrap")?.textContent.includes("Bundesgasse 3"));
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => document.querySelector(".field.active .field-label")?.textContent === "To");
    await page.keyboard.type("inselspital", { delay: 8 });
    await page.waitForFunction(() => document.querySelector("#search-results .row-wrap")?.textContent.includes("Inselspital"));
    await page.keyboard.press("Enter");
    await page.waitForSelector(".jrow");
    await page.waitForSelector(".tabs [role=tab]");
    await page.locator(".tabs [role=tab]").nth(1).click();
    await page.waitForSelector(".walkcard");
    return (await text(".walkcard-big")).replace(/\s+/g, " ");
  });

  await step("step-free and a slow pace visibly change Zürich HB → Ostermundigen", async () => {
    const url = await planUrl(D.from, D.to, `&t=${zurich(day)}`);
    const read = async () => {
      await page.waitForSelector(".jrow");
      await page.locator(".jrow").first().click();
      await page.waitForSelector(".tl");
      const t = { times: await text(".jhead-times b"), walk: (await page.locator(".walk-meta").allInnerTexts()).join(" / ").replace(/\s+/g, " "), steps: await count(".steps .step") };
      return t;
    };
    await page.goto(url);
    const normal = await read();
    await page.goto(url + "&o=w3_s2_e0_c1");
    const slow = await read();
    expect(JSON.stringify(normal) !== JSON.stringify(slow), "the journey did not change");
    return `${normal.times} (${normal.walk}) → ${slow.times} (${slow.walk})`;
  });

  await step("rural: Scuol-Tarasp → Zermatt", async () => {
    await page.goto(await planUrl("Scuol-Tarasp", "Zermatt", `&t=${zurich(day)}`));
    await page.waitForSelector(".jrow");
    await page.locator(".jrow").first().click();
    await page.waitForSelector(".tl");
    return `${await text(".jhead-times")}, ${await count(".tl-ride")} rides`.replace(/\s+/g, " ");
  });

  await step("night: few or no journeys are shown plainly", async () => {
    await page.goto(await planUrl("Scuol-Tarasp", "Zermatt", `&t=${zurich(day.slice(0, 10) + "T23:40")}`));
    await page.waitForSelector(".jrow, .empty");
    const n = await count(".jrow");
    return n ? `${n} journeys, first ${(await text(".jrow-l2")).replace(/\s+/g, " ")}` : await text(".empty strong");
  });

  await step("offline: the shell reloads from the service worker and says it is offline", async () => {
    if (process.env.KANTE_URL) return "skipped: needs the production build (no service worker on a dev server)";
    const c2 = await context(browser, { width: 390, height: 844, sim: D.sim, clock: D.clock, sw: true });
    const p2 = await c2.newPage();
    const e2 = [];
    p2.on("pageerror", (e) => e2.push("pageerror: " + e.message));
    try {
      await p2.goto(server.url + "/");
      await p2.waitForSelector(".lcard");
      await p2.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 20000 });
      await p2.waitForTimeout(1200);
      await c2.setOffline(true);
      await p2.reload();
      await p2.waitForSelector(".searchbar-main", { timeout: 15000 });
      await p2.waitForSelector(".lcard", { timeout: 15000 });
      await p2.waitForFunction(() => /Offline|Couldn't refresh/.test(document.querySelector(".status-line")?.textContent ?? ""), null, { timeout: 45000 });
      expect(e2.length === 0, e2.join("; "));
      return (await p2.locator(".status-line").first().innerText()).trim();
    } finally {
      await c2.close();
    }
  });
}

await page.screenshot({ path: new URL("../shots/smoke-last.png", import.meta.url).pathname }).catch(() => undefined);
await browser.close();
server.stop();
if (skipped.length) console.log("\nskipped: " + skipped.join(", "));
if (errors.length) {
  failed = true;
  console.log("\nconsole / network errors:\n  " + [...new Set(errors)].join("\n  "));
}
console.log(failed ? "\nSMOKE FAILED" : `\nsmoke passed (${REAL ? "real engine at " + server.api : "mock"})`);
process.exit(failed ? 1 : 0);
