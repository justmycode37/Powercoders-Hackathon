// A journey query as it lives in the URL, and the store of answers.
import { signal } from "@preact/signals";
import { api } from "./api/client";
import type { Journey, OnboardRef, Place, PlaceRef, PlanRequest, PlanResponse } from "./api/types";
import { dist } from "./lib/geo";
import { readJSON, writeJSON } from "./lib/store";
import { nowS } from "./lib/time";
import { applySharedSettings, decodeSettings, encodeSettings, planOptions, settings, userPos, type Pos, type Settings } from "./state";

/** A chosen endpoint: a place, or "wherever I am". */
export type PlaceSel = Place | { kind: "here" };
export const HERE: PlaceSel = { kind: "here" };
export const isHere = (p: PlaceSel | null): p is { kind: "here" } => p?.kind === "here";

const KIND_CODE: Record<string, Place["kind"]> = { s: "station", a: "address", p: "poi", c: "coord" };

export function encodePlace(p: PlaceSel | null): string | undefined {
  if (!p) return undefined;
  if (isHere(p)) return "here";
  const name = p.name.replace(/[~|]/g, " ");
  return `${p.id}~${name}~${p.lat.toFixed(5)},${p.lon.toFixed(5)}~${p.kind[0]}`;
}
export function decodePlace(s: string | undefined): PlaceSel | null {
  if (!s) return null;
  if (s === "here") return HERE;
  const [id, name, ll, k] = s.split("~");
  const [lat, lon] = (ll ?? "").split(",").map(Number);
  if (!id || lat === undefined || lon === undefined || Number.isNaN(lat) || Number.isNaN(lon)) return null;
  return { id, name: name || "Pinned location", lat, lon, kind: KIND_CODE[k ?? ""] ?? (id.startsWith("st:") ? "station" : "coord") };
}
export function coordPlace(lat: number, lon: number, name = "Pinned location"): Place {
  return { id: `coord:${lat.toFixed(5)},${lon.toFixed(5)}`, kind: "coord", name, lat, lon };
}

export interface PlanQuery {
  from: PlaceSel | null;
  to: PlaceSel | null;
  /** Unix seconds; null = now. */
  time: number | null;
  arriveBy: boolean;
  onboard: OnboardRef | null;
}

export function parseQuery(params: Record<string, string>): PlanQuery {
  let onboard: OnboardRef | null = null;
  if (params.ob) {
    const [tripId, serviceDate, seq] = params.ob.split("|");
    if (tripId && serviceDate) onboard = { tripId, serviceDate, ...(seq ? { nextSeq: Number(seq) } : {}) };
  }
  const t = params.t ? Number(params.t) : NaN;
  return {
    from: decodePlace(params.from) ?? (onboard ? null : HERE),
    to: decodePlace(params.to),
    time: Number.isFinite(t) ? t : null,
    arriveBy: params.arr === "1",
    onboard,
  };
}
export function queryParams(q: PlanQuery, withOptions = false): Record<string, string | undefined> {
  const o = withOptions ? encodeSettings(settings.peek()) : "";
  return {
    from: q.onboard ? undefined : encodePlace(q.from),
    to: encodePlace(q.to),
    t: q.time === null ? undefined : String(q.time),
    arr: q.arriveBy ? "1" : undefined,
    ob: q.onboard ? [q.onboard.tripId, q.onboard.serviceDate, q.onboard.nextSeq ?? ""].join("|").replace(/\|$/, "") : undefined,
    o: o || undefined,
  };
}
/** Options carried by a shared link apply to this session. */
let sharedApplied = "";
export function adoptSharedOptions(params: Record<string, string>): void {
  if (params.o && params.o !== sharedApplied) {
    sharedApplied = params.o;
    const dec = decodeSettings(params.o);
    const cur = settings.peek();
    if ((Object.keys(dec) as (keyof Settings)[]).some((k) => JSON.stringify(dec[k]) !== JSON.stringify(cur[k]))) applySharedSettings(dec);
  }
}

// ---------------------------------------------------------------- store

export interface PlanState {
  key: string;
  status: "loading" | "ready" | "error" | "need-origin";
  error?: string;
  res?: PlanResponse;
  journeys: Journey[];
  earlier?: string;
  later?: string;
  more: "earlier" | "later" | null;
  /** Unix seconds the answer was received. */
  at: number;
  /** Shown from storage; a fresh answer is on its way or could not be fetched. */
  stale?: boolean;
}
export const plan = signal<PlanState | null>(null);

let ctl: AbortController | null = null;
let request: PlanRequest | null = null;
let anchor: Pos | null = null;

function ref(p: PlaceSel, pos: Pos | null): PlaceRef | null {
  if (isHere(p)) {
    if (!pos) return null;
    // keep the same origin while the user has not really moved, so GPS jitter does not re-plan
    if (!anchor || dist(anchor.lat, anchor.lon, pos.lat, pos.lon) > 60) anchor = pos;
    return { lat: +anchor.lat.toFixed(5), lon: +anchor.lon.toFixed(5), name: "Current location" };
  }
  if (p.kind === "coord") return { lat: p.lat, lon: p.lon, name: p.name };
  return { id: p.id, name: p.name };
}

function build(q: PlanQuery): PlanRequest | null {
  if (!q.to) return null;
  const to = ref(q.to, userPos.peek());
  if (!to) return null;
  const req: PlanRequest = { to, options: planOptions(settings.peek()) };
  if (q.onboard) req.onboard = q.onboard;
  else {
    const from = q.from ? ref(q.from, userPos.peek()) : null;
    if (!from) return null;
    req.from = from;
  }
  if (q.time !== null) req.time = q.time;
  if (q.arriveBy) req.arriveBy = true;
  return req;
}

interface StoredPlan { key: string; res: PlanResponse; journeys: Journey[]; earlier?: string; later?: string; at: number }

/**
 * Make sure the store holds (or is fetching) the answer to `q` with the current
 * settings and position. Cheap to call on every render.
 */
export function ensurePlan(q: PlanQuery, opts: { maxAgeS?: number } = {}): void {
  const req = build(q);
  const cur = plan.peek();
  if (!req) {
    const key = "need:" + JSON.stringify(queryParams(q));
    if (cur?.key !== key) {
      ctl?.abort();
      plan.value = { key, status: "need-origin", journeys: [], more: null, at: nowS() };
    }
    return;
  }
  const key = JSON.stringify(req);
  if (cur?.key === key) {
    const age = nowS() - cur.at;
    const expired = opts.maxAgeS !== undefined && q.time === null && cur.status === "ready" && !cur.stale && age > opts.maxAgeS;
    if (!expired) return;
  }
  ctl?.abort();
  ctl = new AbortController();
  request = req;
  // show what we have: the same query refreshing, or the last answer from storage
  let prev: PlanState | null = cur?.key === key && cur.res ? cur : null;
  if (!prev) {
    const st = readJSON<StoredPlan>("kante.lastplan");
    if (st?.key === key) prev = { ...st, status: "ready", more: null, stale: true };
  }
  plan.value = prev ? { ...prev, status: prev.status === "error" ? "loading" : prev.status, more: null } : { key, status: "loading", journeys: [], more: null, at: nowS() };
  const signal = ctl.signal;
  api.plan(req, signal).then(
    (res) => {
      if (signal.aborted) return;
      const st: StoredPlan = { key, res, journeys: prune(res.journeys), earlier: res.earlier, later: res.later, at: nowS() };
      plan.value = { ...st, status: "ready", more: null };
      writeJSON("kante.lastplan", st);
    },
    (err: Error) => {
      if (signal.aborted || err.name === "AbortError") return;
      const p = plan.peek();
      if (p?.key !== key) return;
      if (p.res) {
        plan.value = { ...p, status: "ready", stale: true, error: err.message };
        return;
      }
      // offline: the last answer for the same two places is better than nothing
      const st = readJSON<StoredPlan>("kante.lastplan");
      if (st && samePlaces(st.key, req)) plan.value = { ...st, key, status: "ready", more: null, stale: true, error: err.message };
      else plan.value = { ...p, status: "error", error: err.message };
    },
  );
}

function samePlaces(storedKey: string, req: PlanRequest): boolean {
  try {
    const old = JSON.parse(storedKey) as PlanRequest;
    const id = (r: PlaceRef | undefined) => r?.id ?? r?.name ?? "";
    return id(old.to) === id(req.to) && id(old.from) === id(req.from) && old.onboard?.tripId === req.onboard?.tripId;
  } catch {
    return false;
  }
}

/**
 * Drops journeys that another one beats outright: leaving no earlier, arriving no
 * later, with no more changes. Each page of the engine's answer is optimal on its
 * own; next to its neighbours a page can hold such leftovers (a long detour that
 * arrives with a train leaving an hour later).
 */
export function prune(list: Journey[]): Journey[] {
  const broken = (j: Journey) => (j.alerts ?? []).some((a) => a.severity === "severe");
  return list.filter(
    (j) =>
      !list.some(
        (k) => k !== j && !broken(k) && k.dep >= j.dep && k.arr <= j.arr && k.transfers <= j.transfers && (k.dep > j.dep || k.arr < j.arr || k.transfers < j.transfers),
      ),
  );
}

export function loadMore(dir: "earlier" | "later"): void {
  const p = plan.peek();
  const cursor = dir === "earlier" ? p?.earlier : p?.later;
  if (!p || !request || !cursor || p.more) return;
  const key = p.key;
  plan.value = { ...p, more: dir };
  api.plan({ ...request, page: cursor }, ctl?.signal).then(
    (res) => {
      const cur = plan.peek();
      if (cur?.key !== key) return;
      const seen = new Set(cur.journeys.map((j) => j.id));
      const fresh = res.journeys.filter((j) => !seen.has(j.id));
      plan.value = {
        ...cur, more: null,
        journeys: prune(dir === "earlier" ? [...fresh, ...cur.journeys] : [...cur.journeys, ...fresh]),
        earlier: dir === "earlier" ? res.earlier : cur.earlier,
        later: dir === "later" ? res.later : cur.later,
      };
    },
    () => {
      const cur = plan.peek();
      if (cur?.key === key) plan.value = { ...cur, more: null };
    },
  );
}

/** The journey a detail / Go screen refers to; survives reloads through storage. */
export function findJourney(id: string | undefined): Journey | null {
  if (!id) return null;
  const p = plan.peek();
  const hit = p?.journeys.find((j) => j.id === id) ?? (p?.res?.walkOnly?.id === id ? p.res.walkOnly : null);
  if (hit) {
    writeJSON("kante.journey", hit);
    return hit;
  }
  const st = readJSON<Journey>("kante.journey");
  return st?.id === id ? st : null;
}

/** The journey screen the user looked at last, offered again on the home screen. */
export interface LastTrip { url: string; title: string; dep: number; arr: number; at: number }
export const lastTrip = signal<LastTrip | null>(readJSON<LastTrip>("kante.lasttrip"));
export function rememberTrip(t: LastTrip | null): void {
  lastTrip.value = t;
  if (t) writeJSON("kante.lasttrip", t);
  else {
    try {
      localStorage.removeItem("kante.lasttrip");
    } catch {
      /* ignore */
    }
  }
}
