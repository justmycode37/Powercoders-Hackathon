// MapLibre engine: loaded lazily after the shell has painted. It renders the
// declarative scene (map/scene.ts) into a fixed set of GeoJSON sources that are
// only ever updated with setData.
import { Map as MLMap, setWorkerUrl, type GeoJSONSource, type StyleSpecification, type ExpressionSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { effect } from "@preact/signals";
import { api } from "../api/client";
import type { IndoorFeatureProps, Quay, Vehicle } from "../api/types";
import { bboxOf, type BBox, type LngLat } from "../lib/geo";
import { levelShort, lineColor, lineLabel, lineStroke } from "../lib/lines";
import { nowMs } from "../lib/time";
import { writeJSON } from "../lib/store";
import { simulated, userPos } from "../state";
import { camera, DEFAULT_CENTER, defaults, handlers, insets, levels, mapApi, mapLevel, mapReady, mapView, savedView, scene, type Camera, type Scene } from "./scene";
import { darkStyle } from "./dark";
import { makeImage } from "./sprites";

setWorkerUrl(workerUrl);

type FC = GeoJSON.FeatureCollection;
const EMPTY: FC = { type: "FeatureCollection", features: [] };
const SOURCES = ["indoor", "ride", "walk", "focus", "stops", "lvl", "signs", "veh", "me", "pins"] as const;
type Src = (typeof SOURCES)[number];

const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

export async function createMap(container: HTMLElement, style: Promise<StyleSpecification>): Promise<void> {
  const base = await style;
  const styleFor = (dark: boolean) => (dark ? darkStyle(base) : base);
  const start = userPos.peek() ?? savedView ?? DEFAULT_CENTER;
  const map = new MLMap({
    container,
    style: styleFor(darkQuery.matches),
    center: [start.lon, start.lat],
    zoom: userPos.peek() ? 16 : (savedView?.zoom ?? 15.2),
    minZoom: 6,
    maxZoom: 20,
    maxBounds: [[4.5, 44.9], [12.2, 48.6]],
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
    touchPitch: false,
    maxPitch: 0,
    fadeDuration: 120,
    refreshExpiredTiles: false,
  });
  map.touchZoomRotate.disableRotation();
  map.keyboard.disableRotation();

  let dark = darkQuery.matches;
  let ready = false;
  const data: Record<Src, FC> = { indoor: EMPTY, ride: EMPTY, walk: EMPTY, focus: EMPTY, stops: EMPTY, lvl: EMPTY, signs: EMPTY, veh: EMPTY, me: EMPTY, pins: EMPTY };
  const set = (id: Src, fc: FC) => {
    data[id] = fc;
    if (ready) (map.getSource(id) as GeoJSONSource | undefined)?.setData(fc);
  };

  // ------------------------------------------------------------ layers

  const levelOpacity = (on: number, off: number): ExpressionSpecification | number => {
    const l = mapLevel.peek();
    if (l === null) return on;
    return ["case", ["any", ["==", ["get", "lvl"], l], ["==", ["get", "lvl2"], l]], on, off];
  };

  const WALK = "#FFD23F";
  const WALK_EDGE = "#14161A";
  const offLevel = (): ExpressionSpecification | null => {
    const l = mapLevel.peek();
    return l === null ? null : ["all", ["!=", ["get", "lvl"], l], ["!=", ["get", "lvl2"], l]];
  };
  const walkColor = (): ExpressionSpecification | string => {
    const off = offLevel();
    return off ? ["case", off, dark ? "#5B6472" : "#C3C8D1", WALK] : WALK;
  };
  const walkOpacity = (on: number): ExpressionSpecification => {
    const off = offLevel();
    return off ? ["case", ["get", "dim"], on * 0.4, off, on * 0.8, on] : ["case", ["get", "dim"], on * 0.4, on];
  };
  const walkArrow = (): ExpressionSpecification | string => {
    const off = offLevel();
    return off ? ["case", off, "arr|g", "arr|k"] : "arr|k";
  };

  function install(): void {
    const firstSymbol = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
    for (const id of SOURCES) if (!map.getSource(id)) map.addSource(id, { type: "geojson", data: data[id] });
    const casing = dark ? "#0B0D10" : "#FFFFFF";
    const zoomW = (a: number, b: number): ExpressionSpecification => ["interpolate", ["linear"], ["zoom"], 10, a, 17, b];
    map.addLayer({
      id: "k-indoor", type: "line", source: "indoor", minzoom: 16.4,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": ["match", ["get", "kind"], "steps", dark ? "#FDBA74" : "#B45309", "escalator", dark ? "#C4B5FD" : "#7C3AED", "lift", dark ? "#5EEAD4" : "#0F766E", "platform", dark ? "#94A3B8" : "#64748B", dark ? "#8EA0C4" : "#6B7C9E"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 16.4, ["match", ["get", "kind"], "platform", 2, 0.8], 19, ["match", ["get", "kind"], "platform", 8, "lift", 6, 3]],
        "line-opacity": levelOpacity(0.5, 0.08),
        "line-dasharray": [1, 0],
      },
    }, firstSymbol);
    map.addLayer({
      id: "k-indoor-steps", type: "line", source: "indoor", minzoom: 16.5, filter: ["==", ["get", "kind"], "steps"],
      paint: { "line-color": casing, "line-width": ["interpolate", ["linear"], ["zoom"], 16.5, 1, 19, 3], "line-dasharray": [0.35, 0.35], "line-opacity": levelOpacity(0.9, 0) },
    }, firstSymbol);
    map.addLayer({
      id: "k-ride-casing", type: "line", source: "ride", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": casing, "line-width": zoomW(5, 10), "line-opacity": ["case", ["get", "dim"], 0.5, 1] },
    }, firstSymbol);
    map.addLayer({
      id: "k-ride", type: "line", source: "ride", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": ["get", "color"], "line-width": zoomW(3, 6), "line-opacity": ["case", ["get", "dim"], 0.4, 1] },
    }, firstSymbol);
    // walking: a band with arrows in the direction of travel; the part on another level is greyed
    map.addLayer({
      id: "k-walk-casing", type: "line", source: "walk", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": WALK_EDGE, "line-width": zoomW(5, 10.5), "line-opacity": walkOpacity(0.75) },
    }, firstSymbol);
    map.addLayer({
      id: "k-walk", type: "line", source: "walk", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": walkColor(), "line-width": zoomW(3.5, 8), "line-opacity": walkOpacity(1) },
    }, firstSymbol);
    map.addLayer({
      id: "k-focus-casing", type: "line", source: "focus", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": WALK_EDGE, "line-width": zoomW(8, 15) },
    });
    map.addLayer({
      id: "k-focus", type: "line", source: "focus", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": WALK, "line-width": zoomW(5.5, 11) },
    });
    map.addLayer({
      id: "k-walk-arrows", type: "symbol", source: "walk", minzoom: 14.5,
      layout: {
        "symbol-placement": "line", "symbol-spacing": ["interpolate", ["linear"], ["zoom"], 14.5, 18, 18, 30],
        "icon-image": walkArrow(), "icon-size": ["interpolate", ["linear"], ["zoom"], 14.5, 0.6, 17, 1],
        "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-rotation-alignment": "map", "icon-padding": 0,
      },
      paint: { "icon-opacity": walkOpacity(1) },
    });
    map.addLayer({
      id: "k-stops", type: "circle", source: "stops",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, ["case", ["get", "end"], 3, 0], 13, ["case", ["get", "end"], 5, 2.5], 17, ["case", ["get", "end"], 7, 4.5]],
        "circle-color": dark ? "#0B0D10" : "#FFFFFF",
        "circle-stroke-color": ["get", "color"],
        "circle-stroke-width": ["case", ["get", "end"], 3, 2],
        "circle-opacity": ["case", ["get", "dim"], 0.4, 1],
        "circle-stroke-opacity": ["case", ["get", "dim"], 0.4, 1],
      },
    });
    map.addLayer({
      id: "k-lvl", type: "symbol", source: "lvl", minzoom: 16,
      layout: { "icon-image": ["get", "img"], "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-anchor": "left", "icon-offset": [8, 0] },
    });
    map.addLayer({
      id: "k-veh-halo", type: "circle", source: "veh", minzoom: 12.5,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 13, ["match", ["get", "live"], "observed", 9, 13], 18, ["match", ["get", "live"], "observed", 20, 34]],
        "circle-color": ["get", "color"],
        "circle-opacity": ["match", ["get", "live"], "observed", 0.2, 0.13],
      },
    });
    map.addLayer({
      id: "k-veh", type: "symbol", source: "veh", minzoom: 12.5,
      layout: { "icon-image": ["get", "img"], "icon-allow-overlap": true, "icon-ignore-placement": true, "icon-size": ["interpolate", ["linear"], ["zoom"], 13, 0.8, 17, 1.05] },
      paint: { "icon-opacity": ["match", ["get", "live"], "timetable", 0.85, 1] },
    });
    map.addLayer({
      id: "k-me-acc", type: "circle", source: "me",
      paint: {
        "circle-radius": ["interpolate", ["exponential", 2], ["zoom"], 0, 0, 22, ["get", "r22"]],
        "circle-color": ["get", "color"], "circle-opacity": 0.14,
      },
    });
    map.addLayer({
      id: "k-me", type: "circle", source: "me",
      paint: { "circle-radius": 7.5, "circle-color": ["get", "color"], "circle-stroke-color": "#FFFFFF", "circle-stroke-width": 3 },
    });
    map.addLayer({
      id: "k-pins", type: "symbol", source: "pins",
      layout: { "icon-image": ["get", "img"], "icon-anchor": ["get", "anchor"], "icon-allow-overlap": true, "icon-ignore-placement": true },
    });
    map.addLayer({
      id: "k-signs", type: "symbol", source: "signs",
      layout: {
        "icon-image": ["get", "img"], "icon-allow-overlap": true, "icon-ignore-placement": true, "symbol-sort-key": ["get", "sort"],
        // unsigned context edges only appear close up, where they do not clutter
        "icon-size": ["interpolate", ["linear"], ["zoom"], 14, ["case", ["get", "dot"], 0.01, ["get", "ctx"], 0.55, 0.85], 16.6, ["case", ["get", "dot"], 0.01, ["get", "ctx"], 0.85, 1], 17, ["case", ["get", "ctx"], 0.9, 1], 18.5, ["case", ["get", "ctx"], 1.1, 1.15]],
      },
      paint: { "icon-opacity": levelOpacity(1, 0.3) },
    });
    ready = true;
    for (const id of SOURCES) (map.getSource(id) as GeoJSONSource).setData(data[id]);
  }

  // signs and vehicle badges are drawn on demand
  map.setMissingStyleImageResolver((id) => {
    if (map.hasImage(id)) return;
    const img = makeImage(id, dark);
    if (img) map.addImage(id, img.data, { pixelRatio: img.ratio });
  });
  map.on("style.load", install);
  darkQuery.addEventListener("change", (ev) => {
    dark = ev.matches;
    ready = false;
    map.setStyle(styleFor(dark));
    render(scene.peek());
  });

  // ------------------------------------------------------------ scene → sources

  const quayIndex = new Map<string, Quay>();
  let quayLevels: { lvl: number; lon: number; lat: number }[] = [];
  let context: Quay[] = [];

  function sign(q: Quay, variant: "s" | "m" | "x" | "l", sort: number): GeoJSON.Feature {
    quayIndex.set(q.id, q);
    const label = variant === "l" && q.label ? `${q.label}|${q.noun}` : q.label;
    if (q.level !== undefined && q.level !== 0) quayLevels.push({ lvl: Math.round(q.level), lon: q.lon, lat: q.lat });
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [q.lon, q.lat] },
      properties: { id: q.id, img: `sg|${variant}|${label}`, lvl: Math.round(q.level ?? 0), lvl2: Math.round(q.level ?? 0), sort, ctx: variant === "s", dot: variant === "s" && !q.label },
    };
  }

  function render(sc: Scene): void {
    const ride: GeoJSON.Feature[] = [];
    const walk: GeoJSON.Feature[] = [];
    const stops: GeoJSON.Feature[] = [];
    const signs: GeoJSON.Feature[] = [];
    const pins: GeoJSON.Feature[] = [];
    const taken = new Set<string>();
    const marks: GeoJSON.Feature[] = [];
    quayLevels = [];
    const routeLevels: { lvl: number; lon: number; lat: number }[] = [];
    let focus: FC = EMPTY;
    const pt = (c: LngLat, props: Record<string, unknown>): GeoJSON.Feature => ({ type: "Feature", geometry: { type: "Point", coordinates: c }, properties: props });

    const j = sc.journey;
    if (j) {
      j.legs.forEach((leg, i) => {
        const dim = sc.activeLeg != null && sc.activeLeg !== i;
        if (leg.type === "ride") {
          const color = lineStroke(leg.line, dark);
          ride.push({ type: "Feature", geometry: { type: "LineString", coordinates: leg.geometry }, properties: { color, dim } });
          for (const c of leg.intermediate) stops.push(pt([c.quay.lon, c.quay.lat], { color, end: false, dim }));
          stops.push(pt([leg.to.quay.lon, leg.to.quay.lat], { color, end: true, dim }));
          if (!leg.onboard) {
            signs.push(sign(leg.from.quay, "l", 10));
            taken.add(leg.from.quay.id);
          } else stops.push(pt([leg.from.quay.lon, leg.from.quay.lat], { color, end: true, dim }));
        } else {
          // one feature per run of equal level so other levels can be dimmed
          const g = leg.geometry;
          const lv = leg.levels ?? [];
          let start = 0;
          for (let k = 1; k <= g.length; k++) {
            const a = Math.round(lv[k - 1] ?? 0);
            const b = k < g.length ? Math.round(lv[k] ?? 0) : NaN;
            if (lv[k - 1] != null) routeLevels.push({ lvl: a, lon: g[k - 1]![0], lat: g[k - 1]![1] });
            if (k === g.length || b !== a) {
              const end = Math.min(k, g.length - 1);
              if (end > start) walk.push({ type: "Feature", geometry: { type: "LineString", coordinates: g.slice(start, end + 1) }, properties: { lvl: a, lvl2: a, dim } });
              start = end;
            }
          }
          // a marker where the route changes level: which way, and to which level
          if (!dim)
            for (const st of leg.steps ?? []) {
              if (st.level === undefined || st.toLevel === undefined || st.toLevel === st.level) continue;
              const at = g[Math.min(g.length - 1, Math.round((st.from + st.to) / 2))];
              if (at) marks.push(pt(at, { img: `lv|${st.toLevel > st.level ? "u" : "d"}|${levelShort(st.toLevel)}` }));
            }
          if (sc.slice && sc.slice.leg === i) {
            const part = g.slice(sc.slice.from, sc.slice.to + 1);
            if (part.length > 1) focus = { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "LineString", coordinates: part }, properties: {} }] };
            else if (part.length === 1) stops.push(pt(part[0]!, { color: WALK_EDGE, end: true, dim: false }));
          }
        }
      });
      const first = j.legs[0];
      const last = j.legs[j.legs.length - 1];
      if (first?.type === "walk") pins.push(pt([first.from.lon, first.from.lat], { img: "pin|from", anchor: "center" }));
      if (last?.type === "walk") pins.push(pt([last.to.lon, last.to.lat], { img: "pin|to", anchor: "bottom" }));
      else if (last) pins.push(pt([last.to.quay.lon, last.to.quay.lat], { img: "pin|to", anchor: "bottom" }));
    }
    if (sc.pins?.from) pins.push(pt([sc.pins.from.lon, sc.pins.from.lat], { img: "pin|from", anchor: "center" }));
    if (sc.pins?.to) pins.push(pt([sc.pins.to.lon, sc.pins.to.lat], { img: "pin|to", anchor: "bottom" }));
    if (sc.trip) {
      const color = lineStroke(sc.trip.line, dark);
      ride.push({ type: "Feature", geometry: { type: "LineString", coordinates: sc.trip.geometry }, properties: { color, dim: false } });
      sc.trip.calls.forEach((c, i) => stops.push(pt([c.quay.lon, c.quay.lat], { color, end: i === 0 || i === sc.trip!.calls.length - 1, dim: false })));
    }
    if (sc.station) {
      for (const q of sc.station.quays) {
        if (taken.has(q.id)) continue;
        signs.push(sign(q, q.id === sc.station.selected ? "x" : "m", q.id === sc.station.selected ? 9 : 5));
        taken.add(q.id);
      }
    }
    if (sc.hero && !taken.has(sc.hero.id)) {
      signs.push(sign(sc.hero, "l", 10));
      taken.add(sc.hero.id);
    }
    for (const q of context) if (!taken.has(q.id)) signs.push(sign(q, "s", 1));
    set("ride", { type: "FeatureCollection", features: ride });
    set("walk", { type: "FeatureCollection", features: walk });
    set("stops", { type: "FeatureCollection", features: stops });
    set("signs", { type: "FeatureCollection", features: signs });
    set("pins", { type: "FeatureCollection", features: pins });
    set("lvl", { type: "FeatureCollection", features: marks });
    set("focus", focus);
    routePoints = [...routeLevels, ...quayLevels];
    publishLevels();
  }

  /** levelled vertices of the walking route */
  let routePoints: { lvl: number; lon: number; lat: number }[] = [];
  /** levelled indoor features with their bounding boxes */
  let indoorBoxes: { lvl: number; lvl2: number; box: BBox }[] = [];
  function publishLevels(): void {
    const b = map.getBounds();
    const [w, s, e, n] = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
    const all = new Set<number>();
    for (const p of routePoints) if (p.lon >= w && p.lon <= e && p.lat >= s && p.lat <= n) all.add(p.lvl);
    // only what is on screen counts: a station two streets away must not bring up the switcher
    for (const f of indoorBoxes) {
      if (f.box[2] < w || f.box[0] > e || f.box[3] < s || f.box[1] > n) continue;
      all.add(f.lvl);
      all.add(f.lvl2);
    }
    const list = map.getZoom() >= 16.4 && all.size > 1 ? [...all].sort((a, b) => b - a) : [];
    if (list.join() !== levels.peek().join()) levels.value = list;
  }

  effect(() => render(scene.value));
  effect(() => {
    mapLevel.value;
    if (!ready) return;
    map.setPaintProperty("k-indoor", "line-opacity", levelOpacity(0.5, 0.08));
    map.setPaintProperty("k-indoor-steps", "line-opacity", levelOpacity(0.9, 0));
    map.setPaintProperty("k-signs", "icon-opacity", levelOpacity(1, 0.3));
    map.setPaintProperty("k-walk", "line-color", walkColor());
    map.setPaintProperty("k-walk", "line-opacity", walkOpacity(1));
    map.setPaintProperty("k-walk-casing", "line-opacity", walkOpacity(0.75));
    map.setPaintProperty("k-walk-arrows", "icon-opacity", walkOpacity(1));
    map.setLayoutProperty("k-walk-arrows", "icon-image", walkArrow());
  });
  effect(() => {
    const p = userPos.value;
    if (!p) return set("me", EMPTY);
    const acc = simulated.value ? 0 : Math.min(p.accuracy ?? 0, 400);
    const r22 = (acc * 2 ** 22) / (78271.5 * Math.cos((p.lat * Math.PI) / 180));
    set("me", {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] }, properties: { r22, color: simulated.value ? "#E8590C" : "#2F6BFF" } }],
    });
  });

  // ------------------------------------------------------------ camera

  function pad(): { top: number; bottom: number; left: number; right: number } {
    const i = insets.peek();
    const h = container.clientHeight;
    const w = container.clientWidth;
    const bottom = Math.min(i.bottom, h * 0.62);
    // room for the signs at the ends of a route, and for the location button at the bottom right
    return { top: Math.min(i.top + 40, h * 0.3), bottom: bottom + 44, left: Math.min(i.left, w * 0.6) + 56, right: 64 };
  }
  function apply(c: Camera): void {
    const padding = pad();
    const view = map.getBounds();
    const far = (lon: number, lat: number) => {
      const dx = view.getEast() - view.getWest();
      const dy = view.getNorth() - view.getSouth();
      return lon < view.getWest() - dx * 2 || lon > view.getEast() + dx * 2 || lat < view.getSouth() - dy * 2 || lat > view.getNorth() + dy * 2;
    };
    if (c.kind === "bounds") {
      const [w, s, e, n] = c.bbox;
      const duration = reducedMotion.matches || far((w + e) / 2, (s + n) / 2) ? 0 : 550;
      map.fitBounds([[w, s], [e, n]], { padding, maxZoom: c.maxZoom ?? 17, duration, essential: true });
    } else {
      const zoom = c.zoom ?? Math.max(map.getZoom(), c.minZoom ?? 0);
      const duration = reducedMotion.matches || far(c.lon, c.lat) ? 0 : 600;
      // an offset, not padding: padding passed to easeTo would stick to the map and add up
      const offset: [number, number] = [(padding.left - padding.right) / 2, (padding.top - padding.bottom) / 2];
      map.easeTo({ center: [c.lon, c.lat], zoom, offset, duration, essential: true });
    }
  }
  // the camera refits its subject into the free area whenever the sheet settles,
  // unless the traveller has moved the map by hand since
  let lastCam: Camera | null = null;
  let userMoved = false;
  effect(() => {
    const c = camera.value;
    if (!c) return;
    lastCam = c;
    userMoved = false;
    apply(c);
  });
  let insetKey = "";
  effect(() => {
    const i = insets.value;
    const key = `${i.top}|${i.bottom}|${i.left}`;
    if (key === insetKey) return;
    insetKey = key;
    if (lastCam && !userMoved && mapReady.peek()) apply(lastCam);
  });
  for (const ev of ["dragstart", "zoomstart"] as const)
    map.on(ev, (e) => {
      if ((e as { originalEvent?: Event }).originalEvent) userMoved = true;
    });

  // ------------------------------------------------------------ context: quays, indoor network, vehicles

  const cover = (b: BBox, cell: number): BBox => [
    Math.floor(b[0] / cell) * cell, Math.floor(b[1] / (cell * 0.7)) * cell * 0.7,
    Math.ceil(b[2] / cell) * cell, Math.ceil(b[3] / (cell * 0.7)) * cell * 0.7,
  ];
  function loader<T>(minZoom: number, cell: number, fetcher: (b: BBox, s: AbortSignal) => Promise<T>, done: (v: T | null) => void) {
    const cache = new Map<string, T>();
    let ctl: AbortController | null = null;
    let current = "";
    return (b: BBox, zoom: number) => {
      if (zoom < minZoom) {
        ctl?.abort();
        if (current !== "") done(null);
        current = "";
        return;
      }
      const c = cover(b, cell);
      const key = c.map((x) => x.toFixed(4)).join(",");
      if (key === current) return;
      current = key;
      ctl?.abort();
      const hit = cache.get(key);
      if (hit) return done(hit);
      ctl = new AbortController();
      fetcher(c, ctl.signal).then(
        (v) => {
          if (cache.size > 24) cache.delete(cache.keys().next().value!);
          cache.set(key, v);
          if (current === key) done(v);
        },
        () => {
          if (current === key) current = "";
        },
      );
    };
  }
  const loadQuays = loader(15.6, 0.008, (b, s) => api.quays(b, s), (r) => {
    context = r?.quays ?? [];
    render(scene.peek());
  });
  const loadIndoor = loader(15.8, 0.008, (b, s) => api.indoor(b, s), (fc) => {
    indoorBoxes = [];
    const features = (fc?.features ?? []).map((f: GeoJSON.Feature<GeoJSON.LineString, IndoorFeatureProps>) => {
      const p = f.properties as IndoorFeatureProps;
      const lvl = Math.round(p.level ?? 0);
      const lvl2 = Math.round(p.toLevel ?? p.level ?? 0);
      if (p.indoor || p.level !== null) {
        const box = bboxOf(f.geometry.coordinates as LngLat[]);
        if (box) indoorBoxes.push({ lvl, lvl2, box });
      }
      return { ...f, properties: { kind: p.kind, lvl, lvl2 } };
    });
    set("indoor", { type: "FeatureCollection", features });
    publishLevels();
  });

  let vehicles: Vehicle[] = [];
  let vehCtl: AbortController | null = null;
  let vehTimer = 0;
  function loadVehicles(): void {
    clearTimeout(vehTimer);
    vehCtl?.abort();
    if (map.getZoom() < 12.5 || document.hidden) {
      vehicles = [];
      set("veh", EMPTY);
      return;
    }
    const b = map.getBounds();
    const dx = (b.getEast() - b.getWest()) * 0.2;
    const dy = (b.getNorth() - b.getSouth()) * 0.2;
    vehCtl = new AbortController();
    api.vehicles([b.getWest() - dx, b.getSouth() - dy, b.getEast() + dx, b.getNorth() + dy], vehCtl.signal).then(
      (r) => {
        vehicles = r.vehicles;
        drawVehicles();
      },
      () => undefined,
    );
    vehTimer = window.setTimeout(loadVehicles, 15000);
  }
  const vehIndex = new Map<string, Vehicle>();
  function drawVehicles(): void {
    if (!vehicles.length) {
      if (data.veh.features.length) set("veh", EMPTY);
      return;
    }
    const now = nowMs() / 1000;
    vehIndex.clear();
    const features: GeoJSON.Feature[] = [];
    for (const v of vehicles) {
      const span = v.arr - v.dep;
      const f = span > 0 ? Math.min(1, Math.max(0, (now - v.dep) / span)) : 1;
      const c = lineColor(v.line);
      const key = v.tripId + "@" + v.serviceDate;
      vehIndex.set(key, v);
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [v.from[0] + (v.to[0] - v.from[0]) * f, v.from[1] + (v.to[1] - v.from[1]) * f] },
        properties: { key, color: dark ? c.dfg : c.bg, live: v.live, img: `vh|${lineLabel(v.line) || v.line.category}|${c.bg}|${c.fg}|${v.live[0]}` },
      });
    }
    set("veh", { type: "FeatureCollection", features });
  }
  window.setInterval(() => {
    if (!document.hidden && vehicles.length && !map.isMoving()) drawVehicles();
  }, 200);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadVehicles();
  });

  let moveTimer = 0;
  function onMoved(): void {
    const c = map.getCenter();
    const b = map.getBounds();
    const zoom = map.getZoom();
    const bbox: BBox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
    mapView.value = { lat: c.lat, lon: c.lng, zoom, bbox };
    writeJSON("kante.view", { lat: c.lat, lon: c.lng, zoom });
    loadQuays(bbox, zoom);
    loadIndoor(bbox, zoom);
    publishLevels();
    // zooming out by hand leaves the level view; a camera animation passing through must not
    if (zoom < 16 && userMoved && mapLevel.peek() !== null) mapLevel.value = null;
    loadVehicles();
  }
  map.on("moveend", () => {
    clearTimeout(moveTimer);
    moveTimer = window.setTimeout(onMoved, 120);
  });

  // ------------------------------------------------------------ input

  let pressTimer = 0;
  let suppressClick = 0;
  map.on("click", (e) => {
    if (Date.now() < suppressClick) return;
    const p = e.point;
    const hits = ready ? map.queryRenderedFeatures([[p.x - 14, p.y - 14], [p.x + 14, p.y + 14]], { layers: ["k-signs", "k-veh"] }) : [];
    const signHit = hits.find((f) => f.layer.id === "k-signs");
    if (signHit) {
      const q = quayIndex.get(String(signHit.properties.id));
      const tap = handlers.quayTap ?? defaults.quayTap;
      if (q && tap) return tap(q);
    }
    const vehHit = hits.find((f) => f.layer.id === "k-veh");
    if (vehHit) {
      const v = vehIndex.get(String(vehHit.properties.key));
      const tap = handlers.vehicleTap ?? defaults.vehicleTap;
      if (v && tap) return tap(v);
    }
    (handlers.mapTap ?? defaults.mapTap)?.({ lat: e.lngLat.lat, lon: e.lngLat.lng });
  });
  const cancelPress = () => clearTimeout(pressTimer);
  map.on("touchstart", (e) => {
    cancelPress();
    if (e.originalEvent.touches.length !== 1) return;
    const { lngLat, point } = e;
    pressTimer = window.setTimeout(() => {
      suppressClick = Date.now() + 700;
      navigator.vibrate?.(12);
      (handlers.longPress ?? defaults.longPress)?.({ lat: lngLat.lat, lon: lngLat.lng, x: point.x, y: point.y });
    }, 520);
  });
  for (const ev of ["touchend", "touchcancel", "touchmove", "movestart", "zoomstart"] as const) map.on(ev, cancelPress);
  map.on("contextmenu", (e) => {
    e.preventDefault();
    (handlers.longPress ?? defaults.longPress)?.({ lat: e.lngLat.lat, lon: e.lngLat.lng, x: e.point.x, y: e.point.y });
  });

  mapApi.center = () => {
    const c = map.getCenter();
    return { lat: c.lat, lon: c.lng };
  };
  mapApi.at = (x, y) => {
    const c = map.unproject([x, y]);
    return { lat: c.lat, lon: c.lng };
  };
  mapApi.zoomBy = (d) => map.easeTo({ zoom: map.getZoom() + d, duration: reducedMotion.matches ? 0 : 250 });

  await new Promise<void>((resolve) => map.once("load", () => resolve()));
  onMoved();
  mapReady.value = true;
  performance.mark("kante:map-ready");
  const c0 = camera.peek();
  if (c0) apply(c0);
  // debugging and tests
  (window as unknown as { __kanteMap?: MLMap }).__kanteMap = map;
}
