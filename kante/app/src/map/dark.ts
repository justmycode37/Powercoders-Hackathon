// Dark variant of the swisstopo light base map, derived at load time by
// remapping the lightness of every colour in the style's paint properties.
import type { StyleSpecification } from "maplibre-gl";

type RGBA = [number, number, number, number];

function parse(c: string): RGBA | null {
  const s = c.trim().toLowerCase();
  let m = /^#([0-9a-f]{3,8})$/.exec(s);
  if (m) {
    let h = m[1]!;
    if (h.length === 3 || h.length === 4) h = [...h].map((x) => x + x).join("");
    const n = parseInt(h.slice(0, 6), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, h.length === 8 ? parseInt(h.slice(6), 16) / 255 : 1];
  }
  m = /^rgba?\(([^)]+)\)$/.exec(s);
  if (m) {
    const p = m[1]!.split(/[\s,/]+/).filter(Boolean).map(Number);
    if (p.length >= 3 && p.every((x) => !Number.isNaN(x))) return [p[0]!, p[1]!, p[2]!, p[3] ?? 1];
  }
  m = /^hsla?\(([^)]+)\)$/.exec(s);
  if (m) {
    const p = m[1]!.split(/[\s,/]+/).filter(Boolean).map((x) => parseFloat(x));
    if (p.length >= 3) return [...fromHsl(p[0]!, p[1]! / 100, p[2]! / 100), p[3] ?? 1] as RGBA;
  }
  return null;
}
function toHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function fromHsl(h: number, s: number, l: number): [number, number, number] {
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => Math.round((l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))) * 255);
  return [f(0), f(8), f(4)];
}

type Remap = (h: number, s: number, l: number) => [number, number, number];
/** Land, water, buildings: invert lightness into a narrow dark range with a cool tint. */
const ground: Remap = (h, s, l) => (s < 0.1 ? [222, 0.2, 0.075 + (1 - l) * 0.5] : [h, s * 0.55, 0.08 + (1 - l) * 0.62]);
/** Road surfaces: lighter than the land so the network stays readable. */
const road: Remap = (h, s, l) => [s < 0.1 ? 222 : h, s < 0.1 ? 0.16 : s * 0.5, 0.2 + l * 0.12];
const roadCasing: Remap = (h, s, l) => [s < 0.1 ? 222 : h, s < 0.1 ? 0.18 : s * 0.5, 0.1 + (1 - l) * 0.12];
/** Text: light on dark. */
const text: Remap = (h, s, l) => [s < 0.1 ? 222 : h, s < 0.1 ? 0.12 : s * 0.7, Math.min(0.86, 0.5 + (1 - l) * 0.4)];
const halo: Remap = () => [222, 0.25, 0.08];

function convert(c: string, f: Remap): string {
  const p = parse(c);
  if (!p) return c;
  const [h, s, l] = toHsl(p[0], p[1], p[2]);
  const [r, g, b] = fromHsl(...f(h, s, l));
  return `rgba(${r},${g},${b},${p[3]})`;
}
function walk(v: unknown, f: Remap): unknown {
  if (typeof v === "string") return convert(v, f);
  if (Array.isArray(v)) return v.map((x) => walk(x, f));
  if (v && typeof v === "object") {
    const o: Record<string, unknown> = {};
    for (const [k, x] of Object.entries(v)) o[k] = walk(x, f);
    return o;
  }
  return v;
}

const HIDE = /^(hillshade|scree|hachure|pattern_landcover|contour_line)/;

export function darkStyle(base: StyleSpecification): StyleSpecification {
  const style = structuredClone(base);
  for (const layer of style.layers) {
    if (HIDE.test(layer.id)) {
      layer.layout = { ...(layer.layout ?? {}), visibility: "none" } as never;
      continue;
    }
    const paint = layer.paint as Record<string, unknown> | undefined;
    if (!paint) continue;
    const isRoadFill = /(^|_)fill$/.test(layer.id) && layer.type === "line";
    const isRoadCasing = /road_casing|tunnel_road|pedestrian|footway|parking/.test(layer.id);
    for (const key of Object.keys(paint)) {
      if (!key.endsWith("-color")) continue;
      const f = key === "text-halo-color" || key === "icon-halo-color" ? halo : key === "text-color" || key === "icon-color" ? text : isRoadFill ? road : isRoadCasing ? roadCasing : ground;
      paint[key] = walk(paint[key], f);
    }
  }
  return style;
}
