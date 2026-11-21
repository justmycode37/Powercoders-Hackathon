import type { Mode, WalkStepKind } from "../api/types";

// 24×24 stroke icons, drawn for this app.
const P: Record<string, string> = {
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.3-4.3"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  swap: '<path d="M8 4v16M8 20l-3.5-3.5M8 20l3.5-3.5M16 20V4M16 4l-3.5 3.5M16 4l3.5 3.5"/>',
  locate: '<circle cx="12" cy="12" r="6.5"/><circle cx="12" cy="12" r="2" fill="currentColor"/><path d="M12 2v3.5M12 18.5V22M2 12h3.5M18.5 12H22"/>',
  nav: '<path d="M12 3l7 17-7-4-7 4z" fill="currentColor"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  walk: '<circle cx="13" cy="4.5" r="1.7" fill="currentColor"/><path d="M9.5 21l2.2-6.2-2.4-2.6L10.6 8l3 3 3 .8M10.6 8L7.8 9.4 7 12.6M11.7 14.8l3.2 2.4.9 3.8"/>',
  tram: '<rect x="6" y="5.5" width="12" height="11.5" rx="3"/><path d="M6 11.5h12M9.5 20.5l1-3.5M14.5 20.5l-1-3.5M12 5.5V3M9 3h6"/><path d="M9.5 14.2h.01M14.5 14.2h.01" stroke-width="2.6"/>',
  bus: '<rect x="5" y="4" width="14" height="13" rx="3"/><path d="M5 11h14M8 17v2.5M16 17v2.5"/><path d="M8.6 14h.01M15.4 14h.01" stroke-width="2.6"/>',
  rail: '<rect x="6" y="3" width="12" height="14" rx="3.5"/><path d="M6 10.5h12M9 21l2-4M15 21l-2-4"/><path d="M9.5 13.8h.01M14.5 13.8h.01" stroke-width="2.6"/>',
  boat: '<path d="M3 18.5c1.5 1.4 3 1.4 4.5 0s3-1.4 4.5 0 3 1.4 4.5 0 3-1.4 4.5 0M5.2 15l-1-4h15.6l-1 4M8 11V6.5h8V11M12 6.5V4"/>',
  cable: '<path d="M3 5.5l18-2.5M12 4.3V8"/><rect x="7" y="8" width="10" height="10.5" rx="2.5"/><path d="M7 13h10"/>',
  stairs: '<path d="M4 20h4v-4h4v-4h4V8h4"/>',
  "stairs-up": '<path d="M4 20h4v-4h4v-4h4V8h4M5 10l5-5M10 5H6.5M10 5v3.5"/>',
  "stairs-down": '<path d="M4 20h4v-4h4v-4h4V8h4M5 4l5 5M10 9H6.5M10 9V5.5"/>',
  lift: '<rect x="5" y="3" width="14" height="18" rx="2.5"/><path d="M9.5 10l2.5-3 2.5 3M9.5 14l2.5 3 2.5-3"/>',
  escalator: '<path d="M3 19h4.5l8-10H21"/><circle cx="9" cy="6" r="1.7" fill="currentColor"/><path d="M9 9v3.5"/>',
  ramp: '<path d="M3 19h18V9L3 19z"/>',
  cross: '<path d="M4 20L8 4M10 20l4-16M16 20l4-16"/>',
  enter: '<path d="M14 4h5v16h-5M4 12h10M10 8l4 4-4 4"/>',
  exit: '<path d="M10 4H5v16h5M11 12h10M17 8l4 4-4 4"/>',
  flag: '<path d="M5 21V4M5 4.5h12l-2.5 4 2.5 4H5"/>',
  dot: '<circle cx="12" cy="12" r="4" fill="currentColor"/>',
  sliders: '<path d="M4 7h9M19 7h1M4 17h1M11 17h9"/><circle cx="16" cy="7" r="2.5"/><circle cx="8" cy="17" r="2.5"/>',
  right: '<path d="M9 5l7 7-7 7"/>',
  down: '<path d="M5 9l7 7 7-7"/>',
  up: '<path d="M5 15l7-7 7 7"/>',
  star: '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.8z"/>',
  home: '<path d="M4 11l8-7 8 7M6 9.5V20h12V9.5"/>',
  work: '<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M9 7V5.5a1.5 1.5 0 011.5-1.5h3A1.5 1.5 0 0115 5.5V7M3 13h18"/>',
  pin: '<path d="M12 21s-7-6.3-7-11.2a7 7 0 0114 0C19 14.7 12 21 12 21z"/><circle cx="12" cy="9.8" r="2.4"/>',
  map: '<path d="M9 4L3 6.2V20l6-2.2 6 2.2 6-2.2V4l-6 2.2L9 4zM9 4v13.8M15 6.2V20"/>',
  wheelchair: '<circle cx="10" cy="4.5" r="1.7" fill="currentColor"/><path d="M10 8v6h5.5l2.5 5M10 10.8h4.5M7.3 12.2a5 5 0 105.9 7"/>',
  alert: '<path d="M12 4l9.3 16H2.7L12 4zM12 10v4.5"/><path d="M12 17.3h.01" stroke-width="2.6"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.7h.01" stroke-width="2.6"/>',
  onboard: '<rect x="5" y="3.5" width="14" height="14.5" rx="3.5"/><path d="M8.8 11l2.3 2.3 4.2-4.6M8 18v2.5M16 18v2.5"/>',
  share: '<path d="M12 15V3.5M12 3.5L8 7.5M12 3.5l4 4M5 12.5V20h14v-7.5"/>',
  go: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
  board: '<path d="M4 6h16M4 12h16M4 18h10"/>',
  history: '<path d="M4 12a8 8 0 102.3-5.6M4 4.5v3.8h3.8M12 8v4.2l2.8 1.8"/>',
  live: '<path d="M6.3 17.7a8 8 0 010-11.4M17.7 6.3a8 8 0 010 11.4M9.2 14.8a4 4 0 010-5.6M14.8 9.2a4 4 0 010 5.6"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/>',
  arrow: '<path d="M12 3.5l5.5 15-5.5-3.3-5.5 3.3z" fill="currentColor" stroke-linejoin="round"/>',
  layers: '<path d="M12 3.5l9 4.8-9 4.8-9-4.8 9-4.8zM3.5 13l8.5 4.5 8.5-4.5"/>',
  target: '<circle cx="12" cy="12" r="3"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/>',
  seat: '<path d="M7 4v9a2 2 0 002 2h7M7 9h5a2 2 0 012 2v4M16 15l2.5 5M9 15v5"/>',
  moon: '<path d="M19.5 14.2A8 8 0 019.8 4.5a8 8 0 109.7 9.7z" fill="currentColor"/>',
  bell: '<path d="M6 16.5V11a6 6 0 0112 0v5.5l1.5 2h-15zM10 20.5a2.2 2.2 0 004 0"/>',
  dots: '<path d="M12 5.5h.01M12 12h.01M12 18.5h.01" stroke-width="2.8"/>',
  list: '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01" stroke-width="2.8"/>',
  stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="2" fill="currentColor"/>',
  play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor" stroke-linejoin="round"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 11-2.4-5.5M19.5 4.5v4h-4"/>',
  hand: '<path d="M12 21c-3.5 0-6-2.6-6-6V8.2a1.4 1.4 0 012.8 0V12M8.8 12V5.4a1.4 1.4 0 012.8 0V11M11.6 11V4.8a1.4 1.4 0 012.8 0V11.4M14.4 11.4V6.8a1.4 1.4 0 012.8 0V15c0 3.4-2.2 6-5.2 6"/>',
  offline: '<path d="M4 4l16 16M8.5 15.5a5 5 0 017 0M5.5 12.2a9.5 9.5 0 013.3-2.2M12.5 9.2a9.5 9.5 0 016 3M2.5 9a14 14 0 013.7-2.6M10.7 4.7A14 14 0 0121.5 9"/><path d="M12 19h.01" stroke-width="2.6"/>',
};

const MODE_ICON: Record<Mode, string> = {
  rail: "rail", tram: "tram", bus: "bus", metro: "rail", boat: "boat", funicular: "cable", cableway: "cable",
  rack: "rail", lift: "lift", ondemand: "bus", other: "bus",
};
const STEP_ICON: Record<WalkStepKind, string> = {
  depart: "nav", walk: "walk", cross: "cross", "stairs-up": "stairs-up", "stairs-down": "stairs-down",
  "escalator-up": "escalator", "escalator-down": "escalator", lift: "lift", "ramp-up": "ramp", "ramp-down": "ramp",
  enter: "enter", exit: "exit", platform: "walk", arrive: "flag",
};

export function Icon({ name, size = 20, class: cls, label }: { name: string; size?: number; class?: string; label?: string }) {
  return (
    <svg
      class={"icon" + (cls ? " " + cls : "")}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden={label ? undefined : "true"}
      role={label ? "img" : undefined}
      aria-label={label}
      dangerouslySetInnerHTML={{ __html: P[name] ?? P.dot! }}
    />
  );
}
export const modeIcon = (m: Mode): string => MODE_ICON[m] ?? "bus";
export const stepIcon = (k: WalkStepKind): string => STEP_ICON[k] ?? "walk";
