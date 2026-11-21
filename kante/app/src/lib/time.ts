import { signal } from "@preact/signals";

// The server's clock is authoritative for countdowns: a phone that is a minute
// off would otherwise show wrong "leave in" times. The API client feeds the
// HTTP Date header in here.
let skewMs = 0;

// A simulated clock ("?clock=2026-11-23T08:00", "?clock=off") lets the app be
// tried and tested at another time of day: it runs on from the chosen moment
// and the API calls carry it. Stored for the tab only.
function readSim(): number | null {
  try {
    const q = new URLSearchParams(location.search).get("clock");
    if (q === "off") sessionStorage.removeItem("kante.clock");
    else if (q) {
      const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(q) ? q : q + zurichOffset(q));
      if (!Number.isNaN(t)) sessionStorage.setItem("kante.clock", String(t - Date.now()));
    }
    const v = sessionStorage.getItem("kante.clock");
    return v === null ? null : Number(v);
  } catch {
    return null;
  }
}
/** "+01:00" or "+02:00" for a Swiss wall-clock time. */
function zurichOffset(local: string): string {
  const guess = Date.parse(local + "Z");
  if (Number.isNaN(guess)) return "+01:00";
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Zurich", timeZoneName: "shortOffset" }).formatToParts(guess - 3600_000);
  const h = Number(/([+-]\d+)/.exec(parts.find((p) => p.type === "timeZoneName")?.value ?? "+1")?.[1] ?? 1);
  return `${h < 0 ? "-" : "+"}${String(Math.abs(h)).padStart(2, "0")}:00`;
}
export const simClock = signal<number | null>(readSim());
export function stopSimClock(): void {
  try {
    sessionStorage.removeItem("kante.clock");
  } catch {
    /* ignore */
  }
  simClock.value = null;
  bump();
}
/** Unix seconds to send with requests while the clock is simulated. */
export const simTime = (): number | undefined => (simClock.peek() === null ? undefined : nowS());

export function noteServerDate(header: string | null, sentAt: number, receivedAt: number): void {
  if (!header || simClock.peek() !== null) return;
  const server = Date.parse(header);
  if (Number.isNaN(server)) return;
  // the Date header has 1 s resolution: only correct for skews that matter
  const skew = server + 500 - (sentAt + receivedAt) / 2;
  const next = Math.abs(skew) > 20_000 ? skew : 0;
  if (Math.abs(next - skewMs) > 5000) {
    skewMs = next;
    bump();
  }
}
export const nowMs = (): number => Date.now() + (simClock.peek() ?? skewMs);
export const nowS = (): number => Math.floor(nowMs() / 1000);

/** Unix seconds, updated every second (for countdowns). */
export const tick = signal(nowS());
/** Unix seconds, updated every 10 s (for lists of departures). */
export const tick10 = signal(nowS());

function bump(): void {
  const n = nowS();
  tick.value = n;
  if (Math.abs(n - tick10.peek()) >= 10) tick10.value = n;
}
setInterval(() => {
  if (!document.hidden) bump();
}, 1000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) bump();
});

const TZ = "Europe/Zurich";
const fHm = new Intl.DateTimeFormat("de-CH", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const fParts = new Intl.DateTimeFormat("en-CA", {
  timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
const fDay = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric", month: "short" });

/** "14:07" in Swiss local time. */
export const hm = (unix: number): string => fHm.format(unix * 1000);

export interface ZParts { date: string; time: string; secs: number }
export function zparts(unix: number): ZParts {
  const p: Record<string, string> = {};
  for (const x of fParts.formatToParts(unix * 1000)) p[x.type] = x.value;
  return { date: `${p.year}-${p.month}-${p.day}`, time: `${p.hour}:${p.minute}`, secs: +p.hour! * 3600 + +p.minute! * 60 + +p.second! };
}
/** Unix seconds of a Swiss local date ("2026-11-23") and time ("14:05"). */
export function fromZurich(date: string, time: string): number {
  const [y, m, d] = date.split("-").map(Number);
  const [h, min] = time.split(":").map(Number);
  const guess = Date.UTC(y!, m! - 1, d!, h, min) / 1000;
  // Zurich is ahead of UTC by the difference between the wall clocks
  const z = zparts(guess);
  const [zy, zm, zd] = z.date.split("-").map(Number);
  const wall = Date.UTC(zy!, zm! - 1, zd!) / 1000 + z.secs - (z.secs % 60);
  return guess - (wall - guess);
}

/** "Today", "Tomorrow", or "Mon 23 Nov". */
export function dayLabel(unix: number, now = nowS()): string {
  const a = zparts(unix).date;
  if (a === zparts(now).date) return "Today";
  if (a === zparts(now + 86400).date) return "Tomorrow";
  if (a === zparts(now - 86400).date) return "Yesterday";
  return fDay.format(unix * 1000);
}

/** "< 1 min", "23 min", "1 h 05 min". Never "0 min" for a duration that is not zero. */
export function dur(s: number): string {
  if (s > 0 && s < 60) return "< 1 min";
  const m = Math.max(0, Math.round(s / 60));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h} h ${String(r).padStart(2, "0")} min` : `${h} h`;
}
/** Where seconds decide: "45 s", "1 min 15 s", then whole minutes rounded down. */
export function durExact(s: number): string {
  s = Math.max(0, Math.round(s));
  if (s < 60) return `${s} s`;
  if (s < 90) return s % 60 ? `1 min ${s % 60} s` : "1 min";
  return dur(Math.floor(s / 60) * 60);
}
/** Spoken form: "4 minutes", "1 hour 5 minutes". */
export function durSpoken(s: number): string {
  const m = Math.max(1, Math.round(s / 60));
  const h = Math.floor(m / 60);
  const r = m % 60;
  const mins = `${r} ${r === 1 ? "minute" : "minutes"}`;
  if (!h) return mins;
  return `${h} ${h === 1 ? "hour" : "hours"}${r ? " " + mins : ""}`;
}
/** Whole minutes until `unix`; never rounds up (do not overpromise). */
export function minsUntil(unix: number, now: number): number {
  return Math.floor((unix - now) / 60);
}
/** "now", "3 min", "1 h 12 min", "left" — countdown wording for departures. */
export function countdown(unix: number, now: number): string {
  const s = unix - now;
  if (s < -30) return "left";
  if (s < 60) return "now";
  return dur(Math.floor(s / 60) * 60);
}
/** "2:10" style for the last minutes, otherwise minutes. */
export function clock(s: number): string {
  if (s < 0) s = 0;
  if (s >= 3600) return dur(s);
  if (s >= 600) return `${Math.floor(s / 60)} min`;
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}
/** Whole minutes of a delay in seconds, rounded to the nearest minute. */
export const delayMins = (s: number | undefined): number => (s === undefined ? 0 : Math.round(s / 60));
