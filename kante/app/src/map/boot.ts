// Starts the map without blocking the first paint: the style JSON and the
// MapLibre chunk are requested in parallel once the shell is on screen.
import type { StyleSpecification } from "maplibre-gl";
import { mapFailed } from "./scene";

const STYLE_URL = "https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json";
let started = false;

export function bootMap(container: HTMLElement): void {
  if (started) return;
  started = true;
  const style = fetch(STYLE_URL).then((r) => {
    if (!r.ok) throw new Error("map style: HTTP " + r.status);
    return r.json() as Promise<StyleSpecification>;
  });
  style.catch(() => undefined);
  import("./engine")
    .then((m) => m.createMap(container, style))
    .catch((err: Error) => {
      mapFailed.value = err.message || "The map could not be loaded";
    });
}
