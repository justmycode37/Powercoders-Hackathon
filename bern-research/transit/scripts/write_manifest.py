#!/usr/bin/env python3
"""Write the provenance manifests.

Usage:  python scripts/write_manifest.py

  SOURCES.json        every input: name, url, publisher, licence, retrieved, bytes, sha256, used_for
                      (collected from the per-download .cache/<name>/source.json files)
  data/MANIFEST.json  every output file: path, bytes, sha256, records, built_by, sources
"""
from __future__ import annotations

import hashlib
import json
import sys

from common import CACHE, DATA, ROOT, SOURCES, TIMEZONE

GTFS_26 = ["gtfs_fp2026"]
GTFS_27 = ["gtfs_fp2027"]
ATLAS = ["atlas_service_point", "atlas_service_point_years", "atlas_traffic_point", "atlas_traffic_point_years"]

OUTPUTS = [
    # path, description, built_by, sources, how to count records
    ("stations.geojson", "Stations (atlas service points / DiDok) in coverage, tiers bern / ring / connected", "build_stops.py", ATLAS + GTFS_26 + GTFS_27 + ["boundary_bern"], "features"),
    ("edges.geojson", "Boarding edges (kerbs, platforms) and boarding areas of those stations", "build_stops.py", ATLAS + GTFS_26 + GTFS_27, "features"),
    ("edge_lookup.json", "number -> designation -> edge SLOID(s)", "build_stops.py", ATLAS + GTFS_26 + GTFS_27, "stations"),
    ("gtfs_stop_map_fp2026.json", "GTFS stop_id -> edge / station SLOID with stop_times shares, timetable 2026", "build_stops.py", ATLAS + GTFS_26, "stops"),
    ("gtfs_stop_map_fp2027.json", "GTFS stop_id -> edge / station SLOID with stop_times shares, timetable 2027", "build_stops.py", ATLAS + GTFS_27, "stops"),
    ("coverage_stops.json", "Coverage logic and counts for stations and edges", "build_stops.py", ATLAS + ["boundary_bern"], None),
    ("accessibility_edges.json", "Accessibility per boarding edge (atlas platform-v2, BfR wheelchair classes)", "build_accessibility.py", ["atlas_prm_platform", "bfr_wheelchair"], "edges"),
    ("accessibility_stations.json", "Accessibility per station (atlas stop-point, reference points, toilets, parking, contact points, relations)", "build_accessibility.py",
     ["atlas_prm_stop_point", "atlas_prm_reference_point", "atlas_prm_toilet", "atlas_prm_parking_lot", "atlas_prm_contact_point", "atlas_prm_relation", "bfr_wheelchair"], "stations"),
    ("sectors.geojson", "Platform sectors with atlas coordinates", "build_accessibility.py", ["atlas_sectors"], "features"),
    ("coverage_accessibility.json", "Counts for the accessibility outputs", "build_accessibility.py", [], None),
]
for feed, src in (("fp2026", GTFS_26), ("fp2027", GTFS_27)):
    OUTPUTS += [
        (f"{feed}/gtfs_bern_{feed}.zip", "Lossless GTFS subset: every trip serving Bern, source rows verbatim", "extract_gtfs.py + build_timetable.py", src + ATLAS[:2] + ["boundary_bern"], None),
        (f"{feed}/timetable.json", "Compact pattern-encoded timetable (decodes to the exact stop_times of the subset)", "build_timetable.py", src, "meta.counts.trips"),
        (f"{feed}/edge_directions.json", "Derived: lines and next stops per stop / edge in tiers bern and ring", "build_timetable.py", src, "stops"),
        (f"{feed}/segments.geojson", "Derived: every stop-to-stop hop with lines, trip-days and run time", "build_timetable.py", src, "features"),
        (f"{feed}/lines.geojson", "Derived: representative stop sequence per line and direction", "build_timetable.py", src, "features"),
        (f"{feed}/transfers.json", "Minimum transfer times and in-seat transfers (Bern area)", "build_timetable.py", src, "rows"),
        (f"{feed}/timetable_stats.json", "Record counts of the timetable build", "build_timetable.py", src, None),
    ]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count(path, how):
    if not how or path.suffix == ".zip":
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    for part in how.split("."):
        doc = doc[part]
    return doc if isinstance(doc, int) else len(doc)


def main() -> int:
    sources = []
    for name in SOURCES:
        meta_path = CACHE / name / "source.json"
        if not meta_path.exists():
            print(f"missing {meta_path}: run fetch_sources.py", file=sys.stderr)
            return 1
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        sources.append({
            "name": name,
            "title": SOURCES[name]["title"],
            "url": m["request_url"],
            "landing_page": m["landing_page"],
            "publisher": SOURCES[name]["publisher"],
            "licence": SOURCES[name]["licence"],
            "retrieved": m["fetched_at_utc"],
            "source_last_modified": m["http_last_modified"],
            "file": m["resolved_file"],
            "bytes": m["bytes"],
            "sha256": m["sha256"],
            "used_for": SOURCES[name]["used_for"],
            "cache_path": m["local_file"],
        })
    (ROOT / "SOURCES.json").write_text(json.dumps({
        "folder": "bern-research/transit",
        "note": "Inputs of every file under data/. Raw downloads are kept in the git-ignored .cache/ folder; "
                "scripts/fetch_sources.py downloads them again and records the same fields in .cache/<name>/source.json. "
                "No source needs a login or key. atlas files are republished every night under a new resource id, so "
                "`url` is the link that was valid at `retrieved`; fetch_sources.py looks the current link up on "
                "`landing_page` by file name.",
        "attribution": "Source: opentransportdata.swiss (timetable and atlas master data); Federal Office of Topography swisstopo (municipal boundary).",
        "not_used": [{
            "name": "gtfs_rt",
            "title": "GTFS Realtime trip updates",
            "url": "https://api.opentransportdata.swiss/la/gtfs-rt",
            "publisher": "Business office SKI",
            "status": "blocked: needs a personal API key (Bearer token) from https://api-manager.opentransportdata.swiss/; no key is configured on this machine",
        }],
        "sources": sources,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    outputs = []
    for rel, desc, built_by, srcs, how in OUTPUTS:
        path = DATA / rel
        if not path.exists():
            print(f"missing output {rel}", file=sys.stderr)
            continue
        size = path.stat().st_size
        outputs.append({"path": f"data/{rel}", "description": desc, "bytes": size, "sha256": sha256(path),
                        "records": count(path, how), "built_by": f"scripts/{built_by}", "sources": srcs,
                        "commit": size <= 25 * 1024 * 1024})
    (DATA / "MANIFEST.json").write_text(json.dumps({
        "folder": "bern-research/transit/data",
        "timezone": TIMEZONE,
        "rebuild": "python scripts/run_all.py",
        "outputs": outputs,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(o["bytes"] for o in outputs)
    print(f"SOURCES.json: {len(sources)} sources; data/MANIFEST.json: {len(outputs)} outputs, {total / 1e6:.1f} MB, "
          f"largest {max(outputs, key=lambda o: o['bytes'])['path']} {max(o['bytes'] for o in outputs) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
