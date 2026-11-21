#!/usr/bin/env python3
"""Optional: fetch GTFS Realtime trip updates and keep those that match the Bern timetable.

Usage:  set OTD_API_KEY=<your key>          (never write the key into a file)
        python scripts/gtfs_rt.py --feed fp2026

STATUS: NOT RUN. No API key is configured on the machine this folder was built on, so this
script has never talked to the live endpoint. The request shape follows the publisher's
cookbook (https://opentransportdata.swiss/en/cookbook/realtime-prediction-cookbook/gtfs-rt/);
the JSON field names below follow the GTFS Realtime specification and may need adjusting on
first contact. Without OTD_API_KEY the script exits with code 2 and does nothing.

Endpoint  GET https://api.opentransportdata.swiss/la/gtfs-rt?format=JSON
Headers   Authorization: Bearer <key>, User-Agent: any value, Accept-Encoding: gzip
Limits    2 requests per minute per key (sliding window); the free tier lists 5 per minute
Matching  A trip update refers to trip_id + start_date of the GTFS static feed that is valid on
          that day; stop_time_update.stop_id uses the same ids as stop_times.txt. Both are kept
          verbatim in data/<feed>/timetable.json (patterns[].t.id, stops[][0]), so the join is
          direct. The publisher states that each realtime feed belongs to one static feed
          and that a new static feed is activated for realtime at about 08:00 the next day,
          so rebuild the static data (run_all.py) when the weekly static file changes.

Output    data/<feed>/realtime_sample.json: trip updates for trips in the Bern subset with the
          delay per stop, the edge SLOID and the scheduled time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import sys
import urllib.request

from common import DATA, USER_AGENT
from timetable import Timetable

URL = "https://api.opentransportdata.swiss/la/gtfs-rt?format=JSON"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", default="fp2026", choices=["fp2026", "fp2027"])
    args = ap.parse_args()
    key = os.environ.get("OTD_API_KEY")
    if not key:
        print("blocked: OTD_API_KEY is not set. Get a key at https://api-manager.opentransportdata.swiss/ "
              "(product GTFS Realtime), then set it in the environment.", file=sys.stderr)
        return 2

    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    feed = json.loads(raw.decode("utf-8"))

    tt = Timetable.load(args.feed)
    ours = {}
    for pi, p in enumerate(tt.patterns):
        for ti, tid in enumerate(p["t"]["id"]):
            ours[tid] = (pi, ti)
    edge_of = {s[0]: s[2] for s in tt.stops}

    def get(d, *names):
        for n in names:
            if n in d:
                return d[n]
        return None

    kept = []
    entities = get(feed, "entity", "Entity") or []
    for ent in entities:
        tu = get(ent, "tripUpdate", "trip_update", "TripUpdate")
        if not tu:
            continue
        trip = get(tu, "trip", "Trip") or {}
        tid = get(trip, "tripId", "trip_id", "TripId")
        if tid not in ours:
            continue
        pi, ti = ours[tid]
        p = tt.patterns[pi]
        updates = []
        for stu in get(tu, "stopTimeUpdate", "stop_time_update", "StopTimeUpdate") or []:
            sid = get(stu, "stopId", "stop_id", "StopId")
            dep = get(stu, "departure", "Departure") or {}
            arr = get(stu, "arrival", "Arrival") or {}
            updates.append({"stop_id": sid, "edge_sloid": edge_of.get(sid),
                            "stop_sequence": get(stu, "stopSequence", "stop_sequence", "StopSequence"),
                            "arrival_delay_s": get(arr, "delay", "Delay"), "departure_delay_s": get(dep, "delay", "Delay"),
                            "schedule_relationship": get(stu, "scheduleRelationship", "schedule_relationship", "ScheduleRelationship")})
        kept.append({"trip_id": tid, "start_date": get(trip, "startDate", "start_date", "StartDate"),
                     "route": tt.routes[p["r"]][2], "headsign": tt.headsigns[p["h"]],
                     "original_trip_id": p["t"]["oid"][ti],
                     "schedule_relationship": get(trip, "scheduleRelationship", "schedule_relationship", "ScheduleRelationship"),
                     "stop_time_updates": updates})
    out = DATA / args.feed / "realtime_sample.json"
    out.write_text(json.dumps({
        "source": "opentransportdata.swiss GTFS Realtime (https://api.opentransportdata.swiss/la/gtfs-rt)",
        "retrieved": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "static_feed": tt.meta["source"],
        "entities_in_feed": len(entities), "matched_to_bern_subset": len(kept),
        "inferred": False,
        "trip_updates": kept,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(kept)} of {len(entities)} entities match the Bern subset -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
