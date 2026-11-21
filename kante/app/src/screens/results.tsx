import { useEffect, useState } from "preact/hooks";
import type { Journey, RideLeg, WalkLeg } from "../api/types";
import { metres } from "../lib/geo";
import { changesOf, changesText, firstAction, journeyBounds, journeyLabel, walkFeatures, worstAlert } from "../lib/journey";
import { lineTitle } from "../lib/lines";
import { dayLabel, dur, hm, nowS, tick10 } from "../lib/time";
import { flyTo, scene } from "../map/scene";
import { adoptSharedOptions, ensurePlan, isHere, loadMore, parseQuery, plan, queryParams, type PlaceSel, type PlanQuery } from "../plan";
import { go, href, openOverlay, route } from "../router";
import { accessLabel, DEFAULT_SETTINGS, geoStatus, online, settings, startGeo, tripView, userPos } from "../state";
import { Delay, Empty, LegChain, Notice, Platform, Skeleton, TimeBar } from "../ui/bits";
import { Icon } from "../ui/icons";
import { detent, isWide, Sheet, SheetClose } from "../ui/sheet";
import { useMeta } from "./sheets";

export const placeName = (p: PlaceSel | null, fallback = ""): string => (p ? (isHere(p) ? "Current location" : p.name) : fallback);
const kmh = (v: number) => v.toFixed(1).replace(".0", "");

/** Journey query in the URL → plan store, re-planned whenever options or location change. */
export function usePlan(maxAgeS?: number): PlanQuery {
  const params = route.value.params;
  adoptSharedOptions(params);
  const q = parseQuery(params);
  const s = settings.value;
  const pos = userPos.value;
  const t = tick10.value;
  useEffect(() => {
    ensurePlan(q, { maxAgeS });
  }, [JSON.stringify(queryParams(q)), JSON.stringify(s), pos?.lat, pos?.lon, maxAgeS === undefined ? 0 : Math.floor(t / 30)]);
  return q;
}

/** The from/to card floating over the map. Tapping a row edits that end. */
export function OdCard({ q, onboardText }: { q: PlanQuery; onboardText?: string }) {
  const params = route.value.params;
  const swap = () => go("plan", queryParams({ ...q, from: q.to, to: q.from }), { replace: true });
  return (
    <div class="topcard od" role="group" aria-label="Start and destination">
      <span class="od-marks" aria-hidden="true">
        <i class="od-ring" />
        <i class="od-dots" />
        <i class="od-pin" />
      </span>
      <div class="od-rows">
        {q.onboard ? (
          <a class="od-row" href={href("onboard")} aria-label={`From on board ${onboardText ?? ""}. Change`}>
            <Icon name="onboard" size={16} />
            <span class="trunc">{onboardText || "On board"}</span>
          </a>
        ) : (
          <a class="od-row" href={href("search", { ...params, j: undefined, f: "from" })} aria-label={`From ${placeName(q.from, "not chosen")}. Change start`}>
            <span class={"trunc" + (q.from ? "" : " placeholder")}>{placeName(q.from, "Choose start")}</span>
          </a>
        )}
        <a class="od-row" href={href("search", { ...params, j: undefined, f: "to" })} aria-label={`To ${placeName(q.to, "not chosen")}. Change destination`}>
          <span class={"trunc" + (q.to ? "" : " placeholder")}>{placeName(q.to, "Choose destination")}</span>
        </a>
      </div>
      <div class="od-side">
        <button class="round-btn plain" onClick={() => openOverlay("settings")} aria-label="Options">
          <Icon name="sliders" size={20} />
        </button>
        {!q.onboard && (
          <button class="round-btn plain" onClick={swap} aria-label="Swap start and destination">
            <Icon name="swap" size={20} />
          </button>
        )}
      </div>
    </div>
  );
}

/** "Leave now", "Leave at 08:30", "Leave tomorrow at 08:30", "Arrive by Mon 23 Nov, 08:30". */
export function timeLabel(q: PlanQuery, time = q.time, arriveBy = q.arriveBy, withToday = false): string {
  if (time === null) return "Leave now";
  const day = dayLabel(time);
  const relative = day === "Today" || day === "Tomorrow" || day === "Yesterday";
  if (arriveBy) return `Arrive by ${day === "Today" && !withToday ? "" : relative ? day.toLowerCase() + ", " : day + ", "}${hm(time)}`;
  if (day === "Today" && !withToday) return `Leave at ${hm(time)}`;
  return relative ? `Leave ${day.toLowerCase()} at ${hm(time)}` : `Leave ${day}, ${hm(time)}`;
}

export function Results() {
  const q = usePlan(90);
  const p = plan.value;
  const params = route.value.params;
  const s = settings.value;
  const meta = useMeta();
  const [tab, setTab] = useState<"pt" | "walk">("pt");
  const walkOnly = p?.res?.walkOnly ?? null;
  const showWalk = tab === "walk" && !!walkOnly;
  const first = showWalk ? walkOnly : (p?.journeys[0] ?? walkOnly ?? null);
  useEffect(() => {
    scene.value = first ? { journey: first } : {};
    if (first) {
      const b = journeyBounds(first);
      if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 16.5 });
    }
  }, [first?.id]);
  useEffect(() => {
    if (!walkOnly && tab === "walk") setTab("pt");
  }, [walkOnly]);

  const now = tick10.value;
  const acc = accessLabel(s);
  const obLeg = q.onboard && p?.journeys[0]?.legs[0]?.type === "ride" ? (p.journeys[0].legs[0] as RideLeg) : null;
  const open = (j: Journey) => go("journey", { ...params, j: j.id });
  const loading = (!p || p.status === "loading") && !p?.journeys.length;
  const fastest = p?.journeys.length ? Math.min(...p.journeys.map((j) => j.durationS)) : null;
  const stepFree = s.wheelchair || s.stairs === "never";
  const view = tripView.value;
  let lastDay = dayLabel(now, now);
  return (
    <>
      <OdCard q={q} onboardText={obLeg ? `${lineTitle(obLeg.line)} to ${obLeg.headsign}` : q.onboard ? "On board" : undefined} />
      <Sheet
        label="Journeys"
        initial={view === "list" ? "full" : "mid"}
        onDetent={(d) => (tripView.value = d === "full" ? "list" : "map")}
        header={
          <>
            <div class="sheet-title">
              {walkOnly ? (
                <div class="tabs" role="tablist" aria-label="How to travel">
                  <button role="tab" aria-selected={!showWalk} class={showWalk ? "" : "on"} onClick={() => setTab("pt")}>
                    <Icon name="rail" size={20} />
                    {fastest !== null ? dur(fastest) : "Public transport"}
                  </button>
                  <button role="tab" aria-selected={showWalk} class={showWalk ? "on" : ""} onClick={() => setTab("walk")}>
                    <Icon name="walk" size={20} />
                    {dur(walkOnly.durationS)}
                  </button>
                </div>
              ) : (
                <h1>Journeys</h1>
              )}
              <span class="sheet-actions">
                {!isWide.value && (
                  <button
                    class="round-btn"
                    aria-label={view === "list" ? "Show the map" : "Show the list"}
                    onClick={() => {
                      const next = detent.peek() === "full" ? "mid" : "full";
                      detent.value = next;
                      tripView.value = next === "full" ? "list" : "map";
                    }}
                  >
                    <Icon name={view === "list" ? "map" : "list"} size={18} />
                  </button>
                )}
                <SheetClose onClick={() => go("home")} label="Close journeys" />
              </span>
            </div>
            <div class="chips" role="toolbar" aria-label="Journey options">
              <button class={"chip" + (q.time !== null ? " on" : "")} onClick={() => openOverlay("time")}>
                <Icon name="clock" size={16} />
                {timeLabel(q)}
                <Icon name="down" size={14} />
              </button>
              <button class={"chip" + (s.walkKmh !== DEFAULT_SETTINGS.walkKmh ? " on" : "")} onClick={() => openOverlay("speed")} aria-label={`Walking speed ${kmh(s.walkKmh)} km/h. Change`}>
                <Icon name="walk" size={16} />
                {kmh(s.walkKmh)} km/h
                <Icon name="down" size={14} />
              </button>
              {acc && (
                <button class="chip on" onClick={() => openOverlay("settings")} aria-label={`Options: ${acc}`}>
                  <Icon name="wheelchair" size={16} />
                  {acc}
                </button>
              )}
              {s.modes && (
                <button class="chip on" onClick={() => openOverlay("settings")}>
                  Some transport types off
                </button>
              )}
            </div>
          </>
        }
      >
        {loading && <Skeleton rows={4} kind="card" label="Loading journeys" />}
        {p?.status === "need-origin" && <NeedOrigin q={q} />}
        {p?.status === "error" && (
          <Notice kind="severe" icon={online.value ? undefined : "offline"} action={<button class="pill-btn" onClick={() => { plan.value = null; ensurePlan(q); }}>Try again</button>}>
            {p.error ?? "Couldn't plan this journey"}
          </Notice>
        )}
        {p && p.status !== "need-origin" && p.status !== "error" && (p.journeys.length > 0 || p.res) && (
          <div class={"results" + (p.status === "loading" ? " refreshing" : "")} aria-busy={p.status === "loading"}>
            {p.stale &&
              (p.error ? (
                <Notice kind="warning" icon="offline">
                  {p.error} — showing saved journeys from {hm(p.at)}
                </Notice>
              ) : (
                <div class="status-line" role="status">
                  Updating journeys…
                </div>
              ))}
            {showWalk ? (
              <WalkSummary j={walkOnly!} onOpen={() => open(walkOnly!)} />
            ) : (
              <>
                {p.earlier && p.journeys.length > 0 && (
                  <button class="more" onClick={() => loadMore("earlier")} disabled={p.more === "earlier"}>
                    <Icon name="up" size={16} /> {p.more === "earlier" ? "Loading earlier journeys…" : "Earlier"}
                  </button>
                )}
                <ol class="journeys">
                  {p.journeys.map((j) => {
                    const day = dayLabel(j.dep, now);
                    const sep = day !== lastDay;
                    lastDay = day;
                    return (
                      <li key={j.id}>
                        {sep && <div class="day-sep">{day}</div>}
                        <JourneyRow j={j} now={now} onOpen={() => open(j)} />
                      </li>
                    );
                  })}
                </ol>
                {p.status === "ready" && p.journeys.length === 0 && (
                  <Empty
                    icon="search"
                    title={s.wheelchair ? "No wheelchair-accessible journeys found" : stepFree ? "No step-free journeys found" : "No journeys found"}
                    action={
                      <button class="pill-btn" onClick={() => openOverlay("settings")}>
                        Open options
                      </button>
                    }
                  >
                    {stepFree
                      ? "Try another time, increase the maximum walk, or allow stairs and escalators in Options."
                      : s.modes
                        ? "Try another time, a longer maximum walk, or more transport types in Options."
                        : "Try another time or a longer maximum walk in Options."}
                    {walkOnly ? " Or walk the whole way — see the walking tab." : ""}
                  </Empty>
                )}
                {p.later && p.journeys.length > 0 && (
                  <button class="more" onClick={() => loadMore("later")} disabled={p.more === "later"}>
                    <Icon name="down" size={16} /> {p.more === "later" ? "Loading later journeys…" : "Later"}
                  </button>
                )}
              </>
            )}
            {p.res && <p class="foot-note">{p.res.realtime && meta?.realtime.enabled !== false ? "Live delays included where operators report them" : "Timetable only — no live updates"}</p>}
          </div>
        )}
      </Sheet>
    </>
  );
}

function NeedOrigin({ q }: { q: PlanQuery }) {
  const st = geoStatus.value;
  return (
    <Empty
      icon="locate"
      title={st === "denied" ? "Location access is blocked" : st === "asking" ? "Finding your location…" : st === "unavailable" ? "Couldn't find your location" : "Where are you starting from?"}
      action={
        <div class="empty-actions">
          {st !== "denied" && st !== "asking" && (
            <button class="pill-btn primary" onClick={startGeo}>
              Use my location
            </button>
          )}
          <a class="pill-btn" href={href("search", { ...queryParams({ ...q, from: null }), f: "from" })}>
            Choose start
          </a>
        </div>
      }
    >
      {st === "denied"
        ? "Allow location in your browser settings, choose a start, or long-press the map (right-click on desktop) and choose “I'm here”."
        : st === "asking"
          ? "Wait a moment, or choose a start yourself."
          : st === "unavailable"
            ? "Check your device's location settings, or choose a start yourself."
            : "Kante needs your location to plan from where you are — or choose a start yourself."}
    </Empty>
  );
}

/** Walking the whole way, as its own tab. */
function WalkSummary({ j, onOpen }: { j: Journey; onOpen: () => void }) {
  const leg = j.legs[0] as WalkLeg | undefined;
  const feats = leg ? walkFeatures(leg) : [];
  return (
    <button class="walkcard" onClick={onOpen}>
      <span class="walkcard-big">
        <b>{dur(j.durationS)}</b>
        <span>
          {metres(j.walkM)} at {kmh(settings.value.walkKmh)} km/h
        </span>
      </span>
      <span class="walkcard-sub">
        {hm(j.dep)} – {hm(j.arr)}
        {feats.length > 0 && " · " + feats.join(", ")}
        {leg?.approximate && " · estimated, no mapped footpath"}
      </span>
      <span class="walkcard-cta">
        Walking directions <Icon name="right" size={16} />
      </span>
    </button>
  );
}

/**
 * One journey as a three-line row on a fixed grid: every vehicle's badge and the
 * duration; the two clock times with the proportional bar between them; and
 * under it the first boarding point, the countdown and the time to change.
 */
function JourneyRow({ j, now, onOpen }: { j: Journey; now: number; onOpen: () => void }) {
  const act = firstAction(j, now);
  const changes = changesOf(j, settings.value.marginS);
  const worst = worstAlert(j);
  const cancelled = j.legs.some((l) => l.type === "ride" && l.cancelled);
  const tight = changes.some((c) => c.level !== "ok");
  return (
    <button class={"jrow" + (act.gone ? " gone" : "") + (cancelled ? " cancelled" : "")} onClick={onOpen} aria-label={journeyLabel(j, now)}>
      <span class="jrow-l1">
        <LegChain legs={j.legs} />
        <b class="jrow-dur">{dur(j.durationS)}</b>
      </span>
      <span class="jrow-l2">
        <b class="jrow-time">{hm(j.dep)}</b>
        <TimeBar j={j} />
        <b class="jrow-time end">{hm(j.arr)}</b>
      </span>
      <span class="jrow-l3">
        <span class="jrow-plat">{act.quay && <Platform quay={act.quay} planned={act.planned} />}</span>
        <span class="jrow-mid">
          {act.text && (
            <span class={"jrow-act " + (act.gone ? "gone" : act.state)}>
              {act.text}
              {!act.onboard && <Delay s={act.delayS} short />}
            </span>
          )}
          <span class={"jrow-chg" + (tight ? " tight" : "")}>
            {changesText(changes).split(" · ")[0]}
            {changes.length > 0 && <span class="jrow-chg-min"> · {changesText(changes).split(" · ")[1]}</span>}
          </span>
        </span>
        <span class="jrow-flag">{worst && <Icon name="alert" size={18} class={worst.severity} />}</span>
      </span>
      {worst && (
        <span class={"jrow-alert " + worst.severity}>
          <span class="trunc2">{cancelled && !/cancel/i.test(worst.text) ? "Cancelled — " : ""}{worst.text}</span>
        </span>
      )}
    </button>
  );
}
