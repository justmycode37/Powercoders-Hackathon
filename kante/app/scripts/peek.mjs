// Development helper: open a page of the running app, optionally act on it, and save a screenshot.
//   node scripts/peek.mjs <out.png> <path> [--w=390 --h=844 --dark --clock=2026-11-23T08:00 --nosim --wait=sel]
//                         [click:<selector> | type:<text> | key:<Enter> | wait:<selector> | sleep:<ms> | eval:<js> ...]
import { launch, context, watch, mapIdle, expand, BERN_STATION } from "./lib.mjs";

const [out, path, ...rest] = process.argv.slice(2);
const opt = Object.fromEntries(rest.filter((a) => a.startsWith("--")).map((a) => a.slice(2).split("=")).map(([k, v]) => [k, v ?? true]));
const steps = rest.filter((a) => !a.startsWith("--"));
const base = process.env.KANTE_URL || "http://localhost:5199";
const browser = await launch();
const ctx = await context(browser, { width: Number(opt.w ?? 390), height: Number(opt.h ?? 844), dark: !!opt.dark, sim: opt.nosim ? null : BERN_STATION, clock: opt.clock });
const page = await ctx.newPage();
const errors = watch(page);
await page.goto(base + (await expand(process.env.KANTE_API || "http://localhost:8080", path)));
await page.waitForTimeout(600);
for (const s of steps) {
  const i = s.indexOf(":");
  const [cmd, arg] = [s.slice(0, i), s.slice(i + 1)];
  try {
    if (cmd === "click") await page.locator(arg).first().click({ timeout: 8000 });
    else if (cmd === "type") await page.keyboard.type(arg, { delay: 12 });
    else if (cmd === "key") await page.keyboard.press(arg);
    else if (cmd === "wait") await page.waitForSelector(arg, { timeout: 12000 });
    else if (cmd === "sleep") await page.waitForTimeout(Number(arg));
    else if (cmd === "eval") console.log("eval:", JSON.stringify(await page.evaluate(arg)));
  } catch (err) {
    console.log(`step failed: ${s}: ${err.message.split("\n")[0]}`);
  }
}
if (!opt.nomap) await mapIdle(page, 15000);
await page.screenshot({ path: out });
console.log("url:", page.url().slice(0, 300));
if (errors.length) console.log("errors:\n  " + errors.join("\n  "));
await browser.close();
