#!/usr/bin/env python3
"""Stage B2: timetable outputs for one feed.

Usage:  python scripts/build_timetable.py --feed fp2026

Reads   .cache/work_<feed>/*.txt (extract_gtfs.py) and data/gtfs_stop_map_<feed>.json (build_stops.py)
Writes  data/<feed>/gtfs_bern_<feed>.zip     lossless GTFS subset: every trip serving Bern, rows verbatim
        data/<feed>/timetable.json           compact pattern-encoded timetable (see docs/SCHEMA.md)
        data/<feed>/edge_directions.json     derived: where vehicles go next from each stop/edge (inferred)
        data/<feed>/segments.geojson         derived: every stop-to-stop hop with lines, trip-days, run time (inferred geometry)
        data/<feed>/lines.geojson            derived: one representative stop sequence per line and direction (inferred geometry)
        data/<feed>/transfers.json           minimum transfer times between stations (from transfers.txt)
        data/<feed>/timetable_stats.json     record counts

Nothing is dropped or re-timed: timetable.json decodes back to the exact stop_times rows of the
subset (validate.py proves this), times stay in seconds after service-day midnight and may be
>= 86400 (GTFS 24:00:00+), service days are explicit bitmasks over the feed's date range.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import math
import sys
import zipfile

from common import CACHE, DATA, TIMEZONE, bearing_deg, haversine_m, hms_to_sec

GTFS_FILES = ["agency.txt", "routes.txt", "trips.txt", "stop_times.txt", "stops.txt", "calendar.txt",
              "calendar_dates.txt", "frequencies.txt", "transfers.txt", "feed_info.txt"]


def rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def ymd(s: str) -> dt.date:
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True, choices=["fp2026", "fp2027"])
    args = ap.parse_args()
    feed = args.feed
    work = CACHE / f"work_{feed}"
    out = DATA / feed
    out.mkdir(parents=True, exist_ok=True)
    src_meta = json.loads((CACHE / f"gtfs_{feed}" / "source.json").read_text(encoding="utf-8"))
    stop_map = json.loads((DATA / f"gtfs_stop_map_{feed}.json").read_text(encoding="utf-8"))
    smap = {e["stop_id"]: e for e in stop_map["stops"]}

    # ---- 1. lossless GTFS subset zip (fixed timestamps -> byte-reproducible) ----
    zpath = out / f"gtfs_bern_{feed}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in GTFS_FILES:
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, (work / name).read_bytes(), compresslevel=9)

    feed_info = next(rows(work / "feed_info.txt"))
    start, end = ymd(feed_info["feed_start_date"]), ymd(feed_info["feed_end_date"])
    n_days = (end - start).days + 1

    # ---- 2. service day bitmasks: calendar.txt weekdays, then calendar_dates.txt exceptions ----
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    svc_days: dict[str, set[int]] = {}
    out_of_range = 0
    for c in rows(work / "calendar.txt"):
        s, e = ymd(c["start_date"]), ymd(c["end_date"])
        flags = [c[d] == "1" for d in wd]
        days = set()
        for i in range(max(0, (s - start).days), min(n_days - 1, (e - start).days) + 1):
            if flags[(start + dt.timedelta(days=i)).weekday()]:
                days.add(i)
        svc_days[c["service_id"]] = days
    n_add = n_rem = 0
    for c in rows(work / "calendar_dates.txt"):
        i = (ymd(c["date"]) - start).days
        if not 0 <= i < n_days:
            out_of_range += 1
            continue
        days = svc_days.setdefault(c["service_id"], set())
        if c["exception_type"] == "1":
            days.add(i)
            n_add += 1
        else:
            days.discard(i)
            n_rem += 1

    def mask_hex(days: set[int]) -> str:
        """Bit i (LSB = feed_start_date) set when the service runs on feed_start_date + i days."""
        v = 0
        for i in days:
            v |= 1 << i
        return format(v, "x")

    # ---- 3. tables ----
    agencies = list(rows(work / "agency.txt"))
    agency_idx = {a["agency_id"]: i for i, a in enumerate(agencies)}
    routes = sorted(rows(work / "routes.txt"), key=lambda r: (int(r["route_type"]), r["route_short_name"], r["route_id"]))
    route_idx = {r["route_id"]: i for i, r in enumerate(routes)}
    trips = {t["trip_id"]: t for t in rows(work / "trips.txt")}

    stop_ids: list[str] = []
    stop_idx: dict[str, int] = {}

    def sidx(stop_id: str) -> int:
        i = stop_idx.get(stop_id)
        if i is None:
            i = stop_idx[stop_id] = len(stop_ids)
            stop_ids.append(stop_id)
        return i

    # stop_times grouped per trip (contiguous in the extract)
    patterns: dict[tuple, dict] = {}
    n_st = n_over24 = 0
    max_sec = 0
    edge_next = collections.defaultdict(collections.Counter)       # stop_id -> (route, headsign, next number) -> trip-days
    stop_route_days = collections.defaultdict(collections.Counter)
    seg = {}                                                       # (from stop, to stop) -> accumulators
    pattern_days = collections.Counter()

    def flush(tid, buf):
        nonlocal n_st, n_over24, max_sec
        t = trips[tid]
        arr = [hms_to_sec(b[1]) for b in buf]
        dep = [hms_to_sec(b[2]) for b in buf]
        t0 = dep[0]
        key = (t["route_id"], t["direction_id"], t["trip_headsign"],
               tuple(b[3] for b in buf), tuple(int(b[4]) for b in buf),
               tuple(int(b[5] or 0) for b in buf), tuple(int(b[6] or 0) for b in buf))
        p = patterns.get(key)
        if p is None:
            p = patterns[key] = {"profiles": {}, "trips": []}
        prof = []
        for a, d in zip(arr, dep):
            prof.append(a - t0)
            prof.append(d - t0)
        prof = tuple(prof)
        pi = p["profiles"].setdefault(prof, len(p["profiles"]))
        p["trips"].append((t0, tid, t["service_id"], pi, t["trip_short_name"], t["original_trip_id"], t["hints"], t["block_id"]))
        n_st += len(buf)
        n_over24 += sum(1 for a, d in zip(arr, dep) if a >= 86400 or d >= 86400)
        max_sec = max(max_sec, max(arr), max(dep))
        days = len(svc_days.get(t["service_id"], ()))
        rs = routes[route_idx[t["route_id"]]]["route_short_name"]
        pattern_days[key] += days
        rt = int(routes[route_idx[t["route_id"]]]["route_type"])
        for j, b in enumerate(buf):
            stop_route_days[b[3]][rs] += days
            if j + 1 < len(buf):
                edge_next[b[3]][(rs, t["trip_headsign"], buf[j + 1][3])] += days
                a = seg.get((b[3], buf[j + 1][3]))
                if a is None:
                    a = seg[(b[3], buf[j + 1][3])] = {"days": 0, "trips": 0, "routes": collections.Counter(), "types": set(), "run": collections.Counter()}
                a["days"] += days
                a["trips"] += 1
                a["routes"][rs] += days
                a["types"].add(rt)
                a["run"][arr[j + 1] - dep[j]] += max(days, 1)

    with open(work / "stop_times.txt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        cur, buf = None, []
        for r in rd:
            if r[0] != cur:
                if buf:
                    flush(cur, buf)
                cur, buf = r[0], []
            buf.append(r)
        if buf:
            flush(cur, buf)

    # ---- 4. encode ----
    used_services = sorted({t[2] for p in patterns.values() for t in p["trips"]})
    service_idx = {s: i for i, s in enumerate(used_services)}
    missing_services = [s for s in used_services if s not in svc_days]
    headsigns, hints = [], []
    hs_idx, hint_idx = {}, {}

    def intern(table, index, value):
        i = index.get(value)
        if i is None:
            i = index[value] = len(table)
            table.append(value)
        return i

    enc_patterns = []
    order = sorted(patterns.items(), key=lambda kv: (route_idx[kv[0][0]], kv[0][1], kv[0][2], kv[0][3]))
    trip_ref = {}
    for pi, (key, p) in enumerate(order):
        route_id, direction, headsign, stops_t, seq_t, pu_t, do_t = key
        tr = sorted(p["trips"])
        e = {
            "r": route_idx[route_id],
            "d": int(direction) if direction != "" else None,
            "h": intern(headsigns, hs_idx, headsign),
            "s": [sidx(s) for s in stops_t],
        }
        if list(seq_t) != list(range(1, len(seq_t) + 1)):
            e["q"] = list(seq_t)                 # original stop_sequence when not simply 1..n
        if any(pu_t):
            e["pu"] = list(pu_t)                 # pickup_type per stop (0 regular, 1 none, 2 phone, 3 driver)
        if any(do_t):
            e["do"] = list(do_t)                 # drop_off_type per stop
        e["p"] = [list(prof) for prof, _ in sorted(p["profiles"].items(), key=lambda kv: kv[1])]
        e["t"] = {
            "st": [t[0] for t in tr],            # departure at first stop, seconds after service-day midnight
            "id": [t[1] for t in tr],            # GTFS trip_id
            "sv": [service_idx[t[2]] for t in tr],
            "pf": [t[3] for t in tr],            # index into p (time profile)
            "sn": [t[4] for t in tr],            # trip_short_name (train / course number)
            "oid": [t[5] for t in tr],           # original_trip_id (SJYID), the stable journey id
            "hi": [intern(hints, hint_idx, t[6]) for t in tr],
        }
        if any(t[7] for t in tr):
            e["t"]["bl"] = [t[7] for t in tr]    # block_id
        for ti, t in enumerate(tr):
            trip_ref[t[1]] = (pi, ti)
        enc_patterns.append(e)

    freqs = []
    for f in rows(work / "frequencies.txt"):
        pi, ti = trip_ref[f["trip_id"]]
        freqs.append([pi, ti, hms_to_sec(f["start_time"]), hms_to_sec(f["end_time"]), int(f["headway_secs"]), int(f["exact_times"] or 0)])

    stops_tbl = []
    for sid in stop_ids:
        m = smap[sid]
        stops_tbl.append([sid, m["number"], m["edge_sloid"], m["platform_code"], m["lon"], m["lat"]])
    station_tbl = {}
    for sid in stop_ids:
        m = smap[sid]
        station_tbl[str(m["number"])] = [m["station_sloid"], m["stop_name"], m["tier"]]

    counts = {
        "agencies": len(agencies), "routes": len(routes), "trips": len(trips), "stop_times": n_st,
        "patterns": len(enc_patterns), "time_profiles": sum(len(e["p"]) for e in enc_patterns),
        "services": len(used_services), "stops": len(stop_ids), "stations": len(station_tbl),
        "frequencies": len(freqs),
        "stop_time_rows_with_time_at_or_after_24h": n_over24,
        "max_time": f"{max_sec // 3600:02d}:{max_sec % 3600 // 60:02d}:{max_sec % 60:02d}",
        "calendar_rows": sum(1 for _ in rows(work / "calendar.txt")),
        "calendar_dates_added": n_add, "calendar_dates_removed": n_rem,
        "calendar_dates_outside_feed_range": out_of_range,
        "services_without_calendar": len(missing_services),
        "transfers": sum(1 for _ in rows(work / "transfers.txt")),
    }
    doc = {
        "meta": {
            "feed": feed,
            "title": f"Bern transit timetable, compact encoding of every trip serving Bern municipality ({feed})",
            "source": f"opentransportdata.swiss {src_meta['title']}, file {src_meta['resolved_file']}",
            "source_url": src_meta["landing_page"],
            "source_sha256": src_meta["sha256"],
            "source_retrieved_utc": src_meta["fetched_at_utc"],
            "feed_version": feed_info["feed_version"],
            "feed_publisher": feed_info["feed_publisher_name"],
            "feed_start_date": start.isoformat(),
            "feed_end_date": end.isoformat(),
            "timezone": TIMEZONE,
            "source_agency_timezone": sorted({a["agency_timezone"] for a in agencies}),
            "time_unit": "seconds after service-day midnight (noon minus 12 h); values >= 86400 are after midnight of the next calendar day",
            "service_mask": "hex integer; bit i (least significant = feed_start_date) is set when the service runs on feed_start_date + i days",
            "inferred": False,
            "counts": counts,
        },
        "agencies": [[a["agency_id"], a["agency_name"], a["agency_url"]] for a in agencies],
        "routes": [[r["route_id"], agency_idx[r["agency_id"]], r["route_short_name"], r["route_long_name"], r["route_desc"], int(r["route_type"])] for r in routes],
        "stations": station_tbl,
        "stops": stops_tbl,
        "services": {"ids": used_services, "masks": [mask_hex(svc_days.get(s, set())) for s in used_services]},
        "headsigns": headsigns,
        "hints": hints,
        "patterns": enc_patterns,
        "frequencies": freqs,
    }
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    text = text.replace(',"agencies":', ',\n"agencies":').replace(',"routes":', ',\n"routes":').replace(',"stations":', ',\n"stations":') \
               .replace(',"stops":[[', ',\n"stops":[[').replace(',"services":', ',\n"services":').replace(',"headsigns":', ',\n"headsigns":') \
               .replace(',"patterns":', ',\n"patterns":').replace('},{"r":', '},\n{"r":').replace(',"frequencies":', ',\n"frequencies":')
    (out / "timetable.json").write_text(text + "\n", encoding="utf-8")

    # ---- 5. derived directions per stop / edge ----
    def circ_mean(pairs):
        x = sum(w * math.cos(math.radians(b)) for b, w in pairs)
        y = sum(w * math.sin(math.radians(b)) for b, w in pairs)
        if math.hypot(x, y) < 1e-9:
            return None, 0.0
        r = math.hypot(x, y) / sum(w for _, w in pairs)
        return round((math.degrees(math.atan2(y, x)) + 360) % 360, 1), round(r, 3)

    directions = []
    for sid in stop_ids:
        m = smap[sid]
        if m["tier"] not in ("bern", "ring"):
            continue
        nxt = edge_next.get(sid, {})
        pairs, items = [], []
        for (rs, hs, nsid), days in nxt.items():
            n = smap[nsid]
            b = None
            if (n["lon"], n["lat"]) != (m["lon"], m["lat"]):
                b = round(bearing_deg(m["lon"], m["lat"], n["lon"], n["lat"]), 1)
                pairs.append((b, days))
            items.append((days, rs, hs, n["number"], n["stop_name"], b))
        agg = collections.OrderedDict()
        for days, rs, hs, nn, nname, b in sorted(items, key=lambda x: (-x[0], x[1], x[2])):
            k = (rs, hs, nn)
            if k not in agg:
                agg[k] = {"route": rs, "headsign": hs, "next_number": nn, "next_name": nname, "bearing_deg": b, "trip_days": 0}
            agg[k]["trip_days"] += days
        mean, conc = circ_mean(pairs) if pairs else (None, 0.0)
        directions.append({
            "stop_id": sid,
            "edge_sloid": m["edge_sloid"],
            "station_sloid": m["station_sloid"],
            "number": m["number"],
            "stop_name": m["stop_name"],
            "platform_code": m["platform_code"],
            "tier": m["tier"],
            "routes": [r for r, _ in stop_route_days[sid].most_common()],
            "trip_days": sum(stop_route_days[sid].values()),
            "terminating_only": not nxt,
            "bearing_mean_deg": mean,
            "bearing_concentration": conc,
            "next": list(agg.values())[:12],
        })
    ddoc = {
        "feed": feed,
        "description": "For every GTFS stop (edge) in tiers bern and ring: the routes calling there and where they go next. "
                       "trip_days = scheduled trips x operating days in the feed. bearing = initial great-circle bearing "
                       "from this stop coordinate to the next stop coordinate, weighted by trip_days "
                       "(bearing_concentration 1 = all departures leave the same way, near 0 = opposite ways).",
        "source": f"derived from GTFS stop_times.txt and stops.txt ({src_meta['resolved_file']})",
        "inferred": True,
        "inferred_how": "computed from consecutive stop_times of trips serving Bern; straight-line bearings, not track or road geometry",
        "stops": directions,
    }
    (out / "edge_directions.json").write_text(
        json.dumps(ddoc, ensure_ascii=False, separators=(",", ":")).replace('},{"stop_id"', '},\n{"stop_id"') + "\n", encoding="utf-8")

    # ---- 6. derived network geometry: hops and representative lines (straight lines between stops) ----
    how = "straight line between consecutive stop coordinates of the timetable; not the track or road alignment"
    src = f"derived from GTFS stop_times.txt and stops.txt ({src_meta['resolved_file']})"

    def weighted_median(counter):
        tot = sum(counter.values())
        acc = 0
        for v, w in sorted(counter.items()):
            acc += w
            if acc * 2 >= tot:
                return v

    seg_feats = []
    for (a, b), v in sorted(seg.items()):
        ma, mb = smap[a], smap[b]
        seg_feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[ma["lon"], ma["lat"]], [mb["lon"], mb["lat"]]]},
                          "properties": {
                              "from_stop_id": a, "to_stop_id": b,
                              "from_edge_sloid": ma["edge_sloid"], "to_edge_sloid": mb["edge_sloid"],
                              "from_station_sloid": ma["station_sloid"], "to_station_sloid": mb["station_sloid"],
                              "from_number": ma["number"], "to_number": mb["number"],
                              "from_name": ma["stop_name"], "to_name": mb["stop_name"],
                              "from_tier": ma["tier"], "to_tier": mb["tier"],
                              "routes": [r for r, _ in v["routes"].most_common()],
                              "route_types": sorted(v["types"]),
                              "trips": v["trips"], "trip_days": v["days"],
                              "run_time_s_median": weighted_median(v["run"]),
                              "length_m_straight": round(haversine_m(ma["lon"], ma["lat"], mb["lon"], mb["lat"])),
                              "source": src, "inferred": True, "inferred_how": how}})
    counts["segments"] = len(seg_feats)

    def write_fc(name, desc, feats):
        d = {"type": "FeatureCollection", "name": name, "description": desc, "feed": feed,
             "crs_note": "WGS84 (EPSG:4326) lon/lat, 7 decimals", "features": feats}
        (out / f"{name}.geojson").write_text(
            json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace('},{"type":"Feature"', '},\n{"type":"Feature"') + "\n", encoding="utf-8")

    write_fc("segments", "Every hop between two consecutive stops of a trip serving Bern, with the lines using it. "
                         "trip_days = trips x operating days in the feed. Geometry is a straight line (inferred).", seg_feats)

    by_line = collections.defaultdict(list)
    for key, days in pattern_days.items():
        r = routes[route_idx[key[0]]]
        by_line[(r["agency_id"], r["route_short_name"], r["route_desc"], r["route_type"], key[1])].append((days, key))
    line_feats = []
    for (agency_id, rs, desc, rtype, direction), pats in sorted(by_line.items(), key=lambda kv: (int(kv[0][3]), kv[0][1], kv[0][0], kv[0][4])):
        days, key = max(pats, key=lambda x: (x[0], len(x[1][3])))
        ms = [smap[s] for s in key[3]]
        line_feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[m["lon"], m["lat"]] for m in ms]},
                           "properties": {
                               "route_short_name": rs, "route_desc": desc, "route_type": int(rtype),
                               "agency_id": agency_id, "agency_name": agencies[agency_idx[agency_id]]["agency_name"],
                               "direction_id": int(direction) if direction != "" else None,
                               "headsign": key[2], "first_stop": ms[0]["stop_name"], "last_stop": ms[-1]["stop_name"],
                               "stop_ids": list(key[3]), "stop_numbers": [m["number"] for m in ms],
                               "stops_in_bern": sum(1 for m in ms if m["tier"] == "bern"),
                               "route_ids": sorted({k[0] for _, k in pats}),
                               "pattern_trip_days": days,
                               "line_trip_days": sum(d for d, _ in pats),
                               "line_pattern_count": len(pats),
                               "representative": "stop sequence with the most trip-days for this line and direction; other variants are in timetable.json",
                               "source": src, "inferred": True, "inferred_how": how}})
    counts["lines"] = len(line_feats)
    write_fc("lines", "One representative stop sequence per line (operator, short name, category) and direction_id. Straight lines between stops (inferred).", line_feats)

    # ---- 7. transfers (stop-to-stop rules of transfers.txt, station level where both ends are stations) ----
    tr = []
    for t in rows(work / "transfers.txt"):
        a, b = smap.get(t["from_stop_id"]), smap.get(t["to_stop_id"])
        local = a and b and a["tier"] in ("bern", "ring") and b["tier"] in ("bern", "ring")
        if not (local or t["from_trip_id"] or t["to_trip_id"]):
            continue                         # rules between far-away stations stay in the GTFS subset zip only
        tr.append([t["from_stop_id"], t["to_stop_id"], a["number"] if a else None, b["number"] if b else None,
                   int(t["transfer_type"] or 0), int(t["min_transfer_time"]) if t["min_transfer_time"] else None,
                   t["from_route_id"] or None, t["to_route_id"] or None, t["from_trip_id"] or None, t["to_trip_id"] or None])
    (out / "transfers.json").write_text(json.dumps({
        "feed": feed,
        "description": "transfers.txt rules between stops of tiers bern and ring, plus all trip-to-trip rules of the subset. "
                       "transfer_type 2 = minimum time needed (min_transfer_time, seconds), 4 = in-seat transfer between two trips. "
                       "Rules between far-away stations are in the GTFS subset zip only.",
        "columns": ["from_stop_id", "to_stop_id", "from_number", "to_number", "transfer_type", "min_transfer_time", "from_route_id", "to_route_id", "from_trip_id", "to_trip_id"],
        "source": f"GTFS transfers.txt ({src_meta['resolved_file']})", "inferred": False,
        "rows": tr,
    }, ensure_ascii=False, separators=(",", ":")).replace("],[", "],\n[") + "\n", encoding="utf-8")

    stats = {"feed": feed, "counts": counts,
             "files": {p.name: p.stat().st_size for p in sorted(out.iterdir()) if p.is_file() and p.name != "timetable_stats.json"}}
    (out / "timetable_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
