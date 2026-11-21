// What the screens say about a journey, in one place so the list, the detail
// and the guidance agree.
import type { Journey, JourneyAlert, Leg, Quay, RideLeg, StopCall, WalkLeg } from "../api/types";
import { bboxOf, type BBox, type LngLat } from "./geo";
import { lineTitle, quayShort } from "./lines";
import { dayLabel, delayMins, dur, hm } from "./time";

export const liveDep = (c: StopCall): number => (c.dep ?? c.arr ?? 0) + (c.depDelayS ?? c.arrDelayS ?? 0);
export const liveArr = (c: StopCall): number => (c.arr ?? c.dep ?? 0) + (c.arrDelayS ?? c.depDelayS ?? 0);
export const ridesOf = (j: Journey): RideLeg[] => j.legs.filter((l): l is RideLeg => l.type === "ride");
/** A change at the same boarding point: nothing to walk. */
export const samePoint = (l: WalkLeg): boolean => l.durationS === 0 && l.distanceM === 0;
export const isWalkOnly = (j: Journey): boolean => j.legs.every((l) => l.type === "walk");

export function journeyBounds(j: Journey): BBox | null {
  const pts: LngLat[] = [];
  for (const l of j.legs) for (const c of l.geometry) pts.push(c);
  return bboxOf(pts);
}

/** "Bay L", "Platform 7" or the stop's name: where a walk ends. */
export function walkTarget(j: Journey, idx: number): string {
  const leg = j.legs[idx] as WalkLeg;
  const next = j.legs[idx + 1];
  if (next?.type === "ride") {
    const q = next.from.quay;
    return quayShort(q) || q.stationName;
  }
  return leg.to.name;
}

export interface FirstAction {
  /** "Leave in 4 min", "Leaves in 4 min", "Leave now", "Left 3 min ago"; "" when it is too far ahead to count down. */
  text: string;
  when: number;
  gone: boolean;
  /** live-late / live-on-time / timetable, for the colour and the word next to it */
  state: "ok" | "late" | "plain";
  onboard?: boolean;
  /** First boarding point of the journey. */
  quay?: Quay;
  planned?: string;
  delayS?: number;
}

/** What to do first, and when. The verb is the traveller's when the journey starts on foot. */
export function firstAction(j: Journey, now: number): FirstAction {
  const first = j.legs[0]!;
  const ride = ridesOf(j).find((r) => !r.onboard);
  const quay = ride?.from.quay;
  const planned = ride?.from.plannedLabel;
  if (first.type === "ride" && first.onboard) {
    const when = liveArr(first.to);
    return { text: `Get off at ${first.to.quay.stationName}`, when, gone: false, state: "plain", onboard: true };
  }
  const when = first.type === "walk" ? first.dep : liveDep(first.from);
  const walkFirst = first.type === "walk";
  const delayS = ride?.from.depDelayS;
  const state: FirstAction["state"] = !ride || ride.live === "timetable" ? "plain" : delayMins(delayS) > 0 ? "late" : "ok";
  const s = when - now;
  let text = "";
  if (s < -45) text = `${walkFirst ? "Left" : "Left"} ${dur(-s)} ago`;
  else if (s < 60) text = walkFirst ? "Leave now" : "Leaves now";
  else if (s < 3600) text = `${walkFirst ? "Leave" : "Leaves"} in ${dur(Math.floor(s / 60) * 60)}`;
  return { text, when, gone: s < -45, state, quay, planned, delayS };
}

/** Spare time on a change, counting the user's own extra change time as spare. */
export function spare(leg: WalkLeg, marginS: number): { s: number; level: "ok" | "tight" | "missed" } | null {
  if (leg.slackS === undefined || leg.kind !== "transfer") return null;
  const s = leg.slackS + marginS;
  return { s, level: s < 0 ? "missed" : leg.slackS < 60 ? "tight" : "ok" };
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
export function walkFeatures(leg: WalkLeg): string[] {
  const out: string[] = [];
  if (leg.stairsUp) out.push(`${plural(leg.stairsUp, "step", "steps")} up`);
  if (leg.stairsDown) out.push(`${plural(leg.stairsDown, "step", "steps")} down`);
  if (leg.escalators) out.push(leg.escalators === 1 ? "escalator" : `${leg.escalators} escalators`);
  if (leg.lifts) out.push(leg.lifts === 1 ? "lift" : `${leg.lifts} lifts`);
  return out;
}

export interface ChangeInfo {
  /** Seconds between getting off and the next departure. */
  availS: number;
  walkS: number;
  level: "ok" | "tight" | "missed";
}
/** Every change of vehicle with the time it leaves. */
export function changesOf(j: Journey, marginS: number): ChangeInfo[] {
  const out: ChangeInfo[] = [];
  let prev: RideLeg | null = null;
  let walk: WalkLeg | null = null;
  for (const l of j.legs) {
    if (l.type === "walk") walk = l;
    else {
      if (prev && !l.stayOnBoard) {
        const sp = walk ? spare(walk, marginS) : null;
        out.push({ availS: liveDep(l.from) - liveArr(prev.to), walkS: walk?.durationS ?? 0, level: sp?.level ?? "ok" });
      }
      prev = l;
      walk = null;
    }
  }
  return out;
}
/** "Direct", "1 change · 8 min", "3 changes · ≥ 6 min" (each change has at least that long). */
export function changesText(ch: ChangeInfo[]): string {
  if (!ch.length) return "Direct";
  const mins = ch.map((c) => Math.max(0, Math.floor(c.availS / 60)));
  // one change: the time there is for it; several: the shortest, which is the one that decides
  return `${plural(ch.length, "change", "changes")} · ${mins.length === 1 ? "" : "≥ "}${Math.min(...mins)} min`;
}

const RANK = { info: 0, warning: 1, severe: 2 } as const;
/** The alert that most needs a decision; delays are shown next to the times instead. */
export function worstAlert(j: Journey): JourneyAlert | null {
  const flagged = (j.alerts ?? []).filter((a) => a.severity !== "info");
  return flagged.length ? flagged.reduce((a, b) => (RANK[b.severity] > RANK[a.severity] ? b : a)) : null;
}

/** For screen readers: the whole row in one sentence. */
export function journeyLabel(j: Journey, now: number): string {
  const act = firstAction(j, now);
  const rides = ridesOf(j);
  const parts = [
    `${hm(j.dep)} to ${hm(j.arr)}`,
    dayLabel(j.dep, now) !== "Today" ? dayLabel(j.dep, now) : "",
    dur(j.durationS),
    rides.length ? (j.transfers === 0 ? "direct" : plural(j.transfers, "change", "changes")) : "on foot",
    rides.map((r) => lineTitle(r.line)).join(", then "),
    act.text,
    act.quay ? quayShort(act.quay) : "",
    delayMins(act.delayS) > 0 ? `${plural(delayMins(act.delayS), "minute", "minutes")} late` : "",
    worstAlert(j)?.text ?? "",
  ];
  return parts.filter(Boolean).join(". ");
}

/** Legs with something to do or see (drops zero-length same-point changes). */
export const visibleLegs = (j: Journey): Leg[] => j.legs.filter((l) => l.type === "ride" || !samePoint(l));
