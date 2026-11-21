// Map symbols are drawn on a canvas on demand (MapLibre asks through
// "styleimagemissing"), so signs use the system font and need no sprite sheet.

export interface Sprite { data: ImageData; ratio: number }

const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const INK = "#14161A";
const EDGE = "#FFD23F";

function canvas(w: number, h: number, ratio: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement("canvas");
  c.width = Math.ceil(w * ratio);
  c.height = Math.ceil(h * ratio);
  const ctx = c.getContext("2d", { willReadFrequently: true })!;
  ctx.scale(ratio, ratio);
  return [c, ctx];
}
function rr(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}
const NOUN: Record<string, string> = { track: "Platform", bay: "Bay", edge: "Stop", pier: "Pier", stop: "Stop" };

/** id: "sg|<s|m|x|l>|<label>[|<noun>]", "vh|<name>|<bg>|<fg>|<o|p|t>", "pin|from|to", "arr|<k|g>", "lv|<u|d>|<level>" */
export function makeImage(id: string, dark: boolean): Sprite | null {
  const ratio = Math.min(3, Math.max(2, Math.ceil(window.devicePixelRatio || 1)));
  const parts = id.split("|");
  if (parts[0] === "sg") return signSprite(parts[1] ?? "s", parts[2] ?? "", parts[3] ?? "", dark, ratio);
  if (parts[0] === "vh") return vehicleSprite(parts[1] ?? "", parts[2] ?? INK, parts[3] ?? "#fff", parts[4] ?? "t", dark, ratio);
  if (parts[0] === "pin") return pinSprite(parts[1] === "to", dark, ratio);
  if (parts[0] === "arr") return arrowSprite(parts[1] === "g", dark, ratio);
  if (parts[0] === "lv") return levelSprite(parts[1] === "u", parts[2] ?? "", dark, ratio);
  return null;
}

function signSprite(variant: string, label: string, noun: string, dark: boolean, ratio: number): Sprite {
  const big = variant === "l";
  const fs = big ? 21 : variant === "s" ? 12.5 : 14.5;
  const h = big ? 38 : variant === "s" ? 21 : 25;
  const m = big ? 6 : 3; // room for the shadow / outline
  const sel = variant === "x";
  const bg = sel ? EDGE : dark ? "#F2F3F5" : INK;
  const ink = sel || dark ? INK : "#FFFFFF";
  const stripe = sel ? INK : EDGE;
  const outline = dark ? "#0B0D10" : "#FFFFFF";
  const probe = document.createElement("canvas").getContext("2d")!;
  if (!label) {
    // unsigned edge: a small marker without inventing a name
    const d = big ? 32 : variant === "s" ? 13 : 18;
    const [c, ctx] = canvas(d + m * 2, d + m * 2, ratio);
    const r = d / 2;
    if (big) {
      ctx.shadowColor = "rgba(8,12,24,.35)";
      ctx.shadowBlur = 5;
      ctx.shadowOffsetY = 1.5;
    }
    ctx.fillStyle = outline;
    ctx.beginPath();
    ctx.arc(m + r, m + r, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.fillStyle = bg;
    ctx.beginPath();
    ctx.arc(m + r, m + r, r - 1.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = stripe;
    ctx.beginPath();
    ctx.arc(m + r, m + r, r * 0.36, 0, Math.PI * 2);
    ctx.fill();
    return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
  }
  probe.font = `800 ${fs}px ${FONT}`;
  const tw = probe.measureText(label).width;
  const nounText = big ? (NOUN[noun] ?? "") : "";
  probe.font = `600 11px ${FONT}`;
  const nw = nounText ? probe.measureText(nounText).width + 6 : 0;
  const padX = big ? 9 : 5.5;
  const w = Math.max(h, tw + nw + padX * 2);
  const [c, ctx] = canvas(w + m * 2, h + m * 2, ratio);
  if (big) {
    ctx.shadowColor = "rgba(8,12,24,.4)";
    ctx.shadowBlur = 6;
    ctx.shadowOffsetY = 2;
  }
  ctx.fillStyle = outline;
  rr(ctx, m - 1.5, m - 1.5, w + 3, h + 3, big ? 8.5 : 6.5);
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.save();
  rr(ctx, m, m, w, h, big ? 7 : 5);
  ctx.clip();
  ctx.fillStyle = bg;
  ctx.fillRect(m, m, w, h);
  ctx.fillStyle = stripe;
  ctx.fillRect(m, m + h - (big ? 4.5 : 3), w, big ? 4.5 : 3);
  ctx.restore();
  ctx.fillStyle = ink;
  ctx.textBaseline = "middle";
  const cy = m + (h - (big ? 4.5 : 3)) / 2 + 0.5;
  let x = m + (w - tw - nw) / 2;
  if (nounText) {
    ctx.font = `600 11px ${FONT}`;
    ctx.fillText(nounText, x, cy + 0.5);
    x += nw;
  }
  ctx.font = `800 ${fs}px ${FONT}`;
  ctx.fillText(label, x, cy);
  return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
}

function vehicleSprite(name: string, bg: string, fg: string, live: string, dark: boolean, ratio: number): Sprite {
  const probe = document.createElement("canvas").getContext("2d")!;
  const label = name.length > 6 ? name.slice(0, 6) : name;
  probe.font = `800 11px ${FONT}`;
  const tw = probe.measureText(label).width;
  const h = 19;
  const w = Math.max(h, tw + 11);
  const m = 3;
  const [c, ctx] = canvas(w + m * 2, h + m * 2, ratio);
  const solid = live !== "t";
  // timetable-only vehicles are hollow with a dashed outline: clearly a guess
  ctx.fillStyle = solid ? (dark ? "#0B0D10" : "#FFFFFF") : "transparent";
  rr(ctx, m - 1.5, m - 1.5, w + 3, h + 3, (h + 3) / 2);
  ctx.fill();
  ctx.fillStyle = solid ? bg : dark ? "#141A26" : "#FFFFFF";
  rr(ctx, m, m, w, h, h / 2);
  ctx.fill();
  if (!solid || live === "p") {
    ctx.strokeStyle = solid ? "rgba(255,255,255,.9)" : bg;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 2.2]);
    rr(ctx, m + 0.75, m + 0.75, w - 1.5, h - 1.5, (h - 1.5) / 2);
    ctx.stroke();
  }
  ctx.fillStyle = solid ? fg : dark ? "#E6EAF5" : bg;
  ctx.font = `800 11px ${FONT}`;
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  ctx.fillText(label, m + w / 2, m + h / 2 + 0.5);
  return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
}

/** Origin: a ring. Destination: an ink pin with the yellow dot. The same two shapes as in the from/to card and the timeline. */
function pinSprite(dest: boolean, dark: boolean, ratio: number): Sprite {
  if (!dest) {
    const d = 18;
    const [c, ctx] = canvas(d + 8, d + 8, ratio);
    ctx.shadowColor = "rgba(8,10,14,.35)";
    ctx.shadowBlur = 3;
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = "#FFFFFF";
    ctx.beginPath();
    ctx.arc(4 + d / 2, 4 + d / 2, d / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.strokeStyle = INK;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(4 + d / 2, 4 + d / 2, d / 2 - 3.5, 0, Math.PI * 2);
    ctx.stroke();
    return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
  }
  const w = 26;
  const h = 34;
  const [c, ctx] = canvas(w + 8, h + 6, ratio);
  ctx.translate(4, 2);
  ctx.shadowColor = "rgba(8,10,14,.4)";
  ctx.shadowBlur = 4;
  ctx.shadowOffsetY = 1.5;
  ctx.fillStyle = dark ? "#F2F3F5" : INK;
  ctx.beginPath();
  ctx.moveTo(w / 2, h);
  ctx.bezierCurveTo(w / 2 - 3, h - 9, 0, h - 14, 0, w / 2);
  ctx.arc(w / 2, w / 2, w / 2, Math.PI, 0);
  ctx.bezierCurveTo(w, h - 14, w / 2 + 3, h - 9, w / 2, h);
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.fillStyle = dark ? INK : EDGE;
  ctx.beginPath();
  ctx.arc(w / 2, w / 2, 5, 0, Math.PI * 2);
  ctx.fill();
  return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
}

/** Arrowhead pointing east; MapLibre turns it along the walking route. */
function arrowSprite(grey: boolean, dark: boolean, ratio: number): Sprite {
  const [c, ctx] = canvas(9, 9, ratio);
  ctx.fillStyle = grey ? (dark ? "#9AA3B2" : "#7B8494") : INK;
  ctx.beginPath();
  ctx.moveTo(1.2, 1);
  ctx.lineTo(8, 4.5);
  ctx.lineTo(1.2, 8);
  ctx.lineTo(2.8, 4.5);
  ctx.closePath();
  ctx.fill();
  return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
}

/** Pill pinned to the route where it changes level: which way, and the level it leads to. */
function levelSprite(up: boolean, label: string, dark: boolean, ratio: number): Sprite {
  const probe = document.createElement("canvas").getContext("2d")!;
  probe.font = `700 13px ${FONT}`;
  const tw = probe.measureText(label).width;
  const h = 24;
  const w = tw + 32;
  const m = 4;
  const [c, ctx] = canvas(w + m * 2, h + m * 2, ratio);
  ctx.shadowColor = "rgba(8,10,14,.35)";
  ctx.shadowBlur = 4;
  ctx.shadowOffsetY = 1;
  ctx.fillStyle = dark ? "#23272E" : "#FFFFFF";
  rr(ctx, m, m, w, h, h / 2);
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.strokeStyle = dark ? "#F2F3F5" : INK;
  ctx.lineWidth = 1.5;
  rr(ctx, m + 0.75, m + 0.75, w - 1.5, h - 1.5, (h - 1.5) / 2);
  ctx.stroke();
  // arrow up or down
  const ax = m + 12;
  const cy = m + h / 2;
  ctx.lineWidth = 2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  const d = up ? -1 : 1;
  ctx.moveTo(ax, cy - 5 * d);
  ctx.lineTo(ax, cy + 5 * d);
  ctx.moveTo(ax - 4, cy + 1 * d);
  ctx.lineTo(ax, cy + 5 * d);
  ctx.lineTo(ax + 4, cy + 1 * d);
  ctx.stroke();
  ctx.fillStyle = dark ? "#F2F3F5" : INK;
  ctx.font = `700 13px ${FONT}`;
  ctx.textBaseline = "middle";
  ctx.fillText(label, m + 22, cy + 0.5);
  return { data: ctx.getImageData(0, 0, c.width, c.height), ratio };
}
