# Kante — web app

Mobile-first PWA for door-to-door public transport in Switzerland. Preact +
signals, MapLibre GL JS (loaded lazily), hand-written CSS, no router or UI
library. The HTTP contract with the engine is `src/api/types.ts`.

The interface follows the three studies in `docs/ui-research/` (Google Maps,
SBB Mobile, Transit) and the copy review next to them:

- **One map, everything else a sheet** (Google Maps): three detents — low,
  fitted to the sheet's header; middle, half the screen; expanded, stopping
  short of the top — a round close button, no scrim. The camera refits its
  subject into the free area when the sheet settles; the location button rides
  on the sheet's edge. Only text entry and Options are full screen.
- **Departures on launch** (Transit): map on the top 44 %, full-bleed cards in
  the line's colour below, the search bar on the seam with "I'm on board" in it.
- **Journey rows and timeline on one grid** (SBB): times bold at both edges, a
  proportional bar between, platform in a fixed right-aligned slot; delays as
  "+4 min" after the scheduled time.
- **Guidance** (Transit GO): one sentence per stage, a segmented bar with a
  puck, one card for the leg in hand; closing minimises to a strip on the map.

Kante's own: the brand is ink with the yellow "edge" (never SBB red, Google
blue/teal or Transit green), the where-to-stand sign, written directions at
every change, the walking band on the map, and the level switcher that follows
the current step.

## Run

```sh
npm install
npm run dev          # Vite on :5173; /api is proxied to http://localhost:8080 (override: KANTE_API=http://host:port)
npm run dev:mock     # mock engine on :8080 + Vite on :5173
npm run build        # type-check + production build → dist/  (the engine serves dist/ live — build only what works)
npm run preview      # serve dist/ on :4173 with the same /api proxy
```

Geolocation needs HTTPS (or localhost). On a phone over plain HTTP, long-press
the map and choose **I'm here** to set a location by hand; a chip shows while
it is on. The service worker (offline shell, map cache) is only registered in
production builds and also needs HTTPS or localhost.

**Another time of day:** open the app with `?clock=2026-11-23T08:00` (Swiss
time) to run it at that moment; `?clock=off` or the chip on the map ends it.
The clock runs on from there and every request carries it, so the engine
answers for that time. Live data is of course only there for the real "now".

## Check

```sh
npm run typecheck    # app, and the mock against src/api/types.ts
npm run smoke        # headless Chromium through every flow against the mock; fails on console errors and failed API calls
npm run smoke:real   # the same plus address/POI, step-free, rural, night and offline flows against the real engine
npm run shots        # screenshots of every screen and state against the real engine → shots/
npm run perf         # bundle sizes and load timings
npm run peek -- out.png "/station?id=…" --clock=2026-11-23T08:00 click:.dep   # one-off screenshot of a running app
```

The scripts build into `.cache/dist-test` (never `dist/`) and start
`vite preview` on a private port. Against the mock (`:8097`) the clock is fixed
at Mon 23 Nov 2026 14:02; against the real engine the app's clock is simulated
at the next weekday 08:00. `KANTE_URL` points them at an app that is already
running, `KANTE_API` at another engine.

## Mock engine

`mock/server.mjs` (plain Node, `// @ts-check` against the contract) implements
every endpoint on a synthetic timetable: the Bern hub with the real boarding
point coordinates, a hand-built multi-level walking network of Bern station,
city lines, the rail corridor to Zürich, deterministic delays, platform changes
and cancellations. It exists so the flows can be tested without the engine and
with trouble on demand; the design is judged on real responses.

## Layout of `src/`

| Path | What |
|---|---|
| `api/` | The contract (`types.ts`) and the fetch client with abortable, keyed queries |
| `lib/lines.ts` | The 13-colour line palette and its assignment (curated → mode → number), line and platform names |
| `lib/journey.ts` | What every screen says about a journey: first action, spare time, changes, alerts |
| `lib/time.ts`, `lib/geo.ts` | Clock (server-corrected or simulated), durations, distances |
| `ui/sheet.tsx` | The bottom sheet and modal sheet |
| `ui/stand.tsx`, `ui/bits.tsx` | Where-to-stand card, badges, platform slot, leg chain, time bar |
| `screens/` | Home, search, results, journey, guidance (`go.tsx`), departure board and trip, on board, options |
| `map/` | `scene.ts` (what to show, tiny) and the lazy MapLibre engine with canvas-drawn sprites |
| `plan.ts`, `state.ts`, `router.ts` | Journey query in the URL, settings and saved places, history routing |

## Line colours

The feed has none, so `lib/lines.ts` assigns each line one of thirteen palette
entries with a fixed text colour (every pair ≥ 4.9 : 1) and light and dark
values: a curated override per operator first, then a mode default
(long-distance rail slate, boats teal, cableways brown, night lines indigo),
then the line number (`n × 5 mod 12`). The curated table currently holds only a
from-memory starting set for Zürich trams and must be checked against the
operators' network maps before it is extended.
