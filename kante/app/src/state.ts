import { computed, signal } from "@preact/signals";
import type { Journey, LineBadge, Mode, Place, PlanOptions } from "./api/types";
import { persisted } from "./lib/store";
import type { LatLon } from "./lib/geo";

// ---------------------------------------------------------------- settings

export interface Settings {
  /** Walking speed on level ground, km/h. */
  walkKmh: number;
  stairs: "ok" | "avoid" | "never";
  escalators: boolean;
  wheelchair: boolean;
  /** Extra time on every change, seconds. */
  marginS: number;
  maxWalkMin: number;
  /** null = all modes */
  modes: Mode[] | null;
}
export const DEFAULT_SETTINGS: Settings = {
  walkKmh: 4.7, stairs: "ok", escalators: true, wheelchair: false, marginS: 120, maxWalkMin: 20, modes: null,
};
export const SPEED_PRESETS: { label: string; kmh: number }[] = [
  { label: "Slow", kmh: 3 },
  { label: "Relaxed", kmh: 4 },
  { label: "Normal", kmh: 4.7 },
  { label: "Brisk", kmh: 5.5 },
  { label: "Fast", kmh: 6.5 },
];
export const MODE_GROUPS: { label: string; modes: Mode[] }[] = [
  { label: "Train", modes: ["rail", "metro", "rack"] },
  { label: "Tram", modes: ["tram"] },
  { label: "Bus", modes: ["bus", "ondemand"] },
  { label: "Boat", modes: ["boat"] },
  { label: "Cable car & funicular", modes: ["cableway", "funicular", "lift", "other"] },
];

const stored = persisted<Partial<Settings>>("kante.settings", {});
/** Options carried by a shared link override the stored ones until the user changes something. */
const override = signal<Partial<Settings> | null>(null);
export const settings = computed<Settings>(() => ({ ...DEFAULT_SETTINGS, ...stored.value, ...(override.value ?? {}) }));
export function updateSettings(patch: Partial<Settings>): void {
  stored.value = { ...settings.peek(), ...patch };
  override.value = null;
}
export function applySharedSettings(s: Partial<Settings>): void {
  override.value = s;
}

export function speedName(kmh: number): string {
  let best = SPEED_PRESETS[0]!;
  for (const p of SPEED_PRESETS) if (Math.abs(p.kmh - kmh) < Math.abs(best.kmh - kmh)) best = p;
  return best.label;
}
export function planOptions(s: Settings): PlanOptions {
  const o: PlanOptions = {
    walkSpeed: Math.round((s.walkKmh / 3.6) * 1000) / 1000,
    stairs: s.wheelchair ? "never" : s.stairs,
    escalators: s.wheelchair ? false : s.escalators,
    wheelchair: s.wheelchair,
    transferMarginS: s.marginS,
    maxWalkMin: s.maxWalkMin,
  };
  if (s.modes) o.modes = s.modes;
  return o;
}
/** Short label of the active accessibility profile, or null for the default. */
export function accessLabel(s: Settings): string | null {
  if (s.wheelchair) return "Wheelchair accessible";
  if (s.stairs === "never") return s.escalators ? "No stairs" : "Step-free";
  if (s.stairs === "avoid") return s.escalators ? "Fewer stairs" : "Fewer stairs, no escalators";
  if (!s.escalators) return "No escalators";
  return null;
}
/** Compact encoding for shareable URLs: only what differs from the defaults. */
export function encodeSettings(s: Settings): string {
  const parts: string[] = [];
  if (s.walkKmh !== DEFAULT_SETTINGS.walkKmh) parts.push("w" + s.walkKmh);
  if (s.stairs !== "ok") parts.push("s" + (s.stairs === "never" ? 2 : 1));
  if (!s.escalators) parts.push("e0");
  if (s.wheelchair) parts.push("c1");
  if (s.marginS !== DEFAULT_SETTINGS.marginS) parts.push("m" + s.marginS);
  if (s.maxWalkMin !== DEFAULT_SETTINGS.maxWalkMin) parts.push("x" + s.maxWalkMin);
  if (s.modes) parts.push("o" + s.modes.join("."));
  return parts.join("_");
}
export function decodeSettings(str: string): Partial<Settings> {
  const out: Partial<Settings> = {};
  for (const part of str.split("_")) {
    const v = part.slice(1);
    const n = Number(v);
    switch (part[0]) {
      case "w": if (n >= 1.5 && n <= 9) out.walkKmh = n; break;
      case "s": out.stairs = n === 2 ? "never" : n === 1 ? "avoid" : "ok"; break;
      case "e": out.escalators = n !== 0; break;
      case "c": out.wheelchair = n === 1; break;
      case "m": if (n >= 0 && n <= 1800) out.marginS = n; break;
      case "x": if (n >= 1 && n <= 90) out.maxWalkMin = n; break;
      case "o": out.modes = v.split(".").filter(Boolean) as Mode[]; break;
    }
  }
  return out;
}

// ---------------------------------------------------------------- location

export interface Pos extends LatLon { accuracy?: number; at: number }
export type GeoStatus = "idle" | "asking" | "on" | "denied" | "unavailable";

export const gps = signal<Pos | null>(null);
/** A position the user set by hand ("I'm here"); overrides GPS until cleared. */
export const simulated = persisted<Pos | null>("kante.sim", null);
export const geoStatus = signal<GeoStatus>("idle");
export const userPos = computed<Pos | null>(() => simulated.value ?? gps.value);

let watchId: number | null = null;
export function startGeo(): void {
  if (!("geolocation" in navigator)) {
    geoStatus.value = "unavailable";
    return;
  }
  if (watchId !== null) return;
  if (geoStatus.peek() !== "on") geoStatus.value = "asking";
  watchId = navigator.geolocation.watchPosition(
    (p) => {
      geoStatus.value = "on";
      gps.value = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, at: Date.now() };
    },
    (err) => {
      geoStatus.value = err.code === err.PERMISSION_DENIED ? "denied" : "unavailable";
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
      watchId = null;
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
  );
}
/** Start watching without a prompt when the permission was granted earlier. */
export function resumeGeo(): void {
  if (!("permissions" in navigator) || !("geolocation" in navigator)) return;
  navigator.permissions
    .query({ name: "geolocation" })
    .then((st) => {
      if (st.state === "granted") startGeo();
      else if (st.state === "denied") geoStatus.value = "denied";
    })
    .catch(() => undefined);
}

// ---------------------------------------------------------------- places the user keeps

export interface Saved { home?: Place; work?: Place; favs: Place[] }
export const saved = persisted<Saved>("kante.saved", { favs: [] });
export const recents = persisted<Place[]>("kante.recents", []);
export function remember(p: Place): void {
  if (p.kind === "coord" && !p.name) return;
  const { distM: _d, ...clean } = p;
  recents.value = [clean, ...recents.peek().filter((x) => x.id !== p.id)].slice(0, 8);
}

// ---------------------------------------------------------------- "I'm on board"

export interface ActiveOnboard {
  tripId: string;
  serviceDate: string;
  nextSeq?: number;
  line: LineBadge;
  headsign: string;
  /** Unix seconds after which the trip is certainly over. */
  until: number;
}
export const onboard = persisted<ActiveOnboard | null>("kante.onboard", null);

// ---------------------------------------------------------------- toast

export const toast = signal<{ text: string; id: number } | null>(null);
let toastTimer = 0;
export function showToast(text: string): void {
  const id = Date.now();
  toast.value = { text, id };
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    if (toast.peek()?.id === id) toast.value = null;
  }, 2600);
}

// ---------------------------------------------------------------- views the user chose

/** Journey screens open as a list (sheet expanded) or with the map (sheet at half); the last choice sticks. */
export const tripView = persisted<"list" | "map">("kante.tripview", "list");

// ---------------------------------------------------------------- guidance in progress

export interface Guidance {
  /** Address of the guidance screen to return to. */
  url: string;
  journey: Journey;
  /** Destination name for the strip. */
  to: string;
  startedAt: number;
}
/** The journey being followed. Closing the guidance screen minimises it; only "End" clears this. */
export const guidance = persisted<Guidance | null>("kante.guidance", null);

export const online = signal(typeof navigator === "undefined" ? true : navigator.onLine !== false);
if (typeof window !== "undefined") {
  window.addEventListener("online", () => (online.value = true));
  window.addEventListener("offline", () => (online.value = false));
}
