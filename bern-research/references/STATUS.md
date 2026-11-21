# references/ STATUS (Bern Station Reference Collection)

Updated 03:00 Europe/Zurich, 2026-11-21, after the lead review of 02:55. **READY for the lead to validate and commit.**
`validation/report.md`: **OK, 0 errors, 0 warnings.** Details are in HANDOFF.md, section "Changes after the lead review".

## Lead review items (02:55): done
1. **Search false positives.** Rule: a station link whose only source is `relation: search` stays only if a Commons station
   category (hand-mapped seeds and their subcategories, or the station's Wikidata P373; not the city-wide "Tram stops in Bern")
   or precise coordinates within 400 m place the file at the station.
   - Stored items with a search-only link: **5 reviewed, 0 confirmed, 5 removed** from `images/` and set to `stored: false`
     with `not_stored_reason`. They are the memorial plaque `commons:146611998`, 2 climate-demo photos,
     "Wankdorf Bahnhof nördliches Gebiet 07" and "Tram Tramlink Bern Roof".
   - Linked-only records: **162 flagged `relevance_unverified: true`**, with the reason in `relevance_check`.
2. **"Attribution" licences.** All 9 used `{{Kurt Rasmussen permission}}`, a permission template with no licence URL.
   **All 9 were removed** from the stored subset. New rule: a Commons file is stored only if Commons provides a `LicenseUrl`.
   **0 stored files lack `licence_url`.**
3. **`SOURCES.json`.** All 9 entries now have `bytes` and `sha256`; the transit inputs are split per file.
   In `data/stations.json`, 8571420 "Oberscherli, Scherliau" (Köniz) is kept with `in_transit_coverage: false` and a `coverage_note`:
   whole adjoining municipalities are included here, transit/ has a 5 km ring, and no reference points at it.
   The validator now enforces all three rules.

## Counts
- 2,450 references. 172 stored files, 55.9 MiB: 122 Commons, 22 Panoramax, 16 orthophotos, 12 glTF assets.
- 41 stations have stored files; 90 have any reference. 1,638 viewpoints are in `references.geojson`.

## Blocked
- Mapillary (token needed), KartaView (API unresponsive). Both are recorded as links. No new harvesting was done for this review.

## Ready for the lead to commit (cleaned paths)
- `bern-research/references/` except `.cache/` (ignored by `references/.gitignore`): `.gitignore`, `STATUS.md`, `HANDOFF.md`,
  `ATTRIBUTION.md`, `SOURCES.json`, `manifest.json`, `references.geojson`, `by_station.json`, `browse.html`, `data/`,
  `images/`, `orthophoto/`, `assets/`, `tools/`, `validation/`. 248 files, about 65 MB, no file above 5 MB.
- Removed since your last look (not on disk any more, never committed): 13 image files, 5 search false positives
  (listed above) and 8 Rasmussen-permission files (`commons:50104748, 50104767, 46058516, 50104762, 50104749, 30246582,
  46058522, 30671211`). The 9th, `commons:41464297`, had already dropped out of the stored set. All 13 remain in
  `manifest.json` as linked records with a `not_stored_reason`.
