// Modal sheets and the controls floating over the map, shared by several screens.
import { signal } from "@preact/signals";
import { useEffect, useState } from "preact/hooks";
import { api, useQuery } from "../api/client";
import type { MetaResponse, Mode, Place } from "../api/types";
import { metres, type LatLon } from "../lib/geo";
import { levelShort, levelSpoken, cap } from "../lib/lines";
import { dayLabel, fromZurich, hm, nowS, simClock, stopSimClock, zparts } from "../lib/time";
import { flyTo, insets, mapApi } from "../map/scene";
import { openStation, planTo } from "../nav";
import { coordPlace, parseQuery, queryParams } from "../plan";
import { closeOverlay, go, navigate, href, openOverlay, route } from "../router";
import { DEFAULT_SETTINGS, MODE_GROUPS, saved, settings, showToast, simulated, SPEED_PRESETS, speedName, startGeo, geoStatus, updateSettings, userPos } from "../state";
import { Icon } from "../ui/icons";
import { isWide, Modal } from "../ui/sheet";
import { timeLabel } from "./results";

/** Station found under a tap on the map. */
export const mapCard = signal<{ station: Place; distM?: number } | null>(null);
/** Location the user long-pressed. */
export const pressMenu = signal<(LatLon & { x: number; y: number }) | null>(null);

const kmh = (v: number) => v.toFixed(1).replace(".0", "");

// ---------------------------------------------------------------- engine facts, fetched once

const metaSig = signal<MetaResponse | null>(null);
let metaAsked = false;
export function useMeta(): MetaResponse | null {
  if (!metaAsked) {
    metaAsked = true;
    api.meta().then((m) => (metaSig.value = m), () => (metaAsked = false));
  }
  return metaSig.value;
}

// ---------------------------------------------------------------- walking speed (two taps from the results)

export function SpeedSheet() {
  const s = settings.value;
  return (
    <Modal title="Walking speed">
      <div class="speed-grid" role="radiogroup" aria-label="Walking speed">
        {SPEED_PRESETS.map((p) => (
          <button
            key={p.kmh}
            class={"speed-opt" + (Math.abs(p.kmh - s.walkKmh) < 0.05 ? " on" : "")}
            role="radio"
            aria-checked={Math.abs(p.kmh - s.walkKmh) < 0.05}
            data-autofocus={Math.abs(p.kmh - s.walkKmh) < 0.05 ? "" : undefined}
            onClick={() => {
              updateSettings({ walkKmh: p.kmh });
              closeOverlay();
            }}
          >
            <b>{p.label}</b>
            <span>{kmh(p.kmh)} km/h</span>
            <small>about {Math.round(1000 / (p.kmh / 3.6) / 60)} min per km</small>
          </button>
        ))}
      </div>
      <p class="hint">Journeys update right away: a slower pace allows more time to change and may suggest different routes.</p>
      <button class="pill-btn block" onClick={() => { history.replaceState({ overlay: "settings", depth: route.peek().depth }, "", location.href); route.value = { ...route.peek(), overlay: "settings" }; }}>
        <Icon name="sliders" size={18} /> All options
      </button>
    </Modal>
  );
}

// ---------------------------------------------------------------- all options (full screen)

function Toggle({ label, sub, checked, onChange }: { label: string; sub?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label class="toggle">
      <span>
        <b>{label}</b>
        {sub && <small>{sub}</small>}
      </span>
      <input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange((e.target as HTMLInputElement).checked)} />
      <i aria-hidden="true" />
    </label>
  );
}
function Stepper({ label, value, unit, min, max, step, onChange }: { label: string; value: number; unit: string; min: number; max: number; step: number; onChange: (v: number) => void }) {
  return (
    <div class="stepper">
      <b>{label}</b>
      <div class="stepper-ctl">
        <button class="round-btn" onClick={() => onChange(Math.max(min, value - step))} disabled={value <= min} aria-label={`Decrease ${label.toLowerCase()}`}>
          <Icon name="minus" size={18} />
        </button>
        <output aria-live="polite">
          {value} {unit}
        </output>
        <button class="round-btn" onClick={() => onChange(Math.min(max, value + step))} disabled={value >= max} aria-label={`Increase ${label.toLowerCase()}`}>
          <Icon name="plus" size={18} />
        </button>
      </div>
    </div>
  );
}

export function SettingsSheet() {
  const s = settings.value;
  const meta = useMeta();
  const sv = saved.value;
  const stepFree = s.stairs === "never" && !s.escalators && !s.wheelchair;
  const groupOn = (modes: Mode[]) => !s.modes || modes.some((m) => s.modes!.includes(m));
  const toggleGroup = (modes: Mode[], on: boolean) => {
    const all = MODE_GROUPS.flatMap((g) => g.modes);
    const cur = new Set(s.modes ?? all);
    for (const m of modes) on ? cur.add(m) : cur.delete(m);
    updateSettings({ modes: cur.size === all.length ? null : cur.size === 0 ? null : [...cur] });
  };
  const savedRow = (icon: string, label: string, p: Place | undefined, clear: () => void, slot?: string) => (
    <div class="saved-row" key={label + (p?.id ?? "")}>
      <Icon name={icon} size={20} />
      <span class="row-text">
        <b>{label}</b>
        <small class="trunc">{p ? p.name : "Not set"}</small>
      </span>
      {p ? (
        <button class="pill-btn" onClick={clear} aria-label={`Remove ${label.toLowerCase()}`}>
          Remove
        </button>
      ) : (
        slot && (
          <button class="pill-btn" onClick={() => go("search", { f: "to", set: slot }, { replace: true })}>
            Set
          </button>
        )
      )}
    </div>
  );
  const rt = meta?.realtime;
  return (
    <Modal title="Options" full>
      <section class="opt">
        <h3>Walking speed</h3>
        <div class="speed-read">
          <b>{kmh(s.walkKmh)} km/h</b>
          <span>
            {speedName(s.walkKmh)} · about {Math.round(1000 / (s.walkKmh / 3.6) / 60)} min per km
          </span>
        </div>
        <input
          class="range"
          type="range"
          min="2.5"
          max="7"
          step="0.1"
          value={s.walkKmh}
          data-autofocus
          aria-label="Walking speed in kilometres per hour"
          aria-valuetext={`${kmh(s.walkKmh)} kilometres per hour, ${speedName(s.walkKmh)}`}
          onInput={(e) => updateSettings({ walkKmh: Math.round(Number((e.target as HTMLInputElement).value) * 10) / 10 })}
        />
        <div class="chips wrap">
          {SPEED_PRESETS.map((p) => (
            <button key={p.kmh} class={"chip" + (Math.abs(p.kmh - s.walkKmh) < 0.05 ? " on" : "")} onClick={() => updateSettings({ walkKmh: p.kmh })}>
              {p.label} {kmh(p.kmh)}
            </button>
          ))}
        </div>
        <p class="hint">Used for every walk: to the stop, between vehicles and to the door. It decides whether a change is possible.</p>
      </section>
      <section class="opt">
        <h3>Accessibility</h3>
        <Toggle
          label="Step-free"
          sub="No stairs and no escalators — for wheelchairs, pushchairs and heavy luggage"
          checked={stepFree || s.wheelchair}
          onChange={(v) => updateSettings(v ? { stairs: "never", escalators: false } : { stairs: "ok", escalators: true, wheelchair: false })}
        />
        <Toggle
          label="Fewer stairs"
          sub="Take a lift or ramp when the detour is small"
          checked={s.stairs === "avoid"}
          onChange={(v) => updateSettings({ stairs: v ? "avoid" : "ok", wheelchair: false })}
        />
        <Toggle label="No escalators" checked={!s.escalators || s.wheelchair} onChange={(v) => updateSettings({ escalators: !v, wheelchair: v ? s.wheelchair : false })} />
        <Toggle
          label="Wheelchair accessible"
          sub="Also avoid paths marked unsuitable and barriers a wheelchair can't pass"
          checked={s.wheelchair}
          onChange={(v) => updateSettings(v ? { wheelchair: true, stairs: "never", escalators: false } : { wheelchair: false })}
        />
        <p class="hint">Stairs, lifts and ramps come from OpenStreetMap and may be incomplete. Check on site when it matters.</p>
      </section>
      <section class="opt">
        <h3>Changes and walking</h3>
        <Stepper label="Extra change time" value={Math.round(s.marginS / 60)} unit="min" min={0} max={15} step={1} onChange={(v) => updateSettings({ marginS: v * 60 })} />
        <Stepper label="Maximum walk" value={s.maxWalkMin} unit="min" min={5} max={60} step={5} onChange={(v) => updateSettings({ maxWalkMin: v })} />
        <p class="hint">Extra change time is added to the walking time at every change. Maximum walk is the longest single walk to, from or between stops.</p>
      </section>
      <section class="opt">
        <h3>Transport types</h3>
        {MODE_GROUPS.map((g) => (
          <Toggle key={g.label} label={g.label} checked={groupOn(g.modes)} onChange={(v) => toggleGroup(g.modes, v)} />
        ))}
      </section>
      <section class="opt">
        <h3>Saved places</h3>
        {savedRow("home", "Home", sv.home, () => (saved.value = { ...sv, home: undefined }), "home")}
        {savedRow("work", "Work", sv.work, () => (saved.value = { ...sv, work: undefined }), "work")}
        {sv.favs.map((p) => savedRow("star", p.name, p, () => (saved.value = { ...sv, favs: sv.favs.filter((x) => x.id !== p.id) })))}
      </section>
      <section class="opt">
        <h3>Location</h3>
        {simulated.value ? (
          <div class="saved-row">
            <Icon name="locate" size={20} />
            <span class="row-text">
              <b>Simulated location is on</b>
              <small>
                {simulated.value.lat.toFixed(5)}, {simulated.value.lon.toFixed(5)}
              </small>
            </span>
            <button class="pill-btn" onClick={() => (simulated.value = null)}>
              Stop
            </button>
          </div>
        ) : (
          <p class="hint">Want to check another area? Long-press the map (right-click on desktop) and choose “I'm here”.</p>
        )}
      </section>
      <section class="opt">
        <button class="pill-btn block" onClick={() => { updateSettings(DEFAULT_SETTINGS); showToast("Options reset"); }}>
          Reset all options
        </button>
        <p class="hint about">
          {rt ? (rt.enabled ? "Live delays active" : "Timetable only (live data off)") : "Kante"}
          {meta ? ` · timetable valid ${meta.validFrom} – ${meta.validTo}` : ""}
          <br />
          {(meta?.attribution ?? ["Timetable and real-time data: opentransportdata.swiss", "Walking network: © OpenStreetMap contributors", "Base map: © swisstopo"]).join(" · ")}
        </p>
      </section>
    </Modal>
  );
}

// ---------------------------------------------------------------- time

export function TimeSheet() {
  const params = route.value.params;
  const q = parseQuery(params);
  const now = nowS();
  const [mode, setMode] = useState<"now" | "dep" | "arr">(q.time === null ? "now" : q.arriveBy ? "arr" : "dep");
  const [t, setT] = useState<number>(q.time ?? Math.ceil(now / 300) * 300);
  const z = zparts(t);
  const apply = (m: typeof mode, time: number) => {
    const next = { ...q, time: m === "now" ? null : time, arriveBy: m === "arr" };
    navigate(href(route.peek().name, { ...params, ...queryParams(next), j: undefined }), { replace: true });
  };
  const quick = (time: number) => {
    setT(time);
    if (mode === "now") setMode("dep");
  };
  const today = zparts(now).date;
  const eveningToday = fromZurich(today, "20:00") > now;
  const evening = eveningToday ? fromZurich(today, "20:00") : fromZurich(zparts(now + 86400).date, "20:00");
  return (
    <Modal title="When?">
      <div class="segmented" role="radiogroup" aria-label="Leave or arrive">
        {(["now", "dep", "arr"] as const).map((m) => (
          <button key={m} role="radio" aria-checked={mode === m} class={mode === m ? "on" : ""} onClick={() => setMode(m)} data-autofocus={mode === m ? "" : undefined}>
            {m === "now" ? "Leave now" : m === "dep" ? "Leave at" : "Arrive by"}
          </button>
        ))}
      </div>
      <div class={"time-inputs" + (mode === "now" ? " off" : "")}>
        <label>
          <span>Date</span>
          <input type="date" value={z.date} min={zparts(now - 86400).date} disabled={mode === "now"} onInput={(e) => { const v = (e.target as HTMLInputElement).value; if (v) setT(fromZurich(v, z.time)); }} />
        </label>
        <label>
          <span>Time</span>
          <input type="time" value={z.time} disabled={mode === "now"} onInput={(e) => { const v = (e.target as HTMLInputElement).value; if (v) setT(fromZurich(z.date, v)); }} />
        </label>
      </div>
      <div class="chips wrap">
        <button class="chip" onClick={() => quick((mode === "now" ? Math.ceil(now / 60) * 60 : t) + 900)}>+15 min</button>
        <button class="chip" onClick={() => quick((mode === "now" ? Math.ceil(now / 60) * 60 : t) + 3600)}>+1 h</button>
        <button class="chip" onClick={() => quick(evening)}>{eveningToday ? "Tonight 20:00" : "Tomorrow 20:00"}</button>
        <button class="chip" onClick={() => quick(fromZurich(zparts(now + 86400).date, "08:00"))}>Tomorrow 08:00</button>
      </div>
      <button class="pill-btn primary block" onClick={() => apply(mode, t)} data-testid="time-apply">
        {mode === "now" ? "Leave now" : timeLabel(q, t, mode === "arr", true)}
      </button>
    </Modal>
  );
}

// ---------------------------------------------------------------- long-press menu

export function PressMenu() {
  const p = pressMenu.value;
  const rev = useQuery(p ? `rev:${p.lat.toFixed(5)},${p.lon.toFixed(5)}` : null, (s) => api.reverse(p!.lat, p!.lon, s));
  if (!p) return null;
  const close = () => (pressMenu.value = null);
  const name = rev.data?.name;
  const place = coordPlace(p.lat, p.lon, name || undefined);
  if (rev.data?.detail) place.detail = rev.data.detail;
  return (
    <Modal title={name || "Map location"} onClose={close}>
      {rev.data?.detail && <p class="modal-sub">{rev.data.detail}</p>}
      <ul class="rows menu">
        <li>
          <button class="row" data-autofocus onClick={() => { close(); planTo(place); }}>
            <span class="row-icon">
              <Icon name="nav" />
            </span>
            <span class="row-text">
              <strong>Directions here</strong>
            </span>
          </button>
        </li>
        <li>
          <button class="row" onClick={() => { close(); go("search", { ...queryParams({ from: place, to: null, time: null, arriveBy: false, onboard: null }), f: "to" }); }}>
            <span class="row-icon">
              <Icon name="pin" />
            </span>
            <span class="row-text">
              <strong>Start from here</strong>
            </span>
          </button>
        </li>
        <li>
          <button
            class="row"
            onClick={() => {
              close();
              api.nearby(p.lat, p.lon, 400, 1).then(
                (r) => (r.stations[0] ? openStation(r.stations[0].place.id) : showToast("No stops nearby")),
                () => showToast("Couldn't look up stops"),
              );
            }}
          >
            <span class="row-icon">
              <Icon name="board" />
            </span>
            <span class="row-text">
              <strong>Departures near here</strong>
            </span>
          </button>
        </li>
        <li>
          <button
            class="row"
            data-testid="sim-here"
            onClick={() => {
              simulated.value = { lat: p.lat, lon: p.lon, at: Date.now() };
              showToast("Simulated location set");
              close();
            }}
          >
            <span class="row-icon sim">
              <Icon name="locate" />
            </span>
            <span class="row-text">
              <strong>I'm here</strong>
              <span>Use this as my location until I switch it off</span>
            </span>
          </button>
        </li>
      </ul>
    </Modal>
  );
}

/** Card for a stop tapped on the map: name, distance and the two things to do with it. */
export function MapCard() {
  const c = mapCard.value;
  if (!c) return null;
  return (
    <div class="map-card" role="dialog" aria-label={c.station.name}>
      <div class="map-card-head">
        <span class="row-text">
          <strong class="trunc">{c.station.name}</strong>
          {c.distM !== undefined && userPos.value && <span>{metres(c.distM)} from your location</span>}
        </span>
        <button class="round-btn" aria-label="Close" onClick={() => (mapCard.value = null)}>
          <Icon name="close" size={16} />
        </button>
      </div>
      <div class="map-card-actions">
        <button class="pill-btn primary" onClick={() => { const st = c.station; mapCard.value = null; openStation(st.id); }}>
          Departures
        </button>
        <button class="pill-btn" onClick={() => { const st = c.station; mapCard.value = null; planTo(st); }}>
          Directions
        </button>
      </div>
    </div>
  );
}

/**
 * Controls floating over the map. The location button rides 16 px above the
 * sheet's top edge (the sheet moves `#fab-rail`); the level pill sits at the left
 * edge in the middle of the free map area and only shows over indoor data.
 */
export function MapControls({ levels, level, onLevel }: { levels: number[]; level: number | null; onLevel: (l: number | null) => void }) {
  const pos = userPos.value;
  const ins = insets.value;
  const sim = simulated.value;
  const clock = simClock.value;
  const home = route.value.name === "home";
  // scroll the selected level into view when the route moves it
  useEffect(() => {
    document.querySelector(".levels button.on")?.scrollIntoView({ block: "nearest" });
  }, [level, levels.join()]);
  return (
    <>
      <div class="map-top" style={isWide.value || ins.top < 40 ? undefined : { top: `${ins.top + 8}px` }}>
        <div class="map-chips">
          {sim && (
            <button class="sim-chip" onClick={() => (simulated.value = null)} aria-label="Simulated location is on. Tap to stop">
              <Icon name="locate" size={14} />
              Simulated location
              <Icon name="close" size={13} />
            </button>
          )}
          {clock !== null && (
            <button class="sim-chip" onClick={stopSimClock} aria-label="Simulated time is on. Tap to stop">
              <Icon name="clock" size={14} />
              {dayLabel(nowS()) === "Today" ? "" : dayLabel(nowS()) + " "}
              {hm(nowS())}
              <Icon name="close" size={13} />
            </button>
          )}
        </div>
        {home && (
          <button class="fab small" onClick={() => openOverlay("settings")} aria-label="Options: walking speed, accessibility, transport types">
            <Icon name="sliders" size={20} />
          </button>
        )}
      </div>
      {levels.length > 1 && (
        <div
          class="levels"
          role="radiogroup"
          aria-label="Level"
          style={isWide.value ? undefined : { top: `${Math.round(ins.top + (window.innerHeight - ins.bottom - ins.top) / 2)}px` }}
        >
          {levels.map((l) => (
            <button key={l} role="radio" aria-checked={level === l} class={level === l ? "on" : ""} onClick={() => onLevel(level === l ? null : l)} aria-label={cap(levelSpoken(l))}>
              <span>{levelShort(l)}</span>
            </button>
          ))}
        </div>
      )}
      <div class="fab-rail" id="fab-rail">
        <div class="attrib">© swisstopo · © OpenStreetMap</div>
        <div class="zoom">
          <button onClick={() => mapApi.zoomBy?.(1)} aria-label="Zoom in">
            <Icon name="plus" size={18} />
          </button>
          <button onClick={() => mapApi.zoomBy?.(-1)} aria-label="Zoom out">
            <Icon name="minus" size={18} />
          </button>
        </div>
        <button
          class="fab"
          aria-label={pos ? "Centre the map on my location" : "Use my location"}
          onClick={() => {
            if (pos) flyTo({ kind: "point", lat: pos.lat, lon: pos.lon, minZoom: 16 });
            else openOverlay("locate");
          }}
        >
          <Icon name={pos ? "nav" : "locate"} size={24} />
        </button>
      </div>
    </>
  );
}

export function LocateSheet() {
  const st = geoStatus.value;
  return (
    <Modal title="Your location">
      <p class="hint big">
        {st === "denied"
          ? "Location access is blocked. Allow location for this site in your browser settings, then try again."
          : "Kante uses your location for departures around you, for walking directions and to work out which vehicle you're on. It stays on your device and in the requests to Kante."}
      </p>
      <button class="pill-btn primary block" data-autofocus onClick={() => { closeOverlay(); startGeo(); }}>
        <Icon name="locate" size={18} /> {st === "denied" ? "Try again" : "Use my location"}
      </button>
      <p class="hint">Want to check another area? Long-press the map (right-click on desktop) and choose “I'm here”.</p>
    </Modal>
  );
}
