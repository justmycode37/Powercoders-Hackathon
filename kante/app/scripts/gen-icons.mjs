// Renders the PNG app icons from public/icons/icon.svg with headless Chromium.
import { chromium } from "playwright";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dir = fileURLToPath(new URL("../public/icons/", import.meta.url));
const svg = readFileSync(dir + "icon.svg", "utf8");
// maskable: full-bleed background, glyph inside the central safe zone
const maskable = svg
  .replace('rx="112"', 'rx="0"')
  .replace('<g fill="#fff">', '<g fill="#fff" transform="translate(256 240) scale(.72) translate(-256 -232)">');

const browser = await chromium.launch();
const page = await browser.newPage();
for (const [name, size, src] of [["icon-192.png", 192, svg], ["icon-512.png", 512, svg], ["maskable-512.png", 512, maskable]]) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(`<style>html,body{margin:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${src}`);
  await page.screenshot({ path: dir + name, omitBackground: true });
  console.log("wrote", name);
}
await browser.close();
