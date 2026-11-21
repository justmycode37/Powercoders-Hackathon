import { useEffect, useRef } from "preact/hooks";
import { api } from "./api/client";
import { dist } from "./lib/geo";
import { bootMap } from "./map/boot";
import { defaults, levels, mapFailed, mapLevel, mapReady } from "./map/scene";
import { openStation, openTrip } from "./nav";
import { route } from "./router";
import { Go, GuidanceStrip } from "./screens/go";
import { Home } from "./screens/home";
import { JourneyScreen } from "./screens/journey";
import { Onboard } from "./screens/onboard";
import { Results } from "./screens/results";
import { Pick, Search } from "./screens/search";
import { LocateSheet, mapCard, MapCard, MapControls, PressMenu, pressMenu, SettingsSheet, SpeedSheet, TimeSheet } from "./screens/sheets";
import { Station, Trip } from "./screens/station";
import { online, toast, userPos } from "./state";
import { Icon } from "./ui/icons";

const SCREENS = { home: Home, search: Search, pick: Pick, plan: Results, journey: JourneyScreen, go: Go, station: Station, trip: Trip, onboard: Onboard };
const OVERLAYS: Record<string, () => preact.JSX.Element> = { settings: SettingsSheet, speed: SpeedSheet, time: TimeSheet, locate: LocateSheet };

export function App() {
  const r = route.value;
  const mapEl = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // the shell is on screen: now fetch the map
    const start = () => mapEl.current && bootMap(mapEl.current);
    const id = requestAnimationFrame(() => setTimeout(start, 0));
    // what a tap on the map does on every screen, unless the screen says otherwise
    defaults.longPress = (p) => (pressMenu.value = p);
    defaults.quayTap = (quay) => openStation(quay.stationId, quay.label ? quay.id : undefined);
    defaults.vehicleTap = (v) => openTrip(v.tripId, v.serviceDate);
    defaults.mapTap = (p) => {
      const name = route.peek().name;
      if (name === "pick" || name === "go") return;
      if (mapCard.peek()) return void (mapCard.value = null);
      api.nearby(p.lat, p.lon, 90, 1).then(
        (res) => {
          const st = res.stations[0];
          const me = userPos.peek();
          mapCard.value = st ? { station: st.place, distM: me ? dist(me.lat, me.lon, st.place.lat, st.place.lon) : undefined } : null;
        },
        () => undefined,
      );
    };
    return () => cancelAnimationFrame(id);
  }, []);
  useEffect(() => {
    mapCard.value = null;
  }, [r.name, r.params.id, r.params.j]);
  const Screen = SCREENS[r.name] ?? Home;
  const Overlay = r.overlay ? OVERLAYS[r.overlay] : null;
  return (
    <div class={"app s-" + r.name}>
      <div class={"map-wrap" + (mapReady.value ? " ready" : "")}>
        <div class="map" ref={mapEl} />
        {mapFailed.value && (
          <div class="map-error" role="status">
            <Icon name="offline" size={16} /> {online.value ? "Map unavailable" : "You're offline — the map isn't available"}. Everything else still works.
          </div>
        )}
        <MapControls levels={levels.value} level={mapLevel.value} onLevel={(l) => (mapLevel.value = l)} />
        <MapCard />
        <GuidanceStrip />
      </div>
      <div class="panel" key={r.name}>
        <Screen />
      </div>
      {Overlay && <Overlay />}
      <PressMenu />
      {toast.value && (
        <div class="toast" role="status" key={toast.value.id}>
          {toast.value.text}
        </div>
      )}
    </div>
  );
}
