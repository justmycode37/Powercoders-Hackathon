// Guidance: one sentence per stage, a segmented progress bar with a puck, one
// card for the leg in hand. Closing the screen minimises it to a strip on the
// map; only "End" stops it.
import { useEffect, useMemo, useState } from "preact/hooks";
import type { Journey, RideLeg, WalkLeg } from "../api/types";
import { alongLine, bboxOf, dist, metres } from "../lib/geo";
import { liveArr, liveDep, samePoint, spare, walkFeatures } from "../lib/journey";
import { cap, lineLabel, lineTitle, lineVars, quayShort } from "../lib/lines";
import { readJSON, writeJSON } from "../lib/store";
import { clock, dur, durExact, hm, nowS, tick } from "../lib/time";
import { flyTo, mapLevel, scene } from "../map/scene";
import { findJourney, HERE, plan, queryParams, type PlanQuery } from "../plan";
import { back, go, href, route } from "../router";
import { guidance, settings, showToast, userPos, type Pos } from "../state";
import { Delay, Empty, LegChain, Notice, Platform, Skeleton } from "../ui/bits";
import { Icon, modeIcon, stepIcon } from "../ui/icons";
import { Sheet, SheetClose } from "../ui/sheet";
import { StandCard } from "../ui/stand";
import { focusWalkStep, StepRow } from "./journey";
import { placeName, usePlan } from "./results";

type Phase =
  | { kind: "walk"; leg: number; walk: WalkLeg; next: RideLeg | null; start: number; end: number }
  | { kind: "board"; leg: number; ride: RideLeg; start: number; end: number }
  | { kind: "ride"; leg: number; ride: RideLeg; start: number; end: number }
  | { kind: "arrived"; leg: number; start: number; end: number };

/** A journey as a sequence of single things to do. */
export function phases(j: Journey): Phase[] {
  const out: Phase[] = [];
  let t = j.dep;
  j.legs.forEach((leg, i) => {
    if (leg.type === "walk") {
      const next = j.legs[i + 1];
      if (!samePoint(leg) || leg.kind === "direct") out.push({ kind: "walk", leg: i, walk: leg, next: next?.type === "ride" ? next : null, start: leg.dep, end: leg.arr });
      t = leg.arr;
    } else {
      if (!leg.onboard && !leg.stayOnBoard) out.push({ kind: "board", leg: i, ride: leg, start: t, end: liveDep(leg.from) });
      out.push({ kind: "ride", leg: i, ride: leg, start: liveDep(leg.from), end: liveArr(leg.to) });
      t = liveArr(leg.to);
    }
  });
  out.push({ kind: "arrived", leg: j.legs.length - 1, start: j.arr, end: Infinity });
  return out;
}

const AT_STOP_M = 22;
/** Which phase applies now, by the clock and — for walks — by position. */
function current(list: Phase[], now: number, pos: Pos | null): number {
  for (let i = 0; i < list.length; i++) {
    const p = list[i]!;
    if (p.kind === "walk" && pos) {
      const there = dist(pos.lat, pos.lon, p.walk.to.lat, p.walk.to.lon) < AT_STOP_M;
      if (there && now > p.walk.dep - 600) continue;
      // a walk does not end by the clock while the traveller is still on the way: they may be slower
      if (!there && (!p.next || now < liveDep(p.next.from) + 120)) return i;
    }
    if (now < p.end) return i;
  }
  return list.length - 1;
}

export interface Stage {
  /** Changes when the traveller has to do something new. */
  key: string;
  head: string;
  sub: string;
  tone: "" | "warn" | "alarm" | "done";
  /** Worth waking the phone for. */
  notify: boolean;
  /** Something went wrong that only a new plan fixes. */
  replan?: boolean;
  count?: { label: string; secs: number };
}

function walkTargetOf(ph: Extract<Phase, { kind: "walk" }>): string {
  if (ph.next) return quayShort(ph.next.from.quay) || ph.next.from.quay.stationName;
  return ph.walk.to.name;
}
/** The step of a walk the traveller is on: by position along the path when known, else by the clock. */
function currentStep(w: WalkLeg, now: number, pos: Pos | null): number {
  const steps = w.steps ?? [];
  if (!steps.length) return -1;
  const frac = pos ? alongLine(pos, w.geometry).frac : Math.min(1, Math.max(0, (now - w.dep) / Math.max(1, w.durationS)));
  const vertex = frac * (w.geometry.length - 1);
  let cur = steps.findIndex((s) => vertex <= s.to && s.kind !== "arrive" && !(s.kind === "depart" && s.distM === 0));
  if (cur < 0) cur = steps.length - 1;
  return cur;
}

/** The one sentence for this moment. The same words go to the screen, the strip and the notification. */
export function stageOf(j: Journey, ph: Phase, now: number, pos: Pos | null): Stage {
  if (ph.kind === "walk") {
    const w = ph.walk;
    const target = walkTargetOf(ph);
    const transfer = w.kind === "transfer";
    const summary = `${dur(w.durationS)} walk to ${target}`;
    if (now < w.dep - 59) return { key: `wait${ph.leg}`, head: `Leave in ${dur(Math.floor((w.dep - now) / 60) * 60)}`, sub: cap(summary), tone: "", notify: false, count: { label: "Leave in", secs: w.dep - now } };
    const moved = pos ? alongLine(pos, w.geometry).frac > 0.04 : now > w.dep + 30;
    if (!moved && !transfer && now < w.dep + 90) return { key: `leave${ph.leg}`, head: "Leave now", sub: cap(summary), tone: "warn", notify: true };
    const step = w.steps?.[currentStep(w, now, pos)];
    const stepText = step && step.kind !== "arrive" ? step.text : cap(summary);
    if (ph.next) {
      const left = liveDep(ph.next.from) - now;
      const need = pos ? (1 - alongLine(pos, w.geometry).frac) * w.durationS : Math.max(0, w.arr - now);
      if (ph.next.cancelled) return { key: `cancel${ph.leg}`, head: `Cancelled — ${lineTitle(ph.next.line)}`, sub: "Find another journey from here", tone: "alarm", notify: true, replan: true };
      if (left < -30) return { key: `missed${ph.leg}`, head: `You've probably missed ${lineTitle(ph.next.line)}`, sub: `It left ${target} at ${hm(liveDep(ph.next.from))}`, tone: "alarm", notify: true, replan: true };
      if (left < need - 20) return { key: `hurry${ph.leg}`, head: `Hurry — ${lineTitle(ph.next.line)} leaves in ${durExact(Math.max(0, left))}`, sub: stepText, tone: "warn", notify: true, count: { label: "Leaves in", secs: left } };
      return { key: `walk${ph.leg}`, head: `${transfer ? "Change to" : "Walk to"} ${target}`, sub: stepText, tone: "", notify: transfer, count: { label: `${lineTitle(ph.next.line)} leaves in`, secs: left } };
    }
    return { key: `walk${ph.leg}`, head: `Walk to ${target}`, sub: stepText, tone: "", notify: false, count: { label: "Arrive in", secs: Math.max(0, w.arr - now) } };
  }
  if (ph.kind === "board") {
    const r = ph.ride;
    const q = r.from.quay;
    const left = liveDep(r.from) - now;
    if (r.cancelled) return { key: `cancel${ph.leg}`, head: `Cancelled — ${lineTitle(r.line)}`, sub: "Find another journey from here", tone: "alarm", notify: true, replan: true };
    const where = q.side ? cap(q.side.text) : q.stationName;
    const line = `${lineTitle(r.line)} to ${r.headsign}`;
    if (left <= 20) return { key: `board${ph.leg}`, head: `Board ${lineTitle(r.line)} now`, sub: `To ${r.headsign}`, tone: "warn", notify: true };
    return {
      key: `stand${ph.leg}`,
      head: q.label ? `Stand at ${quayShort(q)}` : `Wait at ${q.stationName}`,
      sub: q.label || q.side ? `${where} · ${line}` : line,
      tone: "",
      notify: false,
      count: { label: "Leaves in", secs: left },
    };
  }
  if (ph.kind === "ride") {
    const r = ph.ride;
    const calls = [...r.intermediate, r.to];
    const left = calls.filter((c) => liveArr(c) > now).length;
    const stop = r.to.quay.stationName;
    const secs = Math.max(0, liveArr(r.to) - now);
    if (r.cancelled) return { key: `cancel${ph.leg}`, head: `Cancelled — ${lineTitle(r.line)}`, sub: "Find another journey from here", tone: "alarm", notify: true, replan: true };
    if (left <= 1 && secs < 45) return { key: `now${ph.leg}`, head: "This is your stop", sub: stop, tone: "warn", notify: true };
    // on a long non-stop ride the next stop is yours from the start: say so calmly, and call it out when it is close
    if (left <= 1 && secs > 240) return { key: `ride${ph.leg}`, head: "Get off at the next stop", sub: stop, tone: "", notify: false, count: { label: "Arrive in", secs } };
    if (left <= 1) return { key: `next${ph.leg}`, head: "Your stop is next", sub: stop, tone: "warn", notify: true, count: { label: "Arrive in", secs } };
    return { key: `ride${ph.leg}`, head: `Get off in ${left} stops`, sub: `at ${stop}`, tone: "", notify: false, count: { label: "Arrive in", secs } };
  }
  const last = j.legs[j.legs.length - 1]!;
  return { key: "arrived", head: "You've arrived", sub: last.type === "walk" ? last.to.name : last.to.quay.stationName, tone: "done", notify: true };
}

// ---------------------------------------------------------------- notifications (only when action is needed)

const notifyOn = () => readJSON<boolean>("kante.notify") === true && typeof Notification !== "undefined" && Notification.permission === "granted";
function announce(st: Stage): void {
  try {
    navigator.vibrate?.(st.tone === "alarm" ? [300, 120, 300, 120, 300] : [200, 100, 200]);
  } catch {
    /* not allowed */
  }
  if (!notifyOn() || !document.hidden) return;
  const opts = { body: st.sub, tag: "kante-go", renotify: true, icon: "/icons/icon-192.png" } as NotificationOptions;
  const viaPage = () => {
    try {
      new Notification(st.head, opts);
    } catch {
      /* some browsers only allow notifications from a service worker */
    }
  };
  if (navigator.serviceWorker?.controller) navigator.serviceWorker.ready.then((reg) => reg.showNotification(st.head, opts), viaPage);
  else viaPage();
}

/** The live stage of the journey being followed; announces each new actionable stage once. */
function useGuidance(j: Journey | null, list: Phase[]): { idx: number; stage: Stage | null } {
  const now = tick.value;
  const pos = userPos.value;
  const idx = list.length ? current(list, now, pos) : 0;
  const ph = list[idx];
  const stage = j && ph ? stageOf(j, ph, now, pos) : null;
  useEffect(() => {
    if (!stage || !j) return;
    const seen = readJSON<{ id: string; key: string }>("kante.stage");
    if (seen?.id === j.id && seen.key === stage.key) return;
    writeJSON("kante.stage", { id: j.id, key: stage.key });
    // not on the very first look at a journey that is not under way yet
    if (stage.notify && (seen?.id === j.id || now >= j.dep - 90)) announce(stage);
  }, [j?.id, stage?.key]);
  return { idx, stage };
}

export function endGuidance(): void {
  guidance.value = null;
}

/** Floating strip on the map while a journey is being followed and its screen is closed. */
export function GuidanceStrip() {
  const g = guidance.value;
  const onGo = route.value.name === "go";
  const list = useMemo(() => (g ? phases(g.journey) : []), [g?.journey.id]);
  const { stage } = useGuidance(g?.journey ?? null, list);
  const now = tick.value;
  useEffect(() => {
    // a finished journey ends by itself
    if (g && now > g.journey.arr + 900) guidance.value = null;
  }, [g?.journey.id, Math.floor(now / 60)]);
  if (!g || !stage || onGo) return null;
  return (
    <a class={"gstrip " + stage.tone} href={g.url} aria-label={`Guidance: ${stage.head}, ${stage.sub}. Open`}>
      <span class="gstrip-text">
        <strong class="trunc">{stage.head}</strong>
        <span class="trunc">
          {stage.sub} · arrive {hm(g.journey.arr)}
        </span>
      </span>
      <ProgressBar j={g.journey} now={now} mini />
      <Icon name="up" size={18} />
    </a>
  );
}

/** One segment per leg in its colour, walks dotted, and a puck where the traveller is. */
function ProgressBar({ j, now, mini, onPick, picked }: { j: Journey; now: number; mini?: boolean; onPick?: (leg: number) => void; picked?: number | null }) {
  const total = Math.max(1, j.arr - j.dep);
  const frac = Math.min(1, Math.max(0, (now - j.dep) / total));
  const legs = j.legs.map((l, i) => ({ l, i })).filter(({ l }) => l.type === "ride" || !samePoint(l));
  return (
    <span class={"pbar" + (mini ? " mini" : "")} role="img" aria-label={`${Math.round(frac * 100)} % of the journey done`}>
      {legs.map(({ l, i }) => {
        const d = l.type === "ride" ? liveArr(l.to) - liveDep(l.from) : l.durationS;
        const start = l.type === "ride" ? liveDep(l.from) : l.dep;
        const done = Math.min(1, Math.max(0, (now - start) / Math.max(1, d)));
        const style = { flexGrow: Math.max(d / total, 0.06), ...(l.type === "ride" ? lineVars(l.line) : {}) };
        const cls = (l.type === "ride" ? "pbar-ride" : "pbar-walk") + (picked === i ? " picked" : "");
        const fill = <i style={{ width: `${done * 100}%` }} />;
        return onPick ? (
          <button key={i} class={cls} style={style} onClick={() => onPick(i)} aria-label={l.type === "ride" ? `Preview ${lineTitle(l.line)}` : "Preview this walk"}>
            {fill}
          </button>
        ) : (
          <span key={i} class={cls} style={style}>
            {fill}
          </span>
        );
      })}
      <b class="pbar-puck" style={{ left: `${frac * 100}%` }} />
    </span>
  );
}

function replanFrom(q: PlanQuery, pos: Pos | null, ph: Phase | undefined, j: Journey): void {
  let from: PlanQuery["from"] = HERE;
  if (!pos && ph) {
    const quay = ph.kind === "walk" ? (ph.next?.from.quay ?? null) : ph.kind === "arrived" ? null : ph.ride.from.quay;
    if (quay) from = { id: quay.stationId, kind: "station", name: quay.stationName, lat: quay.lat, lon: quay.lon };
  }
  const last = j.legs[j.legs.length - 1]!;
  const to = q.to ?? (last.type === "walk" ? { id: `coord:${last.to.lat.toFixed(5)},${last.to.lon.toFixed(5)}`, kind: "coord" as const, name: last.to.name, lat: last.to.lat, lon: last.to.lon } : null);
  endGuidance();
  go("plan", queryParams({ from, to, time: null, arriveBy: false, onboard: null }), { replace: true });
}

export function Go() {
  const q = usePlan(60);
  const params = route.value.params;
  const p = plan.value;
  const g = guidance.value;
  const j = findJourney(params.j) ?? (g && g.journey.id === params.j ? g.journey : null);
  const list = useMemo(() => (j ? phases(j) : []), [j?.id, j?.dep, j?.arr]);
  const [manual, setManual] = useState<number | null>(null);
  const [notify, setNotify] = useState(notifyOn());
  const realNow = tick.value;
  const pos = userPos.value;
  const live = useGuidance(null, list); // announcing is the strip's job; here only the index
  const auto = live.idx;
  const preview = manual !== null && manual !== auto;
  const idx = preview ? manual! : auto;
  const ph = list[idx];
  // a previewed stage is shown as it will look when it begins
  const now = preview && ph ? Math.max(realNow, Math.min(ph.start + (ph.kind === "walk" ? 61 : 1), ph.end - 1)) : realNow;
  const stage = j && ph ? stageOf(j, ph, now, preview ? null : pos) : null;
  const toName = placeName(q.to) || (j ? (() => { const l = j.legs[j.legs.length - 1]!; return l.type === "walk" ? l.to.name : l.to.quay.stationName; })() : "");

  // following this journey: keep it across screens and reloads, with fresh live times
  useEffect(() => {
    if (!j) return;
    guidance.value = { url: location.pathname + location.search, journey: j, to: toName, startedAt: g?.journey.id === j.id ? g.startedAt : nowS() };
  }, [j?.id, j?.dep, j?.arr]);
  useEffect(() => {
    if (!j || !ph) return;
    scene.value = { journey: j, activeLeg: ph.kind === "arrived" ? null : ph.leg };
    const lv = ph.kind === "board" ? ph.ride.from.quay.level : undefined;
    mapLevel.value = lv !== undefined && lv !== 0 ? Math.round(lv) : null;
    if (ph.kind === "board") flyTo({ kind: "point", lat: ph.ride.from.quay.lat, lon: ph.ride.from.quay.lon, zoom: 18 });
    else {
      const leg = j.legs[ph.leg]!;
      const b = bboxOf(pos && ph.kind === "walk" && !preview ? [...leg.geometry, [pos.lon, pos.lat]] : leg.geometry);
      if (b) flyTo({ kind: "bounds", bbox: b, maxZoom: 18 });
    }
  }, [j?.id, idx]);
  // keep the screen on while guiding
  useEffect(() => {
    let lock: { release: () => Promise<void> } | null = null;
    const wl = (navigator as Navigator & { wakeLock?: { request: (t: "screen") => Promise<{ release: () => Promise<void> }> } }).wakeLock;
    wl?.request("screen").then((l) => (lock = l), () => undefined);
    return () => {
      void lock?.release().catch(() => undefined);
    };
  }, []);

  const minimise = () => back(href("journey", params));
  if (!j || !ph || !stage) {
    return (
      <Sheet label="Guidance" initial="mid" header={<div class="sheet-title"><h1>Guidance</h1><span class="sheet-actions"><SheetClose onClick={minimise} /></span></div>}>
        {!p || p.status === "loading" ? (
          <Skeleton rows={3} kind="block" label="Loading journey" />
        ) : (
          <Empty icon="clock" title="This journey is no longer available" action={<a class="pill-btn primary" href={href("plan", queryParams(q))} data-replace>Show current journeys</a>} />
        )}
      </Sheet>
    );
  }
  const end = () => {
    endGuidance();
    showToast("Guidance ended");
    back(href("journey", params));
  };
  const toggleNotify = async () => {
    if (notify) {
      writeJSON("kante.notify", false);
      setNotify(false);
      return;
    }
    if (typeof Notification === "undefined") return showToast("This browser can't show notifications");
    const perm = Notification.permission === "default" ? await Notification.requestPermission() : Notification.permission;
    if (perm !== "granted") return showToast("Notifications are blocked for this site");
    writeJSON("kante.notify", true);
    setNotify(true);
    showToast("Kante will notify you only when you need to act");
  };
  const offRoute = !preview && ph.kind === "walk" && pos && ph.walk.geometry.length > 1 && alongLine(pos, ph.walk.geometry).distM > 70 && realNow > ph.walk.dep;
  // live data says a later change no longer works
  const broken = j.alerts?.find((a) => a.kind === "missed-connection" || a.kind === "cancelled");
  const cur = j.legs[ph.leg]!;
  return (
    <Sheet
      label="Guidance"
      initial="mid"
      mid={0.58}
      class="go"
      header={
        <div class={"go-head " + stage.tone} style={cur.type === "ride" ? lineVars(cur.line) : undefined}>
          <div class="go-top">
            <span class="go-arrive">
              Arrive <b>{hm(j.arr)}</b>
              {preview && <em>Preview</em>}
            </span>
            <span class="sheet-actions">
              <button class={"round-btn" + (notify ? " on" : "")} onClick={toggleNotify} aria-pressed={notify} aria-label={notify ? "Notifications are on. Turn off" : "Notify me when I need to act"}>
                <Icon name="bell" size={18} />
              </button>
              <SheetClose onClick={minimise} label="Minimise guidance" />
            </span>
          </div>
          <div class="go-say" role="status" aria-live="polite">
            <h1>{stage.head}</h1>
            <p>{stage.sub}</p>
          </div>
          {stage.count && stage.count.secs > 0 && (
            <div class="go-count">
              {stage.count.label} <b>{clock(stage.count.secs)}</b>
            </div>
          )}
          <ProgressBar j={j} now={now} onPick={(leg) => { const i = list.findIndex((x) => x.leg === leg && x.kind !== "arrived"); if (i >= 0) setManual(i === auto ? null : i); }} picked={preview ? ph.leg : null} />
        </div>
      }
      footer={
        <div class="actionbar">
          {preview ? (
            <button class="pill-btn start" onClick={() => setManual(null)}>
              Back to now
            </button>
          ) : stage.tone === "done" ? (
            <button class="pill-btn start" onClick={() => { endGuidance(); go("home", {}, { replace: true }); }}>
              Done
            </button>
          ) : (
            <button class="pill-btn danger" onClick={end}>
              <Icon name="stop" size={16} /> End
            </button>
          )}
          <button class="round-btn big" onClick={() => setManual(Math.max(0, idx - 1))} disabled={idx === 0} aria-label="Preview the previous stage">
            <Icon name="back" size={18} />
          </button>
          <button class="round-btn big" onClick={() => setManual(Math.min(list.length - 1, idx + 1))} disabled={idx === list.length - 1} aria-label="Preview the next stage">
            <Icon name="go" size={18} />
          </button>
          <span class="actionbar-sum stack">
            <small>
              Stage {idx + 1} of {list.length}
            </small>
            {!preview && <b>{dur(Math.max(0, j.arr - Math.max(now, j.dep)))} left</b>}
          </span>
        </div>
      }
    >
      {stage.replan && (
        <Notice kind="severe" action={<button class="pill-btn primary" onClick={() => replanFrom(q, pos, ph, j)} data-testid="replan">Find next journey</button>}>
          Kante won't switch you to another journey on its own.
        </Notice>
      )}
      {!stage.replan && broken && (
        <Notice kind={broken.severity} action={<button class="pill-btn primary" onClick={() => replanFrom(q, pos, ph, j)}>Find next journey</button>}>
          {broken.text}
        </Notice>
      )}
      {offRoute && (
        <Notice kind="warning" action={<button class="pill-btn" onClick={() => replanFrom(q, pos, ph, j)}>Plan from here</button>}>
          You're off the planned route
        </Notice>
      )}
      <LegCard ph={ph} j={j} now={now} pos={preview ? null : pos} />
      <ThenRow list={list} idx={idx} onPick={(i) => setManual(i === auto ? null : i)} />
    </Sheet>
  );
}

/** What follows the leg in hand, one line each. */
function ThenRow({ list, idx, onPick }: { list: Phase[]; idx: number; onPick: (i: number) => void }) {
  const rest = list.slice(idx + 1);
  if (!rest.length) return null;
  return (
    <ol class="then-list" aria-label="Coming up">
      {rest.map((n, i) => (
        <li key={i}>
          <button class="then" onClick={() => onPick(idx + 1 + i)}>
            <span class="then-icon" style={n.kind === "board" || n.kind === "ride" ? lineVars(n.ride.line) : undefined}>
              <Icon name={n.kind === "walk" ? "walk" : n.kind === "arrived" ? "flag" : modeIcon(n.ride.line.mode)} size={16} />
            </span>
            <span class="trunc">
              {n.kind === "walk"
                ? `${dur(n.walk.durationS)} walk to ${walkTargetOf(n)}`
                : n.kind === "board"
                  ? `${n.ride.from.quay.label ? "Stand at " + quayShort(n.ride.from.quay) : "Wait at " + n.ride.from.quay.stationName} for ${lineTitle(n.ride.line)}`
                  : n.kind === "ride"
                    ? `Ride ${n.ride.intermediate.length + 1} ${n.ride.intermediate.length ? "stops" : "stop"} to ${n.ride.to.quay.stationName}`
                    : "Arrive"}
            </span>
            <small>{hm(n.kind === "ride" ? n.end : n.start)}</small>
          </button>
        </li>
      ))}
    </ol>
  );
}

function LegCard({ ph, j, now, pos }: { ph: Phase; j: Journey; now: number; pos: Pos | null }) {
  const margin = settings.value.marginS;
  const [open, setOpen] = useState(false);
  if (ph.kind === "walk") {
    const w = ph.walk;
    const steps = w.steps ?? [];
    const cur = currentStep(w, now, pos);
    const sp = spare(w, margin);
    const feats = walkFeatures(w);
    return (
      <>
        <div class="go-card walk">
          <div class="go-card-head">
            <Icon name="walk" size={22} />
            <span>
              <b>{dur(w.durationS)}</b> · {metres(w.distanceM)}
              {feats.length > 0 && " · " + feats.join(", ")}
            </span>
            {sp && sp.level !== "missed" && <span class={"tag " + (sp.level === "ok" ? "ok" : "warn")}>{durExact(sp.s)} to spare</span>}
          </div>
          {steps.length > 0 && (
            <ol class="steps">
              {steps.map((s, i) => (s.kind === "depart" && s.distM === 0 && steps.length > 2 ? null : <StepRow key={i} s={s} active={i === cur} onClick={() => focusWalkStep(j, ph.leg, i)} />))}
            </ol>
          )}
        </div>
        {ph.next && <StandCard quay={ph.next.from.quay} towards={ph.next.towards} bearing={ph.next.bearing} planned={ph.next.from.plannedLabel} kicker="You're walking to" showStation />}
      </>
    );
  }
  if (ph.kind === "arrived") {
    return (
      <div class="arrived">
        <Icon name="flag" size={36} />
        <p>
          {now >= j.arr ? "Arrived" : "Arrive"} at {hm(j.arr)} · {dur(j.durationS)} door to door
        </p>
      </div>
    );
  }
  const r = ph.ride;
  const calls = [...r.intermediate, r.to];
  const ahead = calls.filter((c) => liveArr(c) > now);
  const nextCall = ahead[0] ?? r.to;
  const between = ahead.slice(1, -1);
  const label = lineLabel(r.line);
  return (
    <>
      {ph.kind === "board" && (
        <StandCard quay={r.from.quay} towards={r.towards} bearing={r.bearing} planned={r.from.plannedLabel} onShow={() => flyTo({ kind: "point", lat: r.from.quay.lat, lon: r.from.quay.lon, zoom: 18.5 })} />
      )}
      <div class="go-card ride" style={lineVars(r.line)}>
        <div class="go-card-head">
          <Icon name={modeIcon(r.line.mode)} size={22} />
          <b class="go-line">{label || lineTitle(r.line)}</b>
          <span class="trunc">to {r.headsign}</span>
        </div>
        <ol class="go-stops">
          {ph.kind === "board" ? (
            <li class="first">
              <span>
                <small>Leaves</small>
                <b>{r.from.quay.stationName}</b>
              </span>
              <span class="go-time">
                {hm(r.from.dep ?? liveDep(r.from))} <Delay s={r.from.depDelayS} short />
              </span>
            </li>
          ) : (
            nextCall !== r.to && (
              <li class="first">
                <span>
                  <small>Next stop</small>
                  <b>{nextCall.quay.stationName}</b>
                </span>
                <span class="go-time">{hm(liveArr(nextCall))}</span>
              </li>
            )
          )}
          {(ph.kind === "board" ? r.intermediate.length : between.length) > 0 && (
            <li class="more">
              <button onClick={() => setOpen(!open)} aria-expanded={open}>
                <Icon name={open ? "up" : "down"} size={14} />
                {ph.kind === "board" ? r.intermediate.length : between.length} more {(ph.kind === "board" ? r.intermediate.length : between.length) === 1 ? "stop" : "stops"}
              </button>
              {open && (
                <ul>
                  {(ph.kind === "board" ? r.intermediate : between).map((c) => (
                    <li key={c.seq}>
                      <span class="trunc">{c.quay.stationName}</span>
                      <span>{hm(liveArr(c))}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )}
          <li class="last">
            <span>
              <small>Get off</small>
              <b>{r.to.quay.stationName}</b>
            </span>
            <span class="go-time">
              {hm(r.to.arr ?? liveArr(r.to))} <Delay s={r.to.arrDelayS} short />
              <Platform quay={r.to.quay} planned={r.to.plannedLabel} />
            </span>
          </li>
        </ol>
      </div>
      {(() => {
        const after = j.legs[ph.leg + 1];
        const step = after?.type === "walk" ? after.steps.find((s) => s.kind !== "depart") : null;
        return step && ph.kind === "ride" ? (
          <div class="quiet-line">
            <Icon name={stepIcon(step.kind)} size={14} /> Next: {step.text}
          </div>
        ) : null;
      })()}
    </>
  );
}
