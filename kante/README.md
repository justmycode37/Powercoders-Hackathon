# Kante

A prototype door-to-door public transport app for Switzerland: a Rust routing
engine plus a mobile-first web app (installable PWA). "Kante" is what Swiss
signs call a boarding edge — the app's point is to tell you exactly where to
stand.

What it does that the SBB app and Google Maps do not:

- **Exact boarding point.** Every departure is tied to an individual bus bay,
  tram edge, platform and sector from the national stop registry, with its own
  coordinate, the side of the street and the level — not one averaged stop
  point. At Bern station that is the difference between bay A and bay K2,
  100 m apart.
- **Walking on a real, multi-level pedestrian network** (OpenStreetMap):
  underpasses, stairs, lifts, escalators, with written directions at every
  change.
- **Your walking speed is a routing input.** It decides which changes are
  feasible, not just the displayed minutes.
- **Step-free and fewer-stairs profiles** that change the route.
- **"I'm already on this vehicle"**: plan from inside a running tram or train.
- **Live data** (delays, cancellations, platform changes) from SIRI-ET.

Status: working prototype, built in one long session. Routing is national;
see [Known problems](#known-problems) before trusting it.

## Layout

| Path | What |
|---|---|
| `engine/crates/core` | Shared data model (the contract between crates) |
| `engine/crates/gtfs` | National GTFS + atlas stop registry → timetable |
| `engine/crates/raptor` | Journey search (range RAPTOR), departures, vehicles |
| `engine/crates/osm` | OpenStreetMap PBF → walking graph |
| `engine/crates/walk` | Pedestrian routing, profiles, turn-by-turn steps |
| `engine/crates/link` | Attaches boarding points to the walking graph, footpaths |
| `engine/crates/search` | Geocoder: stations, addresses, places |
| `engine/crates/rt` | SIRI-ET / GTFS-RT parsing, matching, polling |
| `engine/crates/server` | `kante` binary: data build + HTTP API |
| `engine/playground` | One-page debug UI on the API (served at `/playground/`) |
| `app/` | The web app (Preact + MapLibre); `app/src/api/types.ts` is the API contract |
| `docs/ARCHITECTURE.md` | How the pieces fit, crate APIs, product rules |
| `docs/ui-research/` | UI studies of SBB Mobile, Google Maps and Transit, and a copy review |
| `scripts/` | Data download, dev helpers |

## Running it

Needs Rust (nightly or recent stable), Node 22+, about 6 GB of disk and 4 GB
of RAM. No data is in the repository; the first run downloads about 900 MB.

```sh
cd kante
./run.sh            # download data, build caches, build engine + app, serve on :8080
```

Step by step:

```sh
scripts/fetch-data.sh        # GTFS, atlas registry, OSM Switzerland → data/raw
./run.sh build               # data/raw → data/built (a few seconds per step)
./run.sh app                 # build the web app → app/dist
./run.sh serve               # http://localhost:8080  (app at /, debug page at /playground/)
```

Try a plan from the command line (the server must be running):

```sh
scripts/plan.py "Zürich HB" "Ostermundigen, Rüti" 2026-11-23T08:00 steps=1
scripts/plan.py "Zürich HB" "Ostermundigen, Rüti" 2026-11-23T08:00 steps=1 stairs=never wheelchair=1 speed=0.9
```

**Live data** needs a free personal API key from
[opentransportdata.swiss](https://api-manager.opentransportdata.swiss/) for the
SIRI-ET API. Put it in the environment variable `KANTE_OTD_KEY`, or in
`data/secrets/otd.json` as `{"siri-et": "…"}`. Without a key the engine runs on
the timetable alone. `data/` is git-ignored; never commit keys.

**On a phone:** geolocation and the service worker need HTTPS.
`./run.sh phone` exposes the running server to your tailnet with
`tailscale serve`. Without HTTPS, long-press the map in the app to simulate a
location.

Web app development: `cd app && npm install && npm run dev` (proxies `/api` to
the engine on :8080), or `npm run dev:mock` to work without the engine.

## Data sources

- Timetable, stop registry (atlas), real time: [opentransportdata.swiss](https://opentransportdata.swiss) — cite as the source when publishing results.
- Walking network, addresses, places: © OpenStreetMap contributors, ODbL.
- Base map: © swisstopo vector tiles.

The timetable in use is the 2026 feed (valid to 12 December 2026); from
13 December switch the dataset in `scripts/fetch-data.sh` to the 2027 feed.

## Measured on the build machine (32 cores)

- Data build: timetable import about 4 s, walking graph about 5 s, stop
  linking about 1 s, search index about 3 s.
- Engine start: under 2 s. Memory: a few GB.
- Journey plan: 30–130 ms under load; search about 0.05 ms median; a walking
  route across a station about 0.1 ms.
- 35,547 stations, 69,502 boarding points, 2.7 million trips, 3.7 million
  walking-graph edges, 2.2 million addresses.

## Known problems

- **Step-free gaps where OpenStreetMap lacks lifts or ramps**: Zürich HB
  platforms 31–34 have no step-free route; platform islands at Olten, Baden,
  Wil, St. Moritz and Lausanne-Flon are cut off for step-free walkers.
- **Some in-station walks are wrong**: e.g. Arth-Goldau platform 4 → 5 is drawn
  as 434 m. Change *times* there follow the official minimum, the drawn path
  does not.
- **Official change times**: only the stop-pair ones are used; the feed's
  713,140 trip-specific ones are not imported yet.
- **Vehicle positions are estimates** interpolated between stops along straight
  lines. There is no open national GPS feed.
- **With live delays** a result is always feasible but occasionally not the
  fastest.
- Roads without a mapped pavement are walked along the centre line.
- Liechtenstein and foreign stops have no walking network.
- English only. Not yet tested on real phones beyond a quick look.

## Third-party material

The UI studies in `docs/ui-research/` describe other companies' apps. The
screenshots they were written from are not in the repository; each study's
`sources.md` lists where they came from. Kante uses its own name, colours and
icons.
