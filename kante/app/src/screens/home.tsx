import { useEffect, useRef } from "preact/hooks";
import { api, useQuery } from "../api/client";
import type { NearbyLine, NearbyResponse, NearbyStation, Place } from "../api/types";
import { dist, metres } from "../lib/geo";
import { isNight, lineLabel, lineTitle, lineVars, quayShort, sideShort } from "../lib/lines";
import { readJSON, writeJSON } from "../lib/store";
import { dayLabel, delayMins, hm, nowS, tick10 } from "../lib/time";
import { DEFAULT_CENTER, flyTo, mapView, savedView, scene } from "../map/scene";
import { openTrip, planTo } from "../nav";
import { href } from "../router";
import { geoStatus, online, onboard, recents, saved, settings, startGeo, userPos } from "../state";
import { Empty, ModeIcons, Notice, Skeleton } from "../ui/bits";
import { Icon, modeIcon } from "../ui/icons";
import { Sheet } from "../ui/sheet";
import { useMeta } from "./sheets";

interface NearbyCache { key: string; data: NearbyResponse; at: number }
interface Card { st: NearbyStation; l: NearbyLine; walkS: number | null }

/** Rough walking time to a boarding point: straight line plus a detour allowance. */
const walkSecs = (m: number, kmh: number) => (m * 1.3) / (kmh / 3.6);

/** One card per line and direction, at the nearest stop that has it. */
function cards(stations: NearbyStation[], pos: { lat: number; lon: number } | null, kmh: number): Card[] {
  const seen = new Set<string>();
  const out: Card[] = [];
  for (const st of stations) {
    for (const l of st.lines) {
      const key = `${l.line.mode}|${l.line.name}|${l.line.category}|${l.headsign}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ st, l, walkS: pos ? walkSecs(dist(pos.lat, pos.lon, l.quay.lat, l.quay.lon), kmh) : null });
    }
  }
  return out;
}

export function Home() {
  const pos = userPos.value;
  const view = mapView.value;
  const c = pos ?? (view ? { lat: view.lat, lon: view.lon } : (savedView ?? DEFAULT_CENTER));
  // ~80 m grid: small map nudges do not refetch
  const key = `${c.lat.toFixed(3)},${c.lon.toFixed(3)}`;
  const cached = useRef(readJSON<NearbyCache>("kante.nearby")).current;
  const q = useQuery("nearby:" + key, (s) => api.nearby(c.lat, c.lon, 650, 6, s), { refreshS: 30, initial: cached?.data });
  const meta = useMeta();
  useEffect(() => {
    if (q.data && q.at) writeJSON("kante.nearby", { key, data: q.data, at: Math.floor(q.at / 1000) });
  }, [q.data]);
  useEffect(() => {
    scene.value = {};
  }, []);
  // centre on the user once per visit
  const centred = useRef(false);
  useEffect(() => {
    if (pos && !centred.current) {
      centred.current = true;
      flyTo({ kind: "point", lat: pos.lat, lon: pos.lon, minZoom: 15.5 });
    }
  }, [pos?.lat, pos?.lon]);

  const now = tick10.value;
  const ob = onboard.value && onboard.value.until > nowS() ? onboard.value : null;
  const s = saved.value;
  const stations = q.data?.stations ?? [];
  const list = cards(stations, pos, settings.value.walkKmh).slice(0, 16);
  const geo = geoStatus.value;
  const savedAt = q.at ? Math.floor(q.at / 1000) : (cached?.at ?? 0);
  const rt = meta?.realtime;
  const box = meta?.walkBbox;
  const outside = !!box && (c.lon < box[0] - 0.3 || c.lon > box[2] + 0.3 || c.lat < box[1] - 0.3 || c.lat > box[3] + 0.3);
  const shortcuts: Place[] = [...s.favs, ...recents.value.filter((p) => p.id !== s.home?.id && p.id !== s.work?.id && !s.favs.some((f) => f.id === p.id)).slice(0, 3)];
  return (
    <Sheet
      label="Departures near you"
      flat
      mid={0.56}
      overhang={49}
      initial="mid"
      class="home"
      header={
        <>
          <div class="searchbar">
            <a class="searchbar-main" href={href("search", { f: "to" })} aria-label="Where to? Search for a destination">
              <Icon name="search" size={22} />
              <span>Where to?</span>
            </a>
            <a class={"searchbar-ob" + (ob ? " on" : "")} href={href("onboard")} aria-label={ob ? `You're on ${lineTitle(ob.line)}. Change` : "I'm on board: plan from the vehicle you're on"}>
              <Icon name="onboard" size={22} />
              <span>{ob ? "On board" : "I'm on board"}</span>
            </a>
          </div>
          <div class="shortcuts">
            <SavedChip icon="home" label="Home" place={s.home} slot="home" />
            <SavedChip icon="work" label="Work" place={s.work} slot="work" />
            {shortcuts.map((p) => (
              <button key={p.id} class="chip" onClick={() => planTo(p)}>
                <Icon name={s.favs.some((f) => f.id === p.id) ? "star" : "history"} size={16} />
                <span class="trunc">{p.name}</span>
              </button>
            ))}
          </div>
        </>
      }
    >
      {ob && (
        <div class="banner">
          <Icon name="onboard" size={22} />
          <div class="banner-text">
            <strong>You're on {lineTitle(ob.line)}</strong>
            <span class="trunc">to {ob.headsign}</span>
          </div>
          <a class="pill-btn tonal" href={href("search", { f: "to", ob: `${ob.tripId}|${ob.serviceDate}` })}>
            Where to?
          </a>
          <button class="round-btn plain" aria-label="I got off" onClick={() => (onboard.value = null)}>
            <Icon name="close" size={18} />
          </button>
        </div>
      )}
      {!pos && (
        <div class="banner locate">
          <Icon name="locate" size={22} />
          <div class="banner-text">
            <strong>
              {geo === "denied" ? "Location access is blocked" : geo === "asking" ? "Finding your location…" : geo === "unavailable" ? "Couldn't find your location" : "Showing departures near the map centre"}
            </strong>
            <span>
              {geo === "denied"
                ? "Allow location in your browser settings, or long-press the map (right-click on desktop) and choose “I'm here”."
                : geo === "asking"
                  ? "Wait a moment, or search for a stop instead."
                  : geo === "unavailable"
                    ? "Check your device's location settings, or long-press the map and choose “I'm here”."
                    : "Use your location to see what leaves near you and how long the walk is."}
            </span>
          </div>
          {geo !== "denied" && geo !== "asking" && (
            <button class="pill-btn" onClick={startGeo}>
              Use my location
            </button>
          )}
        </div>
      )}
      {rt && !rt.enabled && <Notice kind="info">Timetable only — live delays and platform changes aren't available</Notice>}
      {rt?.enabled && rt.updatedAt !== undefined && nowS() - rt.updatedAt > 600 && nowS() - rt.updatedAt < 86400 && <Notice kind="warning">Live updates are delayed — showing timetable times</Notice>}
      {q.error && q.data && (
        <div class="status-line" role="status">
          <Icon name="offline" size={14} />
          {online.value ? "Couldn't refresh" : "Offline"} · showing departures saved at {hm(savedAt)}
        </div>
      )}
      {!q.data && q.loading && <Skeleton rows={4} kind="card" label="Loading departures" />}
      {!q.data && q.error && (
        <Notice kind="severe" icon={online.value ? undefined : "offline"} action={<button class="pill-btn" onClick={q.reload}>Try again</button>}>
          {q.error}
        </Notice>
      )}
      {q.data && stations.length === 0 &&
        (outside ? (
          <Empty icon="map" title="Outside Kante's coverage area">
            Kante covers public transport in Switzerland. Move the map to Switzerland or search for a Swiss stop.
          </Empty>
        ) : (
          <Empty icon="board" title="No stops nearby">
            Move the map or search for a stop.
          </Empty>
        ))}
      {q.data && stations.length > 0 && list.length === 0 && <Empty icon="clock" title="No upcoming departures">Nothing leaves from the stops around here in the next few hours.</Empty>}
      <div class="near-cards">
        {list.map((cd) => (
          <LineCard key={cd.l.tripId + cd.l.quay.id} card={cd} now={now} />
        ))}
      </div>
      {stations.length > 0 && (
        <>
          <h2 class="section-title">Stops nearby</h2>
          <ul class="rows">
            {stations.map((st) => (
              <li key={st.place.id}>
                <a class="row" href={href("station", { id: st.place.id })}>
                  <span class="row-icon">
                    <ModeIcons modes={st.place.modes?.slice(0, 1)} size={22} />
                  </span>
                  <span class="row-text">
                    <strong class="trunc">{st.place.name}</strong>
                    <span>
                      {metres(st.distM)}
                      {pos ? ` · ${Math.max(1, Math.round(walkSecs(st.distM, settings.value.walkKmh) / 60))} min walk` : " from the map centre"}
                    </span>
                  </span>
                  <span class="row-end">Departures</span>
                  <Icon name="right" size={16} class="muted" />
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </Sheet>
  );
}

function SavedChip({ icon, label, place, slot }: { icon: string; label: string; place: Place | undefined; slot: string }) {
  if (place)
    return (
      <button class="chip" onClick={() => planTo(place)}>
        <Icon name={icon} size={16} />
        {label}
      </button>
    );
  return (
    <a class="chip ghost" href={href("search", { f: "to", set: slot })}>
      <Icon name={icon} size={16} />
      Set {label.toLowerCase()}
    </a>
  );
}

/**
 * Full-bleed card in the line's colour with two loud elements: the line, and
 * the minutes until it leaves. Underneath, what no other app prints here: the
 * boarding point and the walk to it. Live versus timetable is a word.
 */
function LineCard({ card, now }: { card: Card; now: number }) {
  const { l, st, walkS } = card;
  const t = l.next[0];
  const secs = t === undefined ? null : t - now;
  const mins = secs === null ? null : Math.floor(secs / 60);
  const label = lineLabel(l.line);
  const where = quayShort(l.quay) || sideShort(l.quay);
  const walkMin = walkS === null ? null : Math.max(1, Math.round(walkS / 60));
  const when = mins === null ? "no departure" : mins < 1 ? "now" : mins < 60 ? `in ${mins} ${mins === 1 ? "minute" : "minutes"}` : `at ${hm(t!)}`;
  // a departure the walk cannot reach is still shown, but says so
  const tooLate = secs !== null && walkS !== null && secs < walkS - 30 && l.next.length > 1;
  const later = l.next.slice(1, 3).map((x) => Math.floor((x - now) / 60)).filter((m) => m > 0 && m < 60);
  return (
    <a
      class="lcard"
      style={lineVars(l.line)}
      href={href("trip", { id: l.tripId, date: l.serviceDate, seq: l.seq })}
      aria-label={`${lineTitle(l.line)} to ${l.headsign}, ${when}${where ? ", " + where : ""}, ${st.place.name}${walkMin ? `, ${walkMin} min walk` : ""}, ${l.live ? "live" : "timetable"}`}
    >
      <span class="lcard-main">
        <span class={"lcard-line" + (label.length > 3 ? " long" : "")}>
          {isNight(l.line) && <Icon name="moon" size={18} />}
          {label || <Icon name={modeIcon(l.line.mode)} size={36} />}
          {label && <Icon name={modeIcon(l.line.mode)} size={18} class="lcard-mode" />}
        </span>
        <span class="lcard-dir">
          <Icon name="go" size={16} />
          <span class="trunc">{l.headsign}</span>
        </span>
        <span class="lcard-stop">
          {where && <b>{where}</b>}
          <span class="trunc">{st.place.name}</span>
          {walkMin !== null && (
            <span class="lcard-walk">
              <Icon name="walk" size={14} />
              {walkMin} min
            </span>
          )}
        </span>
      </span>
      <span class="lcard-time">
        {mins === null ? (
          <b class="clock">—</b>
        ) : mins < 1 ? (
          <b class="word">now</b>
        ) : mins < 60 ? (
          <>
            <b>{mins}</b>
            <small>min</small>
          </>
        ) : (
          <>
            <b class="clock">{hm(t!)}</b>
            {dayLabel(t!, now) !== "Today" && <small>{dayLabel(t!, now)}</small>}
          </>
        )}
        <span class="lcard-live">
          {l.live ? <i class="live-dot" aria-hidden="true" /> : <Icon name="clock" size={11} />}
          {l.live ? "Live" : "Timetable"}
        </span>
        {tooLate ? <span class="lcard-next">then {later[0] ?? hm(l.next[1]!)}{later[0] !== undefined ? " min" : ""}</span> : later.length > 0 && mins !== null && mins < 60 && <span class="lcard-next">then {later.join(", ")}</span>}
      </span>
    </a>
  );
}
