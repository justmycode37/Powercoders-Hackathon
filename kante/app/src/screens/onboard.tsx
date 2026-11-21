import { useEffect, useState } from "preact/hooks";
import { api, useQuery } from "../api/client";
import type { OnboardCandidate } from "../api/types";
import { metres } from "../lib/geo";
import { isNight, lineLabel, lineTitle, lineVars } from "../lib/lines";
import { hm } from "../lib/time";
import { mapView, scene } from "../map/scene";
import { boardTrip } from "../nav";
import { back, href } from "../router";
import { geoStatus, online, startGeo, userPos } from "../state";
import { Delay, Empty, ModeIcons, Notice, Skeleton } from "../ui/bits";
import { Icon, modeIcon } from "../ui/icons";
import { Sheet, SheetClose } from "../ui/sheet";

/** People know their line and where it is heading, not a vehicle: one card per line and direction, nearest first. */
function byLine(list: OnboardCandidate[]): OnboardCandidate[] {
  const seen = new Set<string>();
  return list.filter((c) => {
    const k = `${c.line.mode}|${c.line.name}|${c.line.category}|${c.headsign}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

export function Onboard() {
  const [filter, setFilter] = useState("");
  const pos = userPos.value;
  const term = filter.trim();
  const key = pos || term ? `ob:${pos ? pos.lat.toFixed(4) + "," + pos.lon.toFixed(4) : ""}:${term}` : null;
  const q = useQuery(key, (s) => api.onboard({ lat: pos?.lat, lon: pos?.lon, q: term || undefined }, s), { refreshS: 15 });
  const c = pos ?? (mapView.value ? { lat: mapView.value.lat, lon: mapView.value.lon } : null);
  const near = useQuery(c ? `obn:${c.lat.toFixed(3)},${c.lon.toFixed(3)}` : null, (s) => api.nearby(c!.lat, c!.lon, 900, 4, s));
  useEffect(() => {
    scene.value = {};
  }, []);
  const pick = (cand: OnboardCandidate) =>
    boardTrip({ tripId: cand.tripId, serviceDate: cand.serviceDate, nextSeq: cand.nextSeq, line: cand.line, headsign: cand.headsign, until: cand.nextArr + 4 * 3600 });
  const list = byLine(q.data?.candidates ?? []).slice(0, term ? 8 : 5);
  const geo = geoStatus.value;
  return (
    <Sheet
      label="I'm on board"
      initial="full"
      header={
        <>
          <div class="sheet-title">
            <div class="title-stack">
              <h1>Which vehicle are you on?</h1>
              <span class="title-sub">Kante plans from your seat, counting the stops still ahead</span>
            </div>
            <span class="sheet-actions">
              <SheetClose onClick={() => back("/")} />
            </span>
          </div>
          <label class="filter">
            <Icon name="search" size={18} />
            <input
              type="search"
              inputMode="search"
              placeholder="Line, e.g. 9 or IC 1"
              value={filter}
              onInput={(e) => setFilter((e.target as HTMLInputElement).value)}
              aria-label="Filter by line"
              autocomplete="off"
              autocapitalize="off"
              spellcheck={false}
            />
          </label>
        </>
      }
    >
      {!pos && (
        <Notice kind="info" action={geo !== "denied" && geo !== "asking" ? <button class="pill-btn" onClick={startGeo}>Use my location</button> : undefined}>
          {geo === "asking" ? "Finding your location…" : "Without your location, Kante can't tell which vehicle you're on. Type the line, or pick your trip from a nearby stop."}
        </Notice>
      )}
      {key && !q.data && q.loading && <Skeleton rows={3} kind="card" label="Looking for vehicles near you" />}
      {q.error && !q.data && <Notice kind="severe" icon={online.value ? undefined : "offline"} action={<button class="pill-btn" onClick={q.reload}>Try again</button>}>{q.error}</Notice>}
      {q.error && q.data && (
        <div class="status-line" role="status">
          <Icon name="offline" size={14} />
          {online.value ? "Couldn't refresh" : "Offline"} — showing vehicles from {hm(Math.floor(q.at / 1000))}
        </div>
      )}
      {list.length > 0 && <h2 class="section-title">{pos ? "Probably one of these" : "Running now"}</h2>}
      <ul class="cands">
        {list.map((cand) => {
          const label = lineLabel(cand.line);
          return (
            <li key={cand.tripId + cand.serviceDate}>
              <button class="cand" style={lineVars(cand.line)} onClick={() => pick(cand)} aria-label={`${lineTitle(cand.line)} to ${cand.headsign}, next stop ${cand.nextStop}`}>
                <span class={"cand-line" + (label.length > 3 ? " long" : "")}>
                  {isNight(cand.line) && <Icon name="moon" size={14} />}
                  {label || <Icon name={modeIcon(cand.line.mode)} size={28} />}
                </span>
                <span class="cand-main">
                  <strong>
                    <Icon name="go" size={14} />
                    <span class="trunc2">{cand.headsign}</span>
                  </strong>
                  <span class="trunc">
                    Next stop {cand.nextStop} · {hm(cand.nextArr + (cand.delayS ?? 0))} <Delay s={cand.delayS} short />
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {key && q.data && list.length === 0 && (
        <Empty icon="onboard" title={term ? `No “${term}” running ${pos ? "near you" : "right now"}` : "No vehicle seems to be right here"}>
          Vehicle positions are estimated from the timetable and live stop times. Try the line number, or pick your trip from a stop.
        </Empty>
      )}
      <h2 class="section-title">Or pick from a nearby stop</h2>
      <p class="hint inset">Open a departure, then choose “I'm on this one”.</p>
      <ul class="rows">
        {(near.data?.stations ?? []).map((st) => (
          <li key={st.place.id}>
            <a class="row" href={href("station", { id: st.place.id })}>
              <span class="row-icon">
                <ModeIcons modes={st.place.modes?.slice(0, 1)} size={22} />
              </span>
              <span class="row-text">
                <strong class="trunc">{st.place.name}</strong>
                <span>{metres(st.distM)}</span>
              </span>
              <Icon name="right" size={16} class="muted" />
            </a>
          </li>
        ))}
        <li>
          <a class="row" href={href("search", { f: "to" })}>
            <span class="row-icon">
              <Icon name="search" />
            </span>
            <span class="row-text">
              <strong>Search for a stop</strong>
              <span>Use the departures button next to a stop</span>
            </span>
          </a>
        </li>
      </ul>
      <p class="foot-note">Kante remembers your trip until you get off, so planning again keeps it.</p>
    </Sheet>
  );
}
