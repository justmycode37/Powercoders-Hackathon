import { useEffect, useState } from "preact/hooks";
import type { Journey, Quay, RideLeg, StopCall, WalkLeg, WalkStep } from "../api/types";
import { bboxOf, metres } from "../lib/geo";
import { firstAction, isWalkOnly, journeyBounds, liveArr, liveDep, samePoint, spare, walkFeatures, walkTarget } from "../lib/journey";
import { cap, levelShort, levelSpoken, lineTitle, lineVars, quayNoun } from "../lib/lines";
import { delayMins, dur, durExact, hm, nowS, tick10 } from "../lib/time";
import { flyTo, handlers, mapLevel, scene } from "../map/scene";
import { openStation } from "../nav";
import { findJourney, plan, queryParams, rememberTrip } from "../plan";
import { go, href, route } from "../router";
import { settings, showToast, tripView } from "../state";
import { Delay, Empty, LegChain, LineBadge, LiveTag, Notice, Platform, Skeleton } from "../ui/bits";
import { Icon, modeIcon, stepIcon } from "../ui/icons";
import { detent, isWide, setDetent, Sheet, SheetClose } from "../ui/sheet";
import { StandCard } from "../ui/stand";
import { placeName, usePlan } from "./results";
import { useMeta } from "./sheets";

/** Show a boarding point close up, with its level selected. */
export function showQuay(q: Quay): void {
  scene.value = { ...scene.peek(), hero: q, slice: null };
  mapLevel.value = q.level !== undefined && q.level !== 0 ? Math.round(q.level) : null;
  flyTo({ kind: "point", lat: q.lat, lon: q.lon, zoom: 18.5 });
  if (detent.peek() === "full") setDetent("mid");
}

export async function shareLink(title: string, url: string): Promise<void> {
  const full = location.origin + url;
  try {
    if (navigator.share) await navigator.share({ title, url: full });
    else {
      await navigator.clipboard.writeText(full);
      showToast("Link copied");
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") showToast("Couldn't share the link");
  }
}

/** The level a walking step is on (or leads to), for the level switcher to follow. */
export function stepLevel(leg: WalkLeg, s: WalkStep): number | null {
  const lv = (s.toLevel !== undefined && s.toLevel !== s.level ? s.toLevel : s.level) ?? leg.levels[s.to] ?? leg.levels[s.from] ?? null;
  return lv === null ? null : Math.round(lv);
}
const multiLevel = (leg: WalkLeg) => leg.levels.some((x) => x !== null && Math.round(x) !== 0);

/** Zoom the map to one walking step and switch to its level. */
export function focusWalkStep(j: Journey, legIdx: number, stepIdx: number): void {
  const l = j.legs[legIdx];
  if (!l || l.type !== "walk") return;
  const s = l.steps[stepIdx];
  if (!s) return;
  scene.value = { journey: j, activeLeg: legIdx, slice: { leg: legIdx, from: s.from, to: s.to } };
  mapLevel.value = multiLevel(l) ? (stepLevel(l, s) ?? 0) : null;
  const part = l.geometry.slice(s.from, s.to + 1);
  const b = bboxOf(part);
  if (b && part.length > 1 && s.distM > 30) flyTo({ kind: "bounds", bbox: b, maxZoom: 18.5 });
  else if (part.length) {
    const mid = part[Math.floor((part.length - 1) / 2)]!;
    const end = part[part.length - 1]!;
    flyTo({ kind: "point", lat: (mid[1] + end[1]) / 2, lon: (mid[0] + end[0]) / 2, zoom: 18.5 });
  }
}

export function JourneyScreen() {
  const q = usePlan();
  const params = route.value.params;
  const p = plan.value;
  const j = findJourney(params.j);
  const [focus, setFocus] = useState<{ leg: number; step?: number } | null>(null);
  const now = tick10.value;
  const toName = placeName(q.to);
  const fromName = q.onboard ? "On board" : placeName(q.from);

  useEffect(() => {
    if (!j) return;
    rememberTrip({ url: location.pathname + location.search, title: `${fromName} to ${toName}`, dep: j.dep, arr: j.arr, at: nowS() });
    scene.value = { journey: j };
    mapLevel.value = null;
    const b = journeyBounds(j);
    if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 16.5 });
    setFocus(null);
  }, [j?.id]);
  useEffect(() => {
    handlers.quayTap = (quay) => {
      const mine = j?.legs.some((l) => l.type === "ride" && l.from.quay.id === quay.id);
      if (mine) {
        setFocus(null);
        showQuay(quay);
      } else openStation(quay.stationId, quay.id);
    };
    return () => {
      handlers.quayTap = null;
      mapLevel.value = null;
    };
  }, [j?.id]);

  const closeUrl = href("plan", queryParams(q));
  const close = () => go("plan", queryParams(q), { replace: true });
  if (!j) {
    const loading = !p || p.status === "loading";
    return (
      <Sheet label="Journey" initial="mid" header={<div class="sheet-title"><h1>Journey</h1><span class="sheet-actions"><SheetClose onClick={close} /></span></div>}>
        {loading ? (
          <Skeleton rows={5} kind="block" label="Loading journey" />
        ) : (
          <Empty icon="clock" title="This journey is no longer available" action={<a class="pill-btn primary" href={closeUrl} data-replace>Show current journeys</a>} />
        )}
      </Sheet>
    );
  }

  const focusStep = (leg: number, step: number) => {
    setFocus({ leg, step });
    focusWalkStep(j, leg, step);
    if (detent.peek() === "full") setDetent("mid");
  };
  const focusLeg = (leg: number) => {
    const l = j.legs[leg];
    if (!l) return;
    setFocus({ leg });
    scene.value = { journey: j, activeLeg: leg };
    mapLevel.value = null;
    const b = bboxOf(l.geometry);
    if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 18 });
    if (detent.peek() === "full") setDetent("mid");
  };
  const overview = () => {
    setFocus(null);
    scene.value = { journey: j };
    mapLevel.value = null;
    const b = journeyBounds(j);
    if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 16.5 });
  };

  const act = firstAction(j, now);
  const fl = focus && focus.step !== undefined ? j.legs[focus.leg] : null;
  const stepping = fl?.type === "walk" ? fl : null;
  const first = j.legs[0]!;
  const last = j.legs[j.legs.length - 1]!;
  const walkOnly = isWalkOnly(j);
  const view = tripView.value;
  const ended = now > j.arr + 120;
  return (
    <Sheet
      label="Journey details"
      initial={view === "list" ? "full" : "mid"}
      onDetent={(d) => (tripView.value = d === "full" ? "list" : "map")}
      header={
        stepping ? (
          <div class="stepnav">
            <button class="round-btn" onClick={() => focusStep(focus!.leg, focus!.step! - 1)} disabled={focus!.step === 0} aria-label="Previous direction">
              <Icon name="back" size={18} />
            </button>
            <div class="stepnav-text" aria-live="polite">
              <small>
                {focus!.step! + 1} of {stepping.steps.length}
                {multiLevel(stepping) && stepLevel(stepping, stepping.steps[focus!.step!]!) !== null && ` · ${cap(levelSpokenShort(stepLevel(stepping, stepping.steps[focus!.step!]!)!))}`}
              </small>
              <strong class="trunc2">{stepping.steps[focus!.step!]!.text}</strong>
            </div>
            <button class="round-btn" onClick={() => focusStep(focus!.leg, focus!.step! + 1)} disabled={focus!.step === stepping.steps.length - 1} aria-label="Next direction">
              <Icon name="go" size={18} />
            </button>
            <SheetClose onClick={overview} label="Back to the whole journey" />
          </div>
        ) : (
          <div class="jhead">
            <div class="sheet-title">
              <LegChain legs={j.legs} max={7} />
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
                <SheetClose onClick={close} label="Close journey" />
              </span>
            </div>
            <div class="jhead-times">
              <b>
                {hm(j.dep)} – {hm(j.arr)}
              </b>
              <span>
                {walkOnly ? `${metres(j.walkM)} on foot` : j.transfers === 0 ? "Direct" : `${j.transfers} ${j.transfers === 1 ? "change" : "changes"}`}
              </span>
            </div>
            {(act.text || act.quay) && !ended && (
              <div class="jhead-act">
                {act.text && (
                  <span class={"jrow-act " + (act.gone ? "gone" : act.state)}>
                    {act.text}
                    {!act.onboard && <Delay s={act.delayS} />}
                  </span>
                )}
                {act.quay && <Platform quay={act.quay} planned={act.planned} long />}
              </div>
            )}
            {ended && <div class="jhead-act"><span class="jrow-act gone">This journey has ended</span></div>}
          </div>
        )
      }
      footer={
        <div class="actionbar">
          <a class="pill-btn start" href={href("go", params)} data-testid="start">
            <Icon name="nav" size={18} />
            Start
          </a>
          <button class="round-btn" aria-label="Share journey" onClick={() => shareLink(`${fromName} to ${toName}`, href("plan", queryParams(q, true)))}>
            <Icon name="share" size={18} />
          </button>
          <span class="actionbar-sum stack">
            <small>Arrive {hm(j.arr)}</small>
            <b>{dur(j.durationS)}</b>
          </span>
        </div>
      }
    >
      {focus && (
        <button class="pill-btn tonal overview-btn" onClick={overview}>
          <Icon name="map" size={16} /> Show full journey
        </button>
      )}
      {j.alerts?.map((a, i) => (
        <Notice key={i} kind={a.severity}>
          {a.text}
        </Notice>
      ))}
      <ol class="tl">
        {first.type === "walk" && <PlaceRow time={first.dep} name={first.from.name} kind="from" />}
        {j.legs.map((leg, i) =>
          leg.type === "walk" ? (
            <WalkBlock key={i} leg={leg} idx={i} j={j} focus={focus} onLeg={() => focusLeg(i)} onStep={(s) => focusStep(i, s)} />
          ) : (
            <RideBlock key={i} leg={leg} now={now} onQuay={(quay) => { setFocus(null); showQuay(quay); }} />
          ),
        )}
        {last.type === "walk" && <PlaceRow time={last.arr} name={last.to.name} kind="to" />}
      </ol>
      <p class="foot-note">
        {j.walkS > 0 ? `${dur(j.walkS)} on foot (${metres(j.walkM)}) at ${settings.value.walkKmh.toFixed(1).replace(".0", "")} km/h` : "No walking on this journey"}
        {settings.value.marginS > 0 && j.transfers > 0 ? ` · ${Math.round(settings.value.marginS / 60)} min extra change time` : ""}
      </p>
    </Sheet>
  );
}

const levelSpokenShort = (l: number): string => (l === 0 ? "ground level" : `level ${levelShort(l)}`);

function PlaceRow({ time, name, kind }: { time: number; name: string; kind: "from" | "to" }) {
  return (
    <li class={"tl-row tl-place " + kind}>
      <span class="tl-time">
        <b>{hm(time)}</b>
      </span>
      <span class="tl-rail">
        <i class={kind === "from" ? "od-ring" : "od-pin"} />
      </span>
      <span class="tl-name">
        <strong>{name}</strong>
        <small>{kind === "from" ? "Start" : "Destination"}</small>
      </span>
    </li>
  );
}

function WalkBlock(props: { leg: WalkLeg; idx: number; j: Journey; focus: { leg: number; step?: number } | null; onLeg: () => void; onStep: (i: number) => void }) {
  const { leg, idx, j, focus } = props;
  const s = settings.value;
  const meta = useMeta();
  const transfer = leg.kind === "transfer";
  // written directions are open at every change; other walks open on request
  const [open, setOpen] = useState<boolean | null>(null);
  const margin = s.marginS;
  const sp = spare(leg, margin);
  const same = samePoint(leg);
  const next = j.legs[idx + 1];
  const target = walkTarget(j, idx);
  const feats = walkFeatures(leg);
  const vertical = leg.stairsUp + leg.stairsDown + leg.escalators + leg.lifts > 0;
  const active = focus?.leg === idx;
  const steps = (leg.steps ?? []).filter((x) => !(x.kind === "depart" && x.distM === 0 && !/level/i.test(x.text)));
  const offset = (leg.steps ?? []).length - steps.length;
  const expanded = open ?? (transfer || (active && focus?.step !== undefined));
  const short = transfer && leg.officialMinS !== undefined && leg.durationS + (sp?.s ?? 0) < leg.officialMinS;
  const stepFree = s.wheelchair || s.stairs === "never";
  const box = meta?.walkBbox;
  const outside = !!box && (leg.from.lon < box[0] || leg.from.lon > box[2] || leg.from.lat < box[1] || leg.from.lat > box[3]);
  if (same)
    return (
      <li class="tl-row tl-walk same">
        <span class="tl-time" />
        <span class="tl-rail walk" />
        <div class="tl-main">
          <strong>Change at the same {next?.type === "ride" ? quayNoun(next.from.quay).toLowerCase() : "place"}</strong>
          {sp && <SpareLine sp={sp} leg={leg} margin={margin} />}
        </div>
      </li>
    );
  return (
    <li class={"tl-row tl-walk" + (active ? " active" : "")}>
      <span class="tl-time">
        <small>{dur(leg.durationS)}</small>
      </span>
      <span class="tl-rail walk">
        <Icon name="walk" size={18} />
      </span>
      <div class="tl-main">
        <button class="walk-sum" onClick={props.onLeg} aria-label={`${transfer ? "Change to" : "Walk to"} ${target}, ${dur(leg.durationS)}, ${metres(leg.distanceM)}. Show on map`}>
          <strong>{transfer ? `Change to ${target}` : `Walk to ${target}`}</strong>
          <span class="walk-meta">
            {dur(leg.durationS)} walk · {metres(leg.distanceM)}
            {feats.length > 0 && " · " + feats.join(", ")}
            {leg.stepFree && (vertical || stepFree) && <span class="tag ok">Step-free</span>}
            {leg.approximate && <span class="tag">Estimated</span>}
          </span>
        </button>
        {sp && <SpareLine sp={sp} leg={leg} margin={margin} />}
        {leg.kind === "access" && next?.type === "ride" && (
          <div class="quiet-line">
            Leave by <b>{hm(leg.dep)}</b>
            {leg.slackS !== undefined && leg.slackS + margin >= 60 ? ` to be there ${dur(Math.floor((leg.slackS + margin) / 60) * 60)} early` : ""}
          </div>
        )}
        {leg.officialMinS !== undefined && (
          <div class={"quiet-line" + (short ? " warn" : "")}>
            {short ? `Shorter than the official ${dur(leg.officialMinS)} change time here` : `Official change time here: ${dur(leg.officialMinS)}`}
          </div>
        )}
        {leg.approximate && stepFree && (
          <div class="quiet-line warn">
            <Icon name="alert" size={14} /> Footpath not mapped — step-free access couldn't be verified here
          </div>
        )}
        {leg.approximate && !stepFree && outside && <div class="quiet-line">Detailed indoor and walking map isn't available here — walking time is estimated.</div>}
        {steps.length > 1 && (
          <>
            <button class="expander" onClick={() => setOpen(!expanded)} aria-expanded={expanded}>
              <Icon name={expanded ? "up" : "down"} size={16} />
              {expanded ? "Hide directions" : `Walking directions (${steps.length})`}
            </button>
            {expanded && (
              <ol class="steps">
                {steps.map((st, i) => (
                  <StepRow key={i} s={st} active={active && focus?.step === i + offset} onClick={() => props.onStep(i + offset)} />
                ))}
              </ol>
            )}
          </>
        )}
      </div>
    </li>
  );
}

function SpareLine({ sp, leg, margin }: { sp: { s: number; level: "ok" | "tight" | "missed" }; leg: WalkLeg; margin: number }) {
  return (
    <div class={"spare " + sp.level}>
      <Icon name={sp.level === "ok" ? "check" : "alert"} size={15} />
      {sp.level === "missed" ? (
        <span>
          <b>Missed change — {durExact(-sp.s)} too late</b>
        </span>
      ) : (
        <span>
          <b>{durExact(sp.s)} to spare</b>
          {(leg.slackS ?? 0) < 0 && margin > 0 && <small> — less than your {Math.round(margin / 60)} min extra change time</small>}
        </span>
      )}
    </div>
  );
}

export function StepRow({ s, active, onClick }: { s: WalkStep; active?: boolean; onClick?: () => void }) {
  const change = s.level !== undefined && s.toLevel !== undefined && s.toLevel !== s.level;
  return (
    <li>
      <button class={"step" + (active ? " active" : "") + " k-" + s.kind} onClick={onClick} aria-current={active ? "step" : undefined}>
        <span class="step-icon">
          <Icon name={stepIcon(s.kind)} size={18} />
        </span>
        <span class="step-text">{s.text}</span>
        {change && (
          <span class="tag lvl" aria-label={`From ${levelSpoken(s.level!)} to ${levelSpoken(s.toLevel!)}`}>
            {levelShort(s.level!)} <Icon name="go" size={11} /> {levelShort(s.toLevel!)}
          </span>
        )}
      </button>
    </li>
  );
}

/** Scheduled time; a delay follows as "+4 min" in the alarm colour, never as a strikethrough. */
export function CallTime({ call, which, strong }: { call: StopCall; which: "dep" | "arr"; strong?: boolean }) {
  const t = which === "dep" ? (call.dep ?? call.arr) : (call.arr ?? call.dep);
  const d = which === "dep" ? (call.depDelayS ?? call.arrDelayS) : (call.arrDelayS ?? call.depDelayS);
  if (t === undefined) return <span class="tl-time" />;
  return (
    <span class="tl-time">
      {strong ? <b>{hm(t)}</b> : <span>{hm(t)}</span>}
      {delayMins(d) !== 0 && <Delay s={d} />}
    </span>
  );
}

function RideBlock({ leg, now, onQuay }: { leg: RideLeg; now: number; onQuay: (q: Quay) => void }) {
  const [open, setOpen] = useState(false);
  const stops = leg.intermediate.length;
  const rideS = liveArr(leg.to) - liveDep(leg.from);
  const remaining = leg.onboard ? [...leg.intermediate, leg.to].filter((cl) => liveArr(cl) > now).length : 0;
  return (
    <li class={"tl-ride" + (leg.cancelled ? " cancelled" : "")} style={lineVars(leg.line)}>
      {leg.onboard ? (
        <div class="tl-row board">
          <span class="tl-time">
            <small>Now</small>
          </span>
          <span class="tl-rail ride first">
            <i class="tl-node">
              <Icon name={modeIcon(leg.line.mode)} size={15} />
            </i>
          </span>
          <span class="tl-name">
            <strong>You're on {lineTitle(leg.line)}</strong>
          </span>
        </div>
      ) : (
        <div class="tl-row board">
          <CallTime call={leg.from} which="dep" strong />
          <span class="tl-rail ride first">
            <i class="tl-node">
              <Icon name={modeIcon(leg.line.mode)} size={15} />
            </i>
          </span>
          <span class="tl-name">
            <strong>{leg.from.quay.stationName}</strong>
          </span>
          <Platform quay={leg.from.quay} planned={leg.from.plannedLabel} />
        </div>
      )}
      <div class="tl-row">
        <span class="tl-time" />
        <span class="tl-rail ride" />
        <div class="tl-main">
          {!leg.onboard && <StandCard quay={leg.from.quay} towards={leg.towards} bearing={leg.bearing} planned={leg.from.plannedLabel} onShow={() => onQuay(leg.from.quay)} />}
          <div class="ride-line">
            <LineBadge line={leg.line} size="lg" />
            <Icon name="go" size={14} />
            <span class="ride-head">{leg.headsign}</span>
          </div>
          {leg.onboard && (
            <div class="quiet-line">
              Next stop {leg.from.quay.stationName}
              {leg.from.arr !== undefined ? ` at ${hm(liveArr(leg.from))}` : ""}
            </div>
          )}
          {leg.cancelled && (
            <div class="spare missed">
              <Icon name="alert" size={15} />
              <b>Cancelled</b>
            </div>
          )}
          {leg.stayOnBoard && <div class="quiet-line">Stay on board — the vehicle continues as {lineTitle(leg.line)}</div>}
          {leg.headwayS !== undefined && <div class="quiet-line">Runs about every {dur(leg.headwayS)}; times are approximate</div>}
          <div class="ride-sum">
            {leg.onboard ? (
              <span class="quiet-line">
                {remaining || stops + 1} {(remaining || stops + 1) === 1 ? "stop" : "stops"} to go · arrive in {dur(Math.max(60, liveArr(leg.to) - now))}
              </span>
            ) : stops > 0 ? (
              <button class="expander" onClick={() => setOpen(!open)} aria-expanded={open}>
                <Icon name={open ? "up" : "down"} size={16} />
                Ride {stops + 1} stops · {dur(rideS)}
              </button>
            ) : (
              <span class="quiet-line">Non-stop · {dur(rideS)}</span>
            )}
            <LiveTag live={leg.live} />
          </div>
        </div>
      </div>
      {open &&
        leg.intermediate.map((cl) => (
          <div key={cl.seq} class={"tl-row mid" + (cl.skipped ? " skipped" : "")}>
            <span class="tl-time">
              <span>{hm(liveArr(cl))}</span>
            </span>
            <span class="tl-rail ride">
              <i class="tl-stopdot" />
            </span>
            <span class="tl-name">
              {cl.quay.stationName}
              {cl.onRequest && <small> · on request</small>}
            </span>
          </div>
        ))}
      <div class="tl-row alight">
        <CallTime call={leg.to} which="arr" />
        <span class="tl-rail ride last">
          <i class="tl-enddot" />
        </span>
        <span class="tl-name">{leg.to.quay.stationName}</span>
        <Platform quay={leg.to.quay} planned={leg.to.plannedLabel} />
      </div>
    </li>
  );
}
