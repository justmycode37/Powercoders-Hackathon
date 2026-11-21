# Bern research: morning handoff

**Status: in progress.** Last updated 2026-11-21 01:51 Europe/Zurich by the lead. This file is rewritten at each
committed snapshot and is final at 07:00. Until then, treat every number below as provisional.

- Checkout: `C:\Users\apfel\Documents\Coding\Powercoders-Hackathon`
- Branch: `bern-transit-3d` (local only, from `origin/main` @ `a4cc40f`; nothing pushed, no PR)
- Team files at the repo root and the earlier demo in `C:\Users\apfel\Documents\Coding\Hackathon\rightside` are untouched.

## Snapshots committed so far

| Commit | Time | Content |
|---|---|---|
| `d9c0739` | 01:43 | Lead contract (`lead/CONTRACT.md`) and source list (`lead/SOURCES.md`) |
| `c8fa6cf` | 01:44 | Validation script (`lead/validate/validate.py`), byte-exact storage rule |

No worker data is committed yet. All four worker threads are running and writing under their own folder.

## Folders

| Folder | Owner | State at 01:50 |
|---|---|---|
| `transit/` | Bern Transit GTFS and DiDok Data | Running. Stop registers and the 2026 and 2027 GTFS feeds are cached; outputs not yet marked ready. |
| `city3d/` | Bern 3D City Basemap Data and Scene | Running. Terrain tile pyramid in progress; no status file yet. |
| `stations/` | Bern Station Geometry and 3D Models | Running. |
| `references/` | Bern Station Reference Collection | Running. Station list built (359 stop points); image harvest in progress. |
| `lead/` | Lead | Contract, source list, validator done. Join checks and thin sample loader follow once file names are published. |

## Still to be filled in

1. Coverage: stations, boarding edges, timetable days, terrain and building extent, station geometry, references.
2. What is official, what is inferred or approximate, and what is missing.
3. Validation: last report, cross-folder join results, findings from the 03:00 and 05:00 data reviews.
4. How to rebuild each folder from the official downloads.
5. How to run the thin sample loader.
6. Licences and attribution lines.
