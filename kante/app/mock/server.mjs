// @ts-check
// Mock Kante engine: implements every endpoint of src/api/types.ts on a small
// synthetic timetable around Bern (plus the rail corridor to Zürich) so the app
// can be developed and tested without the Rust server.
//
//   node mock/server.mjs            listens on :8080 (PORT overrides)
//   KANTE_MOCK_NOW=2026-11-23T14:02:00+01:00 node mock/server.mjs
//       starts the mock's clock at that instant (the app follows the HTTP Date header)

/** @import * as T from '../src/api/types.ts' */
/** @import { LineDef, Station, WEdge } from './data.mjs' */

import http from "node:http";
import { stations, quaysById, quayNodes, lines, places, wnodes, wedges, streetNodes } from "./data.mjs";

const PORT = Number(process.env.PORT) || 8080;
const LATENCY = Number(process.env.KANTE_MOCK_LATENCY) || 0;
const SKEW_MS = process.env.KANTE_MOCK_NOW ? Date.parse(process.env.KANTE_MOCK_NOW) - Date.now() : 0;
if (Number.isNaN(SKEW_MS)) throw new Error("KANTE_MOCK_NOW is not a date");
const nowMs = () => Date.now() + SKEW_MS;
const nowS = () => Math.floor(nowMs() / 1000);

// ---------------------------------------------------------------- helpers

const R = 6371000;
const rad = Math.PI / 180;
/** @param {number} lat1 @param {number} lon1 @param {number} lat2 @param {number} lon2 */
function dist(lat1, lon1, lat2, lon2) {
  const x = (lon2 - lon1) * rad * Math.cos(((lat1 + lat2) / 2) * rad);
  const y = (lat2 - lat1) * rad;
  return Math.sqrt(x * x + y * y) * R;
}
/** @param {number} lat1 @param {number} lon1 @param {number} lat2 @param {number} lon2 */
function bearing(lat1, lon1, lat2, lon2) {
  const x = (lon2 - lon1) * Math.cos(((lat1 + lat2) / 2) * rad);
  const y = lat2 - lat1;
  return (Math.atan2(x, y) / rad + 360) % 360;
}
/** @param {string} s */
function hash(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
const zfmt = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Europe/Zurich", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
/** @param {number} unix */
function zparts(unix) {
  /** @type {Record<string, string>} */
  const p = {};
  for (const x of zfmt.formatToParts(new Date(unix * 1000))) p[x.type] = x.value;
  return { date: `${p.year}-${p.month}-${p.day}`, secs: +p.hour * 3600 + +p.minute * 60 + +p.second };
}
/** Unix time of local midnight of a service date. @param {string} date */
function dayStart(date) {
  const [y, m, d] = date.split("-").map(Number);
  const utc = Date.UTC(y, m - 1, d) / 1000;
  return utc - zparts(utc).secs;
}
/** @param {string} date @param {number} days */
function addDays(date, days) {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}
/** @param {string} s */
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();

/** @param {Station} s @param {{ lat: number, lon: number } | null} [near] @returns {T.Place} */
function stationPlace(s, near) {
  /** @type {T.Place} */
  const p = { id: s.id, kind: "station", name: s.name, lat: s.lat, lon: s.lon, modes: s.modes };
  if (near) p.distM = Math.round(dist(near.lat, near.lon, s.lat, s.lon));
  return p;
}
const stationList = Object.values(stations);
/** @type {Record<string, Station>} */
const stationById = Object.fromEntries(stationList.map((s) => [s.id, s]));

// ---------------------------------------------------------------- timetable

/**
 * @typedef {Object} DirStop
 * @property {Station} station
 * @property {T.Quay} quay
 * @property {number} t seconds from the first stop of this direction
 */
/** @typedef {{ line: LineDef, dir: 0 | 1, stops: DirStop[], headsign: string, duration: number }} Pattern */

/** @param {string} name */
function headsignOf(name) {
  if (name.startsWith("Wabern")) return "Wabern";
  return name.replace(/^(Bern|Zürich|Köniz), /, "").replace(/^Bern (?=Wankdorf|Bümpliz|Brünnen)/, "").replace(", ", " ");
}

/** @type {Pattern[]} */
const patterns = [];
for (const line of lines) {
  const total = line.stops[line.stops.length - 1].t;
  for (const dir of /** @type {const} */ ([0, 1])) {
    const src = dir === 0 ? line.stops : [...line.stops].reverse();
    const stops = src.map((s) => {
      const station = stations[s.station];
      return { station, quay: quaysById[`${station.didok}:0:${s.quay[dir]}`], t: dir === 0 ? s.t : total - s.t };
    });
    patterns.push({ line, dir, stops, headsign: headsignOf(stops[stops.length - 1].station.name), duration: total });
  }
}
/** @type {Map<string, Pattern>} */
const patternByKey = new Map(patterns.map((p) => [`${p.line.id}.${p.dir}`, p]));

/**
 * @typedef {Object} Trip
 * @property {string} id
 * @property {string} date
 * @property {Pattern} pattern
 * @property {number} dep0 unix time of the first departure
 * @property {number | undefined} delayS live delay (undefined: no live data)
 * @property {number} routeDelayS delay the planner knew about (late-breaking delays are 0 here)
 * @property {boolean} cancelled
 * @property {boolean} routable
 * @property {(T.Quay | null)[]} moved per stop: boarding point live data moved the call to
 */

/** @type {Map<string, Trip>} */
const tripCache = new Map();

/** @param {Pattern} p @param {string} date @param {number} k @returns {Trip | null} */
function makeTrip(p, date, k) {
  const first = (p.line.firstS ?? 0) + p.line.offsetS + (p.dir ? Math.round(p.line.headwayS / 2) : 0);
  const rel = first + k * p.line.headwayS;
  if (k < 0 || rel >= (p.line.lastS ?? 86400)) return null;
  const id = `${p.line.id}.${p.dir}.${k}`;
  const key = id + "@" + date;
  let t = tripCache.get(key);
  if (t) return t;
  const h = hash(key);
  const hasLive = p.line.live !== "timetable";
  let delayS;
  if (hasLive) {
    const r = h % 100;
    delayS = r < 50 ? 0 : r < 75 ? 60 + (h % 3) * 60 : r < 90 ? 240 + (h % 4) * 60 : 0;
  }
  const cancelled = hasLive && h % 53 === 7;
  const lateBreaking = (h >>> 8) % 4 === 0;
  /** @type {(T.Quay | null)[]} */
  const moved = p.stops.map(() => null);
  if (hasLive) {
    p.stops.forEach((s, i) => {
      if (s.station.key === "bern" && s.quay.level === 0 && (h >>> 4) % 6 === 2) {
        const n = Number(s.quay.label);
        const other = n === 9 ? 10 : n === 10 ? 9 : n === 12 ? 13 : n === 13 ? 12 : n % 2 ? n + 1 : n - 1;
        moved[i] = quaysById[`8507000:0:${other}`] ?? null;
      }
      if (s.station.key === "bernbhf" && s.quay.label === "L" && (h >>> 4) % 5 === 1) moved[i] = quaysById["8576646:0:A"];
    });
  }
  t = {
    id, date, pattern: p, dep0: dayStart(date) + rel, delayS,
    routeDelayS: lateBreaking ? 0 : (delayS ?? 0),
    cancelled, routable: !cancelled || lateBreaking, moved,
  };
  if (tripCache.size > 60000) tripCache.clear();
  tripCache.set(key, t);
  return t;
}

/** Trips of a pattern whose run overlaps [a, b]. @param {Pattern} p @param {number} a @param {number} b @returns {Trip[]} */
function tripsBetween(p, a, b) {
  /** @type {Trip[]} */
  const out = [];
  const lo = a - p.duration - 600;
  let date = zparts(lo).date;
  for (let d = 0; d < 4; d++, date = addDays(date, 1)) {
    const start = dayStart(date);
    if (start > b) break;
    const first = (p.line.firstS ?? 0) + p.line.offsetS + (p.dir ? Math.round(p.line.headwayS / 2) : 0);
    const k0 = Math.max(0, Math.ceil((lo - start - first) / p.line.headwayS));
    for (let k = k0; ; k++) {
      const t = makeTrip(p, date, k);
      if (!t || t.dep0 > b) break;
      out.push(t);
    }
  }
  return out;
}

/** @param {string} id @param {string} date @returns {Trip | null} */
function findTrip(id, date) {
  const m = /^(.*)\.([01])\.(\d+)$/.exec(id);
  if (!m || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const p = patternByKey.get(`${m[1]}.${m[2]}`);
  return p ? makeTrip(p, date, Number(m[3])) : null;
}

/** @param {Trip} t @param {number} i */
const sched = (t, i) => t.dep0 + t.pattern.stops[i].t;
/** @param {Trip} t @param {number} i */
function quayAt(t, i) {
  const s = t.pattern.stops[i];
  const base = t.moved[i] ?? s.quay;
  return base.noun === "track" && t.pattern.line.sectors ? { ...base, sectors: t.pattern.line.sectors } : base;
}
/** @param {Trip} t @param {number} i @returns {T.StopCall} */
function stopCall(t, i) {
  const n = t.pattern.stops.length;
  /** @type {T.StopCall} */
  const c = { seq: i, quay: quayAt(t, i) };
  if (i > 0) c.arr = sched(t, i);
  if (i < n - 1) c.dep = sched(t, i);
  if (t.delayS !== undefined) {
    if (i > 0) c.arrDelayS = t.delayS;
    if (i < n - 1) c.depDelayS = t.delayS;
  }
  if (t.moved[i]) c.plannedLabel = t.pattern.stops[i].quay.label;
  return c;
}
/** @param {Trip} t @returns {"observed" | "predicted" | "timetable"} */
function liveState(t) {
  if (t.delayS === undefined) return "timetable";
  return t.dep0 + (t.delayS ?? 0) <= nowS() ? t.pattern.line.live : "predicted";
}

// ---------------------------------------------------------------- walking

/** @typedef {{ lat: number, lon: number, level: number | null, id?: string }} Pt */
/**
 * @typedef {Object} Seg one traversed edge, oriented
 * @property {Pt} a
 * @property {Pt} b
 * @property {WEdge["kind"]} kind
 * @property {string} name
 * @property {number} steps
 * @property {number} lenM
 * @property {boolean} indoor
 * @property {[number, number][]} via
 */

/** @type {Map<string, { to: string, edge: WEdge, rev: boolean, lenM: number }[]>} */
const adj = new Map();
for (const id of Object.keys(wnodes)) adj.set(id, []);
for (const edge of wedges) {
  const a = wnodes[edge.a];
  const b = wnodes[edge.b];
  let len = edge.lenM;
  if (len === undefined) {
    const pts = [[a.lon, a.lat], ...(edge.via ?? []), [b.lon, b.lat]];
    len = 0;
    for (let i = 1; i < pts.length; i++) len += dist(pts[i - 1][1], pts[i - 1][0], pts[i][1], pts[i][0]);
    if (edge.kind === "steps") len = Math.max(len, (edge.steps ?? 10) * 0.3);
    if (edge.kind === "lift") len = 4;
  }
  adj.get(edge.a)?.push({ to: edge.b, edge, rev: false, lenM: len });
  adj.get(edge.b)?.push({ to: edge.a, edge, rev: true, lenM: len });
}

/**
 * Seconds to traverse and routing weight; null when the profile may not use the edge.
 * @param {WEdge["kind"]} kind @param {number} lenM @param {number} steps @param {T.WalkOptions} o
 */
function edgeCost(kind, lenM, steps, o) {
  const v = Math.max(0.3, o.walkSpeed);
  switch (kind) {
    case "steps": {
      if (o.stairs === "never" || o.wheelchair) return null;
      const s = (steps * 0.78) / v;
      return { s, w: o.stairs === "avoid" ? s * 3 + 20 : s };
    }
    case "escalator": {
      if (!o.escalators || o.wheelchair) return null;
      const s = lenM / 0.5;
      return { s, w: s };
    }
    case "lift":
      return { s: 40, w: 40 };
    case "crossing": {
      const s = lenM / v + 15;
      return { s, w: s };
    }
    default: {
      const s = lenM / v;
      return { s, w: s };
    }
  }
}
/** @param {T.WalkOptions} o */
const optKey = (o) => `${o.walkSpeed}|${o.stairs}|${o.escalators}|${o.wheelchair}`;

/**
 * Dijkstra over the station graph from several sources.
 * @param {{ id: string, w: number }[]} sources @param {T.WalkOptions} o
 */
function dijkstra(sources, o) {
  /** @type {Map<string, number>} */
  const best = new Map();
  /** @type {Map<string, { from: string, edge: WEdge, rev: boolean, lenM: number } | null>} */
  const prev = new Map();
  /** @type {{ id: string, w: number }[]} */
  const queue = [];
  for (const s of sources) {
    if ((best.get(s.id) ?? Infinity) > s.w) {
      best.set(s.id, s.w);
      prev.set(s.id, null);
      queue.push({ id: s.id, w: s.w });
    }
  }
  while (queue.length) {
    let mi = 0;
    for (let i = 1; i < queue.length; i++) if (queue[i].w < queue[mi].w) mi = i;
    const cur = queue.splice(mi, 1)[0];
    if (cur.w > (best.get(cur.id) ?? Infinity)) continue;
    for (const nb of adj.get(cur.id) ?? []) {
      const c = edgeCost(nb.edge.kind, nb.lenM, nb.edge.steps ?? 0, o);
      if (!c) continue;
      const w = cur.w + c.w;
      if (w < (best.get(nb.to) ?? Infinity)) {
        best.set(nb.to, w);
        prev.set(nb.to, { from: cur.id, edge: nb.edge, rev: nb.rev, lenM: nb.lenM });
        queue.push({ id: nb.to, w });
      }
    }
  }
  return { best, prev };
}

/** Single-source results per node and profile; the graph is tiny, so this makes planning instant. @type {Map<string, ReturnType<typeof dijkstra>>} */
const ssCache = new Map();
/** @param {string} id @param {T.WalkOptions} o */
function fromNode(id, o) {
  const key = id + "|" + optKey(o);
  let r = ssCache.get(key);
  if (!r) {
    r = dijkstra([{ id, w: 0 }], o);
    if (ssCache.size > 4000) ssCache.clear();
    ssCache.set(key, r);
  }
  return r;
}

/** @typedef {{ name: string, lat: number, lon: number, quay?: T.Quay }} WPoint */

/** Graph nodes a point can be attached to, with the connector length. @param {WPoint} p */
function attach(p) {
  const ids = p.quay ? quayNodes[p.quay.id] : undefined;
  if (ids) return ids.map((id) => ({ id, d: dist(p.lat, p.lon, wnodes[id].lat, wnodes[id].lon) }));
  if (p.quay && (p.quay.level ?? 0) !== 0) return [];
  return streetNodes
    .map((id) => ({ id, d: dist(p.lat, p.lon, wnodes[id].lat, wnodes[id].lon) }))
    .filter((x) => x.d < 320)
    .sort((a, b) => a.d - b.d)
    .slice(0, 3);
}

/** @param {number | null | undefined} l */
const lvl = (l) => l ?? 0;
/** @param {number | null | undefined} l */
const levelName = (l) => (l == null || l === 0 ? "street level" : "level " + (l < 0 ? "−" + -l : l));

/**
 * Route on foot between two points with the given profile.
 * @param {WPoint} from @param {WPoint} to @param {T.WalkOptions} o
 * @returns {Omit<T.WalkLeg, "type" | "kind" | "dep" | "arr" | "slackS">}
 */
function walkRoute(from, to, o) {
  const v = Math.max(0.3, o.walkSpeed);
  const straight = dist(from.lat, from.lon, to.lat, to.lon);
  const fromPt = { name: from.name, lat: from.lat, lon: from.lon, ...(from.quay ? { quay: from.quay } : {}) };
  const toPt = { name: to.name, lat: to.lat, lon: to.lon, ...(to.quay ? { quay: to.quay } : {}) };
  const fl = from.quay?.level ?? null;
  const tl = to.quay?.level ?? null;
  if (straight < 1) {
    return {
      from: fromPt, to: toPt, durationS: 0, distanceM: 0, stairsUp: 0, stairsDown: 0, lifts: 0, escalators: 0, stepFree: true,
      geometry: [[from.lon, from.lat], [to.lon, to.lat]], levels: [fl, tl], steps: [],
    };
  }
  const A = attach(from);
  const B = attach(to);
  /** @type {Seg[] | null} */
  let segs = null;
  if (A.length && B.length && !(straight < 70 && lvl(fl) === lvl(tl))) {
    let end = null;
    let endW = Infinity;
    let prev = fromNode(A[0].id, o).prev;
    for (const a of A) {
      const ss = fromNode(a.id, o);
      for (const b of B) {
        const w = a.d / v + (ss.best.get(b.id) ?? Infinity) + b.d / v;
        if (w < endW) {
          endW = w;
          end = b;
          prev = ss.prev;
        }
      }
    }
    if (end && endW < Infinity) {
      /** @type {Seg[]} */
      const chain = [];
      let cur = end.id;
      for (;;) {
        const p = prev.get(cur);
        if (!p) break;
        const a = wnodes[p.from];
        const b = wnodes[cur];
        const via = p.edge.via ?? [];
        chain.push({
          a, b, kind: p.edge.kind, name: p.edge.name, steps: p.edge.steps ?? 0, lenM: p.lenM, indoor: !!p.edge.indoor,
          via: p.rev ? [...via].reverse() : via,
        });
        cur = p.from;
      }
      chain.reverse();
      const startNode = wnodes[cur];
      const endNode = wnodes[end.id];
      /** @returns {WEdge["kind"]} */
      const conn = (/** @type {WPoint} */ p, /** @type {number | null} */ level) =>
        p.quay?.noun === "track" ? "platform" : level !== null ? "corridor" : "footway";
      segs = [];
      const dA = dist(from.lat, from.lon, startNode.lat, startNode.lon);
      if (dA > 2)
        segs.push({ a: { lat: from.lat, lon: from.lon, level: fl ?? startNode.level }, b: startNode, kind: conn(from, startNode.level), name: "", steps: 0, lenM: dA, indoor: false, via: [] });
      segs.push(...chain);
      if (end.d > 2)
        segs.push({ a: endNode, b: { lat: to.lat, lon: to.lon, level: tl ?? endNode.level }, kind: conn(to, endNode.level), name: "", steps: 0, lenM: end.d, indoor: false, via: [] });
      // an outdoor detour through the graph that is much longer than the bee line is not a real path
      const total = segs.reduce((s, x) => s + x.lenM, 0);
      const flat = segs.every((x) => x.a.level === null && x.b.level === null);
      if (flat && total > straight * 1.9 + 40) segs = null;
    }
  }
  if (!segs) {
    // no network here: bee line with a detour factor
    const d = straight * 1.25;
    const outside = !(A.length && B.length);
    return {
      from: fromPt, to: toPt, durationS: Math.round(d / v), distanceM: Math.round(d),
      stairsUp: 0, stairsDown: 0, lifts: 0, escalators: 0, stepFree: true,
      ...(outside ? { approximate: true } : {}),
      geometry: [[from.lon, from.lat], [to.lon, to.lat]], levels: [fl, tl],
      steps: [
        { kind: "depart", text: `Walk to ${to.quay?.label ? nounName(to.quay) + " " + to.quay.label : to.name}`, distM: Math.round(d), durS: Math.round(d / v), from: 0, to: 1 },
        { kind: "arrive", text: `Arrive at ${to.quay?.label ? nounName(to.quay) + " " + to.quay.label : to.name}`, distM: 0, durS: 0, from: 1, to: 1 },
      ],
    };
  }

  /** @type {[number, number][]} */
  const geometry = [[segs[0].a.lon, segs[0].a.lat]];
  /** @type {(number | null)[]} */
  const levels = [segs[0].a.level];
  /** @type {T.WalkStep[]} */
  const steps = [];
  let durS = 0;
  let distM = 0;
  let up = 0;
  let down = 0;
  let lifts = 0;
  let esc = 0;
  /** @type {string | null} */
  let lastClass = null;
  segs.forEach((sg, i) => {
    const startIdx = geometry.length - 1;
    for (const p of sg.via) {
      geometry.push(p);
      levels.push(sg.a.level);
    }
    geometry.push([sg.b.lon, sg.b.lat]);
    levels.push(sg.b.level);
    const cost = edgeCost(sg.kind, sg.lenM, sg.steps, o) ?? { s: sg.lenM / v, w: 0 };
    durS += cost.s;
    distM += sg.lenM;
    const dl = lvl(sg.b.level) - lvl(sg.a.level);
    /** @type {T.WalkStepKind} */
    let kind = "walk";
    let text = "";
    const next = segs[i + 1];
    const target = next?.kind === "platform" || (sg.b.id ?? "").startsWith("p") ? "the platform" : levelName(sg.b.level);
    if (sg.kind === "steps") {
      kind = dl >= 0 ? "stairs-up" : "stairs-down";
      text = `Take the stairs ${dl >= 0 ? "up" : "down"} to ${target}`;
      if (dl >= 0) up += sg.steps;
      else down += sg.steps;
    } else if (sg.kind === "escalator") {
      kind = dl >= 0 ? "escalator-up" : "escalator-down";
      text = `Take the escalator ${dl >= 0 ? "up" : "down"} to ${target}`;
      esc++;
    } else if (sg.kind === "lift") {
      kind = "lift";
      text = `Take the lift from ${levelName(sg.a.level)} to ${levelName(sg.b.level)}`;
      lifts++;
    } else if (sg.kind === "crossing") {
      kind = "cross";
      text = `Cross ${sg.name || "the road"}`;
    } else if (sg.kind === "platform") {
      kind = "platform";
      text = sg.name ? `Walk along ${sg.name.replace("Platform", "platform")}` : i === 0 ? "Walk along the platform to the exit" : `Walk along the platform to ${to.quay ? "track " + to.quay.label : to.name}`;
    } else if (dl !== 0 && sg.a.level !== null && sg.b.level !== null) {
      kind = dl > 0 ? "ramp-up" : "ramp-down";
      text = `Follow the ramp ${dl > 0 ? "up" : "down"} to ${target}`;
    } else if (sg.indoor && sg.a.level === null && sg.b.level !== null) {
      kind = "enter";
      text = `Enter the station${sg.name ? " at the " + sg.name.toLowerCase() : ""}`;
    } else if (sg.indoor && sg.b.level === null && sg.a.level !== null) {
      kind = "exit";
      text = `Leave the station${sg.name ? " by the " + sg.name.toLowerCase() : ""}`;
    } else {
      text = sg.name ? (sg.kind === "corridor" ? `Walk through ${sg.name}` : `Walk along ${sg.name}`) : i === segs.length - 1 ? `Walk to ${to.name}` : "Continue";
    }
    const cls = kind + "|" + sg.name;
    const last = steps[steps.length - 1];
    if (last && lastClass === cls && (kind === "walk" || kind === "platform")) {
      last.distM += sg.lenM;
      last.durS += cost.s;
      last.to = geometry.length - 1;
      if (sg.b.level !== null) last.toLevel = sg.b.level;
    } else {
      /** @type {T.WalkStep} */
      const step = { kind, text, distM: sg.lenM, durS: cost.s, from: startIdx, to: geometry.length - 1 };
      if (sg.name) step.name = sg.name;
      if (sg.a.level !== null) step.level = sg.a.level;
      if (sg.b.level !== null) step.toLevel = sg.b.level;
      steps.push(step);
    }
    lastClass = cls;
  });
  if (steps.length && steps[0].kind === "walk") {
    steps[0].kind = "depart";
    const b = bearing(geometry[0][1], geometry[0][0], geometry[1][1], geometry[1][0]);
    const dirs = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];
    const where = steps[0].name ? ` on ${steps[0].name}` : "";
    steps[0].text = `Head ${dirs[Math.round(b / 45) % 8]}${where}`;
  }
  for (const s of steps) {
    s.distM = Math.round(s.distM);
    s.durS = Math.round(s.durS);
  }
  const toName = to.quay ? `${nounName(to.quay)}${to.quay.label ? " " + to.quay.label : ""}`.trim() || to.name : to.name;
  /** @type {T.WalkStep} */
  const arrive = { kind: "arrive", text: `Arrive at ${to.quay?.label ? toName : to.name}`, distM: 0, durS: 0, from: geometry.length - 1, to: geometry.length - 1 };
  if (levels[levels.length - 1] !== null) arrive.level = /** @type {number} */ (levels[levels.length - 1]);
  steps.push(arrive);
  return {
    from: fromPt, to: toPt, durationS: Math.round(durS), distanceM: Math.round(distM),
    stairsUp: up, stairsDown: down, lifts, escalators: esc, stepFree: up + down + esc === 0,
    geometry, levels, steps,
  };
}
/** @param {T.Quay} quay */
function nounName(quay) {
  return { track: "Platform", bay: "Bay", edge: "", pier: "Pier", stop: "" }[quay.noun];
}

/** quay → nearby quays (static neighbourhood for footpaths) @type {Map<string, T.Quay[]>} */
const neighbours = new Map();
const allQuays = Object.values(quaysById);
for (const a of allQuays) {
  neighbours.set(a.id, allQuays.filter((b) => b !== a && (a.stationId === b.stationId || dist(a.lat, a.lon, b.lat, b.lon) < 480)));
}

/** @type {Map<string, number>} */
const walkSecsCache = new Map();
/** Walking seconds between two boarding points. @param {T.Quay} a @param {T.Quay} b @param {T.WalkOptions} o */
function transferSecs(a, b, o) {
  if (a.id === b.id) return 0;
  const key = `${a.id}>${b.id}|${optKey(o)}`;
  let s = walkSecsCache.get(key);
  if (s === undefined) {
    s = walkRoute(pointOfQuay(a), pointOfQuay(b), o).durationS;
    if (walkSecsCache.size > 200000) walkSecsCache.clear();
    walkSecsCache.set(key, s);
  }
  return s;
}
/** @param {T.Quay} quay @returns {WPoint} */
function pointOfQuay(quay) {
  return { name: quay.stationName, lat: quay.lat, lon: quay.lon, quay };
}

// ---------------------------------------------------------------- journey planning (connection scan)

/**
 * @typedef {Object} Label how a boarding point was reached
 * @property {"access" | "ride" | "onboard"} type
 * @property {number} ready earliest time a vehicle can be boarded here
 * @property {T.Quay} [quay]
 * @property {number} [walkS] walking seconds of the access / transfer that ended here
 * @property {Trip} [trip]
 * @property {number} [enter] stop index boarded
 * @property {number} [exit] stop index alighted
 * @property {Label} [prev]
 */

/** @typedef {{ trip: Trip, i: number, dep: number, arr: number, from: T.Quay, to: T.Quay }} Conn */

/** @param {number} a @param {number} b @param {T.PlanOptions} o @returns {Conn[]} */
function connections(a, b, o) {
  /** @type {Conn[]} */
  const out = [];
  for (const p of patterns) {
    if (o.modes && !o.modes.includes(p.line.badge.mode)) continue;
    for (const t of tripsBetween(p, a, b)) {
      if (!t.routable) continue;
      for (let i = 0; i < p.stops.length - 1; i++) {
        const dep = sched(t, i) + t.routeDelayS;
        if (dep < a) continue;
        out.push({ trip: t, i, dep, arr: sched(t, i + 1) + t.routeDelayS, from: quayAt(t, i), to: quayAt(t, i + 1) });
      }
    }
  }
  out.sort((x, y) => x.dep - y.dep);
  return out;
}

/** @typedef {{ place: T.Place, station: Station | null, point: WPoint }} Endpoint */

/** @param {T.PlaceRef} ref @returns {Endpoint | null} */
function resolve(ref) {
  if (ref.id) {
    const s = stationById[ref.id];
    if (s) return { place: stationPlace(s), station: s, point: { name: s.name, lat: s.lat, lon: s.lon } };
    const pl = places.find((p) => p.id === ref.id);
    if (pl) return { place: pl, station: null, point: { name: pl.name, lat: pl.lat, lon: pl.lon } };
    const m = /^coord:(-?[\d.]+),(-?[\d.]+)$/.exec(ref.id);
    if (m) ref = { lat: Number(m[1]), lon: Number(m[2]), name: ref.name };
  }
  if (typeof ref.lat === "number" && typeof ref.lon === "number" && Number.isFinite(ref.lat) && Number.isFinite(ref.lon)) {
    const name = ref.name || reverse(ref.lat, ref.lon);
    /** @type {T.Place} */
    const place = { id: `coord:${ref.lat.toFixed(5)},${ref.lon.toFixed(5)}`, kind: "coord", name, lat: ref.lat, lon: ref.lon };
    return { place, station: null, point: { name, lat: ref.lat, lon: ref.lon } };
  }
  return null;
}
/** @param {number} lat @param {number} lon */
function reverse(lat, lon) {
  let best = null;
  let bd = 250;
  for (const p of places) {
    const d = dist(lat, lon, p.lat, p.lon);
    if (d < bd) {
      bd = d;
      best = p;
    }
  }
  if (best) return bd < 30 ? best.name : `Near ${best.name}`;
  for (const s of stationList) {
    const d = dist(lat, lon, s.lat, s.lon);
    if (d < bd) {
      bd = d;
      best = s;
    }
  }
  return best ? `Near ${best.name}` : `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

/**
 * Boarding points reachable on foot from an endpoint: [quay, seconds].
 * @param {Endpoint} ep @param {T.PlanOptions} o @param {boolean} egress
 * @returns {Map<string, number>}
 */
function reach(ep, o, egress) {
  /** @type {Map<string, number>} */
  const out = new Map();
  const maxS = o.maxWalkMin * 60;
  if (ep.station) for (const quay of ep.station.quays) out.set(quay.id, 0);
  const cands = allQuays
    .map((quay) => ({ quay, d: dist(ep.point.lat, ep.point.lon, quay.lat, quay.lon) }))
    .filter((x) => x.d < Math.min(2500, maxS * o.walkSpeed) && !out.has(x.quay.id))
    .sort((a, b) => a.d - b.d)
    .slice(0, 60);
  for (const { quay } of cands) {
    const leg = egress ? walkRoute(pointOfQuay(quay), ep.point, o) : walkRoute(ep.point, pointOfQuay(quay), o);
    if (leg.durationS <= maxS) out.set(quay.id, leg.durationS);
  }
  return out;
}

/**
 * One earliest-arrival scan.
 * @param {Conn[]} conns @param {number} t0
 * @param {Map<string, number> | null} access @param {{ trip: Trip, nextSeq: number } | null} onboard
 * @param {Map<string, number>} egress @param {T.PlanOptions} o
 * @returns {{ label: Label, arr: number, dep: number } | null}
 */
function scan(conns, t0, access, onboard, egress, o) {
  const margin = o.transferMarginS;
  /** @type {Map<string, Label>} */
  const S = new Map();
  /** @type {Map<Trip, { enter: number, prev: Label }>} */
  const boarded = new Map();
  if (onboard) boarded.set(onboard.trip, { enter: Math.max(0, onboard.nextSeq - 1), prev: { type: "onboard", ready: t0 } });
  else if (access) {
    for (const [id, s] of access) {
      // arrive at the boarding point `margin` early (stations: you are already there)
      S.set(id, { type: "access", quay: quaysById[id], walkS: s, ready: t0 + s + (s > 0 ? Math.max(60, margin) : 0) });
    }
  }
  /** @type {{ label: Label, arr: number } | null} */
  let best = null;
  const maxS = o.maxWalkMin * 60;
  for (const c of conns) {
    if (best && c.dep >= best.arr) break;
    let b = boarded.get(c.trip);
    if (!b) {
      if (onboard && c.trip === onboard.trip) continue;
      const lab = S.get(c.from.id);
      if (!lab || lab.ready > c.dep) continue;
      b = { enter: c.i, prev: lab };
      boarded.set(c.trip, b);
    } else if (onboard && c.trip === onboard.trip && c.i + 1 < onboard.nextSeq) continue;
    /** @type {Label} */
    const base = { type: "ride", trip: c.trip, enter: b.enter, exit: c.i + 1, prev: b.prev, ready: 0 };
    const eg = egress.get(c.to.id);
    if (eg !== undefined && (!best || c.arr + eg < best.arr)) best = { label: { ...base, quay: c.to, ready: c.arr }, arr: c.arr + eg };
    const cur = S.get(c.to.id);
    if (!cur || c.arr + margin < cur.ready) S.set(c.to.id, { ...base, quay: c.to, walkS: 0, ready: c.arr + margin });
    const from = quaysById[c.to.id] ?? c.to;
    for (const nb of neighbours.get(c.to.id) ?? []) {
      const have = S.get(nb.id);
      if (have && have.ready <= c.arr + margin) continue;
      const w = transferSecs(from, nb, o);
      if (w > maxS) continue;
      if (!have || c.arr + w + margin < have.ready) S.set(nb.id, { ...base, quay: nb, walkS: w, ready: c.arr + w + margin });
    }
  }
  if (!best) return null;
  // departure: when the traveller has to leave the origin
  let first = best.label;
  while (first.prev && first.prev.type === "ride") first = first.prev;
  let dep = t0;
  if (first.prev?.type === "access" && first.trip && first.enter !== undefined) {
    const rideDep = sched(first.trip, first.enter) + first.trip.routeDelayS;
    dep = rideDep - (first.prev.ready - t0);
  }
  return { label: best.label, arr: best.arr, dep };
}

/** Smallest spare time on any change of a found journey. @param {Label} label */
function minSlack(label) {
  let m = Infinity;
  for (let l = /** @type {Label | undefined} */ (label); l && l.type === "ride"; l = l.prev) {
    if (l.prev?.type === "ride" && l.trip && l.enter !== undefined) m = Math.min(m, sched(l.trip, l.enter) + l.trip.routeDelayS - l.prev.ready);
  }
  return m;
}

/**
 * @param {{ label: Label, arr: number, dep: number }} found
 * @param {Endpoint} from @param {Endpoint} to @param {T.PlanOptions} o
 * @returns {T.Journey}
 */
function buildJourney(found, from, to, o) {
  /** @type {Label[]} */
  const rides = [];
  /** @type {Label | undefined} */
  let l = found.label;
  let origin = l;
  while (l && l.type === "ride") {
    rides.push(l);
    origin = /** @type {Label} */ (l.prev);
    l = l.prev;
  }
  rides.reverse();
  const margin = o.transferMarginS;
  /** @type {T.Leg[]} */
  const legs = [];
  /** @type {T.JourneyAlert[]} */
  const alerts = [];
  /** @type {T.RideLeg | null} */
  let prevRide = null;
  rides.forEach((r, idx) => {
    const trip = /** @type {Trip} */ (r.trip);
    const enter = /** @type {number} */ (r.enter);
    const exit = /** @type {number} */ (r.exit);
    const p = trip.pattern;
    const isOnboard = idx === 0 && origin.type === "onboard";
    // on board: `from` is the next stop the vehicle reaches, not a boarding
    const fromCall = stopCall(trip, isOnboard ? Math.min(enter + 1, exit) : enter);
    const toCall = stopCall(trip, exit);
    const delay = trip.delayS ?? 0;
    const depLive = (fromCall.dep ?? sched(trip, enter)) + delay;
    /** @type {T.RideLeg} */
    const ride = {
      type: "ride", line: p.line.badge, headsign: p.headsign, tripId: trip.id, serviceDate: trip.date,
      from: fromCall, to: toCall, intermediate: [], geometry: [], live: liveState(trip),
    };
    if (p.line.number) ride.number = p.line.number;
    for (let i = enter; i <= exit; i++) {
      const quay = quayAt(trip, i);
      ride.geometry.push([quay.lon, quay.lat]);
      if (i > fromCall.seq && i < exit) ride.intermediate.push(stopCall(trip, i));
    }
    const nx = quayAt(trip, enter + 1);
    ride.towards = p.stops[enter + 1].station.name;
    ride.bearing = Math.round(bearing(fromCall.quay.lat, fromCall.quay.lon, nx.lat, nx.lon));
    if (trip.cancelled) ride.cancelled = true;
    if (p.line.badge.mode === "boat") ride.headwayS = undefined;
    if (isOnboard) ride.onboard = true;

    // walk before this ride
    if (idx === 0 && origin.type === "access" && (origin.walkS ?? 0) > 0) {
      const w = walkRoute(from.point, pointOfQuay(fromCall.quay), o);
      const lead = Math.max(60, margin);
      const dep = depLive - lead - w.durationS;
      legs.push({ type: "walk", kind: "access", ...w, dep, arr: dep + w.durationS, slackS: 0 });
    } else if (prevRide) {
      const w = walkRoute(pointOfQuay(prevRide.to.quay), pointOfQuay(fromCall.quay), o);
      const dep = (prevRide.to.arr ?? 0) + (prevRide.to.arrDelayS ?? 0);
      /** @type {T.WalkLeg} */
      const leg = { type: "walk", kind: "transfer", ...w, dep, arr: dep + w.durationS, slackS: depLive - dep - w.durationS - margin };
      const sa = stationById[prevRide.to.quay.stationId];
      if (sa && sa.id === fromCall.quay.stationId && fromCall.quay.noun === "track" && prevRide.to.quay.noun === "track")
        leg.officialMinS = sa.key === "zurich" ? 420 : sa.key === "bern" ? 360 : 180;
      const li = legs.length;
      legs.push(leg);
      const slack = leg.slackS ?? 0;
      const where = fromCall.quay.stationName;
      const mins = (/** @type {number} */ s) => Math.max(0, Math.round(s / 60));
      if (slack + margin < 0)
        alerts.push({ severity: "severe", kind: "missed-connection", leg: li, text: `Missed change at ${where} due to delays` });
      else if (slack < 0)
        alerts.push({ severity: "warning", kind: "tight-change", leg: li, text: `Tight change at ${where}: ${mins(slack + margin)} min to spare` });
      else if (slack < 60 && !trip.cancelled)
        alerts.push({ severity: "warning", kind: "tight-change", leg: li, text: `Tight change at ${where}: ${Math.max(0, Math.round(slack))} s to spare` });
    }
    const li = legs.length;
    legs.push(ride);
    const badge = `${p.line.badge.mode === "rail" ? "" : p.line.badge.mode === "tram" ? "Tram " : p.line.badge.mode === "boat" ? "Boat " : "Bus "}${p.line.badge.name}`;
    if (trip.cancelled) alerts.push({ severity: "severe", kind: "cancelled", leg: li, text: `${badge} is cancelled` });
    else if (delay >= 180) alerts.push({ severity: "info", kind: "delay", leg: li, text: `${badge} is ${Math.round(delay / 60)} min late` });
    if (fromCall.plannedLabel && !isOnboard)
      alerts.push({ severity: "warning", kind: "platform-change", leg: li, text: `${nounName(fromCall.quay) || "Stop"} changed at ${fromCall.quay.stationName}: now ${(nounName(fromCall.quay) || "stop").toLowerCase()} ${fromCall.quay.label} (was ${fromCall.plannedLabel})` });
    prevRide = ride;
  });
  // egress
  const last = /** @type {T.RideLeg} */ (/** @type {unknown} */ (prevRide));
  const lastArr = (last.to.arr ?? 0) + (last.to.arrDelayS ?? 0);
  const inStation = to.station && last.to.quay.stationId === to.station.id;
  if (!inStation) {
    const w = walkRoute(pointOfQuay(last.to.quay), to.point, o);
    legs.push({ type: "walk", kind: "egress", ...w, dep: lastArr, arr: lastArr + w.durationS });
  }
  const first = legs[0];
  const dep = first.type === "walk" ? first.dep : (first.from.dep ?? first.from.arr ?? 0) + (first.from.depDelayS ?? 0);
  const end = legs[legs.length - 1];
  const arr = end.type === "walk" ? end.arr : lastArr;
  let walkS = 0;
  let walkM = 0;
  for (const leg of legs)
    if (leg.type === "walk") {
      walkS += leg.durationS;
      walkM += leg.distanceM;
    }
  const startS = first.type === "ride" && first.onboard ? nowS() : dep;
  /** @type {T.Journey} */
  const j = {
    id: "j" + hash(rides.map((r) => `${r.trip?.id}@${r.trip?.date}:${r.enter}-${r.exit}`).join("|")).toString(36),
    dep: startS, arr, durationS: arr - startS, transfers: rides.length - 1, walkS, walkM, legs,
  };
  if (alerts.length) j.alerts = alerts;
  return j;
}

/** @param {unknown} v @returns {T.PlanOptions} */
function planOptions(v) {
  const o = /** @type {Partial<T.PlanOptions>} */ (v && typeof v === "object" ? v : {});
  /** @type {T.PlanOptions} */
  const out = {
    walkSpeed: Math.min(3, Math.max(0.4, Number(o.walkSpeed) || 1.3)),
    stairs: o.stairs === "avoid" || o.stairs === "never" ? o.stairs : "ok",
    escalators: o.escalators !== false,
    wheelchair: o.wheelchair === true,
    transferMarginS: Math.max(0, Number(o.transferMarginS ?? 120)),
    maxWalkMin: Math.max(1, Number(o.maxWalkMin ?? 20)),
  };
  if (Array.isArray(o.modes) && o.modes.length) out.modes = o.modes;
  if (typeof o.maxTransfers === "number") out.maxTransfers = o.maxTransfers;
  return out;
}

/** @param {T.PlanRequest} req @returns {T.PlanResponse | { error: string }} */
function plan(req) {
  const started = performance.now();
  const o = planOptions(req.options);
  const to = resolve(req.to ?? {});
  if (!to) return { error: "unknown destination" };
  /** @type {{ trip: Trip, nextSeq: number } | null} */
  let onboard = null;
  /** @type {Endpoint | null} */
  let from = null;
  const now = nowS();
  if (req.onboard) {
    const trip = findTrip(req.onboard.tripId, req.onboard.serviceDate);
    if (!trip) return { error: "unknown trip" };
    let nextSeq = req.onboard.nextSeq;
    const n = trip.pattern.stops.length;
    if (nextSeq === undefined) {
      nextSeq = n - 1;
      for (let i = 1; i < n; i++)
        if (sched(trip, i) + (trip.delayS ?? 0) > now) {
          nextSeq = i;
          break;
        }
    }
    nextSeq = Math.min(n - 1, Math.max(1, nextSeq));
    onboard = { trip, nextSeq };
    const s = trip.pattern.stops[nextSeq - 1];
    from = { place: stationPlace(s.station), station: s.station, point: { name: s.station.name, lat: s.station.lat, lon: s.station.lon } };
  } else {
    from = resolve(req.from ?? {});
    if (!from) return { error: "unknown origin" };
  }
  let t = req.time ?? now;
  /** @type {{ dir: "E" | "L", t: number } | null} */
  let page = null;
  if (req.page) {
    try {
      page = JSON.parse(Buffer.from(req.page, "base64url").toString());
    } catch {
      return { error: "bad page cursor" };
    }
  }
  const access = onboard ? null : reach(from, o, false);
  const egress = reach(to, o, true);
  const maxTransfers = o.maxTransfers ?? 6;
  const WANT = 4;

  /** enumerate journeys leaving at or after `t0`, in order of departure @param {number} t0 @param {number} count @param {number} [until] */
  const enumerate = (t0, count, until = Infinity) => {
    const conns = connections(t0 - 60, t0 + 8 * 3600, o);
    /** @type {{ label: Label, arr: number, dep: number }[]} */
    const found = [];
    let cur = t0;
    let guard = 0;
    while (found.length < count && guard++ < 120) {
      let f = scan(conns, cur, access, onboard, egress, o);
      if (!f || f.dep > until) break;
      if (onboard) {
        found.push(f);
        break;
      }
      // leave as late as possible for the same arrival
      for (let i = 0; i < 30; i++) {
        const g = scan(conns, f.dep + 60, access, onboard, egress, o);
        // ... but do not trade a comfortable change for a tight one
        if (g && g.arr <= f.arr && (minSlack(g.label) >= 120 || minSlack(g.label) >= minSlack(f.label))) f = g;
        else break;
      }
      cur = f.dep + 60;
      let n = 0;
      for (let l = /** @type {Label | undefined} */ (f.label); l && l.type === "ride"; l = l.prev) n++;
      if (n - 1 <= maxTransfers) found.push(f);
    }
    return found;
  };

  /** @type {{ label: Label, arr: number, dep: number }[]} */
  let found;
  if (page?.dir === "E") {
    found = enumerate(page.t - 3 * 3600, 60, page.t - 1).slice(-WANT);
  } else if (page?.dir === "L") {
    found = enumerate(page.t, WANT);
  } else if (req.arriveBy) {
    const probe = enumerate(t - 2 * 3600, 1)[0];
    const dur = probe ? probe.arr - probe.dep : 3600;
    found = enumerate(t - dur - 90 * 60, 80).filter((f) => f.arr <= t).slice(-WANT);
  } else {
    found = enumerate(t, WANT);
  }
  found.sort((a, b) => a.dep - b.dep || a.arr - b.arr);
  const journeys = found.map((f) => buildJourney(f, /** @type {Endpoint} */ (from), to, o));
  /** @type {T.PlanResponse} */
  const res = { from: from.place, to: to.place, journeys, tookMs: 0, realtime: true };
  const cursor = (/** @type {"E" | "L"} */ dir, /** @type {number} */ tt) => Buffer.from(JSON.stringify({ dir, t: tt })).toString("base64url");
  if (found.length && !onboard) {
    res.earlier = cursor("E", found[0].dep);
    res.later = cursor("L", found[found.length - 1].dep + 60);
  }
  if (!onboard && !page) {
    const d = dist(from.point.lat, from.point.lon, to.point.lat, to.point.lon);
    if (d < 3200) {
      const w = walkRoute(from.point, to.point, o);
      if (w.durationS <= 45 * 60) {
        const dep = req.arriveBy ? t - w.durationS : Math.max(t, now);
        res.walkOnly = {
          id: "walk", dep, arr: dep + w.durationS, durationS: w.durationS, transfers: 0, walkS: w.durationS, walkM: w.distanceM,
          legs: [{ type: "walk", kind: "direct", ...w, dep, arr: dep + w.durationS }],
        };
      }
    }
  }
  res.tookMs = Math.round((performance.now() - started) * 10) / 10;
  return res;
}

// ---------------------------------------------------------------- departures, trips, vehicles

/** @param {Station} s @param {number} from @param {number} limit @param {string | null} quayId @returns {T.Departure[]} */
function departuresOf(s, from, limit, quayId) {
  /** @type {(T.Departure & { live: number })[]} */
  const out = [];
  for (const p of patterns) {
    for (let i = 0; i < p.stops.length - 1; i++) {
      if (p.stops[i].station !== s) continue;
      const horizon = from + Math.max(3 * 3600, p.line.headwayS * 4);
      for (const t of tripsBetween(p, from - 1200, horizon + p.duration)) {
        const dep = sched(t, i);
        const live = dep + (t.delayS ?? 0);
        if (live < from || dep > horizon) continue;
        const quay = quayAt(t, i);
        if (quayId && quay.id !== quayId) continue;
        const nq = quayAt(t, i + 1);
        /** @type {T.Departure & { live: number }} */
        const d = { line: p.line.badge, headsign: p.headsign, tripId: t.id, serviceDate: t.date, seq: i, dep, quayId: quay.id, towards: p.stops[i + 1].station.name, bearing: Math.round(bearing(quay.lat, quay.lon, nq.lat, nq.lon)), live };
        if (p.line.number) d.number = p.line.number;
        if (t.delayS !== undefined) d.delayS = t.delayS;
        if (t.cancelled) d.cancelled = true;
        if (t.moved[i]) d.plannedLabel = p.stops[i].quay.label;
        out.push(d);
      }
    }
  }
  out.sort((a, b) => a.live - b.live);
  return out.slice(0, limit).map(({ live, ...d }) => d);
}

/** Quays of a station, with sectors stripped (they belong to a call). @param {Station} s */
const stationQuays = (s) => s.quays;

/** @param {Trip} t @param {number} now */
function position(t, now) {
  const p = t.pattern;
  const d = t.delayS ?? 0;
  const n = p.stops.length;
  if (now < sched(t, 0) + d || now > sched(t, n - 1) + d) return null;
  for (let i = 0; i < n - 1; i++) {
    const dep = sched(t, i) + d;
    const arr = sched(t, i + 1) + d;
    if (now <= arr) {
      // dwell for the last 20 s before departure is folded into the segment start
      const a = quayAt(t, i);
      const b = quayAt(t, i + 1);
      const run = Math.max(1, arr - 15 - dep);
      const f = Math.min(1, Math.max(0, (now - dep) / run));
      return { i, dep, arr: arr - 15, a, b, f, lat: a.lat + (b.lat - a.lat) * f, lon: a.lon + (b.lon - a.lon) * f };
    }
  }
  return null;
}

/** @param {number[]} bbox @param {number} now @returns {T.Vehicle[]} */
function vehiclesIn(bbox, now) {
  const [w, s, e, n] = bbox;
  /** @type {T.Vehicle[]} */
  const out = [];
  for (const p of patterns) {
    for (const t of tripsBetween(p, now, now)) {
      if (t.cancelled) continue;
      const pos = position(t, now);
      if (!pos) continue;
      const minLon = Math.min(pos.a.lon, pos.b.lon);
      const maxLon = Math.max(pos.a.lon, pos.b.lon);
      const minLat = Math.min(pos.a.lat, pos.b.lat);
      const maxLat = Math.max(pos.a.lat, pos.b.lat);
      if (maxLon < w || minLon > e || maxLat < s || minLat > n) continue;
      out.push({
        tripId: t.id, serviceDate: t.date, line: p.line.badge, headsign: p.headsign,
        from: [pos.a.lon, pos.a.lat], to: [pos.b.lon, pos.b.lat], dep: pos.dep, arr: pos.arr,
        nextStop: p.stops[pos.i + 1].station.name, nextSeq: pos.i + 1, live: liveState(t),
      });
    }
  }
  return out;
}

/** @param {number} lat @param {number} lon @param {number} now @param {string} qstr @returns {T.OnboardCandidate[]} */
function onboardCandidates(lat, lon, now, qstr) {
  const nq = norm(qstr);
  /** @type {T.OnboardCandidate[]} */
  const out = [];
  for (const p of patterns) {
    const name = norm(p.line.badge.name);
    if (nq && !(name === nq || name.startsWith(nq) || name.replace(" ", "").startsWith(nq.replace(" ", "")) || norm(p.headsign).includes(nq))) continue;
    for (const t of tripsBetween(p, now, now)) {
      if (t.cancelled) continue;
      const pos = position(t, now);
      if (!pos) continue;
      const d = dist(lat, lon, pos.lat, pos.lon);
      if (d > (nq ? 60000 : p.line.badge.mode === "rail" ? 1500 : 450)) continue;
      /** @type {T.OnboardCandidate} */
      const c = {
        tripId: t.id, serviceDate: t.date, line: p.line.badge, headsign: p.headsign, distM: Math.round(d),
        nextSeq: pos.i + 1, nextStop: p.stops[pos.i + 1].station.name, nextArr: pos.arr + 15, prevStop: p.stops[pos.i].station.name,
      };
      if (p.line.number) c.number = p.line.number;
      if (t.delayS !== undefined) c.delayS = t.delayS;
      out.push(c);
    }
  }
  out.sort((a, b) => a.distM - b.distM);
  return out.slice(0, 12);
}

/** @param {number} lat @param {number} lon @param {number} radius @param {number} limit @returns {T.NearbyStation[]} */
function nearby(lat, lon, radius, limit) {
  const now = nowS();
  return stationList
    .map((s) => ({ s, d: Math.min(dist(lat, lon, s.lat, s.lon), ...s.quays.map((qq) => dist(lat, lon, qq.lat, qq.lon))) }))
    .filter((x) => x.d <= radius)
    .sort((a, b) => a.d - b.d)
    .slice(0, limit)
    .map(({ s, d }) => {
      const deps = departuresOf(s, now, 80, null).filter((x) => !x.cancelled);
      /** @type {Map<string, T.NearbyLine>} */
      const groups = new Map();
      for (const dep of deps) {
        const key = dep.line.name + "→" + dep.headsign;
        let g = groups.get(key);
        if (!g) {
          if (groups.size >= 6) continue;
          const quay = s.quays.find((x) => x.id === dep.quayId) ?? s.quays[0];
          g = { line: dep.line, headsign: dep.headsign, quay, next: [], live: dep.delayS !== undefined, tripId: dep.tripId, serviceDate: dep.serviceDate, seq: dep.seq };
          groups.set(key, g);
        }
        const group = g;
        if (group.next.length < 3) group.next.push(dep.dep + (dep.delayS ?? 0));
      }
      return { place: stationPlace(s, { lat, lon }), distM: Math.round(d), lines: [...groups.values()] };
    });
}

/** @param {string} qstr @param {{ lat: number, lon: number } | null} near @param {number} limit @returns {T.Place[]} */
function search(qstr, near, limit) {
  const nq = norm(qstr);
  if (!nq) return [];
  const words = nq.split(" ");
  /** @type {{ p: T.Place, score: number }[]} */
  const hits = [];
  const consider = (/** @type {T.Place} */ p, /** @type {number} */ boost) => {
    const name = norm(p.name);
    const nameWords = name.split(" ");
    let score = 0;
    if (name === nq) score = 100;
    else if (name.startsWith(nq)) score = 80;
    else if (words.every((w) => nameWords.some((nw) => nw.startsWith(w)))) score = 60;
    else if (words.every((w) => name.includes(w) || norm(p.detail ?? "").includes(w))) score = 35;
    else return;
    score += boost - name.length * 0.15;
    if (near) score -= Math.min(20, dist(near.lat, near.lon, p.lat, p.lon) / 4000);
    hits.push({ p, score });
  };
  for (const s of stationList) consider(stationPlace(s, near), 10 + Math.min(20, s.quays.length) + (s.modes.includes("rail") ? 8 : 0));
  for (const p of places) consider(near ? { ...p, distM: Math.round(dist(near.lat, near.lon, p.lat, p.lon)) } : p, 0);
  hits.sort((a, b) => b.score - a.score);
  return hits.slice(0, limit).map((h) => h.p);
}

/** @param {number[]} bbox @returns {import("geojson").FeatureCollection<import("geojson").LineString, T.IndoorFeatureProps>} */
function indoor(bbox) {
  const [w, s, e, n] = bbox;
  /** @type {import("geojson").Feature<import("geojson").LineString, T.IndoorFeatureProps>[]} */
  const features = [];
  for (const edge of wedges) {
    const a = wnodes[edge.a];
    const b = wnodes[edge.b];
    if (Math.max(a.lon, b.lon) < w || Math.min(a.lon, b.lon) > e || Math.max(a.lat, b.lat) < s || Math.min(a.lat, b.lat) > n) continue;
    /** @type {T.IndoorFeatureProps} */
    const props = { kind: edge.kind, level: a.level, indoor: !!edge.indoor };
    if (a.level !== b.level) props.toLevel = b.level;
    if (edge.name) props.name = edge.name;
    features.push({
      type: "Feature", properties: props,
      geometry: { type: "LineString", coordinates: [[a.lon, a.lat], ...(edge.via ?? []), [b.lon, b.lat]] },
    });
  }
  return { type: "FeatureCollection", features };
}

// ---------------------------------------------------------------- http

/** @param {URLSearchParams} q @param {string} k */
function num(q, k) {
  const v = q.get(k);
  if (v === null || v === "") return null;
  const x = Number(v);
  return Number.isFinite(x) ? x : null;
}
/** @param {URLSearchParams} q */
function bboxOf(q) {
  const b = (q.get("bbox") ?? "").split(",").map(Number);
  return b.length === 4 && b.every(Number.isFinite) ? b : null;
}

/** @type {Record<string, (q: URLSearchParams, body: unknown) => unknown>} */
const routes = {
  /** @returns {T.MetaResponse} */
  "GET /api/meta": () => ({
    feedVersion: "mock-2026-11",
    validFrom: "2025-12-14",
    validTo: "2026-12-12",
    walkBbox: [7.425, 46.938, 7.462, 46.956],
    realtime: { enabled: true, source: "mock", updatedAt: nowS() - 12, trips: 1234 },
    counts: { stations: stationList.length, quays: allQuays.length, trips: 0, walkEdges: wedges.length },
    attribution: ["© swisstopo", "© OpenStreetMap contributors", "opentransportdata.swiss"],
  }),
  /** @returns {T.SearchResponse} */
  "GET /api/search": (q) => {
    const lat = num(q, "lat");
    const lon = num(q, "lon");
    return { results: search(q.get("q") ?? "", lat !== null && lon !== null ? { lat, lon } : null, num(q, "limit") ?? 10) };
  },
  /** @returns {T.NearbyResponse | { error: string }} */
  "GET /api/nearby": (q) => {
    const lat = num(q, "lat");
    const lon = num(q, "lon");
    if (lat === null || lon === null) return { error: "lat/lon required" };
    return { stations: nearby(lat, lon, num(q, "radius") ?? 500, num(q, "limit") ?? 8) };
  },
  /** @returns {T.ReverseResponse | { error: string }} */
  "GET /api/reverse": (q) => {
    const lat = num(q, "lat");
    const lon = num(q, "lon");
    if (lat === null || lon === null) return { error: "lat/lon required" };
    // the mock knows no addresses: name the pin after the nearest stop
    const near = stationList.map((s) => ({ s, d: dist(lat, lon, s.lat, s.lon) })).sort((a, b) => a.d - b.d)[0];
    const name = near && near.d < 250 ? `Near ${near.s.name}` : "Pinned location";
    return { id: `coord:${lat.toFixed(5)},${lon.toFixed(5)}`, kind: "coord", name, detail: "Bern", lat, lon };
  },
  /** @returns {T.QuaysResponse | { error: string }} */
  "GET /api/quays": (q) => {
    const b = bboxOf(q);
    if (!b) return { error: "bbox required" };
    return { quays: allQuays.filter((x) => x.lon >= b[0] && x.lon <= b[2] && x.lat >= b[1] && x.lat <= b[3]) };
  },
  /** @returns {T.DeparturesResponse | { error: string }} */
  "GET /api/departures": (q) => {
    const quayId = q.get("quay");
    const s = quayId ? stationById[quaysById[quayId]?.stationId] : stationById[q.get("station") ?? ""];
    if (!s) return { error: "unknown station" };
    return {
      station: stationPlace(s), quays: stationQuays(s),
      departures: departuresOf(s, num(q, "time") ?? nowS(), num(q, "limit") ?? 40, quayId), realtime: true,
    };
  },
  /** @returns {T.TripResponse | { error: string }} */
  "GET /api/trip": (q) => {
    const t = findTrip(q.get("id") ?? "", q.get("date") ?? "");
    if (!t) return { error: "unknown trip" };
    const p = t.pattern;
    /** @type {T.TripResponse} */
    const res = {
      tripId: t.id, serviceDate: t.date, line: p.line.badge, headsign: p.headsign,
      calls: p.stops.map((_, i) => stopCall(t, i)),
      geometry: p.stops.map((_, i) => /** @type {[number, number]} */ ([quayAt(t, i).lon, quayAt(t, i).lat])),
      live: liveState(t),
    };
    if (p.line.number) res.number = p.line.number;
    if (t.cancelled) res.cancelled = true;
    return res;
  },
  /** @returns {T.VehiclesResponse | { error: string }} */
  "GET /api/vehicles": (q) => {
    const b = bboxOf(q);
    if (!b) return { error: "bbox required" };
    const t = num(q, "t") ?? nowS();
    return { t, vehicles: vehiclesIn(b, t) };
  },
  /** @returns {T.OnboardResponse | { error: string }} */
  "GET /api/onboard": (q) => {
    const lat = num(q, "lat");
    const lon = num(q, "lon");
    const query = q.get("q") ?? "";
    if ((lat === null || lon === null) && !query) return { error: "lat/lon or q required" };
    return { candidates: onboardCandidates(lat ?? 46.948, lon ?? 7.44, num(q, "t") ?? nowS(), query) };
  },
  "GET /api/indoor": (q) => {
    const b = bboxOf(q);
    if (!b) return { error: "bbox required" };
    return indoor(b);
  },
  /** @returns {T.PlanResponse | { error: string }} */
  "POST /api/plan": (_q, body) => plan(/** @type {T.PlanRequest} */ (body)),
  /** @returns {T.WalkLeg | { error: string }} */
  "POST /api/walk": (_q, body) => {
    const req = /** @type {T.WalkRequest} */ (body);
    const a = resolve(req.from ?? {});
    const b = resolve(req.to ?? {});
    if (!a || !b) return { error: "unknown place" };
    const w = walkRoute(a.point, b.point, planOptions(req.options));
    const dep = nowS();
    return { type: "walk", kind: "direct", ...w, dep, arr: dep + w.durationS };
  },
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", "http://x");
  const handler = routes[`${req.method} ${url.pathname}`];
  /** @param {number} status @param {unknown} body */
  const send = (status, body) => {
    const json = JSON.stringify(body);
    const done = () => {
      res.writeHead(status, {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        date: new Date(nowMs()).toUTCString(),
        "access-control-allow-origin": "*",
      });
      res.end(json);
    };
    if (LATENCY) setTimeout(done, LATENCY);
    else done();
  };
  if (!handler) return send(404, { error: "not found" });
  /** @type {Buffer[]} */
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    try {
      const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : undefined;
      const out = handler(url.searchParams, body);
      const failed = out && typeof out === "object" && "error" in out;
      send(failed ? 400 : 200, out);
    } catch (err) {
      console.error(err);
      send(500, { error: String(err) });
    }
  });
});

server.listen(PORT, () => {
  console.log(`kante mock engine on http://localhost:${PORT}  (clock: ${new Date(nowMs()).toISOString()})`);
});
