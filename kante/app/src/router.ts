import { signal } from "@preact/signals";

export type RouteName = "home" | "search" | "pick" | "plan" | "journey" | "go" | "station" | "trip" | "onboard";
export interface Route {
  name: RouteName;
  params: Record<string, string>;
  /** A modal sheet stacked on the screen (kept in history so Back closes it). */
  overlay: string | null;
  /** Position in this session's history, to know whether Back stays inside the app. */
  depth: number;
}

const NAMES: Record<string, RouteName> = {
  "": "home", search: "search", pick: "pick", plan: "plan", journey: "journey", go: "go", station: "station", trip: "trip", onboard: "onboard",
};

function parse(): Route {
  const name = NAMES[location.pathname.replace(/^\/+|\/+$/g, "")] ?? "home";
  const params: Record<string, string> = {};
  new URLSearchParams(location.search).forEach((v, k) => (params[k] = v));
  const st = (history.state ?? {}) as { overlay?: string; depth?: number };
  return { name, params, overlay: st.overlay ?? null, depth: st.depth ?? 0 };
}

export const route = signal<Route>(parse());

export function href(name: RouteName, params: Record<string, string | number | undefined | null> = {}): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  const s = q.toString().replace(/%3A/g, ":").replace(/%2C/g, ",").replace(/%7E/g, "~").replace(/%7C/g, "|");
  return "/" + (name === "home" ? "" : name) + (s ? "?" + s : "");
}

export function navigate(url: string, opts: { replace?: boolean } = {}): void {
  const depth = route.peek().depth + (opts.replace ? 0 : 1);
  if (opts.replace) history.replaceState({ depth }, "", url);
  else history.pushState({ depth }, "", url);
  route.value = parse();
}
export function go(name: RouteName, params?: Record<string, string | number | undefined | null>, opts?: { replace?: boolean }): void {
  navigate(href(name, params), opts);
}
/** Back inside the app; falls back to `fallback` when the app was opened on this page. */
export function back(fallback = "/"): void {
  if (route.peek().depth > 0) history.back();
  else navigate(fallback, { replace: true });
}
export function openOverlay(name: string): void {
  const r = route.peek();
  history.pushState({ overlay: name, depth: r.depth + 1 }, "", location.href);
  route.value = parse();
}
export function closeOverlay(): void {
  if (route.peek().overlay) history.back();
}

window.addEventListener("popstate", () => {
  route.value = parse();
});

// Plain links navigate inside the app.
document.addEventListener("click", (ev) => {
  if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
  const a = (ev.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
  if (!a || a.target || a.origin !== location.origin || a.hasAttribute("download")) return;
  ev.preventDefault();
  navigate(a.pathname + a.search, { replace: a.dataset.replace !== undefined });
});
