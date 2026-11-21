import { useEffect, useState } from "preact/hooks";
import { api, useQuery } from "../api/client";
import type { Departure, Quay, TripResponse } from "../api/types";
import { bboxOf, metres, dist } from "../lib/geo";
import { liveArr, liveDep } from "../lib/journey";
import { cap, lineLabel, lineTitle, lineVars, quayNoun, quayShort, sideShort } from "../lib/lines";
import { countdown, dayLabel, delayMins, dur, hm, nowS, tick10 } from "../lib/time";
import { flyTo, handlers, scene } from "../map/scene";
import { boardTrip, openStation, planTo } from "../nav";
import { back, go, href, route } from "../router";
import { online, userPos } from "../state";
import { Delay, Empty, LineBadge, LiveTag, ModeIcons, Notice, Platform, Skeleton } from "../ui/bits";
import { Icon } from "../ui/icons";
import { setDetent, Sheet, SheetClose } from "../ui/sheet";
import { StandCard } from "../ui/stand";
import { CallTime } from "./journey";

const natural = new Intl.Collator("de", { numeric: true });
const chipLabel = (q: Quay) => q.label || sideShort(q);

export function Station() {
  const { id = "", quay, by } = route.value.params;
  const main = useQuery(`dep:${id}`, (s) => api.departures({ station: id, limit: 60 }, s), { refreshS: 30, keep: false });
  const byQuay = useQuery(quay ? `depq:${quay}` : null, (s) => api.departures({ quay, limit: 30 }, s), { refreshS: 30, keep: false });
  const [more, setMore] = useState<{ key: string; list: Departure[]; loading: boolean; done: boolean }>({ key: "", list: [], loading: false, done: false });
  const data = main.data;
  const now = tick10.value;
  const quays = data ? [...data.quays].sort((a, b) => natural.compare(a.label || "~", b.label || "~")) : [];
  const selected = quays.find((q) => q.id === quay) ?? null;
  const used = new Set(data?.departures.map((d) => d.quayId));
  const viewKey = `${id}|${quay ?? ""}`;
  const base = (quay ? (byQuay.data?.departures ?? data?.departures.filter((d) => d.quayId === quay)) : data?.departures) ?? [];
  const extra = more.key === viewKey ? more.list : [];
  const deps = [...base, ...extra.filter((d) => !base.some((b) => b.tripId === d.tripId && b.seq === d.seq && b.serviceDate === d.serviceDate))];
  const grouped = by === "bay" && !quay;
  const select = (qid: string | null) => go("station", { id, quay: qid ?? undefined, by: by || undefined }, { replace: true });
  const quayOf = (qid: string) => data?.quays.find((q) => q.id === qid);

  useEffect(() => {
    if (!data) return;
    scene.value = { station: { quays: data.quays, selected: quay ?? null }, hero: selected };
  }, [data, quay]);
  useEffect(() => {
    if (!data) return;
    if (selected) flyTo({ kind: "point", lat: selected.lat, lon: selected.lon, minZoom: 17.5 });
    else {
      const b = bboxOf([[data.station.lon, data.station.lat], ...data.quays.map((q): [number, number] => [q.lon, q.lat])]);
      if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 17.5 });
    }
  }, [data?.station.id, quay]);
  useEffect(() => {
    handlers.quayTap = (q) => {
      if (q.stationId === id) select(q.id === quay ? null : q.id);
      else openStation(q.stationId, q.id, { replace: true });
    };
    return () => {
      handlers.quayTap = null;
    };
  }, [id, quay, by]);

  const loadLater = () => {
    const last = deps[deps.length - 1];
    if (!last || more.loading) return;
    setMore({ key: viewKey, list: extra, loading: true, done: false });
    api.departures({ ...(quay ? { quay } : { station: id }), time: last.dep + 1, limit: 40 }).then(
      (r) => setMore({ key: viewKey, list: [...extra, ...r.departures], loading: false, done: r.departures.length === 0 }),
      () => setMore({ key: viewKey, list: extra, loading: false, done: false }),
    );
  };

  const pos = userPos.value;
  const st = data?.station;
  const refreshError = main.error ?? byQuay.error;
  const labelled = quays.filter((q) => chipLabel(q) && (q.label || used.has(q.id)));
  const nounPlural = quays.some((q) => q.noun === "track") ? (quays.some((q) => q.noun === "bay") ? "Platforms and bays" : "Platforms") : "Bays";
  let lastDay = dayLabel(now, now);
  return (
    <Sheet
      label="Departures"
      initial="mid"
      header={
        <>
          <div class="sheet-title">
            <div class="title-stack">
              <h1 class="trunc">{st?.name ?? "Departures"}</h1>
              <span class="title-sub">
                <ModeIcons modes={st?.modes} size={14} /> Departures
                {st && pos ? ` · ${metres(dist(pos.lat, pos.lon, st.lat, st.lon))} away` : ""}
              </span>
            </div>
            <span class="sheet-actions">
              {st && (
                <button class="round-btn" aria-label={`Directions to ${st.name}`} onClick={() => planTo(st)}>
                  <Icon name="nav" size={18} />
                </button>
              )}
              <SheetClose onClick={() => back("/")} />
            </span>
          </div>
          {labelled.length > 0 && (
            <div class="chips" role="toolbar" aria-label={nounPlural}>
              <button class={"chip" + (!quay && !grouped ? " on" : "")} onClick={() => go("station", { id }, { replace: true })} aria-pressed={!quay && !grouped}>
                By time
              </button>
              <button class={"chip" + (grouped ? " on" : "")} onClick={() => go("station", { id, by: "bay" }, { replace: true })} aria-pressed={grouped}>
                By {quays.some((q) => q.noun === "track") ? "platform" : "bay"}
              </button>
              <i class="chips-sep" aria-hidden="true" />
              {labelled.map((q) => (
                <button
                  key={q.id}
                  class={"chip bay-chip" + (q.id === quay ? " on" : "") + (used.has(q.id) ? "" : " idle")}
                  onClick={() => select(q.id === quay ? null : q.id)}
                  aria-pressed={q.id === quay}
                  aria-label={q.label ? quayShort(q) : `Stop, ${sideShort(q).toLowerCase()}`}
                >
                  {cap(chipLabel(q))}
                </button>
              ))}
            </div>
          )}
        </>
      }
    >
      {refreshError && data && (
        <div class="status-line" role="status">
          <Icon name="offline" size={14} />
          {online.value ? "Couldn't refresh" : "Offline"} — showing times from {hm(Math.floor((main.at || Date.now()) / 1000))}
        </div>
      )}
      {!data && main.loading && <Skeleton rows={7} label="Loading departures" />}
      {!data && main.error && <Notice kind="severe" icon={online.value ? undefined : "offline"} action={<button class="pill-btn" onClick={main.reload}>Try again</button>}>{main.error}</Notice>}
      {data && !data.realtime && <div class="status-line">Timetable only — no live updates</div>}
      {selected && (
        <StandCard
          quay={selected}
          kicker={`Selected ${quayNoun(selected).toLowerCase()}`}
          showStation
          onShow={() => {
            flyTo({ kind: "point", lat: selected.lat, lon: selected.lon, zoom: 18.5 });
            setDetent("low");
          }}
        />
      )}
      {quay && byQuay.loading && !byQuay.data && (
        <div class="status-line" role="status" aria-live="polite">
          Loading departures…
        </div>
      )}
      {data && deps.length === 0 && !(quay && byQuay.loading) && (
        <Empty icon="clock" title={selected ? `No departures from this ${quayNoun(selected).toLowerCase()} in the next few hours` : "No upcoming departures"} />
      )}
      {grouped ? (
        <ByBay deps={deps} quays={quays} now={now} onQuay={select} />
      ) : (
        <ul class="deps">
          {deps.map((d) => {
            const day = dayLabel(d.dep, now);
            const sep = day !== lastDay;
            lastDay = day;
            return (
              <li key={d.tripId + d.serviceDate + d.seq}>
                {sep && <div class="day-sep">{day}</div>}
                <DepRow d={d} quay={quayOf(d.quayId)} now={now} />
              </li>
            );
          })}
        </ul>
      )}
      {data && deps.length > 0 && !grouped && !(more.key === viewKey && more.done) && (
        <button class="more" onClick={loadLater} disabled={more.loading}>
          <Icon name="down" size={16} /> {more.loading ? "Loading later departures…" : "Later departures"}
        </button>
      )}
      {data && data.realtime && <p class="foot-note">Live times where the operator reports them</p>}
    </Sheet>
  );
}

/** One departure on the journey grid: time, line, direction, minutes to go, and the platform or bay in its slot. */
function DepRow({ d, quay, now }: { d: Departure; quay: Quay | undefined; now: number }) {
  const live = d.dep + (d.delayS ?? 0);
  const soon = live - now < 3600;
  const cd = countdown(live, now);
  return (
    <a class={"dep" + (d.cancelled ? " cancelled" : "")} href={href("trip", { id: d.tripId, date: d.serviceDate, seq: d.seq })}>
      <span class="dep-time">
        <b>{hm(d.dep)}</b>
        {d.cancelled ? <small class="late">Cancelled</small> : <Delay s={d.delayS} />}
      </span>
      <LineBadge line={d.line} size="lg" />
      <span class="dep-main">
        <span class="dep-head trunc2">{d.headsign}</span>
        {d.towards && d.towards !== d.headsign && <small class="trunc">Next stop: {d.towards}</small>}
      </span>
      <span class="dep-count">{!d.cancelled && soon && (cd === "now" || cd === "left" ? <b>{cd}</b> : <><b>{cd.replace(" min", "")}</b><small>min</small></>)}</span>
      <span class="dep-plat">{quay && <Platform quay={quay} planned={d.plannedLabel} />}</span>
    </a>
  );
}

/** Departures grouped by platform or bay, then by line and direction with its next times. */
function ByBay({ deps, quays, now, onQuay }: { deps: Departure[]; quays: Quay[]; now: number; onQuay: (id: string) => void }) {
  const groups = quays
    .map((q) => ({ q, list: deps.filter((d) => d.quayId === q.id && !d.cancelled) }))
    .filter((g) => g.list.length > 0);
  return (
    <div class="bays">
      {groups.map(({ q, list }) => {
        const lines = new Map<string, Departure[]>();
        for (const d of list) {
          const k = d.line.name + "|" + d.line.category + "|" + d.headsign;
          lines.set(k, [...(lines.get(k) ?? []), d]);
        }
        return (
          <section key={q.id} class="bay">
            <button class="bay-head" onClick={() => onQuay(q.id)} aria-label={`${quayShort(q) || "Stop"}${q.side ? ", " + q.side.text : ""}. Show only this one`}>
              <span class="bay-name">
                {q.label ? (
                  <>
                    {quayNoun(q)} <b>{q.label}</b>
                  </>
                ) : (
                  <b>Stop</b>
                )}
              </span>
              {q.side && <span class="bay-side trunc">{cap(q.side.text)}</span>}
              <Icon name="right" size={16} class="muted" />
            </button>
            <ul>
              {[...lines.values()].slice(0, 6).map((ds) => {
                const d = ds[0]!;
                return (
                  <li key={d.tripId + d.seq}>
                    <a class="bay-row" href={href("trip", { id: d.tripId, date: d.serviceDate, seq: d.seq })}>
                      <LineBadge line={d.line} size="lg" />
                      <span class="dep-head trunc2">{d.headsign}</span>
                      <span class="bay-times">
                        {ds.slice(0, 3).map((x, i) => {
                          const t = x.dep + (x.delayS ?? 0);
                          const cd = t - now < 3600 ? countdown(t, now) : hm(t);
                          return i === 0 ? <b key={i}>{cd}</b> : <span key={i}>{cd.replace(" min", "")}</span>;
                        })}
                      </span>
                    </a>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------- trip

/** Where the vehicle should be now, judged from its (live) stop times. */
export function tripProgress(t: TripResponse, now: number): { state: "before" | "running" | "done"; next: number; atStop: boolean; text: string } {
  const calls = t.calls;
  const n = calls.length;
  if (n < 2) return { state: "done", next: 0, atStop: false, text: "" };
  if (now < liveDep(calls[0]!)) return { state: "before", next: 1, atStop: true, text: `Leaves ${calls[0]!.quay.stationName} at ${hm(liveDep(calls[0]!))}` };
  if (now >= liveArr(calls[n - 1]!)) return { state: "done", next: n - 1, atStop: false, text: "This trip has ended" };
  for (let i = 1; i < n; i++) {
    if (now < liveArr(calls[i]!)) return { state: "running", next: i, atStop: false, text: `Between ${calls[i - 1]!.quay.stationName} and ${calls[i]!.quay.stationName}` };
    if (i < n - 1 && now < liveDep(calls[i]!)) return { state: "running", next: i + 1, atStop: true, text: `At ${calls[i]!.quay.stationName}` };
  }
  return { state: "done", next: n - 1, atStop: false, text: "This trip has ended" };
}

export function Trip() {
  const { id = "", date = "", seq } = route.value.params;
  const q = useQuery(`trip:${id}:${date}`, (s) => api.trip(id, date, s), { refreshS: 30, keep: false });
  const t = q.data;
  const now = tick10.value;
  const at = seq !== undefined ? Number(seq) : null;
  const call = t && at !== null ? (t.calls.find((c) => c.seq === at) ?? null) : null;
  useEffect(() => {
    if (!t) return;
    scene.value = { trip: t, hero: call?.quay ?? null };
    if (call) flyTo({ kind: "point", lat: call.quay.lat, lon: call.quay.lon, minZoom: 16 });
    else {
      const b = bboxOf(t.geometry);
      if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 15.5 });
    }
  }, [t?.tripId, t?.serviceDate, at]);

  const prog = t ? tripProgress(t, now) : null;
  const delay = t ? (t.calls[Math.min(prog!.next, t.calls.length - 1)]?.arrDelayS ?? t.calls[0]?.depDelayS) : undefined;
  const board = () => {
    if (!t || !prog) return;
    boardTrip({ tripId: t.tripId, serviceDate: t.serviceDate, nextSeq: t.calls[prog.next]?.seq, line: t.line, headsign: t.headsign, until: liveArr(t.calls[t.calls.length - 1]!) + 600 });
  };
  const callIdx = call && t ? t.calls.indexOf(call) : -1;
  const next = callIdx >= 0 && t ? t.calls[callIdx + 1] : undefined;
  const leaves = call ? liveDep(call) : 0;
  const label = t ? lineLabel(t.line) : "";
  return (
    <Sheet
      label="Trip"
      initial="mid"
      header={
        <>
          <div class="sheet-title">
            {t ? (
              <>
                <LineBadge line={t.line} size="xl" icon={!label || label.length < 3} />
                <div class="title-stack">
                  <h1 class="trunc">{t.headsign}</h1>
                  <span class="title-sub trunc">
                    {lineTitle(t.line)}
                    {t.number && t.number !== t.line.name ? ` · no. ${t.number}` : ""} · {t.line.operator}
                  </span>
                </div>
              </>
            ) : (
              <h1>Trip</h1>
            )}
            <span class="sheet-actions">
              <SheetClose onClick={() => back("/")} />
            </span>
          </div>
          {t && prog && (
            <div class="trip-status">
              <LiveTag live={t.live} />
              {t.cancelled ? <b class="late">Cancelled</b> : delayMins(delay) > 0 ? <Delay s={delay} /> : t.live !== "timetable" && prog.state !== "done" ? <b class="ontime">On time</b> : null}
              {!t.cancelled && <span class="trip-where trunc">{prog.text}</span>}
            </div>
          )}
        </>
      }
      footer={
        t && prog && prog.state !== "done" && !t.cancelled ? (
          <div class="actionbar">
            <button class="pill-btn start" onClick={board} data-testid="im-on-this">
              <Icon name="onboard" size={18} />
              I'm on this one
            </button>
            {call && leaves > now && (
              <span class="actionbar-sum">
                <small>Leaves {call.quay.stationName.length < 18 ? call.quay.stationName : "here"}</small>
                <b>{countdown(leaves, now) === "now" ? "now" : "in " + countdown(leaves, now)}</b>
              </span>
            )}
          </div>
        ) : undefined
      }
    >
      {!t && q.loading && <Skeleton rows={8} label="Loading trip" />}
      {!t && q.error && <Notice kind="severe" icon={online.value ? undefined : "offline"} action={<button class="pill-btn" onClick={q.reload}>Try again</button>}>{q.error}</Notice>}
      {t && q.error && (
        <div class="status-line" role="status">
          <Icon name="offline" size={14} />
          {online.value ? "Couldn't refresh" : "Offline"} — showing times from {hm(Math.floor(q.at / 1000))}
        </div>
      )}
      {t && call && prog?.state !== "done" && leaves > now - 60 && !t.cancelled && (
        <StandCard quay={call.quay} towards={next?.quay.stationName} planned={call.plannedLabel} kicker={`Where to stand at ${call.quay.stationName}`} onShow={() => { flyTo({ kind: "point", lat: call.quay.lat, lon: call.quay.lon, zoom: 18.5 }); setDetent("mid"); }} />
      )}
      {t && prog && prog.state === "running" && !t.cancelled && (
        <p class="status-line">
          <Icon name="info" size={14} /> Vehicle position is estimated from {t.live === "timetable" ? "the timetable" : "live stop times"}, not GPS
        </p>
      )}
      {t && prog && (
        <ol class={"tl calls" + (t.cancelled ? " cancelled" : "")} style={lineVars(t.line)}>
          {t.calls.map((c, i) => {
            const past = prog.state === "done" || (prog.state === "running" && i < prog.next - (prog.atStop ? 1 : 0));
            const here = prog.state === "running" && !t.cancelled && i === prog.next - (prog.atStop ? 1 : 0);
            const lastCall = i === t.calls.length - 1;
            return (
              <li key={c.seq} class={"tl-ride" + (past ? " past" : "") + (c.seq === at ? " at" : "") + (c.skipped ? " skipped" : "")}>
                <a class="tl-row call" href={href("station", { id: c.quay.stationId, quay: c.quay.label ? c.quay.id : undefined })}>
                  <CallTime call={c} which={lastCall ? "arr" : "dep"} strong={c.seq === at} />
                  <span class={"tl-rail ride" + (i === 0 ? " first" : lastCall ? " last" : "")}>
                    {i === 0 || lastCall ? <i class="tl-enddot" /> : <i class="tl-stopdot" />}
                    {here && <i class={"tl-veh" + (prog.atStop ? " stopped" : "")} role="img" aria-label="Estimated vehicle position" />}
                  </span>
                  <span class="tl-name">
                    {c.seq === at ? <strong>{c.quay.stationName}</strong> : c.quay.stationName}
                    {c.onRequest && <small> · on request</small>}
                    {c.skipped && <small> · not served</small>}
                  </span>
                  <Platform quay={c.quay} planned={c.plannedLabel} />
                </a>
              </li>
            );
          })}
        </ol>
      )}
      {t && (
        <p class="foot-note">
          {prog?.state === "done" ? `Trip ended at ${hm(liveArr(t.calls[t.calls.length - 1]!))}` : nowS() < liveDep(t.calls[0]!) ? `Starts in ${dur(liveDep(t.calls[0]!) - nowS())}` : `Timetable for ${dayLabel(liveDep(t.calls[0]!))}`}
          {t.headwayS !== undefined ? ` · runs about every ${dur(t.headwayS)}; times are approximate` : ""}
        </p>
      )}
    </Sheet>
  );
}
