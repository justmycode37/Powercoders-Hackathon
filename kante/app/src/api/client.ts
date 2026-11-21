import { useEffect, useRef, useState } from "preact/hooks";
import { noteServerDate, nowMs, simTime } from "../lib/time";
import type {
  DeparturesResponse, IndoorFeatureProps, MetaResponse, NearbyResponse, OnboardResponse, PlanRequest, PlanResponse,
  QuaysResponse, ReverseResponse, SearchResponse, TripResponse, VehiclesResponse, WalkLeg, WalkRequest,
} from "./types";
import type { BBox } from "../lib/geo";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

type Params = Record<string, string | number | undefined | null>;

async function request<T>(path: string, params?: Params, body?: unknown, signal?: AbortSignal): Promise<T> {
  let url = "/api/" + path;
  if (params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
    const s = q.toString();
    if (s) url += "?" + s;
  }
  const sentAt = Date.now();
  let res: Response;
  try {
    res = await fetch(url, body === undefined ? { signal } : { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(navigator.onLine === false ? "You're offline" : "Can't reach Kante right now", 0);
  }
  noteServerDate(res.headers.get("date"), sentAt, Date.now());
  if (!res.ok) {
    let msg = "Something went wrong on our side";
    try {
      const j = (await res.json()) as { error?: string };
      if (j.error) msg = j.error;
    } catch {
      /* not JSON */
    }
    throw new ApiError(msg, res.status);
  }
  return (await res.json()) as T;
}

const bboxStr = (b: BBox) => b.map((x) => x.toFixed(5)).join(",");
type Indoor = GeoJSON.FeatureCollection<GeoJSON.LineString, IndoorFeatureProps>;

export const api = {
  meta: (s?: AbortSignal) => request<MetaResponse>("meta", undefined, undefined, s),
  search: (q: string, near: { lat: number; lon: number } | null, s?: AbortSignal) =>
    request<SearchResponse>("search", { q, lat: near?.lat.toFixed(5), lon: near?.lon.toFixed(5), limit: 12 }, undefined, s),
  // `time` is honoured by the engine although the contract does not list it; only sent with a simulated clock
  nearby: (lat: number, lon: number, radius: number, limit: number, s?: AbortSignal) =>
    request<NearbyResponse>("nearby", { lat: lat.toFixed(5), lon: lon.toFixed(5), radius, limit, time: simTime() }, undefined, s),
  reverse: (lat: number, lon: number, s?: AbortSignal) => request<ReverseResponse>("reverse", { lat: lat.toFixed(5), lon: lon.toFixed(5) }, undefined, s),
  quays: (b: BBox, s?: AbortSignal) => request<QuaysResponse>("quays", { bbox: bboxStr(b) }, undefined, s),
  indoor: (b: BBox, s?: AbortSignal) => request<Indoor>("indoor", { bbox: bboxStr(b) }, undefined, s),
  vehicles: (b: BBox, s?: AbortSignal) => request<VehiclesResponse>("vehicles", { bbox: bboxStr(b), t: simTime() }, undefined, s),
  departures: (p: { station?: string; quay?: string; time?: number; limit?: number }, s?: AbortSignal) =>
    request<DeparturesResponse>("departures", { ...p, time: p.time ?? simTime() }, undefined, s),
  trip: (id: string, date: string, s?: AbortSignal) => request<TripResponse>("trip", { id, date }, undefined, s),
  onboard: (p: { lat?: number; lon?: number; q?: string }, s?: AbortSignal) =>
    request<OnboardResponse>("onboard", { lat: p.lat?.toFixed(5), lon: p.lon?.toFixed(5), q: p.q, t: simTime() }, undefined, s),
  plan: (req: PlanRequest, s?: AbortSignal) => request<PlanResponse>("plan", undefined, req.time === undefined && simTime() !== undefined ? { ...req, time: simTime() } : req, s),
  walk: (req: WalkRequest, s?: AbortSignal) => request<WalkLeg>("walk", undefined, req, s),
};

export interface Query<T> {
  data: T | undefined;
  /** Unix ms the data was received (0 for data handed in as `initial`). */
  at: number;
  error: string | null;
  /** A request is in flight (data may still hold the previous answer). */
  loading: boolean;
  reload: () => void;
}

/**
 * Fetch keyed by `key`: a new key aborts the request in flight, so a slow answer
 * can never overwrite a newer one. The previous data stays visible while loading
 * unless `keep` is false. `refreshS` re-fetches quietly on an interval.
 */
export function useQuery<T>(
  key: string | null,
  fetcher: (signal: AbortSignal) => Promise<T>,
  opts: { refreshS?: number; keep?: boolean; initial?: T } = {},
): Query<T> {
  const [state, setState] = useState<{ key: string | null; data: T | undefined; at: number; error: string | null; loading: boolean }>({
    key, data: opts.initial, at: 0, error: null, loading: key !== null,
  });
  const [nonce, setNonce] = useState(0);
  const fn = useRef(fetcher);
  fn.current = fetcher;
  useEffect(() => {
    if (key === null) {
      setState({ key, data: undefined, at: 0, error: null, loading: false });
      return;
    }
    const ctl = new AbortController();
    let timer = 0;
    const run = (quiet: boolean) => {
      if (!quiet) setState((s) => ({ key, data: opts.keep === false && s.key !== key ? undefined : s.data, at: s.at, error: null, loading: true }));
      fn.current(ctl.signal).then(
        (data) => {
          if (!ctl.signal.aborted) setState({ key, data, at: nowMs(), error: null, loading: false });
        },
        (err: Error) => {
          if (ctl.signal.aborted || err.name === "AbortError") return;
          setState((s) => ({ key, data: s.data, at: s.at, error: err.message, loading: false }));
        },
      );
    };
    run(false);
    if (opts.refreshS) {
      timer = window.setInterval(() => {
        if (!document.hidden) run(true);
      }, opts.refreshS * 1000);
    }
    return () => {
      ctl.abort();
      clearInterval(timer);
    };
  }, [key, nonce]);
  return { data: state.data, at: state.at, error: state.error, loading: state.loading, reload: () => setNonce((n) => n + 1) };
}
