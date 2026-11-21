import type { LineBadge, Mode, Quay } from "../api/types";

// ---------------------------------------------------------------- line colours
//
// The Swiss feed carries no line colours. Every line gets one entry of a fixed
// 13-colour palette (docs/ui-research/transit.md §9.4), so it keeps the same
// colour on cards, badges, leg bars, map polylines and vehicles. Text colours
// are part of the palette (every pair ≥ 4.9 : 1), never computed at run time.

export interface LineColor {
  name: string;
  /** Light theme: surface and the text on it. */
  bg: string;
  fg: string;
  /** 12 % wash for chips and backgrounds. */
  tint: string;
  /** Dark theme: surface and the text on it (the vivid line colour). */
  dbg: string;
  dfg: string;
}

const P = (name: string, bg: string, fg: string, tint: string, dbg: string, dfg: string): LineColor => ({ name, bg, fg, tint, dbg, dfg });
const INK = "#14161A";
// table order matters: the first twelve are the wheel for numbered lines
export const PALETTE: LineColor[] = [
  P("red", "#C8322B", "#FFFFFF", "#F8E6E6", "#2E1415", "#E6908C"),
  P("rust", "#B5490A", "#FFFFFF", "#F6E9E2", "#2A180F", "#F58C4E"),
  P("amber", "#F2B400", INK, "#FDF6E0", "#352B0D", "#F2B400"),
  P("olive", "#5B7A00", "#FFFFFF", "#EBEFE0", "#1A210D", "#8CBC00"),
  P("green", "#1B7F3B", "#FFFFFF", "#E4F0E7", "#0F2218", "#29C25A"),
  P("teal", "#007A78", "#FFFFFF", "#E0EFEF", "#0A2123", "#00BCB9"),
  P("azure", "#0B72B5", "#FFFFFF", "#E2EEF6", "#0C1F2E", "#47B0F4"),
  P("blue", "#2456C8", "#FFFFFF", "#E5EBF8", "#101A31", "#87A5E9"),
  P("indigo", "#4B3FB5", "#FFFFFF", "#E9E8F6", "#17162E", "#A39CDD"),
  P("violet", "#7B2D9B", "#FFFFFF", "#EFE6F3", "#201329", "#C891DF"),
  P("magenta", "#B4237A", "#FFFFFF", "#F6E5EF", "#2A1123", "#E784BF"),
  P("brown", "#7A4A2B", "#FFFFFF", "#EFE9E6", "#201815", "#D09B79"),
  P("slate", "#3D4A5C", "#FFFFFF", "#E8E9EB", "#15181E", "#97A5BA"),
];
const byName = (n: string): LineColor => PALETTE.find((p) => p.name === n) ?? PALETTE[12]!;

/**
 * 1. Curated overrides: `operator pattern` → `line` → palette entry, for networks
 * whose riders know their lines by colour. The entries below are a starting set
 * written from memory of the operators' network maps and snapped to the palette;
 * they need checking against the published maps before anyone relies on them.
 */
const CURATED: { operator: RegExp; mode?: Mode; lines: Record<string, string> }[] = [
  {
    operator: /Verkehrsbetriebe Zürich/i,
    mode: "tram",
    lines: { "2": "red", "3": "green", "4": "indigo", "5": "brown", "6": "rust", "7": "slate", "8": "olive", "9": "violet", "10": "magenta", "11": "green", "13": "amber", "14": "azure", "15": "red", "17": "magenta" },
  },
];

const LONG_DISTANCE = /^(IC|ICE|ICN|EC|IR|IRE|RE|RJ|RJX|TGV|NJ|EN|PE|GEX|BEX|VAE|TER|RB|EXT)/;
export function isNight(line: LineBadge): boolean {
  const cat = line.category.toUpperCase();
  return /^(BN|TN|SN|NB|NFB)$/.test(cat) || /^(N|SN)\d/.test(line.name);
}

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

const cache = new Map<string, LineColor>();
export function lineColor(line: LineBadge): LineColor {
  const key = line.operator + "|" + line.mode + "|" + line.category + "|" + line.name;
  let c = cache.get(key);
  if (c) return c;
  const cat = line.category.toUpperCase();
  const curated = CURATED.find((t) => t.operator.test(line.operator) && (!t.mode || t.mode === line.mode))?.lines[line.name];
  if (curated) c = byName(curated);
  // 2. mode defaults, where colour does not identify the service
  else if (isNight(line)) c = byName("indigo");
  else if (line.mode === "boat") c = byName("teal");
  else if (line.mode === "funicular" || line.mode === "cableway" || line.mode === "lift") c = byName("brown");
  else if ((line.mode === "rail" || line.mode === "rack") && (LONG_DISTANCE.test(cat) || LONG_DISTANCE.test(line.name.toUpperCase()) || !line.name)) c = byName("slate");
  // 3. everything else by its number, consecutive numbers far apart on the wheel
  else if (/^\d+$/.test(line.name)) c = PALETTE[(Number(line.name) * 5) % 12]!;
  else c = PALETTE[hash(line.name || cat) % 12]!;
  cache.set(key, c);
  return c;
}
/** Custom properties for a line-coloured element; CSS picks the light or dark pair. */
export function lineVars(line: LineBadge): Record<string, string> {
  const c = lineColor(line);
  return { "--lc": c.bg, "--lf": c.fg, "--lt": c.tint, "--ldc": c.dbg, "--ldf": c.dfg };
}
/** Colour of a line as a stroke on the map (vivid on the dark map). */
export const lineStroke = (line: LineBadge, dark: boolean): string => (dark ? lineColor(line).dfg : lineColor(line).bg);

// ---------------------------------------------------------------- names

const MODE_NAME: Record<Mode, string> = {
  rail: "Train", tram: "Tram", bus: "Bus", metro: "Metro", boat: "Boat", funicular: "Funicular",
  cableway: "Cable car", rack: "Train", lift: "Lift", ondemand: "On-demand bus", other: "Service",
};
export const modeName = (m: Mode): string => MODE_NAME[m] ?? "Service";

/** What to print in a badge: "IC 8", "S3", "10". Empty when the feed has only an internal number. */
export function lineLabel(line: LineBadge): string {
  let n = line.name.trim();
  // cableways and funiculars often carry a four-digit timetable field number, not a public name
  if ((line.mode === "funicular" || line.mode === "cableway" || line.mode === "lift") && /^\d{3,}$/.test(n)) return "";
  // "IC8" → "IC 8" as on the departure boards; "S3", "R4" stay as they are
  const m = /^(ICE|ICN|IC|IR|RE|EC|RJX|RJ|TGV|PE|NJ|EN)(\d+)$/.exec(n);
  if (m) n = `${m[1]} ${m[2]}`;
  return n;
}
/** "Tram 9", "IC 1", "Bus 10", "Cable car". */
export function lineTitle(line: LineBadge): string {
  const label = lineLabel(line);
  if (!label) return modeName(line.mode);
  if (line.mode === "rail" || line.mode === "rack") return label;
  return `${modeName(line.mode)} ${label}`;
}

const NOUN: Record<Quay["noun"], string> = { track: "Platform", bay: "Bay", edge: "Stop", pier: "Pier", stop: "Stop" };
const NOUN_SHORT: Record<Quay["noun"], string> = { track: "Pl.", bay: "Bay", edge: "", pier: "Pier", stop: "" };
export const quayNoun = (q: Quay): string => NOUN[q.noun] ?? "Stop";
/** "A–C" from "A-C". */
export const sectors = (s: string | undefined): string => (s ? s.replace(/-/g, "–") : "");
export const sectorWord = (s: string): string => (s.replace(/[^A-Za-z0-9]/g, "").length === 1 ? "Sector" : "Sectors");
/** "Bay K1", "Platform 7", or "" when the boarding point is unsigned. */
export function quayShort(q: Quay): string {
  return q.label ? `${quayNoun(q)} ${q.label}` : "";
}
/** "Pl.", "Bay", "Pier" — the short noun for tight columns; "" for a plain stop. */
export const quayNounShort = (q: Quay): string => NOUN_SHORT[q.noun] ?? "";
/** Tight columns: "Pl. 7", "Bay C". Pair it with `quayShort` as the accessible name. */
export function quayTiny(q: Quay): string {
  return q.label ? `${NOUN_SHORT[q.noun] ?? ""} ${q.label}`.trim() : "";
}
/** "South side of Bubenbergplatz" → "South side". */
export function sideShort(q: Quay): string {
  return q.side ? cap(q.side.text.replace(/ of .*/, "")) : "";
}
export const cap = (s: string): string => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** "Level −2", "Level 1"; null for ground or unknown. */
export function levelText(level: number | undefined | null): string | null {
  if (level === undefined || level === null || level === 0) return null;
  return `Level ${levelShort(level)}`;
}
export const levelShort = (l: number): string => (l < 0 ? "−" + fmtLevel(-l) : fmtLevel(l));
const fmtLevel = (l: number): string => (Number.isInteger(l) ? String(l) : l.toFixed(1));
/** For screen readers: "ground level", "level minus 1". */
export const levelSpoken = (l: number): string => (l === 0 ? "ground level" : `level ${l < 0 ? "minus " + fmtLevel(-l) : fmtLevel(l)}`);
/** In prose: "ground level", "level −1". */
export const levelProse = (l: number): string => (l === 0 ? "ground level" : `level ${levelShort(l)}`);
