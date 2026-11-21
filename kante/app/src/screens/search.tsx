import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { api, useQuery } from "../api/client";
import type { Place } from "../api/types";
import { metres } from "../lib/geo";
import { lineTitle, modeName } from "../lib/lines";
import { mapApi, mapView, scene, insets } from "../map/scene";
import { openStation } from "../nav";
import { coordPlace, HERE, isHere, parseQuery, queryParams, type PlaceSel, type PlanQuery } from "../plan";
import { back, go, route } from "../router";
import { onboard, recents, remember, saved, showToast, userPos } from "../state";
import { BackButton, Empty } from "../ui/bits";
import { Icon, modeIcon } from "../ui/icons";
import { isWide } from "../ui/sheet";

type Field = "from" | "to";

/** Put `p` into the query; go to the results when both ends are known. */
function choose(q: PlanQuery, field: Field, p: PlaceSel, params: Record<string, string>): void {
  if (!isHere(p)) remember(p);
  const slot = params.set as "home" | "work" | undefined;
  if (slot && !isHere(p)) {
    saved.value = { ...saved.peek(), [slot]: p };
    showToast(`${slot === "home" ? "Home" : "Work"} saved`);
    go("home", {}, { replace: true });
    return;
  }
  const next: PlanQuery = { ...q, [field]: p };
  // the same place at both ends makes no journey
  const other = field === "from" ? "to" : "from";
  const o = next[other];
  if ((o && !isHere(o) && !isHere(p) && o.id === p.id) || (isHere(p) && isHere(o))) {
    next[other] = null;
    showToast("Start and destination can't be the same");
  }
  if (next.to && (next.from || next.onboard)) go("plan", queryParams(next), { replace: true });
  else go("search", { ...queryParams(next), f: next.to ? "from" : "to" }, { replace: true });
}

const selName = (p: PlaceSel | null): string => (p ? (isHere(p) ? "Current location" : p.name) : "");

export function Search() {
  const params = route.value.params;
  const q = parseQuery(params);
  const field: Field = params.f === "from" ? "from" : "to";
  const setting = params.set as "home" | "work" | undefined;
  // what was typed belongs to the field it was typed into: switching field starts empty without a late reset that could eat keystrokes
  const [entry, setEntry] = useState({ field, text: "" });
  const text = entry.field === field ? entry.text : "";
  const setText = (t: string) => setEntry({ field, text: t });
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const pendingEnter = useRef(false);
  const term = text.trim();
  const near = userPos.value ?? (mapView.value ? { lat: mapView.value.lat, lon: mapView.value.lon } : null);
  const res = useQuery(term ? `s:${term}` : null, (s) => api.search(term, near, s));
  const results = term ? (res.data?.results ?? []) : [];

  useLayoutEffect(() => {
    setActive(0);
    input.current?.focus();
  }, [field]);
  useEffect(() => {
    scene.value = {};
  }, []);
  useEffect(() => {
    setActive(0);
    if (pendingEnter.current && !res.loading) {
      pendingEnter.current = false;
      if (results[0]) choose(q, field, results[0], params);
    }
  }, [res.data, res.loading]);

  const ob = q.onboard ? onboard.value : null;
  const pick = (p: PlaceSel) => choose(q, field, p, params);
  const other = field === "from" ? q.to : q.from;
  const quick: { key: string; icon: string; title: string; sub?: string; act: () => void }[] = [];
  if (!term) {
    if (!isHere(other) && !setting)
      quick.push({ key: "here", icon: "locate", title: "Current location", sub: userPos.value ? undefined : "Location permission needed", act: () => pick(HERE) });
    quick.push({ key: "map", icon: "map", title: "Choose on map", act: () => go("pick", { ...params, f: field }) });
  }
  const s = saved.value;
  const suggestions: Place[] = term
    ? results
    : [s.home, s.work, ...s.favs, ...recents.value].filter((p): p is Place => !!p).filter((p, i, a) => a.findIndex((x) => x.id === p.id) === i);
  const count = quick.length + suggestions.length;

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(count - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (term && res.loading) {
        pendingEnter.current = true;
        return;
      }
      const i = term ? active : Math.max(active, 0);
      if (i < quick.length) quick[i]?.act();
      else if (suggestions[i - quick.length]) pick(suggestions[i - quick.length]!);
    } else if (e.key === "Escape") back();
  };
  const swap = () => go("search", { ...queryParams({ ...q, from: q.to, to: q.from }), f: field }, { replace: true });
  const fieldBox = (f: Field) => {
    const sel = f === "from" ? q.from : q.to;
    const isActive = f === field;
    const label = f === "from" ? "From" : "To";
    if (f === "from" && q.onboard)
      return (
        <div class="field locked">
          <span class="field-label">From</span>
          <span class="field-value trunc">
            <Icon name="onboard" size={16} /> {ob ? `On board ${lineTitle(ob.line)} to ${ob.headsign}` : "On board"}
          </span>
          <button class="round-btn plain small" aria-label="I'm not on board" onClick={() => go("search", { ...queryParams({ ...q, onboard: null, from: HERE }), f: field }, { replace: true })}>
            <Icon name="close" size={16} />
          </button>
        </div>
      );
    return (
      <label class={"field" + (isActive ? " active" : "")}>
        <span class="field-label">{setting ? (setting === "home" ? "Home" : "Work") : label}</span>
        {isActive ? (
          <input
            ref={input}
            type="search"
            inputMode="search"
            enterkeyhint="search"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="off"
            spellcheck={false}
            placeholder={selName(sel) || (f === "from" ? "Stop, station or address" : "Where to?")}
            value={text}
            onInput={(e) => setText((e.target as HTMLInputElement).value)}
            onKeyDown={onKey}
            aria-label={label}
            aria-controls="search-results"
            aria-activedescendant={count ? `sr-${active}` : undefined}
            aria-autocomplete="list"
          />
        ) : (
          <button class="field-value trunc" onClick={() => go("search", { ...params, f }, { replace: true })}>
            {selName(sel) || <span class="placeholder">{f === "from" ? "Choose start" : "Choose destination"}</span>}
          </button>
        )}
        {isActive && text && (
          <button class="round-btn plain small" aria-label="Clear" onClick={() => { setText(""); input.current?.focus(); }}>
            <Icon name="close" size={16} />
          </button>
        )}
      </label>
    );
  };

  let idx = -1;
  const row = (p: Place) => {
    idx++;
    const i = idx;
    const fav = s.favs.some((x) => x.id === p.id);
    return (
      <li key={p.id} class={"row-wrap" + (i === active ? " active" : "")} id={`sr-${i}`} role="option" aria-selected={i === active}>
        <button class="row" onClick={() => pick(p)}>
          <span class="row-icon">
            <Icon name={p.id === s.home?.id ? "home" : p.id === s.work?.id ? "work" : p.kind === "station" ? modeIcon(p.modes?.[0] ?? "rail") : p.kind === "poi" ? "star" : "pin"} />
          </span>
          <span class="row-text">
            <strong class="wrap">{p.name}</strong>
            <span class="trunc">
              {p.kind === "station" ? [...new Set((p.modes ?? []).map(modeName))].join(", ") || "Stop" : (p.detail ?? (p.kind === "coord" ? "Pinned location" : ""))}
              {p.distM !== undefined && ` · ${metres(p.distM)}`}
            </span>
          </span>
        </button>
        {p.kind === "station" && !setting && (
          <button class="round-btn plain" aria-label={`Departures from ${p.name}`} onClick={() => openStation(p.id, undefined, { replace: true })}>
            <Icon name="board" size={18} />
          </button>
        )}
        {!setting && (
          <button
            class={"round-btn plain" + (fav ? " on" : "")}
            aria-label={fav ? `Remove ${p.name} from favourites` : `Add ${p.name} to favourites`}
            aria-pressed={fav}
            onClick={() => (saved.value = { ...s, favs: fav ? s.favs.filter((x) => x.id !== p.id) : [...s.favs, { ...p, distM: undefined }].slice(-8) })}
          >
            <Icon name="star" size={18} />
          </button>
        )}
      </li>
    );
  };
  const groups: [string, Place[]][] = term
    ? [
        ["Stops and stations", suggestions.filter((p) => p.kind === "station")],
        ["Addresses", suggestions.filter((p) => p.kind === "address")],
        ["Places", suggestions.filter((p) => p.kind === "poi" || p.kind === "coord")],
      ]
    : [["Saved and recent", suggestions]];
  // keyboard order follows the visual order
  const ordered = groups.flatMap(([, list]) => list);
  suggestions.splice(0, suggestions.length, ...ordered);
  return (
    <div class="search-screen">
      <div class="search-head">
        <BackButton />
        <div class="fields">
          {!setting && fieldBox("from")}
          {fieldBox(setting ? field : "to")}
        </div>
        {!setting && !q.onboard && (
          <button class="round-btn plain" onClick={swap} aria-label="Swap start and destination">
            <Icon name="swap" />
          </button>
        )}
      </div>
      <div class="search-body" id="search-results" role="listbox" aria-label="Suggestions" aria-busy={res.loading}>
        {quick.length > 0 && (
          <ul class="rows">
            {quick.map((k) => {
              idx++;
              const i = idx;
              return (
                <li key={k.key} class={"row-wrap" + (i === active ? " active" : "")} id={`sr-${i}`} role="option" aria-selected={i === active}>
                  <button class="row" onClick={k.act}>
                    <span class="row-icon brand">
                      <Icon name={k.icon} />
                    </span>
                    <span class="row-text">
                      <strong>{k.title}</strong>
                      {k.sub && <span>{k.sub}</span>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {groups.map(
          ([title, list]) =>
            list.length > 0 && (
              <section key={title}>
                <h2 class="section-title">{title}</h2>
                <ul class="rows">{list.map(row)}</ul>
              </section>
            ),
        )}
        {term && res.loading && !res.data && (
          <p class="status-line" role="status">
            Searching…
          </p>
        )}
        {!term && suggestions.length === 0 && <p class="hint inset">Search for any stop, station, address or place in Switzerland.</p>}
        {term && !res.loading && res.data && results.length === 0 && <Empty icon="search" title={`Nothing found for “${term}”`}>Check the spelling, or choose a location on the map.</Empty>}
        {term && res.error && <Empty icon="offline" title="Search isn't available right now">{res.error}</Empty>}
      </div>
    </div>
  );
}

/** Drop a pin: the map is moved under a fixed crosshair. */
export function Pick() {
  const params = route.value.params;
  const q = parseQuery(params);
  const field: Field = params.f === "from" ? "from" : "to";
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    scene.value = {};
    insets.value = { top: 68, bottom: isWide.value ? 0 : 150, left: 0 };
  }, []);
  const confirm = () => {
    const el = document.querySelector(".crosshair") as HTMLElement | null;
    const mapEl = document.querySelector(".map") as HTMLElement | null;
    let p = mapView.value ? { lat: mapView.value.lat, lon: mapView.value.lon } : null;
    if (el && mapEl && mapApi.at) {
      const r = el.getBoundingClientRect();
      const m = mapEl.getBoundingClientRect();
      p = mapApi.at(r.left + r.width / 2 - m.left, r.bottom - m.top);
    }
    if (!p) return showToast("The map is still loading");
    const at = p;
    setBusy(true);
    // name the pin after the nearest address; without an answer it stays a pinned location
    let fired = false;
    const done = (name?: string, detail?: string) => {
      if (fired) return;
      fired = true;
      const place = coordPlace(at.lat, at.lon, name || undefined);
      if (detail) place.detail = detail;
      choose(q, field, place, params);
    };
    const timer = setTimeout(() => done(), 1200);
    api.reverse(at.lat, at.lon).then(
      (r) => {
        clearTimeout(timer);
        done(r.name, r.detail);
      },
      () => {
        clearTimeout(timer);
        done();
      },
    );
  };
  return (
    <>
      <header class="topcard pickbar">
        <BackButton />
        <strong>Choose {params.set ? params.set : field === "from" ? "start" : "destination"} on the map</strong>
      </header>
      <div class="crosshair" aria-hidden="true">
        <i class="od-pin big" />
      </div>
      <div class="pick-card">
        <p>Move the map until the pin is on the spot.</p>
        <button class="pill-btn primary block" onClick={confirm} disabled={busy} data-testid="pick-confirm">
          Use this location
        </button>
      </div>
    </>
  );
}
