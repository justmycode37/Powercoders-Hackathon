#!/usr/bin/env python3
"""Stage B3: accessibility attributes and platform sectors, joined on the edge / station SLOID.

Usage:  python scripts/build_accessibility.py      (after build_stops.py)

Writes  data/accessibility_edges.json      per boarding edge: atlas platform-v2 + BfR wheelchair classification
        data/accessibility_stations.json   per station: atlas stop-point-v2, reference points, toilets, parking,
                                           contact points, relations (step-free / tactile links), BfR station row
        data/sectors.geojson               platform sectors (A, B, C ...) with their atlas coordinates
Only stations and edges that are in data/stations.geojson / data/edges.geojson are kept, all tiers.
Values are copied as published (atlas enumerations such as YES / NO / TO_BE_COMPLETED / NOT_APPLICABLE);
empty source cells are left out.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import sys

from common import DATA, read_atlas

SKIP = {"creationDate", "status"}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def clean(row: dict, drop=()) -> dict:
    out = {}
    for k, v in row.items():
        if k in SKIP or k in drop or v == "":
            continue
        if v in ("true", "false"):
            v = v == "true"
        elif re.fullmatch(r"-?\d+\.\d+", v):
            v = float(v)
        elif "|" in v and k in ("infoOpportunities", "meansOfTransport"):
            v = v.split("|")
        out[snake(k)] = v
    return out


def swiss_date(s: str) -> str:
    d, m, y = s.split(".")
    return f"{y}-{m}-{d}"


def main() -> int:
    edges = {f["properties"]["sloid"]: f["properties"] for f in json.loads((DATA / "edges.geojson").read_text(encoding="utf-8"))["features"]}
    stations = {f["properties"]["sloid"]: f["properties"] for f in json.loads((DATA / "stations.geojson").read_text(encoding="utf-8"))["features"] if f["properties"]["sloid"]}
    today = dt.date.today().isoformat()

    # ---- BfR wheelchair classification (rows carry validity windows; keep all, mark the one valid today) ----
    flags = ["Autonomie", "Rampeneinsatz", "Voranmeldung", "Ersatztransport", "keinZugang", "keineInfo"]
    bfr_edge, bfr_station = collections.defaultdict(list), collections.defaultdict(list)
    for r in read_atlas("bfr_wheelchair"):
        sl = r["sloid"]
        target = bfr_edge if sl in edges else bfr_station if sl in stations else None
        if target is None:
            continue
        vf, vt = swiss_date(r["gültigVon"]), swiss_date(r["gültigBis"])
        target[sl].append({
            "sg": [f for f in flags if r[f"sg_{f}"] == "1"],
            "ug": [f for f in flags if r[f"ug_{f}"] == "1"],
            "valid_from": vf, "valid_to": vt, "valid_today": vf <= today <= vt,
        })

    # ---- per edge ----
    prm_edge = {r["sloid"]: r for r in read_atlas("atlas_prm_platform") if r["sloid"] in edges}
    edge_out = {}
    for sl in sorted(set(prm_edge) | set(bfr_edge)):
        e = edges[sl]
        rec = {"station_sloid": e["station_sloid"], "station_number": e["station_number"], "designation": e["designation"],
               "designation_operational": e["designation_operational"], "tier": e["tier"]}
        if sl in prm_edge:
            rec["atlas_platform"] = clean(prm_edge[sl], drop=("sloid", "parentSloidServicePoint", "parentNumberServicePoint"))
        if sl in bfr_edge:
            rec["bfr_wheelchair"] = sorted(bfr_edge[sl], key=lambda x: x["valid_from"])
        edge_out[sl] = rec

    # ---- per station ----
    st_out = collections.defaultdict(dict)
    for r in read_atlas("atlas_prm_stop_point"):
        if r["sloid"] in stations:
            st_out[r["sloid"]]["atlas_stop_point"] = clean(r, drop=("sloid", "number"))
    for source, key in (("atlas_prm_reference_point", "reference_points"), ("atlas_prm_toilet", "toilets"),
                        ("atlas_prm_parking_lot", "parking_lots"), ("atlas_prm_contact_point", "contact_points")):
        for r in read_atlas(source):
            if r["parentSloidServicePoint"] in stations:
                st_out[r["parentSloidServicePoint"]].setdefault(key, []).append(clean(r, drop=("parentSloidServicePoint", "parentNumberServicePoint")))
    n_rel = 0
    for r in read_atlas("atlas_prm_relation"):
        if r["parentSloidServicePoint"] in stations:
            st_out[r["parentSloidServicePoint"]].setdefault("relations", []).append(clean(r, drop=("parentSloidServicePoint", "parentNumberServicePoint")))
            n_rel += 1
    for sl, rows_ in bfr_station.items():
        st_out[sl]["bfr_wheelchair"] = sorted(rows_, key=lambda x: x["valid_from"])
    station_out = {}
    for sl in sorted(st_out):
        s = stations[sl]
        station_out[sl] = {"number": s["number"], "name": s["name"], "tier": s["tier"], **st_out[sl]}

    bfr_note = ("BfR_Haltestellendaten flags as published. Each row gives the wheelchair boarding class for the period "
                "valid_from..valid_to: Autonomie (independent boarding), Rampeneinsatz (ramp operated by staff), "
                "Voranmeldung (advance notice needed), Ersatztransport (replacement shuttle), keinZugang (no access), "
                "keineInfo (no information). The prefixes sg / ug are the publisher's column prefixes; in the data they "
                "line up with track-bound vehicles (train, tram) and vehicles that are not track-bound (bus). That reading "
                "is ours and is not stated on the dataset page.")
    (DATA / "accessibility_edges.json").write_text(json.dumps({
        "description": "Accessibility per boarding edge, keyed by edge SLOID (join with edges.geojson). "
                       "atlas_platform = atlas platform-v2 row, field names in snake_case, enumerations as published, "
                       "lengths and heights in centimetres as in atlas. bfr_wheelchair = " + bfr_note,
        "source": "atlas platform-v2 (actual-date-platform.csv); BfR_Haltestellendaten.csv (bfr-rollstuhl)",
        "inferred": False,
        "retrieved": today,
        "edges": edge_out,
    }, ensure_ascii=False, separators=(",", ":")).replace('},"ch:1:sloid:', '},\n"ch:1:sloid:') + "\n", encoding="utf-8")
    (DATA / "accessibility_stations.json").write_text(json.dumps({
        "description": "Accessibility per station, keyed by station SLOID (join with stations.geojson). atlas_stop_point = atlas "
                       "stop-point-v2 row; reference_points, toilets, parking_lots, contact_points = atlas rows of the station; "
                       "relations = step-free access, tactile marks and contrasting areas between a reference point and an element "
                       "(element_sloid is an edge, toilet, parking lot or contact point). bfr_wheelchair = " + bfr_note,
        "source": "atlas stop-point-v2, reference-point-v2, toilet-v2, parking-lot-v2, contact-point-v2, relation-v2 (actual-date files); BfR_Haltestellendaten.csv",
        "inferred": False,
        "retrieved": today,
        "stations": station_out,
    }, ensure_ascii=False, separators=(",", ":")).replace('},"ch:1:sloid:', '},\n"ch:1:sloid:') + "\n", encoding="utf-8")

    # ---- sectors ----
    feats = []
    for r in read_atlas("atlas_sectors"):
        e = edges.get(r["trafficPointSloid"])
        if not e:
            continue
        has_geo = bool(r["wgs84East"])
        feats.append({"type": "Feature", "id": r["sloid"],
                      "geometry": {"type": "Point", "coordinates": [round(float(r["wgs84East"]), 7), round(float(r["wgs84North"]), 7)]} if has_geo else None,
                      "properties": {
                          "sloid": r["sloid"], "type": r["type"], "designation": r["designation"] or None,
                          "edge_sloid": r["trafficPointSloid"], "edge_designation": e["designation"],
                          "station_sloid": e["station_sloid"], "station_number": e["station_number"], "station_name": e["station_name"],
                          "tier": e["tier"],
                          "lv95_e": float(r["lv95East"]) if r["lv95East"] else None, "lv95_n": float(r["lv95North"]) if r["lv95North"] else None,
                          "length_m": float(r["length"]) or None if r["length"] else None,
                          "height_m": float(r["height"]) or None if r["height"] else None,
                          "related_groups": r["relatedGroups"] or None, "related_sectors": r["relatedSectors"] or None,
                          "valid_from": r["validFrom"], "valid_to": r["validTo"], "edition_date": r["editionDate"], "status": r["status"],
                          "source": "atlas sectors-and-sector-groups-v2 (actual-date-sectors-and-sector-groups.csv)",
                          "inferred": False, "inferred_how": None}})
    feats.sort(key=lambda f: (f["properties"]["station_number"], f["properties"]["edge_sloid"], f["properties"]["designation"] or ""))
    (DATA / "sectors.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "name": "sectors",
        "description": "Platform sectors (A, B, C ...) of the boarding edges in edges.geojson. One point per sector as held by atlas; "
                       "atlas publishes no extent (length is 0 or empty for all of them), so a point marks the sector, not its span.",
        "crs_note": "WGS84 (EPSG:4326) lon/lat, 7 decimals; LV95 (EPSG:2056) kept as lv95_e / lv95_n",
        "features": feats,
    }, ensure_ascii=False, separators=(",", ":")).replace('},{"type":"Feature"', '},\n{"type":"Feature"') + "\n", encoding="utf-8")

    def tier_count(d):
        return dict(collections.Counter(v["tier"] for v in d.values()))
    bern_edges = [k for k, v in edges.items() if v["tier"] == "bern" and v["type"] == "BOARDING_PLATFORM"]
    summary = {
        "edges_with_accessibility": len(edge_out), "by_tier": tier_count(edge_out),
        "bern_boarding_edges": len(bern_edges),
        "bern_edges_with_atlas_platform": sum(1 for k in bern_edges if "atlas_platform" in edge_out.get(k, {})),
        "bern_edges_with_bfr_wheelchair": sum(1 for k in bern_edges if "bfr_wheelchair" in edge_out.get(k, {})),
        "bern_vehicle_access": dict(collections.Counter(edge_out[k]["atlas_platform"].get("vehicle_access", "(empty)") for k in bern_edges if "atlas_platform" in edge_out.get(k, {})).most_common()),
        "stations_with_accessibility": len(station_out), "stations_by_tier": tier_count(station_out),
        "bern_reference_points": sum(len(v.get("reference_points", [])) for v in station_out.values() if v["tier"] == "bern"),
        "bern_toilets": sum(len(v.get("toilets", [])) for v in station_out.values() if v["tier"] == "bern"),
        "bern_parking_lots": sum(len(v.get("parking_lots", [])) for v in station_out.values() if v["tier"] == "bern"),
        "bern_contact_points": sum(len(v.get("contact_points", [])) for v in station_out.values() if v["tier"] == "bern"),
        "relations": n_rel,
        "sectors": len(feats), "sectors_by_tier": dict(collections.Counter(f["properties"]["tier"] for f in feats)),
        "bern_edges_with_sectors": len({f["properties"]["edge_sloid"] for f in feats if f["properties"]["tier"] == "bern"}),
    }
    (DATA / "coverage_accessibility.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
