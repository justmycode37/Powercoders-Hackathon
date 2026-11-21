#!/usr/bin/env python3
"""Stage A: stream the national GTFS zip once and keep every trip that serves Bern.

Usage:  python scripts/extract_gtfs.py --feed fp2026

Core stops = GTFS stops whose DiDok number belongs to an atlas service point with
municipality FSO number 351 (Bern) and stopPoint=true (valid today or at any time in the
current / next timetable year), plus any GTFS stop whose coordinate lies inside the
swisstopo municipal polygon. A trip is kept when at least one
of its stop_times is at a core stop; the trip is kept whole (all stop_times, original
stop_sequence, original HH:MM:SS strings incl. hours >= 24). Clipping to the Bern area
happens later in build_bern_transit.py, so this stage is a lossless superset.

Output (git-ignored): .cache/work_<feed>/{stop_times,trips,routes,agency,calendar,
calendar_dates,transfers,frequencies,stops,feed_info}.txt + extract_stats.json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time

from common import BERN_FSO, CACHE, SOURCES, Boundary, gtfs_zip, read_atlas, read_table


def split_row(line: bytes) -> list[bytes]:
    """Split one fully quoted GTFS CSV line ("a","b",...) without the csv module (hot loop)."""
    return line.rstrip(b"\r\n")[1:-1].split(b'","')


def core_didok_numbers() -> set[str]:
    """DiDok numbers of atlas stop points in Bern municipality, valid today or at any time in the
    current / next timetable year (temporary and future stops are in the timetable-years file)."""
    return {
        r["number"]
        for source in ("atlas_service_point", "atlas_service_point_years")
        for r in read_atlas(source)
        if r["fsoNumber"] == BERN_FSO and r["stopPoint"] == "true"
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True, choices=["fp2026", "fp2027"])
    args = ap.parse_args()
    t0 = time.time()
    work = CACHE / f"work_{args.feed}"
    work.mkdir(parents=True, exist_ok=True)
    zf = gtfs_zip(args.feed)
    stats: dict = {"feed": args.feed, "source_rows": {}, "kept_rows": {}}

    core_numbers = core_didok_numbers()
    stops = list(read_table(zf, "stops.txt"))
    stats["source_rows"]["stops"] = len(stops)
    core_stop_ids = {s["stop_id"].encode() for s in stops if s["didok"] in core_numbers}
    # catch-all: a GTFS stop atlas does not attribute to Bern but whose coordinate is inside the municipal polygon
    boundary = Boundary(CACHE / "boundary_bern" / SOURCES["boundary_bern"]["file"])
    by_polygon = sorted({(s["didok"], s["stop_name"]) for s in stops
                         if s["didok"] not in core_numbers and boundary.contains(float(s["stop_lon"]), float(s["stop_lat"]))})
    core_stop_ids |= {s["stop_id"].encode() for s in stops if (s["didok"], s["stop_name"]) in by_polygon}
    stats["core_added_by_polygon_only"] = [list(x) for x in by_polygon]
    print(f"core DiDok numbers: {len(core_numbers)}  core GTFS stop_ids: {len(core_stop_ids)}", flush=True)

    # ---- stop_times: one streaming pass, rows of a trip are contiguous in the source ----
    kept_trips: set[bytes] = set()
    used_stops: set[bytes] = set()
    n_rows = n_groups = n_kept_rows = 0
    with zf.open("stop_times.txt") as fh, open(work / "stop_times.txt", "wb") as out:
        header = fh.readline()
        cols = header.lstrip(b"\xef\xbb\xbf").rstrip(b"\r\n").replace(b'"', b"").split(b",")  # header is unquoted
        assert cols[:5] == [b"trip_id", b"arrival_time", b"departure_time", b"stop_id", b"stop_sequence"], cols
        out.write(header.lstrip(b"\xef\xbb\xbf"))
        cur = None
        buf: list[bytes] = []
        hit = False
        buf_stops: list[bytes] = []
        for line in fh:
            n_rows += 1
            f = split_row(line)
            tid = f[0]
            if tid != cur:
                if hit:
                    assert cur not in kept_trips, f"trip rows not contiguous: {cur!r}"
                    kept_trips.add(cur)
                    out.writelines(buf)
                    used_stops.update(buf_stops)
                    n_kept_rows += len(buf)
                n_groups += 1
                cur, buf, buf_stops, hit = tid, [], [], False
            buf.append(line)
            buf_stops.append(f[3])
            if f[3] in core_stop_ids:
                hit = True
            if n_rows % 10_000_000 == 0:
                print(f"  stop_times {n_rows:,} rows, kept trips {len(kept_trips):,} ({time.time()-t0:.0f}s)", flush=True)
        if hit:
            assert cur not in kept_trips
            kept_trips.add(cur)
            out.writelines(buf)
            used_stops.update(buf_stops)
            n_kept_rows += len(buf)
    stats["source_rows"]["stop_times"] = n_rows
    stats["source_trip_groups_in_stop_times"] = n_groups
    stats["kept_rows"]["stop_times"] = n_kept_rows
    print(f"stop_times: {n_rows:,} rows / {n_groups:,} trips -> kept {n_kept_rows:,} rows / {len(kept_trips):,} trips", flush=True)

    def filter_table(name: str, keep, track=None):
        """Copy rows of `name` for which keep(fields) is true; return (source_rows, kept_rows)."""
        n = k = 0
        with zf.open(name) as fh, open(work / name, "wb") as out:
            header = fh.readline().lstrip(b"\xef\xbb\xbf")
            out.write(header)
            for line in fh:
                n += 1
                f = split_row(line)
                if keep(f):
                    k += 1
                    out.write(line)
                    if track:
                        track(f)
        stats["source_rows"][name[:-4]] = n
        stats["kept_rows"][name[:-4]] = k
        print(f"{name}: {n:,} -> {k:,}", flush=True)

    # trips.txt: route_id,service_id,trip_id,...
    used_routes: set[bytes] = set()
    used_services: set[bytes] = set()

    def track_trip(f):
        used_routes.add(f[0])
        used_services.add(f[1])

    filter_table("trips.txt", lambda f: f[2] in kept_trips, track_trip)
    assert stats["kept_rows"]["trips"] == len(kept_trips), "every kept trip must exist exactly once in trips.txt"
    stats["trip_groups_equal_trips_txt"] = stats["source_rows"]["trips"] == n_groups

    used_agencies: set[bytes] = set()
    filter_table("routes.txt", lambda f: f[0] in used_routes, lambda f: used_agencies.add(f[1]))
    filter_table("agency.txt", lambda f: f[0] in used_agencies)
    filter_table("calendar.txt", lambda f: f[0] in used_services)
    filter_table("calendar_dates.txt", lambda f: f[0] in used_services)
    filter_table("frequencies.txt", lambda f: f[0] in kept_trips)
    # transfers: keep stop-to-stop rules between used stops/stations and trip-to-trip rules between kept trips
    used_parents = {s["parent_station"].encode() for s in stops if s["stop_id"].encode() in used_stops and s["parent_station"]}
    stop_universe = used_stops | used_parents

    def keep_transfer(f):
        if f[4] or f[5]:
            return f[4] in kept_trips and f[5] in kept_trips
        return f[0] in stop_universe and f[1] in stop_universe

    filter_table("transfers.txt", keep_transfer)
    filter_table("stops.txt", lambda f: f[0] in stop_universe)
    (work / "feed_info.txt").write_bytes(zf.read("feed_info.txt").lstrip(b"\xef\xbb\xbf"))

    stats["core_didok_numbers"] = len(core_numbers)
    stats["core_gtfs_stop_ids"] = len(core_stop_ids)
    stats["seconds"] = round(time.time() - t0, 1)
    (work / "extract_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
