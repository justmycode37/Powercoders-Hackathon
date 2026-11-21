#!/usr/bin/env python3
"""Stage B1: stations, boarding edges, designation lookup and GTFS stop mapping.

Usage:  python scripts/build_stops.py

Reads   .cache/atlas_service_point, .cache/atlas_traffic_point, .cache/boundary_bern,
        .cache/work_<feed>/{stops,stop_times}.txt   (from extract_gtfs.py)
Writes  data/stations.geojson            every station in coverage (atlas service points)
        data/edges.geojson               every boarding edge / boarding area of those stations
        data/edge_lookup.json            number -> designation -> edge sloid(s)
        data/gtfs_stop_map_<feed>.json   GTFS stop_id -> edge / station SLOID + stop_times shares
        data/coverage_stops.json         counts and coverage logic (machine readable)

Coverage tiers (property `tier`):
  bern       atlas service point with municipality FSO number 351 that is a stop point
             (plus operating points that own a boarding edge used by the timetable)
  ring       atlas stop point outside Bern, at most RING_KM from the municipal boundary
  connected  any other station called at by a trip that serves a `bern` stop (either feed)
atlas "valid today" is primary; stops and edges valid only earlier or later in the current / next
timetable year are added from the timetable-years files with valid_today=false.
"""
from __future__ import annotations

import collections
import csv
import json
import sys

from common import (BERN_FSO, CACHE, DATA, FEEDS, RING_KM, SOURCES, Boundary, read_atlas)

SRC_SP = "atlas service-point-v2 (actual-date-swiss-service-point.csv)"
SRC_TP = "atlas traffic-point-v2 (actual-date-world-traffic-point.csv)"
SRC_SP_Y = "atlas service-point-v2 (timetable-years-swiss-service-point.csv); not valid on the retrieval date"
SRC_TP_Y = "atlas traffic-point-v2 (timetable-years-world-traffic-point.csv); not valid on the retrieval date"


def num(v, nd=None):
    if v is None or v == "":
        return None
    f = float(v)
    return round(f, nd) if nd is not None else f


def height(v):
    """atlas stores 0.0 when no height is set; nothing in scope lies at sea level."""
    f = num(v, 1)
    return None if f in (None, 0.0) else f


def coord_precision(r):
    """Flag coordinates that atlas holds only to whole metres (or coarser)."""
    e, n = r.get("lv95East") or "", r.get("lv95North") or ""
    if not e or not n:
        return None, None
    fe, fn = float(e), float(n)
    if fe == int(fe) and fn == int(fn):
        step = 1
        for cand in (1000, 100, 10):
            if int(fe) % cand == 0 and int(fn) % cand == 0:
                step = cand
                break
        return True, f"LV95 easting and northing are whole multiples of {step} m"
    we, wn = r.get("wgs84East") or "", r.get("wgs84North") or ""
    dec = max(len(we.partition(".")[2]), len(wn.partition(".")[2]))
    if dec <= 5:
        return True, f"WGS84 given with {dec} decimals (about {111000 / 10 ** dec:.1f} m)"
    return False, None


def split_list(v):
    return [x for x in (v or "").split("|") if x]


def main() -> int:
    DATA.mkdir(exist_ok=True)
    boundary = Boundary(CACHE / "boundary_bern" / SOURCES["boundary_bern"]["file"])

    # atlas "valid today" is primary; versions that are only valid earlier or later in the current / next
    # timetable year (temporary stops, stops opening at the timetable change) come from the timetable-years file
    sp_by_number = {r["number"]: r for r in read_atlas("atlas_service_point")}
    sp_today = set(sp_by_number)
    for r in read_atlas("atlas_service_point_years"):
        n = r["number"]
        if n not in sp_today and (n not in sp_by_number or r["validTo"] > sp_by_number[n]["validTo"]):
            sp_by_number[n] = r
    sp_rows = list(sp_by_number.values())
    sp_by_sloid = {r["sloid"]: r for r in sp_rows if r["sloid"]}
    tp_by_sloid = {r["sloid"]: r for r in read_atlas("atlas_traffic_point")}
    tp_today = set(tp_by_sloid)
    for r in read_atlas("atlas_traffic_point_years"):
        k = r["sloid"]
        if k not in tp_today and (k not in tp_by_sloid or r["validTo"] > tp_by_sloid[k]["validTo"]):
            tp_by_sloid[k] = r
    tp_rows = list(tp_by_sloid.values())
    for r in tp_rows:                       # atlas drops the parent link once the stop itself has expired
        if not r["parentSloidServicePoint"] and r["number"] in sp_by_number:
            r["parentSloidServicePoint"] = sp_by_number[r["number"]]["sloid"]
            r["_parent_filled"] = True
    tp_by_station = collections.defaultdict(list)
    for r in tp_rows:
        tp_by_station[r["parentSloidServicePoint"]].append(r)

    # ---- GTFS subsets (both feeds when extracted) ----
    gtfs = {}
    for feed in FEEDS:
        work = CACHE / f"work_{feed}"
        if not (work / "stops.txt").exists():
            continue
        stops = list(csv.DictReader(open(work / "stops.txt", encoding="utf-8", newline="")))
        rows = collections.Counter()
        with open(work / "stop_times.txt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            next(rd)
            for row in rd:
                rows[row[3]] += 1
        gtfs[feed] = {"stops": stops, "rows": rows}

    # ---- station universe and tiers ----
    tier = {}                                   # number -> tier
    dist = {}                                   # number -> metres to boundary (outside > 0)
    x0, y0, x1, y1 = boundary.bbox
    pad = RING_KM / 111.0 * 1.6
    def area_tier(r):
        """bern / ring / None from the atlas municipality attribute and the distance to the boundary."""
        n = r["number"]
        if r["fsoNumber"] == BERN_FSO:
            return "bern"
        if not r["wgs84East"]:
            return None
        lon, lat = float(r["wgs84East"]), float(r["wgs84North"])
        if not (x0 - pad <= lon <= x1 + pad and y0 - pad <= lat <= y1 + pad):
            return None
        d = 0.0 if boundary.contains(lon, lat) else boundary.distance_m(lon, lat)
        if d <= RING_KM * 1000:
            dist[n] = round(d)
            return "ring"
        return None

    for r in sp_rows:
        if r["stopPoint"] == "true":
            t = area_tier(r)
            if t:
                tier[r["number"]] = t
    gtfs_only = {}                              # number -> GTFS stop row for stations atlas does not hold
    in_gtfs = {feed: set() for feed in gtfs}
    for feed, g in gtfs.items():
        for s in g["stops"]:
            n = s["didok"]
            in_gtfs[feed].add(n)
            if n not in tier:
                tier[n] = (area_tier(sp_by_number[n]) if n in sp_by_number else None) or "connected"
            if n not in sp_by_number and (n not in gtfs_only or s["location_type"] == "1"):
                gtfs_only[n] = dict(s, _feed=feed)
            # an edge can hang on another atlas service point than the GTFS station (e.g. Bern Europaplatz Sued,
            # an operating point without stopPoint): that parent must be a station record too
            e = tp_by_sloid.get(s["original_stop_id"])
            if e:
                pn = sp_by_sloid.get(e["parentSloidServicePoint"], {}).get("number")
                if pn and pn not in tier:
                    tier[pn] = area_tier(sp_by_number[pn]) or "connected"

    # ---- stations.geojson ----
    station_feats = []
    station_sloid = {}                          # number -> sloid
    for n in sorted(tier):
        r = sp_by_number.get(n)
        if r:
            station_sloid[n] = r["sloid"]
            has_geo = bool(r["wgs84East"])
            lon = num(r["wgs84East"], 7)
            lat = num(r["wgs84North"], 7)
            inside = boundary.contains(lon, lat) if has_geo else None
            if tier[n] == "bern" and has_geo:
                d = boundary.distance_m(lon, lat)
                dist[n] = -round(d) if inside else round(d)
            elif n not in dist and has_geo:
                dist[n] = round(boundary.distance_m(lon, lat))
            edges = tp_by_station.get(r["sloid"], [])
            props = {
                "sloid": r["sloid"],
                "number": int(n),
                "name": r["designationOfficial"],
                "name_long": r["designationLong"] or None,
                "abbreviation": r["abbreviation"] or None,
                "tier": tier[n],
                "municipality": r["municipalityName"] or None,
                "fso_number": int(r["fsoNumber"]) if r["fsoNumber"] else None,
                "canton": r["cantonAbbreviation"] or None,
                "country": r["isoCountryCode"] or None,
                "means_of_transport": split_list(r["meansOfTransport"]),
                "stop_point": r["stopPoint"] == "true",
                "stop_point_type": r["stopPointType"] or None,
                "valid_today": n in sp_today,
                "operator_abbr": r["businessOrganisationAbbreviationDe"] or None,
                "operator_sboid": r["businessOrganisation"] or None,
                "lv95_e": num(r["lv95East"], 2),
                "lv95_n": num(r["lv95North"], 2),
                "height_m": height(r["height"]),
                "coord_rounded": coord_precision(r)[0],
                "coord_rounded_how": coord_precision(r)[1],
                "edge_count": sum(1 for e in edges if e["trafficPointElementType"] == "BOARDING_PLATFORM"),
                "boarding_area_count": sum(1 for e in edges if e["trafficPointElementType"] == "BOARDING_AREA"),
                "valid_from": r["validFrom"],
                "valid_to": r["validTo"],
                "edition_date": r["editionDate"],
                "status": r["status"],
                "dist_to_bern_boundary_m": dist.get(n),
                "inside_boundary_polygon": inside,
                **{f"in_gtfs_{feed}": n in in_gtfs[feed] for feed in gtfs},
                "source": SRC_SP if n in sp_today else SRC_SP_Y,
                "inferred": False,
                "inferred_how": None,
            }
            geom = {"type": "Point", "coordinates": [lon, lat]} if has_geo else None
        else:
            s = gtfs_only[n]
            station_sloid[n] = None
            lon, lat = round(float(s["stop_lon"]), 7), round(float(s["stop_lat"]), 7)
            props = {
                "sloid": None, "number": int(n), "name": s["stop_name"], "name_long": None, "abbreviation": None,
                "tier": tier[n], "municipality": None, "fso_number": None, "canton": None, "country": None,
                "means_of_transport": [], "stop_point": None, "stop_point_type": None, "valid_today": None, "operator_abbr": None, "operator_sboid": None,
                "lv95_e": None, "lv95_n": None, "height_m": None, "coord_rounded": None, "coord_rounded_how": None,
                "edge_count": 0, "boarding_area_count": 0, "valid_from": None, "valid_to": None,
                "edition_date": None, "status": None,
                "dist_to_bern_boundary_m": round(boundary.distance_m(lon, lat)), "inside_boundary_polygon": False,
                **{f"in_gtfs_{feed}": n in in_gtfs[feed] for feed in gtfs},
                "source": f"GTFS stops.txt ({s['_feed']}); station is not in atlas service-point-v2 (foreign station)",
                "inferred": False, "inferred_how": None,
            }
            geom = {"type": "Point", "coordinates": [lon, lat]}
        station_feats.append({"type": "Feature", "id": props["sloid"] or f"didok:{n}", "geometry": geom, "properties": props})

    # ---- GTFS stop_id -> edge / station mapping ----
    gtfs_edge_refs = {feed: set() for feed in gtfs}
    stop_maps = {}
    for feed, g in gtfs.items():
        entries = []
        for s in g["stops"]:
            sid, orig, n = s["stop_id"], s["original_stop_id"], s["didok"]
            st_sloid = station_sloid.get(n)
            edge = None
            inferred, how = False, None
            if s["location_type"] == "1":
                kind = "parent_station"
            elif orig in tp_by_sloid:
                kind = "edge" if sid == orig else "edge_sector_variant"
                edge = orig
            elif orig and orig == st_sloid:
                kind = "station"
            elif n not in sp_by_number:
                kind = "station_not_in_atlas"
            else:
                # GTFS names an edge that atlas (valid today) does not hold: try the public designation
                kind = "edge_unresolved"
                code = s["platform_code"]
                cands = [e["sloid"] for e in tp_by_station.get(st_sloid, [])
                         if code and e["trafficPointElementType"] == "BOARDING_PLATFORM" and e["designation"] == code]
                if len(cands) == 1:
                    kind, edge, inferred = "edge_by_designation", cands[0], True
                    how = "GTFS platform_code equals the atlas designation of exactly one edge of the same station"
            if edge:
                gtfs_edge_refs[feed].add(edge)
            entries.append({
                "stop_id": sid,
                "kind": kind,
                "edge_sloid": edge,
                "edge_station_sloid": tp_by_sloid[edge]["parentSloidServicePoint"] if edge else None,
                "station_sloid": st_sloid,
                "number": int(n),
                "tier": tier[n],
                "stop_name": s["stop_name"],
                "platform_code": s["platform_code"] or None,
                "parent_station": s["parent_station"] or None,
                "original_stop_id": orig or None,
                "lon": round(float(s["stop_lon"]), 7),
                "lat": round(float(s["stop_lat"]), 7),
                "stop_times_rows": g["rows"].get(sid, 0),
                "source": f"GTFS stops.txt ({feed})",
                "inferred": inferred,
                "inferred_how": how,
            })
        def share(sel):
            c = collections.Counter()
            for e in entries:
                if sel(e):
                    c[e["kind"]] += e["stop_times_rows"]
            tot = sum(c.values()) or 1
            edge_rows = c["edge"] + c["edge_sector_variant"] + c["edge_by_designation"]
            return {
                "stop_times_rows": sum(c.values()),
                "rows_by_kind": dict(c.most_common()),
                "share_edge_sloid": round(edge_rows / tot, 4),
                "share_station_sloid_only": round((c["station"] + c["edge_unresolved"]) / tot, 4),
                "share_no_sloid": round(c["station_not_in_atlas"] / tot, 4),
            }
        stop_maps[feed] = {
            "feed": feed,
            "scope": "stops used by trips that serve at least one stop in Bern municipality",
            "kinds": {
                "edge": "stop_id is an atlas boarding-edge SLOID",
                "edge_sector_variant": "generated stop_id (<station>_gen:<edge>_pf:<sectors>); original_stop_id is the atlas edge SLOID",
                "edge_by_designation": "edge id unknown to atlas today; matched by platform_code = designation (inferred)",
                "edge_unresolved": "edge id unknown to atlas today and no unique designation match; resolves to the station only",
                "station": "stop_id is the station (service point) SLOID, no edge assigned in the timetable",
                "station_not_in_atlas": "foreign station without Swiss SLOID; DiDok/UIC number only",
                "parent_station": "location_type=1 parent record (never referenced by stop_times)",
            },
            "summary_all_stops": share(lambda e: True),
            "summary_tier_bern": share(lambda e: e["tier"] == "bern"),
            "summary_tier_bern_and_ring": share(lambda e: e["tier"] in ("bern", "ring")),
            "stop_count_by_kind": dict(collections.Counter(e["kind"] for e in entries).most_common()),
            "stops": entries,
        }
        (DATA / f"gtfs_stop_map_{feed}.json").write_text(
            json.dumps(stop_maps[feed], ensure_ascii=False, separators=(",", ":")).replace('},{"stop_id"', '},\n{"stop_id"') + "\n",
            encoding="utf-8")

    # ---- edges.geojson ----
    edge_feats = []
    lookup = {}
    gtfs_codes = collections.defaultdict(lambda: collections.defaultdict(set))   # number -> code -> edges
    for feed, m in stop_maps.items():
        for e in m["stops"]:
            if e["edge_sloid"] and e["platform_code"]:
                gtfs_codes[e["number"]][e["platform_code"]].add(e["edge_sloid"])
    for n in sorted(tier):
        sl = station_sloid.get(n)
        if not sl:
            continue
        edges = sorted(tp_by_station.get(sl, []), key=lambda e: (e["trafficPointElementType"], e["designation"], e["designationOperational"], e["sloid"]))
        if not edges:
            continue
        sp = sp_by_number[n]
        entry = {"sloid": sl, "name": sp["designationOfficial"], "tier": tier[n],
                 "by_designation": collections.defaultdict(list), "by_designation_operational": collections.defaultdict(list),
                 "by_gtfs_platform_code": {k: sorted(v) for k, v in sorted(gtfs_codes.get(int(n), {}).items())}}
        for e in edges:
            has_geo = bool(e["wgs84East"])
            rounded, rounded_how = coord_precision(e)
            is_edge = e["trafficPointElementType"] == "BOARDING_PLATFORM"
            props = {
                "sloid": e["sloid"],
                "type": e["trafficPointElementType"],
                "designation": e["designation"] or None,
                "designation_operational": e["designationOperational"] or None,
                "station_sloid": sl,
                "station_number": int(n),
                "station_name": sp["designationOfficial"],
                "area_sloid": e["parentSloid"] or None,
                "tier": tier[n],
                "compass_direction_deg": num(e["compassDirection"], 1),
                "length_m": num(e["length"], 2),
                "boarding_area_height_cm": num(e["boardingAreaHeight"], 2),
                "lv95_e": num(e["lv95East"], 3),
                "lv95_n": num(e["lv95North"], 3),
                "height_m": height(e["height"]),
                "has_geometry": has_geo,
                "coord_rounded": rounded,
                "coord_rounded_how": rounded_how,
                "valid_from": e["validFrom"],
                "valid_to": e["validTo"],
                "edition_date": e["editionDate"],
                "status": e["status"],
                "valid_today": e["sloid"] in tp_today,
                **{f"in_gtfs_{feed}": e["sloid"] in gtfs_edge_refs[feed] for feed in gtfs},
                "source": SRC_TP if e["sloid"] in tp_today else SRC_TP_Y,
                "inferred": bool(e.get("_parent_filled")),
                "inferred_how": "atlas row carries no parent service point (the stop has expired); station taken from the edge's own number" if e.get("_parent_filled") else None,
            }
            geom = {"type": "Point", "coordinates": [num(e["wgs84East"], 7), num(e["wgs84North"], 7)]} if has_geo else None
            edge_feats.append({"type": "Feature", "id": e["sloid"], "geometry": geom, "properties": props})
            if is_edge:
                if e["designation"]:
                    entry["by_designation"][e["designation"]].append(e["sloid"])
                if e["designationOperational"]:
                    entry["by_designation_operational"][e["designationOperational"]].append(e["sloid"])
        if entry["by_designation"] or entry["by_designation_operational"] or entry["by_gtfs_platform_code"]:
            lookup[n] = entry

    def fc(name, desc, feats, extra=None):
        doc = {"type": "FeatureCollection", "name": name, "description": desc,
               "crs_note": "WGS84 (EPSG:4326) lon/lat, 7 decimals; LV95 (EPSG:2056) kept as lv95_e / lv95_n; heights in metres LN02 as published by atlas (null = not set in atlas)",
               **(extra or {}), "features": feats}
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).replace('},{"type":"Feature"', '},\n{"type":"Feature"')
        (DATA / f"{name}.geojson").write_text(text + "\n", encoding="utf-8")

    cov_logic = {
        "bern": "atlas service point with municipality FSO number 351 (atlas attribute fsoNumber) that is a stop point, "
                "or an operating point owning a boarding edge the timetable uses (stop_point=false)",
        "ring": f"atlas stop point outside Bern whose coordinate is at most {RING_KM:g} km from the swisstopo municipal boundary of Bern",
        "connected": "any other station called at by a GTFS trip that serves at least one `bern` stop (fp2026 or fp2027)",
    }
    fc("stations", "Stations (atlas service points / DiDok) in Bern transit coverage", station_feats, {"tiers": cov_logic})
    fc("edges", "Boarding edges (kerbs, platforms) and boarding areas of the stations in stations.geojson", edge_feats, {"tiers": cov_logic})

    (DATA / "edge_lookup.json").write_text(json.dumps({
        "description": "number (DiDok/UIC, as used by transport.opendata.ch) -> public designation -> boarding edge SLOID(s). "
                       "A designation can map to several edges; pick by proximity or by_gtfs_platform_code. "
                       "by_gtfs_platform_code also covers sector strings such as '2A-D'.",
        "source": SRC_TP, "inferred": False,
        "stations": lookup,
    }, ensure_ascii=False, separators=(",", ":")).replace('},"85', '},\n"85') + "\n", encoding="utf-8")

    # ---- coverage summary ----
    tiers = collections.Counter(tier.values())
    edge_types = collections.Counter((f["properties"]["tier"], f["properties"]["type"]) for f in edge_feats)
    bern_edges = [f["properties"] for f in edge_feats if f["properties"]["tier"] == "bern" and f["properties"]["type"] == "BOARDING_PLATFORM"]
    cov = {
        "coverage_logic": cov_logic,
        "ring_km": RING_KM,
        "stations_by_tier": dict(tiers),
        "stations_total": len(station_feats),
        "stations_not_in_atlas": sorted(int(n) for n in gtfs_only),
        "edges_by_tier_and_type": {f"{t}/{k}": v for (t, k), v in sorted(edge_types.items())},
        "edges_total": len(edge_feats),
        "bern_edges": {
            "boarding_platforms": len(bern_edges),
            "with_geometry": sum(1 for p in bern_edges if p["has_geometry"]),
            "with_compass_direction": sum(1 for p in bern_edges if p["compass_direction_deg"] is not None),
            "with_public_designation": sum(1 for p in bern_edges if p["designation"]),
            "with_height": sum(1 for p in bern_edges if p["height_m"] is not None),
            "coord_rounded": sum(1 for p in bern_edges if p["coord_rounded"]),
            "not_valid_today": sum(1 for p in bern_edges if not p["valid_today"]),
            **{f"referenced_by_gtfs_{feed}": sum(1 for p in bern_edges if p[f"in_gtfs_{feed}"]) for feed in gtfs},
        },
        "bern_stations": {
            "total": tiers["bern"],
            "stop_points": sum(1 for f in station_feats if f["properties"]["tier"] == "bern" and f["properties"]["stop_point"]),
            "not_valid_today": sorted([f["properties"]["name"], f["properties"]["valid_from"], f["properties"]["valid_to"]]
                                      for f in station_feats if f["properties"]["tier"] == "bern" and not f["properties"]["valid_today"]),
            "operating_points_owning_edges": sorted(f["properties"]["name"] for f in station_feats
                                                    if f["properties"]["tier"] == "bern" and not f["properties"]["stop_point"]),
            "inside_generalised_boundary_polygon": sum(1 for f in station_feats if f["properties"]["tier"] == "bern" and f["properties"]["inside_boundary_polygon"]),
            "outside_generalised_boundary_polygon": sorted(
                [f["properties"]["name"], f["properties"]["dist_to_bern_boundary_m"]]
                for f in station_feats if f["properties"]["tier"] == "bern" and f["properties"]["inside_boundary_polygon"] is False),
            "without_edges": sorted(f["properties"]["name"] for f in station_feats
                                    if f["properties"]["tier"] == "bern" and f["properties"]["edge_count"] == 0),
            **{f"in_gtfs_{feed}": sum(1 for f in station_feats if f["properties"]["tier"] == "bern" and f["properties"][f"in_gtfs_{feed}"]) for feed in gtfs},
        },
        "ring_stations_inside_polygon_but_other_municipality": sorted(
            [f["properties"]["name"], f["properties"]["municipality"]]
            for f in station_feats if f["properties"]["tier"] == "ring" and f["properties"]["inside_boundary_polygon"]),
        "gtfs_stop_map": {feed: {k: m[k] for k in ("summary_all_stops", "summary_tier_bern", "summary_tier_bern_and_ring", "stop_count_by_kind")}
                          for feed, m in stop_maps.items()},
    }
    (DATA / "coverage_stops.json").write_text(json.dumps(cov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(cov, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
