# references/ HANDOFF (Bern Station Reference Collection)

Owner: thread "Bern Station Reference Collection". Branch `bern-transit-3d`. Written for the lead and the station-model
session. Counts are filled in from `validation/report.json`. Re-run `tools/09_validate.py` to refresh them.

## What this folder gives you

| Path | What | Licence |
|---|---|---|
| `manifest.json` | **The product.** One list of every reference: Commons photos, Panoramax street-level photos, orthophoto crops, operator plans and links, parametric assets. Common schema below. | per record |
| `references.geojson` | Camera positions (Point, WGS84, 7 decimals) of every photo that has one, with `heading_deg`, `field_of_view_deg`, `station_number`/`station_sloid`, `edges_in_view` (edge SLOIDs). | per feature |
| `by_station.json` | atlas `number` → `sloid`, name, counts per kind, ids of stored and linked references. | n/a |
| `images/<number>/` | Downloaded licensed subset, scaled derivatives (Commons 1280 px for the 5 focus stations, 960 px elsewhere; Panoramax SD 2048 px). | CC BY / CC BY-SA / CC0 / PD per file |
| `orthophoto/` | swisstopo SWISSIMAGE crops of 16 hubs, LV95, `.jgw` world file and `.json` sidecar each. | swisstopo OGD, "© swisstopo" |
| `assets/` | 10 original parametric glTF 2.0 assets with sidecars (evidence, units, axes, origin). **All approximate.** Khronos glTF validator: 0 errors, 0 warnings. | CC0 |
| `ATTRIBUTION.md` | Credit line for every stored file. | n/a |
| `SOURCES.json` | Input provenance (name, url, publisher, licence, retrieved, bytes, sha256, used_for). | n/a |
| `data/*.json` | Intermediate, reproducible inputs: stations, Commons candidates, Panoramax items, operator links, Wikidata join, orthophoto and asset indexes, photo records. | n/a |
| `validation/report.{json,md}` | Contract checks. | n/a |

## Record schema (`manifest.json` → `references[]`)

Core fields, present on every record:

- `id`: stable id. `commons:<pageid>`, `panoramax:<uuid>`, `ortho-<number>_<slug>`, `link:<slug>` or `asset:<slug>`.
- `kind`: `photo` | `streetlevel_photo` | `orthophoto` | `station_plan_pdf` | `interactive_plan` | `kerb_plan_pdf` |
  `network_map_pdf` | `design_standard_pdf` | `planning_pdf` | `project_magazine_pdf` | `open_dataset` |
  `imagery_service` | `historic_photo` | `web_page` | `index_page` | `parametric_asset`.
- `title`, `source`, `source_page_url`, `original_url`, `author`, `licence`, `licence_url`.
- `stations[]`: `{number, sloid, name, relation, distance_m}`, primary first. `relation` is `category`
  (hand-mapped Commons category), `geosearch` (GeoData distance), `panoramax-radius`, `crop centre`, `covers` or `models`.
- `stored` (bool), `file` (path relative to `references/`), `download` `{file, derivative_url, bytes, sha256, scaled, retrieved}`.
- `redistributable`, `redistributable_why`.
- `feature_tags[]` and `feature_tags_inferred`: platform, concourse, entrance, canopy, tram_stop, shelter,
  stairs_lift, signage, clock, ticket_machine, bench, facade, square, aerial, vehicle, construction, night, map_plan,
  artwork, street_level, orthophoto.
- `model_use`: what this reference can tell a 3D modeller.
- `viewpoint`: `{camera {lat, lon, source}, heading_deg, heading_source, field_of_view_deg, setting}`.
- `edges_in_view[]`: `{edge_sloid, designation, station_number, distance_m, bearing_offset_deg}`. These are inferred:
  atlas edges within 45 m of the camera and inside the field of view.
- `edge_designations[]`: a track or edge letter named in the title or description, resolved to edge SLOIDs through
  `transit/data/edge_lookup.json`.
- `capture_date` (ISO date or year), `capture_date_source`.
- `inferred`, `inferred_how`. Contract rule 4.

## How to load

```python
import json
m = json.load(open("bern-research/references/manifest.json", encoding="utf-8"))
zyt = [r for r in m["references"] if any(s["number"] == 8507110 for s in r["stations"])]
stored = [r for r in zyt if r["stored"]]          # files you can ship
plans  = [r for r in zyt if r["kind"].endswith("_pdf")]   # links only
```

For the station-model session: per station, open `by_station.json[number].stored`. Use the orthophoto (`.jgw`,
EPSG:2056) for footprints. Use Panoramax and Commons photos that have `heading_deg` for camera matching, and the
Trafimage / BERNMOBIL plans (link only) for levels and edge letters.

## Rebuild

Python 3.11, standard library only. Run from `bern-research/references/`. HTTP answers are cached in `.cache/` (git-ignored).

```
python -I -X utf8 tools/01_stations.py          # atlas stop points (data.sbb.ch)
python -I -X utf8 tools/01b_wikidata.py         # Wikidata join (P954)
python -I -X utf8 tools/02_harvest_commons.py   # Commons categories + geosearch + imageinfo (slow: API rate limit)
python -I -X utf8 tools/03_harvest_panoramax.py # Panoramax STAC search
python -I -X utf8 tools/04_operator_links.py    # link register + live URL checks
python -I -X utf8 tools/05_orthophotos.py       # SWISSIMAGE crops
python -I -X utf8 tools/06_select_download.py   # licence filter, scoring, download subset (reads ../transit/data read-only)
python -I -X utf8 tools/07_assets.py            # parametric glTF assets (reads data/orthophotos.json)
python -I -X utf8 tools/08_build_manifest.py    # manifest, geojson, by_station, ATTRIBUTION, SOURCES
python -I -X utf8 tools/09_validate.py          # contract checks -> validation/report.*
python -I -X utf8 tools/10_browse_page.py       # browse.html (static, no scripts)
```

## Coverage (validation run 2026-11-21 after the lead review of 02:55, `validation/report.md`)

- **2,450 references**: 2,143 Commons photos (1,850 storable: open licence *with* a licence URL; 1,405 with a camera position),
  233 Panoramax photos (all CC BY-SA 4.0, all with position and compass heading), 16 orthophoto crops, 46 operator and
  open-data links (all URLs checked live on 2026-11-21), and 12 parametric assets.
- Commons candidates come from 30 hand-mapped categories, GeoData geosearch around every rail and tram stop, and 13
  targeted full-text searches. **Search hits are link-only unless confirmed**: a station link whose only source is
  `relation: search` counts as confirmed only when one of the file's Commons categories is a station category (the
  hand-mapped seeds and their subcategories, or the station's Wikidata P373 category; the city-wide "Tram stops in Bern"
  does not count) or its coordinates (at least 4 decimals) lie within 400 m of the station point. Result: 0 confirmed and
  **162 flagged `relevance_unverified: true`** with the reason in `relevance_check` and `not_stored_reason`.
- **172 stored files, 55.9 MiB** (contract limit 60 MB, largest file well under 5 MB): 122 Commons photos, 22 Panoramax
  photos, 16 orthophotos and 12 glTF assets. Licences of stored photos: CC BY-SA 4.0 (102, of which 22 Panoramax),
  CC BY-SA 3.0 / 3.0 ch / 2.0 (20), CC0 (13), CC BY 4.0 / 3.0 / 2.0 (9). Every stored file has a `licence_url`.
- **90 stations** have at least one reference and **41** have stored files. Focus stations (stored; linked):
  Bern 8507000 (52; 815 Commons and 25 Panoramax photos, 3 SBB plans, 6 planning PDFs, 2 RBS magazines);
  Bern, Bahnhof 8576646 (32; 277 Commons and 10 Panoramax, BERNMOBIL Kantenplan); Bern, Zytglogge 8507110 (12; 444 Commons, Kantenplan K);
  Bern Wankdorf 8516161 (8; 32 Commons, 34 Panoramax, SBB plan, BERNMOBIL Kantenplan);
  Bern, Wankdorf Center 8588699 (1, the orthophoto; only 10 off-topic Commons files exist nearby. This is a real gap).
- Camera pose: 38 stored photos have a compass heading. 27 stored photos list the atlas edges in view, e.g. Bern track 21/22
  and Bahnhof edge I. 1,638 viewpoints are in `references.geojson`.
- Stored capture years: 2000s 17, 2010s 70, 2020s 35. Photos from before 1990 are never stored (historic state).
- Every stored Commons photo has at least one feature tag. Untagged photos are linked, never stored. Each record that is
  not stored carries a `not_stored_reason`.
- `by_station.json` gives each station its Wikidata QID and Commons category (62 stations joined on P954). Its
  `by_feature` lists the reference ids per feature tag.

## Changes after the lead review (02:55)

1. Search false positives: 5 stored search hits were removed from `images/`, now `stored: false`: the Holocaust memorial
   plaque `commons:146611998` ("Welle 7" is a building name), 2 climate-protest photos, "Wankdorf Bahnhof nördliches
   Gebiet 07" and "Tram Tramlink Bern Roof" (no station category, no precise coordinates). All 162 search-only links are
   flagged `relevance_unverified: true`. The selection rule and `tools/09_validate.py` now enforce this.
2. "Attribution" licences: the 9 stored files tagged "Attribution" all use the Commons permission template
   `{{Kurt Rasmussen permission}}` (https://commons.wikimedia.org/wiki/Template:Kurt_Rasmussen_permission), not an open
   licence with a URL, and they have 2-decimal coordinates. They were removed from the stored subset. Rule: a Commons file is
   stored only if Commons gives a `LicenseUrl`. This also makes "Public domain" files without a URL link-only (1,850 of
   2,143 storable). Freed slots were refilled by the next best-scored files, keeping the per-station caps.
3. `SOURCES.json`: the transit inputs are now three entries with bytes and sha256 each (`edge_lookup.json`,
   `edges.geojson`, `stations.geojson`). `data/stations.json` now carries `in_transit_coverage`. The only station outside
   transit coverage is 8571420 "Oberscherli, Scherliau" (Köniz). It is kept with a `coverage_note`: this folder includes all
   stop points of the four adjoining municipalities, transit/ only those within 5 km of the Bern boundary or on a trip
   serving Bern, and no reference points at it. The validator checks both.

## Approximate, missing, caveats

- **Feature tags are keyword-inferred** (`feature_tags_inferred: true`). Check visually before relying on a tag. Station links
  from GeoData distance (`relation: geosearch`) can point to the nearest stop rather than the one shown. `camera_to_station_m`
  is on every photo record, so you can filter (4 stored photos are more than 400 m from the station point; Bern station itself spans about 400 m).
- **`edges_in_view` is inferred** from the camera position, heading and an assumed field of view (65 degrees for Commons,
  EXIF value for Panoramax) against atlas edge points within 45 m. It says the edge is probably in frame, not certainly.
- Commons camera positions come from `{{Location}}`. When only an object location exists, the record says so in
  `viewpoint.camera.source`.
- **Every parametric asset is approximate** (`approximate: true` in the sidecar and in the glTF node extras). Evidence is
  cited per asset, mostly Commons ids and SBB datasets. The station clock is deliberately generic (the SBB clock design is
  protected). The Baldachin is a flat slab at an estimated 9 m: its outline was hand-traced from SWISSIMAGE (about 1.5 m error),
  its four column positions are guessed, and the real roof is doubly curved. Its LV95 anchor and footprint are in the sidecar.
- Operator plans (SBB Trafimage, BERNMOBIL Kantenpläne, Libero network map, City of Bern standards and planning PDFs,
  RBS magazines, ARE fact sheet) are **links only**: no open licence. sbb.ch answers only browser user agents (403 otherwise).
- Not harvested: **Mapillary** (API token needed, contract rule 9) and **KartaView** (API did not answer). Also not harvested:
  Commons geosearch around bus-only stops (60 m radius returned mostly old-town facades; skipped because of API rate limits),
  and Commons originals narrower than 960 px (upload.wikimedia.org answered 429 to this client; 2 selected files skipped).
- SWISSIMAGE capture year is not recorded per crop; look it up in the swisstopo metadata layer.
- The licence for `mobiliar-im-bahnhof` is not stated, so it is used only for per-station counts (evidence) and nothing is copied.
- The removed seed "Category:New Bern station" (New Bern, North Carolina) is filtered out in `06_select_download.py`.

## Paths ready to commit

`bern-research/references/` except `.cache/` (git-ignored by `references/.gitignore`): `.gitignore`, the docs
(`HANDOFF.md`, `STATUS.md`, `ATTRIBUTION.md`), `manifest.json`, `references.geojson`, `by_station.json`, `SOURCES.json`,
`browse.html`, `data/`, `images/`, `orthophoto/`, `assets/`, `tools/`, `validation/`. About 65 MB and 248 files in total, of which 55.9 MiB is stored media.
