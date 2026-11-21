#!/usr/bin/env python3
"""Validate every output of the transit folder and write validation/report.{json,md}
plus validation/sample_departures.{json,md}.

Usage:  python scripts/validate.py [--online] [--node]

  --online  cross-check sample departures against transport.opendata.ch/v1/stationboard
            (independent official timetable API; about a dozen bounded requests)
  --node    compare web/bern-transit.js with scripts/timetable.py (needs `node` on PATH)

Exit code 1 when a hard check fails.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
import io

from common import (CACHE, DATA, FEEDS, ROOT, SOURCES, USER_AGENT, VALIDATION, Boundary, haversine_m, hms_to_sec)
from timetable import Timetable

SAMPLE_STATIONS = [
    (8507000, "Bern (main station, rail)"),
    (8576646, "Bern, Bahnhof (tram and bus stop at the main station)"),
    (8507110, "Bern, Zytglogge"),
    (8516161, "Bern Wankdorf (rail)"),
    (8590129, "Bern, Wankdorf Bahnhof (tram and bus)"),
]
SAMPLE_TIMES = {
    "fp2026": [
        ("2026-11-24", "08:00:00", "regular Tuesday morning"),
        ("2026-11-23", "08:00:00", "Monday 23 Nov 2026 = Zibelemaerit (onion market): calendar exception with extra services"),
        ("2026-11-22", "00:30:00", "Sunday after midnight: departures of service day Saturday 21 Nov, GTFS times above 24:00:00"),
    ],
    "fp2027": [
        ("2026-12-15", "08:00:00", "first Tuesday of the 2027 timetable"),
        ("2026-12-20", "00:30:00", "Sunday after midnight in the 2027 timetable, GTFS times above 24:00:00"),
    ],
}

RANDOM_SAMPLE = 40

checks: list[dict] = []


def check(name: str, ok: bool, detail="", hard=True):
    checks.append({"check": name, "ok": bool(ok), "hard": hard, "detail": detail})
    print(("PASS " if ok else ("FAIL " if hard else "WARN ")) + name + (f"  [{detail}]" if detail else ""), flush=True)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_rows(zf, name):
    with zf.open(name) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", newline=""))


def validate_sources(report):
    out = {}
    for name, src in SOURCES.items():
        meta = json.loads((CACHE / name / "source.json").read_text(encoding="utf-8"))
        ok = sha256(CACHE / name / src["file"]) == meta["sha256"]
        check(f"source {name}: cached file matches recorded sha256", ok, meta["resolved_file"])
        out[name] = {k: meta[k] for k in ("resolved_file", "http_last_modified", "bytes", "sha256", "fetched_at_utc")}
    report["sources"] = out


def validate_stops(report):
    stations = json.loads((DATA / "stations.geojson").read_text(encoding="utf-8"))["features"]
    edges = json.loads((DATA / "edges.geojson").read_text(encoding="utf-8"))["features"]
    lookup = json.loads((DATA / "edge_lookup.json").read_text(encoding="utf-8"))["stations"]
    boundary = Boundary(CACHE / "boundary_bern" / SOURCES["boundary_bern"]["file"])
    st_by_sloid = {f["properties"]["sloid"]: f for f in stations if f["properties"]["sloid"]}
    st_by_number = {f["properties"]["number"]: f for f in stations}

    check("stations: unique number", len(st_by_number) == len(stations), f"{len(stations)} stations")
    check("stations: unique sloid", len(st_by_sloid) == sum(1 for f in stations if f["properties"]["sloid"]))
    check("edges: unique sloid", len({f["properties"]["sloid"] for f in edges}) == len(edges), f"{len(edges)} edges and areas")
    orphan = [f["properties"]["sloid"] for f in edges if f["properties"]["station_sloid"] not in st_by_sloid]
    check("edges: every edge has a parent station in stations.geojson", not orphan, f"{len(orphan)} orphans")
    tier_mismatch = [f["properties"]["sloid"] for f in edges if st_by_sloid[f["properties"]["station_sloid"]]["properties"]["tier"] != f["properties"]["tier"]]
    check("edges: tier equals the parent station tier", not tier_mismatch)
    prefix_bad = [f["properties"]["sloid"] for f in edges if not f["properties"]["sloid"].startswith(f["properties"]["station_sloid"] + ":")]
    check("edges: edge sloid starts with the station sloid", not prefix_bad, f"{len(prefix_bad)} exceptions", hard=False)

    bern = [f for f in stations if f["properties"]["tier"] == "bern"]
    outside = [f["properties"]["name"] for f in bern if not boundary.contains(*f["geometry"]["coordinates"])]
    check("coverage: all 'bern' stations (atlas fsoNumber 351) lie inside the swisstopo boundary polygon", not outside, f"{len(bern)} stations, outside: {outside}")
    ring_inside = [f["properties"]["name"] for f in stations if f["properties"]["tier"] != "bern" and f["geometry"] and boundary.contains(*f["geometry"]["coordinates"])]
    check("coverage: no station of another tier lies inside the Bern polygon", not ring_inside, str(ring_inside[:5]))
    edge_other = sorted({f["properties"]["station_name"] for f in edges if f["properties"]["tier"] != "bern" and f["geometry"] and boundary.contains(*f["geometry"]["coordinates"])})
    check("coverage: no edge of a non-Bern station lies inside the (generalised) Bern polygon", not edge_other,
          f"border stops atlas attributes to the neighbouring municipality: {edge_other}; trips serving them are included", hard=False)
    ring_far = [f["properties"]["name"] for f in stations if f["properties"]["tier"] == "ring" and f["properties"]["dist_to_bern_boundary_m"] > 5000]
    check("coverage: every 'ring' station is within 5 km of the boundary", not ring_far)

    # edge distance to its own station coordinate
    far = []
    dists = []
    for f in edges:
        p = f["properties"]
        if not f["geometry"] or p["tier"] != "bern" or p["type"] != "BOARDING_PLATFORM":
            continue
        s = st_by_sloid[p["station_sloid"]]
        d = haversine_m(*f["geometry"]["coordinates"], *s["geometry"]["coordinates"])
        dists.append(d)
        if d > 400:
            far.append([p["sloid"], p["station_name"], round(d)])
    check("edges (bern): every edge lies within 400 m of its station coordinate", not far, f"median {statistics.median(dists):.0f} m, max {max(dists):.0f} m, far: {far[:6]}", hard=False)

    # lookup consistency
    edge_ids = {f["properties"]["sloid"] for f in edges}
    bad = [n for n, e in lookup.items() for group in ("by_designation", "by_designation_operational", "by_gtfs_platform_code")
           for ids in e[group].values() for i in ids if i not in edge_ids]
    check("edge_lookup: every referenced edge exists in edges.geojson", not bad)
    amb = sum(1 for e in lookup.values() if e["tier"] == "bern" for ids in e["by_designation"].values() if len(ids) > 1)
    uniq = sum(1 for e in lookup.values() if e["tier"] == "bern" for ids in e["by_designation"].values() if len(ids) == 1)

    # accessibility and sectors join on the same ids
    acc_e = json.loads((DATA / "accessibility_edges.json").read_text(encoding="utf-8"))["edges"]
    acc_s = json.loads((DATA / "accessibility_stations.json").read_text(encoding="utf-8"))["stations"]
    sectors = json.loads((DATA / "sectors.geojson").read_text(encoding="utf-8"))["features"]
    check("accessibility: every edge key exists in edges.geojson", all(k in edge_ids for k in acc_e), f"{len(acc_e)} edges")
    check("accessibility: every station key exists in stations.geojson", all(k in st_by_sloid for k in acc_s), f"{len(acc_s)} stations")
    rel_bad = sum(1 for v in acc_s.values() for r in v.get("relations", []) if r.get("reference_point_element_type") == "PLATFORM" and r["element_sloid"] not in edge_ids)
    check("accessibility: PLATFORM relations point at edges in edges.geojson", rel_bad == 0, f"{rel_bad} relations name an edge that is not in atlas traffic-point-v2", hard=False)
    check("sectors: every sector belongs to an edge in edges.geojson", all(f["properties"]["edge_sloid"] in edge_ids for f in sectors), f"{len(sectors)} sectors")
    edge_geom = {f["properties"]["sloid"]: f["geometry"] for f in edges}
    sd = [haversine_m(*f["geometry"]["coordinates"], *edge_geom[f["properties"]["edge_sloid"]]["coordinates"])
          for f in sectors if f["geometry"] and edge_geom[f["properties"]["edge_sloid"]]]
    check("sectors: a sector point lies within 450 m of its edge point", max(sd) <= 450, f"median {statistics.median(sd):.0f} m, max {max(sd):.0f} m over {len(sd)} sectors", hard=False)

    report["stops"] = {
        "accessibility_edges": len(acc_e), "accessibility_stations": len(acc_s), "sectors": len(sectors),
        "sector_to_edge_distance_m": {"median": round(statistics.median(sd)), "max": round(max(sd))},
        "stations": len(stations),
        "stations_by_tier": dict(collections.Counter(f["properties"]["tier"] for f in stations)),
        "edges_and_areas": len(edges),
        "edges_by_tier_type": {f"{t}/{k}": v for (t, k), v in sorted(collections.Counter((f["properties"]["tier"], f["properties"]["type"]) for f in edges).items())},
        "bern_edge_to_station_distance_m": {"median": round(statistics.median(dists)), "p95": round(sorted(dists)[int(len(dists) * .95)]), "max": round(max(dists))},
        "bern_edges_far_from_station": far,
        "bern_designation_lookup": {"unique_designations": uniq, "designations_shared_by_several_edges": amb},
        "bern_edges_without_geometry": sorted(f["properties"]["sloid"] for f in edges if f["properties"]["tier"] == "bern" and f["properties"]["type"] == "BOARDING_PLATFORM" and not f["geometry"]),
    }
    return st_by_number, {f["properties"]["sloid"]: f for f in edges}


def validate_feed(feed, report, st_by_number, edge_by_sloid, today):
    work = CACHE / f"work_{feed}"
    out = DATA / feed
    rep = report["feeds"][feed] = {}
    stats = json.loads((work / "extract_stats.json").read_text(encoding="utf-8"))
    rep["national_rows"] = stats["source_rows"]
    rep["kept_rows"] = stats["kept_rows"]
    check(f"{feed}: stop_times rows of a trip are contiguous and every trip id is in trips.txt", stats["trip_groups_equal_trips_txt"])

    zf = zipfile.ZipFile(out / f"gtfs_bern_{feed}.zip")
    check(f"{feed}: subset zip passes CRC test", zf.testzip() is None, f"{(out / f'gtfs_bern_{feed}.zip').stat().st_size:,} bytes")
    feed_info = next(zip_rows(zf, "feed_info.txt"))
    rep["feed_info"] = feed_info
    start = dt.date(int(feed_info["feed_start_date"][:4]), int(feed_info["feed_start_date"][4:6]), int(feed_info["feed_start_date"][6:]))
    end = dt.date(int(feed_info["feed_end_date"][:4]), int(feed_info["feed_end_date"][4:6]), int(feed_info["feed_end_date"][6:]))
    rep["valid"] = [start.isoformat(), end.isoformat()]
    rep["valid_today"] = start <= today <= end

    # ---- referential integrity of the GTFS subset ----
    agencies = {a["agency_id"]: a for a in zip_rows(zf, "agency.txt")}
    routes = {r["route_id"]: r for r in zip_rows(zf, "routes.txt")}
    trips = {t["trip_id"]: t for t in zip_rows(zf, "trips.txt")}
    stops = {s["stop_id"]: s for s in zip_rows(zf, "stops.txt")}
    cal = {c["service_id"]: c for c in zip_rows(zf, "calendar.txt")}
    cal_dates = collections.defaultdict(list)
    for c in zip_rows(zf, "calendar_dates.txt"):
        cal_dates[c["service_id"]].append((c["date"], c["exception_type"]))
    check(f"{feed}: routes -> agency", all(r["agency_id"] in agencies for r in routes.values()), f"{len(routes)} routes, {len(agencies)} agencies")
    check(f"{feed}: trips -> routes", all(t["route_id"] in routes for t in trips.values()), f"{len(trips):,} trips")
    check(f"{feed}: trips -> calendar or calendar_dates", all(t["service_id"] in cal or t["service_id"] in cal_dates for t in trips.values()), f"{len(cal):,} services")
    check(f"{feed}: stops -> parent_station", all(not s["parent_station"] or s["parent_station"] in stops for s in stops.values()), f"{len(stops):,} stops")
    tz = sorted({a["agency_timezone"] for a in agencies.values()})
    rep["agency_timezone_in_source"] = tz
    check(f"{feed}: agency_timezone has Zurich rules", set(tz) <= {"Europe/Zurich", "Europe/Berlin"},
          f"source says {tz}; Europe/Berlin and Europe/Zurich share offset and DST dates, outputs are labelled Europe/Zurich")

    # ---- stop_times: integrity, monotonic times, >24h ----
    src_rows = []
    bad_ref = non_mono = over24 = 0
    max_sec = 0
    with zf.open("stop_times.txt") as fh:
        rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8", newline=""))
        next(rd)
        cur, last, last_seq = None, -1, -1
        for r in rd:
            if r[0] not in trips or r[3] not in stops:
                bad_ref += 1
            a, d = hms_to_sec(r[1]), hms_to_sec(r[2])
            if r[0] != cur:
                cur, last, last_seq = r[0], -1, -1
            if a < last or d < a or int(r[4]) <= last_seq:
                non_mono += 1
            last, last_seq = d, int(r[4])
            if a >= 86400 or d >= 86400:
                over24 += 1
            max_sec = max(max_sec, a, d)
            src_rows.append((r[0], r[1], r[2], r[3], int(r[4]), int(r[5] or 0), int(r[6] or 0)))
    check(f"{feed}: stop_times -> trips and stops", bad_ref == 0, f"{len(src_rows):,} rows")
    check(f"{feed}: times never run backwards within a trip, stop_sequence strictly increasing", non_mono == 0, f"{non_mono} violations")
    check(f"{feed}: times at or after 24:00:00 are preserved", over24 > 0, f"{over24:,} rows, latest {max_sec // 3600:02d}:{max_sec % 3600 // 60:02d}:00")
    rep["stop_times_rows"] = len(src_rows)
    rep["rows_at_or_after_24h"] = over24
    rep["latest_time"] = f"{max_sec // 3600:02d}:{max_sec % 3600 // 60:02d}:{max_sec % 60:02d}"

    # ---- compact timetable decodes to exactly the same rows ----
    tt = Timetable.load(feed)
    dec_rows = list(tt.stop_times())
    same = sorted(dec_rows) == sorted(src_rows)
    check(f"{feed}: timetable.json decodes to exactly the stop_times of the GTFS subset", same, f"{len(dec_rows):,} rows compared field by field")
    dec_trips = {t["trip_id"]: t for t in tt.trips()}
    check(f"{feed}: timetable.json decodes to exactly the trips of the GTFS subset", dec_trips == trips, f"{len(dec_trips):,} trips, all 9 columns")
    rcols = [[r["route_id"], r["route_short_name"], r["route_long_name"], r["route_desc"], int(r["route_type"])] for r in routes.values()]
    check(f"{feed}: routes preserved", sorted(rcols) == sorted([r[0], r[2], r[3], r[4], r[5]] for r in tt.routes))

    # ---- calendars: independent recomputation of service days ----
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    mismatch = 0
    total_days = 0
    for i, sid in enumerate(tt.service_ids):
        days = set()
        c = cal.get(sid)
        if c:
            d = dt.date(int(c["start_date"][:4]), int(c["start_date"][4:6]), int(c["start_date"][6:]))
            e = dt.date(int(c["end_date"][:4]), int(c["end_date"][4:6]), int(c["end_date"][6:]))
            while d <= e:
                if c[wd[d.weekday()]] == "1":
                    days.add(d.isoformat())
                d += dt.timedelta(days=1)
        for date, ex in cal_dates.get(sid, []):
            iso = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            (days.add if ex == "1" else days.discard)(iso)
        total_days += len(days)
        if sorted(days) != tt.service_dates(i):
            mismatch += 1
    check(f"{feed}: service-day bitmasks equal calendar.txt + calendar_dates.txt for every service", mismatch == 0,
          f"{len(tt.service_ids):,} services, {total_days:,} service-days, {sum(len(v) for v in cal_dates.values()):,} exceptions")
    rep["services"] = len(tt.service_ids)
    rep["calendar_exceptions"] = {"added": sum(1 for v in cal_dates.values() for x in v if x[1] == "1"),
                                  "removed": sum(1 for v in cal_dates.values() for x in v if x[1] == "2")}

    # ---- stop resolution and coordinates ----
    smap = json.loads((DATA / f"gtfs_stop_map_{feed}.json").read_text(encoding="utf-8"))
    by_stop = {e["stop_id"]: e for e in smap["stops"]}
    unresolved = [s[0] for s in tt.stops if not (by_stop[s[0]]["edge_sloid"] or by_stop[s[0]]["station_sloid"])]
    check(f"{feed}: every timetable stop resolves to an edge SLOID or a station SLOID", all(by_stop[u]["kind"] == "station_not_in_atlas" for u in unresolved),
          f"{len(tt.stops) - len(unresolved)} of {len(tt.stops)} resolve; {len(unresolved)} are stations atlas does not hold (number only)", hard=False)
    check(f"{feed}: every timetable stop has a station record", all(s[1] in st_by_number for s in tt.stops))
    dd = []
    moved = []
    for e in smap["stops"]:
        if e["kind"] in ("edge", "edge_sector_variant") and edge_by_sloid.get(e["edge_sloid"], {}).get("geometry"):
            d = haversine_m(e["lon"], e["lat"], *edge_by_sloid[e["edge_sloid"]]["geometry"]["coordinates"])
            dd.append(d)
            if d > 25:
                moved.append([e["stop_id"], e["stop_name"], round(d)])
    rep["gtfs_vs_atlas_edge_coordinate_m"] = {"compared": len(dd), "median": round(statistics.median(dd), 2), "p95": round(sorted(dd)[int(len(dd) * .95)], 2),
                                              "max": round(max(dd), 1), "over_25_m": len(moved), "examples_over_25_m": sorted(moved, key=lambda x: -x[2])[:10]}
    check(f"{feed}: GTFS stop coordinates agree with atlas edge coordinates (95 % within 5 m)", sorted(dd)[int(len(dd) * .95)] <= 5,
          f"median {statistics.median(dd):.2f} m, p95 {sorted(dd)[int(len(dd) * .95)]:.2f} m, {len(moved)} of {len(dd)} differ by more than 25 m", hard=False)
    rep["stop_resolution"] = {k: smap[k] for k in ("summary_all_stops", "summary_tier_bern", "summary_tier_bern_and_ring", "stop_count_by_kind")}
    other_parent = sorted({(e["stop_name"], edge_by_sloid[e["edge_sloid"]]["properties"]["station_name"]) for e in smap["stops"]
                           if e["edge_sloid"] and e["edge_station_sloid"] != e["station_sloid"]})
    rep["gtfs_stops_whose_edge_belongs_to_another_atlas_station"] = [list(x) for x in other_parent]
    check(f"{feed}: every edge used by the timetable is in edges.geojson", all(e["edge_sloid"] in edge_by_sloid for e in smap["stops"] if e["edge_sloid"]),
          f"{len(other_parent)} GTFS station(s) use edges that atlas files under another service point: {[list(x) for x in other_parent][:4]}")

    # ---- coverage of Bern stations in this feed ----
    served = collections.Counter()
    for p in tt.patterns:
        n = len(p["t"]["id"])
        for si in set(p["s"]):
            served[tt.stops[si][1]] += n
    bern_numbers = sorted(n for n, f in st_by_number.items() if f["properties"]["tier"] == "bern" and f["properties"]["stop_point"])
    unserved = [[n, st_by_number[n]["properties"]["name"]] for n in bern_numbers if served[n] == 0]
    rep["bern_stations_with_trips"] = len(bern_numbers) - len(unserved)
    rep["bern_stations_without_trips"] = unserved
    check(f"{feed}: every atlas stop in Bern municipality has scheduled trips", not unserved, f"{len(bern_numbers) - len(unserved)} of {len(bern_numbers)}; missing: {unserved}", hard=False)

    # trips per day
    per_day = collections.Counter()
    for p in tt.patterns:
        for sv in p["t"]["sv"]:
            m, i = tt.masks[sv], 0
            while m:
                if m & 1:
                    per_day[i] += 1
                m >>= 1
                i += 1
    n_days = (end - start).days + 1
    zero = [(start + dt.timedelta(days=i)).isoformat() for i in range(n_days) if per_day[i] == 0]
    check(f"{feed}: at least one trip runs on every day of the feed", not zero, f"{n_days} days, min {min(per_day[i] for i in range(n_days)):,} / max {max(per_day.values()):,} trips per day")
    wk = collections.defaultdict(list)
    for i in range(n_days):
        wk[(start + dt.timedelta(days=i)).strftime("%a")].append(per_day[i])
    rep["trips_per_day_median_by_weekday"] = {k: int(statistics.median(v)) for k, v in wk.items()}
    rep["trips_per_day"] = {"min": min(per_day[i] for i in range(n_days)), "max": max(per_day.values())}
    rep["counts"] = tt.meta["counts"]
    rep["routes_by_type"] = dict(collections.Counter(f"{r[5]} {r[4]}" for r in tt.routes).most_common())
    rep["trips_by_agency"] = dict(collections.Counter(tt.agencies[tt.routes[p["r"]][1]][1] for p in tt.patterns for _ in p["t"]["id"]).most_common())
    return tt


def validate_slices(feed, tt, report):
    """A window file must hold exactly the trips that run in its window, unchanged."""
    full = {}
    for row in tt.stop_times():
        full[row[0]] = hash((full.get(row[0]), row[1:]))
    for path in sorted((DATA / feed).glob("timetable_20*.json")):
        sl = Timetable(json.loads(path.read_text(encoding="utf-8")))
        w = sl.meta["window"]
        part = {}
        for row in sl.stop_times():
            part[row[0]] = hash((part.get(row[0]), row[1:]))
        same_rows = all(full.get(k) == v for k, v in part.items())

        def running(t, day):
            return {tid for p in t.patterns for tid, sv in zip(p["t"]["id"], p["t"]["sv"]) if t.runs(sv, day)}
        d0, d1 = tt.day_index(w["from"]), tt.day_index(w["to"])
        days_ok = all(running(tt, d) == running(sl, d) for d in range(d0 - 1, d1 + 1))
        deps_ok = all(tt.departures(n, w["from"], "00:00:00", limit=500, window_sec=30 * 3600) == sl.departures(n, w["from"], "00:00:00", limit=500, window_sec=30 * 3600)
                      for n, _ in SAMPLE_STATIONS)
        check(f"{feed}: {path.name} holds exactly the trips running {w['from']} to {w['to']}, unchanged",
              same_rows and days_ok and deps_ok,
              f"{len(part):,} of {len(full):,} trips; stop_times identical: {same_rows}; same trips on each of {d1 - d0 + 2} days: {days_ok}; same departures at the focus stations: {deps_ok}")
        report["feeds"][feed].setdefault("window_files", {})[path.name] = {"trips": len(part), "window": [w["from"], w["to"]], "bytes": path.stat().st_size}


def stationboard(number, date, time_, limit=40):
    q = urllib.parse.urlencode({"id": number, "datetime": f"{date} {time_[:5]}", "limit": limit})
    req = urllib.request.Request(f"https://transport.opendata.ch/v1/stationboard?{q}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))["stationboard"]


def crosscheck(tt, feed, number, label, date, time_, group):
    """Compare our departures with the stationboard of transport.opendata.ch for one station and time."""
    base = {"feed": feed, "group": group, "station_number": number, "station": label, "date": date, "from": time_}
    try:
        board = stationboard(number, date, time_)
        time.sleep(0.7)
    except Exception as exc:                      # network trouble must not fail the offline checks
        return dict(base, error=str(exc))
    api = []
    for b in board:
        t = b["stop"]["departure"]
        if not t:
            continue
        names = {str(b.get("number") or ""), f"{b.get('category') or ''}{b.get('number') or ''}", str(b.get("category") or "")}
        api.append((t[:10], t[11:16], names, b.get("to"), b["stop"].get("platform")))
    if not api:
        return dict(base, api_departures=0, note="API returned no departures")
    last = max((a[0], a[1]) for a in api)
    ours = []
    for d in tt.departures(number, date, time_, limit=5000, window_sec=30 * 3600):
        day = (dt.date.fromisoformat(date) + dt.timedelta(days=d["wall_sec"] // 86400)).isoformat()
        hhmm = f"{d['wall_sec'] % 86400 // 3600:02d}:{d['wall_sec'] % 3600 // 60:02d}"
        if (day, hhmm) < last:
            ours.append((day, hhmm, d["route"], d["platform"]))
    api_in = [a for a in api if (a[0], a[1]) < last]
    pool = collections.Counter((o[0], o[1], o[2]) for o in ours)
    ours_plat = collections.defaultdict(set)
    for o in ours:
        ours_plat[(o[0], o[1], o[2])].add(o[3])
    matched = plat_ok = plat_cmp = 0
    missing = []
    for a in api_in:
        hit = next((n for n in a[2] if pool[(a[0], a[1], n)] > 0), None)
        if hit is None:
            missing.append([a[1], sorted(a[2])[-1], a[3]])
            continue
        pool[(a[0], a[1], hit)] -= 1
        matched += 1
        if a[4]:
            plat_cmp += 1
            plat_ok += a[4] in ours_plat[(a[0], a[1], hit)]
    return dict(base, window_until=last[1], api_departures=len(api_in), ours_in_window=len(ours), api_matched_in_ours=matched,
                api_missing_in_ours=missing[:8], ours_not_in_api=sum(pool.values()), platform_compared=plat_cmp, platform_equal=plat_ok)


def samples(tts, report, online, st_by_number):
    out = {"note": "Scheduled departures decoded from data/<feed>/timetable.json with scripts/timetable.py. "
                   "time = local wall clock (Europe/Zurich); gtfs_time = time in the feed, relative to service_date, may exceed 24:00:00.",
           "samples": []}
    md = ["# Sample departures", "", out["note"], ""]
    xcheck = []
    for feed, tt in tts.items():
        for date, time_, why in SAMPLE_TIMES[feed]:
            for number, label in SAMPLE_STATIONS:
                deps = tt.departures(number, date, time_, limit=10)
                out["samples"].append({"feed": feed, "station_number": number, "station": label, "date": date, "from": time_, "why": why,
                                       "departures": [{k: d[k] for k in ("time", "gtfs_time", "service_date", "route", "route_desc", "headsign", "last_stop", "platform", "edge_sloid", "stop_id", "trip_id", "original_trip_id", "agency")} for d in deps]})
                md += [f"## {label} — {date} from {time_[:5]} ({feed})", "", f"{why}. Station number {number}.", "",
                       "| Time | GTFS time | Service day | Line | Headsign | Platform | Edge SLOID |", "|---|---|---|---|---|---|---|"]
                md += [f"| {d['time'][:5]} | {d['gtfs_time']} | {d['service_date']} | {d['route']} | {d['headsign']} | {d['platform'] or ''} | {d['edge_sloid'] or ''} |" for d in deps]
                md.append("")
                if online:
                    xcheck.append(crosscheck(tt, feed, number, label, date, time_, "focus"))
    if online:
        # breadth: a seeded random sample of Bern stops, regular weekday at noon, both feeds
        rnd = random.Random(351)
        pool = sorted(n for n, f in st_by_number.items() if f["properties"]["tier"] == "bern" and f["properties"]["stop_point"] and f["properties"]["valid_today"])
        for number in sorted(rnd.sample(pool, RANDOM_SAMPLE)):
            for feed, date in (("fp2026", "2026-11-24"), ("fp2027", "2026-12-15")):
                if feed in tts:
                    xcheck.append(crosscheck(tts[feed], feed, number, st_by_number[number]["properties"]["name"], date, "12:00:00", "random"))
    VALIDATION.mkdir(exist_ok=True)
    (VALIDATION / "sample_departures.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (VALIDATION / "sample_departures.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if online:
        report["stationboard_crosscheck"] = {
            "source": "https://transport.opendata.ch/v1/stationboard (independent API on the official timetable; the team app uses it)",
            "method": "same station, date and time; compare (minute, line) pairs inside the window the API returned; then compare the platform letter",
            "results": xcheck,
        }
        totals = {}
        for feed in tts:
            for group in ("focus", "random"):
                xs = [x for x in xcheck if x["feed"] == feed and x["group"] == group]
                tot = sum(x.get("api_departures", 0) for x in xs)
                hit = sum(x.get("api_matched_in_ours", 0) for x in xs)
                extra = sum(x.get("ours_not_in_api", 0) for x in xs)
                pc = sum(x.get("platform_compared", 0) for x in xs)
                pe = sum(x.get("platform_equal", 0) for x in xs)
                errors = sum(1 for x in xs if "error" in x)
                totals[f"{feed}/{group}"] = {"boards": len(xs), "boards_failed_to_load": errors, "api_departures": tot, "matched": hit,
                                             "ours_not_in_api": extra, "platform_compared": pc, "platform_equal": pe}
                what = "focus stations (Bern, Bern Bahnhof, Zytglogge, Wankdorf)" if group == "focus" else f"{RANDOM_SAMPLE} random Bern stops"
                check(f"{feed}: departures at {what} agree with transport.opendata.ch stationboard (>= 95 % of API departures found)",
                      tot > 0 and hit / tot >= 0.95,
                      f"{len(xs) - errors} boards: {hit} of {tot} API departures found at the same minute and line; "
                      f"{extra} of ours not in the API list; platform equal for {pe} of {pc}", hard=False)
        report["stationboard_crosscheck"]["totals"] = totals


def node_compare(tts):
    script = r"""
const fs=require('fs');const a=process.argv.slice(-3);const api=require(a[0]);const q=JSON.parse(a[1]);const out={};
for(const feed of Object.keys(q)){const tt=api.decode(JSON.parse(fs.readFileSync(a[2]+'/'+feed+'/timetable.json','utf8')));
out[feed]=q[feed].map(([n,d,t])=>tt.departures(n,d,t,60).map(x=>[x.time,x.gtfs_time,x.service_date,x.route,x.headsign,x.platform,x.stop_id,x.trip_id]));}
process.stdout.write(JSON.stringify(out));"""
    queries = {feed: [[n, d, t] for d, t, _ in SAMPLE_TIMES[feed] for n, _ in SAMPLE_STATIONS] for feed in tts}
    res = subprocess.run(["node", "-e", script, str(ROOT / "web" / "bern-transit.js"), json.dumps(queries), str(DATA)],
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        check("web/bern-transit.js equals scripts/timetable.py", False, res.stderr[-300:])
        return
    js = json.loads(res.stdout)
    n = 0
    same = True
    for feed, tt in tts.items():
        for (num, d, t), got in zip(queries[feed], js[feed]):
            exp = [[x["time"], x["gtfs_time"], x["service_date"], x["route"], x["headsign"], x["platform"], x["stop_id"], x["trip_id"]] for x in tt.departures(num, d, t, limit=60)]
            n += len(exp)
            same = same and exp == got
    check("web/bern-transit.js returns the same departures as scripts/timetable.py", same, f"{n} departures over {sum(len(v) for v in queries.values())} queries")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--node", action="store_true")
    args = ap.parse_args()
    today = dt.date.today()
    report = {"generated": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "feeds": {}}
    validate_sources(report)
    st_by_number, edge_by_sloid = validate_stops(report)
    tts = {}
    for feed in FEEDS:
        if (DATA / feed / "timetable.json").exists():
            tts[feed] = validate_feed(feed, report, st_by_number, edge_by_sloid, today)
            validate_slices(feed, tts[feed], report)
    if len(tts) == 2:
        a, b = ({s[1] for s in tts[f].stops if st_by_number[s[1]]["properties"]["tier"] == "bern"} for f in ("fp2026", "fp2027"))
        report["bern_stations_only_in_fp2026"] = sorted([n, st_by_number[n]["properties"]["name"]] for n in a - b)
        report["bern_stations_only_in_fp2027"] = sorted([n, st_by_number[n]["properties"]["name"]] for n in b - a)
        ra, rb = ({(r[2], r[4]) for r in tts[f].routes} for f in ("fp2026", "fp2027"))
        report["route_names_only_in_fp2026"] = sorted(f"{d} {n}" for n, d in ra - rb)
        report["route_names_only_in_fp2027"] = sorted(f"{d} {n}" for n, d in rb - ra)
    samples(tts, report, args.online, st_by_number)
    if args.node:
        node_compare(tts)

    hard_fail = [c for c in checks if not c["ok"] and c["hard"]]
    warn = [c for c in checks if not c["ok"] and not c["hard"]]
    report["checks"] = checks
    report["summary"] = {"checks": len(checks), "passed": sum(c["ok"] for c in checks), "warnings": len(warn), "failed": len(hard_fail)}
    VALIDATION.mkdir(exist_ok=True)
    (VALIDATION / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    md = ["# Validation report", "", f"Generated {report['generated']} by `scripts/validate.py`"
          + (" `--online`" if args.online else "") + (" `--node`" if args.node else "") + ".", "",
          f"**{report['summary']['passed']} of {report['summary']['checks']} checks passed, "
          f"{report['summary']['warnings']} warnings, {report['summary']['failed']} failed.**", "",
          "| Result | Check | Detail |", "|---|---|---|"]
    for c in checks:
        md.append(f"| {'pass' if c['ok'] else ('FAIL' if c['hard'] else 'warn')} | {c['check']} | {str(c['detail']).replace('|', '/')} |")
    md += ["", "Numbers behind the checks are in `report.json`; sample departures in `sample_departures.md`."]
    (VALIDATION / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
