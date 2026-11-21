// What the screens want to see on the map. This module is tiny and loaded up
// front; the MapLibre engine (map/engine.ts) is loaded lazily and renders it.
import { signal } from "@preact/signals";
import type { Journey, Quay, TripResponse, Vehicle } from "../api/types";
import type { BBox, LatLon } from "../lib/geo";
import { readJSON } from "../lib/store";

export interface Scene {
  journey?: Journey | null;
  /** Leg to emphasise; others are dimmed. */
  activeLeg?: number | null;
  /** Part of a walk leg's geometry to highlight (vertex indices, inclusive). */
  slice?: { leg: number; from: number; to: number } | null;
  /** Departure board: all boarding points of a station. */
  station?: { quays: Quay[]; selected: string | null } | null;
  trip?: TripResponse | null;
  /** Boarding point shown as a large sign. */
  hero?: Quay | null;
  /** Origin and destination markers for the list of results. */
  pins?: { from?: LatLon | null; to?: LatLon | null } | null;
}
export const scene = signal<Scene>({});

export type Camera =
  | { kind: "bounds"; bbox: BBox; maxZoom?: number }
  | { kind: "point"; lat: number; lon: number; zoom?: number; minZoom?: number };
export const camera = signal<(Camera & { n: number }) | null>(null);
let seq = 0;
export function flyTo(c: Camera): void {
  camera.value = { ...c, n: ++seq };
}

/** Level shown in the station close-up; null = all levels. */
export const mapLevel = signal<number | null>(null);
/** Levels present in the current view (indoor network and walking route). */
export const levels = signal<number[]>([]);

export interface MapView { lat: number; lon: number; zoom: number; bbox: BBox }
export const mapView = signal<MapView | null>(null);
export const savedView = readJSON<{ lat: number; lon: number; zoom: number }>("kante.view");
export const mapReady = signal(false);
export const mapFailed = signal<string | null>(null);

/** Screen space covered by UI, so the map can keep its subject in the visible part. */
export const insets = signal({ top: 0, bottom: 0, left: 0 });

export interface MapHandlers {
  quayTap?: ((q: Quay) => void) | null;
  mapTap?: ((p: LatLon) => void) | null;
  longPress?: ((p: LatLon & { x: number; y: number }) => void) | null;
  vehicleTap?: ((v: Vehicle) => void) | null;
}
/** Callbacks of the current screen; they take precedence over `defaults`. */
export const handlers: MapHandlers = {};
/** What a tap does when the screen has nothing of its own to say (set once by the app). */
export const defaults: MapHandlers = {};

/** Filled in by the engine once it runs. */
export const mapApi: { center?: () => LatLon; zoomBy?: (d: number) => void; at?: (x: number, y: number) => LatLon } = {};

/** Pilot-area default: Bern station. */
export const DEFAULT_CENTER: LatLon = { lat: 46.9481, lon: 7.4401 };
