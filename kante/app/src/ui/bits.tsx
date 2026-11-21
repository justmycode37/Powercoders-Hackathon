import type { ComponentChildren } from "preact";
import type { Journey, Leg, LineBadge as Line, Mode, Quay, RideLeg, StopCall } from "../api/types";
import { liveArr, liveDep } from "../lib/journey";
import { isNight, lineLabel, lineTitle, lineVars, quayNoun, quayNounShort, quayShort } from "../lib/lines";
import { delayMins } from "../lib/time";
import { back } from "../router";
import { Icon, modeIcon } from "./icons";


/** Line badge: a plain rounded rectangle in the line's colour. A nameless line shows its mode. */
export function LineBadge({ line, size, icon }: { line: Line; size?: "lg" | "xl"; icon?: boolean }) {
  const text = lineLabel(line);
  return (
    <span class={"badge" + (size ? " " + size : "")} style={lineVars(line)} role="img" aria-label={lineTitle(line)}>
      {isNight(line) && <Icon name="moon" size={size ? 13 : 10} />}
      {(icon || !text) && <Icon name={modeIcon(line.mode)} size={size === "xl" ? 22 : size ? 16 : 13} />}
      {text}
    </span>
  );
}

export function ModeIcons({ modes, size = 18 }: { modes?: Mode[]; size?: number }) {
  if (!modes?.length) return null;
  return (
    <span class="modes">
      {modes.slice(0, 3).map((m) => (
        <Icon key={m} name={modeIcon(m)} size={size} />
      ))}
    </span>
  );
}

/**
 * The boarding point in its fixed slot: right-aligned, bold ("Pl. 7", "Bay C").
 * Shows nothing for an unsigned stop — a label is never invented.
 */
export function Platform({ quay, planned, long }: { quay: Quay; planned?: string; long?: boolean }) {
  if (!quay.label) return null;
  const changed = planned !== undefined && planned !== "" && planned !== quay.label;
  const noun = long ? quayNoun(quay) : quayNounShort(quay);
  return (
    <span class={"plat" + (changed ? " changed" : "")} aria-label={quayShort(quay) + (changed ? `, changed from ${planned}` : "")}>
      {noun && <span class="plat-noun">{noun}</span>}
      <b>{quay.label}</b>
    </span>
  );
}

/** "+4 min" after a scheduled time, in the alarm colour. Nothing when on time. */
export function Delay({ s, short }: { s: number | undefined; short?: boolean }) {
  const m = delayMins(s);
  if (m === 0) return null;
  const label = `${Math.abs(m)} ${Math.abs(m) === 1 ? "minute" : "minutes"} ${m > 0 ? "late" : "early"}`;
  return (
    <span class={"delay" + (m > 0 ? " late" : " early")} aria-label={label}>
      {m > 0 ? "+" : "−"}
      {Math.abs(m)}
      {short ? "" : " min"}
    </span>
  );
}

const LIVE_WORD = { observed: "Live", predicted: "Expected", timetable: "Timetable" } as const;
/** Real-time state as a word, never by colour or opacity alone. */
export function LiveTag({ live }: { live: "observed" | "predicted" | "timetable" }) {
  return (
    <span class={"live-tag " + live}>
      {live === "timetable" ? <Icon name="clock" size={12} /> : <i class="live-dot" aria-hidden="true" />}
      {LIVE_WORD[live]}
    </span>
  );
}

export function BackButton({ fallback, label = "Back" }: { fallback?: string; label?: string }) {
  return (
    <button class="round-btn plain" onClick={() => back(fallback)} aria-label={label}>
      <Icon name="back" />
    </button>
  );
}

export function Skeleton({ rows = 3, kind = "row", label }: { rows?: number; kind?: "row" | "card" | "block"; label: string }) {
  return (
    <div class="skeletons" aria-busy="true" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} class={"skeleton " + kind} />
      ))}
    </div>
  );
}

export function Notice({ kind = "info", children, action, icon }: { kind?: "info" | "warning" | "severe" | "ok"; children: ComponentChildren; action?: ComponentChildren; icon?: string }) {
  return (
    <div class={"notice " + kind} role={kind === "severe" ? "alert" : "status"}>
      <Icon name={icon ?? (kind === "info" || kind === "ok" ? "info" : "alert")} size={18} />
      <div class="notice-text">{children}</div>
      {action}
    </div>
  );
}

export function Empty({ icon, title, children, action }: { icon: string; title: string; children?: ComponentChildren; action?: ComponentChildren }) {
  return (
    <div class="empty">
      <Icon name={icon} size={28} />
      <strong>{title}</strong>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

// ---------------------------------------------------------------- journey summaries

/** Legs worth showing: zero-length walks (same-point changes) are not a leg to the eye. */
const shown = (l: Leg): boolean => l.type === "ride" || l.durationS >= 60;

/**
 * The leg chain: every vehicle's badge in order, walks as "🚶 4" chips. Used in
 * the result row, the journey header and the minimised guidance strip.
 */
export function LegChain({ legs, max = 6 }: { legs: Leg[]; max?: number }) {
  const items = legs.filter(shown);
  const cut = items.length > max ? items.slice(0, max - 1) : items;
  return (
    <span class="chain" aria-hidden="true">
      {cut.map((l, i) => (
        <>
          {i > 0 && <Icon name="right" size={12} class="chain-sep" />}
          {l.type === "ride" ? (
            // "IC 8" and "S3" say train by themselves; a bare number needs its mode
            <LineBadge line={l.line} icon={!(l.line.mode === "rail" && /[A-Za-z]/.test(l.line.name))} />
          ) : (
            <span class="chain-walk">
              <Icon name="walk" size={14} />
              {Math.max(1, Math.round(l.durationS / 60))}
            </span>
          )}
        </>
      ))}
      {cut.length < items.length && <span class="chain-more">+{items.length - cut.length}</span>}
    </span>
  );
}

/**
 * Proportional time bar between the two clock times: one segment per leg placed
 * by elapsed time, rides in the line colour, walks dotted, a dot per change.
 */
export function TimeBar({ j }: { j: Journey }) {
  const total = Math.max(1, j.arr - j.dep);
  const pct = (t: number) => Math.min(100, Math.max(0, ((t - j.dep) / total) * 100));
  const rides = j.legs.filter((l): l is RideLeg => l.type === "ride");
  return (
    <span class="tbar" aria-hidden="true">
      <i class="tbar-base" />
      {j.legs.map((l, i) => {
        if (l.type === "walk") return null;
        const a = pct(liveDep(l.from));
        const b = pct(liveArr(l.to));
        return <i key={i} class={"tbar-ride" + (l.cancelled ? " cancelled" : "")} style={{ ...lineVars(l.line), left: a + "%", width: Math.max(4, b - a) + "%" }} />;
      })}
      {rides.slice(1).map((l, i) => {
        // the change sits where the previous ride ends
        const prev = rides[i]!;
        return <i key={"c" + i} class="tbar-change" style={{ left: pct((liveArr(prev.to) + liveDep(l.from)) / 2) + "%" }} />;
      })}
      <i class="tbar-end a" />
      <i class="tbar-end b" />
    </span>
  );
}
