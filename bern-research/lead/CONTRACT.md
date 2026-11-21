# Bern research: lead contract

Branch `bern-transit-3d` (local, from `origin/main` @ `a4cc40f`). Freeze **06:15**, handoff **07:00 Europe/Zurich,
Saturday 2026-11-21**. The deliverable is **data that is usable and sourced**: breadth, quality, stable identifiers,
schemas, provenance, licensing, reproducible acquisition, validation and coverage. It is not an app. A viewer is
only ever a thin sample loader that proves the outputs load.

## Who owns what

| Folder | Owner thread | Content |
|---|---|---|
| `bern-research/transit/` | Bern Transit GTFS and DiDok Data | Stops, boarding edges, timetable, calendars |
| `bern-research/city3d/` | Bern 3D City Basemap Data and Scene | Terrain, buildings, bridges, paths; thin 3D scene |
| `bern-research/stations/` | Bern Station Geometry and 3D Models | Station geometry by level, entrances, platforms, sectors |
| `bern-research/references/` | Bern Station Reference Collection | Licensed photos, operator plans, manifest |
| `bern-research/lead/` | Lead (orchestrator thread) | This contract, source list, validation, sample loader, handoff |

All threads share one working tree. Write only inside your folder. The team app at the repo root (`index.html`,
`events.js`, `README.md`, `.gitignore`) and the earlier demo in `..\Hackathon\rightside` are not to be touched.

## Commits

The lead is the only committer. Workers never run `git add`, `git commit`, `git stash`, `git checkout` or anything
else that changes the index or the tree outside their folder. The lead stages explicit paths after validating them,
under ktr0a's verified GitHub identity, with no co-author or tool attribution, and never pushes.

## Conventions the lead validates against

1. **Identifiers.** Stations: atlas `sloid` (`ch:1:sloid:7110`) and `number` (`8507110`, the id used by
   `transport.opendata.ch` and SBB). Boarding edges: atlas edge `sloid` (`ch:1:sloid:7110:0:17`) plus `designation`
   (public letter or track) and `designationOperational`. GTFS ids are kept verbatim next to them. Anything that
   refers to a stop or an edge in any folder carries the SLOID when one exists, so the folders join without
   guessing.
2. **Geometry.** GeoJSON, WGS84 (EPSG:4326), lon/lat, 7 decimals. Keep LV95 (EPSG:2056) values as properties when
   the source has them. Heights in metres, LN02, and say so. 3D assets state their origin, axes and units.
3. **Time.** `Europe/Zurich`. Times after midnight stay above `24:00:00` as in GTFS. Service days are explicit dates.
4. **Honesty flags on every feature or record:** `source` (dataset name) and `inferred` (`true` if geometry or an
   attribute was derived, matched by proximity, estimated or drawn), with `inferred_how`. Approximate dimensions are
   labelled as approximate at the feature, not only in prose.
5. **Provenance.** Each folder has a machine-readable manifest of its inputs (`SOURCES.json`, or the per-download
   `source.json` files plus an index): `name`, `url`, `publisher`, `licence`, `retrieved`, `bytes`, `sha256`,
   `used_for`. Scripts in the folder rebuild every output from those downloads; the command is written down.
6. **Licensing.** Record the licence actually stated by the publisher for each input. Do not put files with
   unclear redistribution rights in the tree: link them. OSM-derived files are ODbL and say so.
7. **Size.** Raw downloads live in a git-ignored cache folder (`.cache/`). Derived files above 25 MB are not
   committed: list them in `STATUS.md` with the rebuild command. Prefer one compact file over thousands of tiny ones
   where it does not hurt use; tile pyramids are fine when bounded.
8. **`STATUS.md` at the folder root**, kept current: what is done and where, what is in progress, what is blocked,
   record counts, and which paths are ready for the lead to validate and commit. The lead reads this file instead
   of interrupting. By **06:15** add `HANDOFF.md`: outputs and schemas, coverage numbers, what is approximate or
   missing, how to rebuild, how to load.
9. **Credentials.** No keys or tokens in files. A source that needs a login or key is recorded as blocked and
   skipped.

## Cross-folder joins the lead will test

- every edge has a parent station, and both are inside the stated coverage area;
- every timetable stop resolves to an edge SLOID or a station SLOID, with the share of each reported;
- station geometry features that belong to an edge carry that edge's SLOID and lie within a stated distance of it;
- city3d terrain heights agree with atlas edge heights within a stated tolerance, and outliers are listed;
- reference images point at a station `number` or SLOID and have licence and attribution filled in.

## Lead outputs

- `lead/SOURCES.md`: source list checked by the lead on 2026-11-21.
- `lead/validate/`: validation script and its last report.
- `lead/sample/`: thin sample loader (one page, overlays on the existing swisstopo map style).
- `bern-research/README.md`: the morning handoff (coverage, what is approximate, tests, how to run).
