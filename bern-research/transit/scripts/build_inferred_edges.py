#!/usr/bin/env python3
"""Infer the boarding edge for stop_times that name only the station (tier bern).

Usage:  python scripts/build_inferred_edges.py --feed fp2026      (after build_timetable.py)

About 2 % of the stop_times at Bern stops reference the station SLOID instead of an edge.
This script writes a SEPARATE, inferred table; it changes no other file.

Rule (bearing vs compass): for a station-level stop followed by another stop, take every
boarding edge of that station that has a coordinate and an atlas compass direction and is
valid during the feed. For each candidate compute the difference between its compass
direction and the bearing from the edge to the next stop of the trip. Accept the best edge
only when its difference is at most BEST_MAX degrees and the second-best edge is at least
MARGIN_MIN degrees worse. Everything else stays unresolved, with the reason.

The same rule is back-tested on the stop_times at Bern stops where GTFS does name the edge.

Output: data/<feed>/inferred_edges.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys

from common import DATA, bearing_deg

BEST_MAX = 50.0        # best candidate may differ from the travel bearing by at most this many degrees
MARGIN_MIN = 60.0      # and the second-best candidate must be at least this much worse
HIGH_BEST_MAX = 25.0   # confidence "high": best within 25 degrees, margin at least 120, exactly two candidate edges,
HIGH_MARGIN_MIN = 120.0  # and no edge of the stop without compass direction or coordinate
RULE = (f"bearing-vs-compass: atlas compass_direction_deg of each boarding edge of the stop compared with the bearing from that "
        f"edge to the next stop of the trip; accepted when the best difference is <= {BEST_MAX:g} degrees and the second-best "
        f"edge is >= {MARGIN_MIN:g} degrees worse")


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decide(cands, lacking, next_lon, next_lat):
    """cands: [(edge_sloid, lon, lat, compass)]. Returns (edge | None, reason | None, best, second, confidence)."""
    if len(cands) < 2:
        return None, None, None, None, None
    scored = sorted((angle_diff(c[3], bearing_deg(c[1], c[2], next_lon, next_lat)), c[0]) for c in cands)
    best, second = scored[0][0], scored[1][0]
    if best <= BEST_MAX and second - best >= MARGIN_MIN:
        high = best <= HIGH_BEST_MAX and second - best >= HIGH_MARGIN_MIN and len(cands) == 2 and lacking == 0
        return scored[0][1], None, round(best, 1), round(second, 1), "high" if high else "medium"
    return None, "ambiguous", round(best, 1), round(second, 1), None


def infer(doc: dict, edge_feats: list) -> tuple[list, dict]:
    """Returns (records for station-level stops at tier-bern stations, back-test on stops with a known edge)."""
    meta = doc["meta"]
    f0, f1 = meta["feed_start_date"], meta["feed_end_date"]
    by_station = collections.defaultdict(lambda: {"cands": [], "lacking": 0, "edges": 0})
    desig = {}
    for f in edge_feats:
        p = f["properties"]
        if p["type"] != "BOARDING_PLATFORM" or p["valid_to"] < f0 or p["valid_from"] > f1:
            continue                                   # boarding areas and edges not valid during the feed are no candidates
        s = by_station[p["station_sloid"]]
        s["edges"] += 1
        desig[p["sloid"]] = p["designation"] or p["designation_operational"]
        if f["geometry"] and p["compass_direction_deg"] is not None:
            s["cands"].append((p["sloid"], f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1], p["compass_direction_deg"]))
        else:
            s["lacking"] += 1
    stops, stations, routes = doc["stops"], doc["stations"], doc["routes"]
    days = [bin(int(m, 16)).count("1") for m in doc["services"]["masks"]]

    groups = {}
    bt = collections.defaultdict(lambda: [0, 0])                  # outcome -> [stop_times, trip_days]
    bt_class = collections.defaultdict(lambda: [0, 0, 0, 0])      # confidence -> [right st, right td, wrong st, wrong td]
    bt_wrong = collections.defaultdict(lambda: [0, 0, 0, 0])      # stop name -> [wrong st, wrong td, right st, right td]
    for p in doc["patterns"]:
        n_trips = len(p["t"]["id"])
        trip_days = sum(days[sv] for sv in p["t"]["sv"])
        route = routes[p["r"]]
        seq = p["s"]
        for j, si in enumerate(seq):
            stop = stops[si]
            st = stations[str(stop[1])]
            if st[2] != "bern":
                continue
            known = stop[2]
            station = by_station.get(st[0])
            nxt = stops[seq[j + 1]] if j + 1 < len(seq) else None
            edge = best = second = conf = None
            if nxt is None:
                reason = "last_stop_of_trip"
            elif station is None or station["edges"] == 0:
                reason = "no_edge_at_stop"
            elif station["edges"] == 1:
                reason = "one_edge_only"
            elif len(station["cands"]) < 2:
                reason = "edges_without_compass_or_coordinates"
            else:
                edge, reason, best, second, conf = decide(station["cands"], station["lacking"], nxt[4], nxt[5])
            if known:                                             # back-test: GTFS names the edge
                if edge is None:
                    outcome = reason
                elif edge == known:
                    outcome = "correct"
                else:
                    outcome = "wrong"
                bt[outcome][0] += n_trips
                bt[outcome][1] += trip_days
                if edge is not None:
                    k = 0 if edge == known else 2
                    bt_class[conf][k] += n_trips
                    bt_class[conf][k + 1] += trip_days
                    w = bt_wrong[(stop[1], st[1])]
                    k = 2 if edge == known else 0
                    w[k] += n_trips
                    w[k + 1] += trip_days
                continue
            key = (stop[0], route[2], route[4], p["d"], doc["headsigns"][p["h"]], nxt[0] if nxt else None)
            g = groups.get(key)
            if g is None:
                g = groups[key] = {
                    "stop_id": stop[0], "station_sloid": st[0], "number": stop[1], "stop_name": st[1],
                    "route": route[2], "route_desc": route[4], "direction_id": p["d"], "headsign": doc["headsigns"][p["h"]],
                    "next_stop_id": nxt[0] if nxt else None, "next_number": nxt[1] if nxt else None,
                    "next_name": stations[str(nxt[1])][1] if nxt else None,
                    "bearing_to_next_deg": round(bearing_deg(stop[4], stop[5], nxt[4], nxt[5]), 1) if nxt and (stop[4], stop[5]) != (nxt[4], nxt[5]) else None,
                    "status": "resolved" if edge else "unresolved",
                    "edge_sloid": edge, "edge_designation": desig.get(edge) if edge else None,
                    "unresolved_reason": reason,
                    "angle_diff_best_deg": best, "angle_diff_second_deg": second,
                    "candidate_edges": len(station["cands"]) if station else 0,
                    "edges_without_compass_or_coordinates": station["lacking"] if station else 0,
                    "confidence": conf,
                    "stop_times": 0, "trip_days": 0,
                    "inferred": True, "inferred_how": RULE,
                }
            g["stop_times"] += n_trips
            g["trip_days"] += trip_days
    records = sorted(groups.values(), key=lambda g: (g["number"], g["route"], str(g["direction_id"]), g["headsign"], str(g["next_stop_id"])))

    def pct(a, b):
        return round(100.0 * a / b, 2) if b else None
    decided_st = bt["correct"][0] + bt["wrong"][0]
    decided_td = bt["correct"][1] + bt["wrong"][1]
    total_st = sum(v[0] for v in bt.values())
    total_td = sum(v[1] for v in bt.values())
    backtest = {
        "what": "the same rule applied to stop_times at tier-bern stops where GTFS names the edge; the named edge is the truth",
        "stop_times": {k: v[0] for k, v in sorted(bt.items())},
        "trip_days": {k: v[1] for k, v in sorted(bt.items())},
        "decided_share_of_all_pct": {"stop_times": pct(decided_st, total_st), "trip_days": pct(decided_td, total_td)},
        "correct_among_decided_pct": {"stop_times": pct(bt["correct"][0], decided_st), "trip_days": pct(bt["correct"][1], decided_td)},
        "wrong_among_decided_pct": {"stop_times": pct(bt["wrong"][0], decided_st), "trip_days": pct(bt["wrong"][1], decided_td)},
        "ambiguous_share_of_all_pct": {"stop_times": pct(bt["ambiguous"][0], total_st), "trip_days": pct(bt["ambiguous"][1], total_td)},
        "by_confidence": {c: {"correct_stop_times": v[0], "wrong_stop_times": v[2], "correct_pct_stop_times": pct(v[0], v[0] + v[2]),
                              "correct_trip_days": v[1], "wrong_trip_days": v[3], "correct_pct_trip_days": pct(v[1], v[1] + v[3])}
                          for c, v in sorted(bt_class.items())},
        "stops_where_the_rule_is_wrong_most_often": [
            {"number": k[0], "stop_name": k[1], "wrong_stop_times": v[0], "wrong_trip_days": v[1],
             "correct_stop_times": v[2], "wrong_pct_stop_times": pct(v[0], v[0] + v[2])}
            for k, v in sorted(bt_wrong.items(), key=lambda kv: -kv[1][1]) if v[0]][:15],
    }
    return records, backtest


def summarise(records):
    res = collections.Counter()
    td = collections.Counter()
    for r in records:
        k = "resolved_" + r["confidence"] if r["status"] == "resolved" else r["unresolved_reason"]
        res[k] += r["stop_times"]
        td[k] += r["trip_days"]
    tot = sum(res.values())
    resolved = sum(v for k, v in res.items() if k.startswith("resolved_"))
    return {"groups": len(records), "groups_resolved": sum(1 for r in records if r["status"] == "resolved"),
            "station_level_stop_times": tot, "stop_times_resolved": resolved, "stop_times_unresolved": tot - resolved,
            "resolved_pct": round(100.0 * resolved / tot, 2) if tot else None,
            "stop_times_by_outcome": dict(sorted(res.items())), "trip_days_by_outcome": dict(sorted(td.items()))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True, choices=["fp2026", "fp2027"])
    args = ap.parse_args()
    tt_path = DATA / args.feed / "timetable.json"
    edges_path = DATA / "edges.geojson"
    doc = json.loads(tt_path.read_text(encoding="utf-8"))
    edge_feats = json.loads(edges_path.read_text(encoding="utf-8"))["features"]
    records, backtest = infer(doc, edge_feats)
    out = {
        "feed": args.feed,
        "description": "Inferred boarding edge for stop_times at tier-bern stops that reference only the station. One record per "
                       "(stop_id, route, direction_id, headsign, next stop). status = resolved (edge_sloid set) or unresolved "
                       "(unresolved_reason set). This table is an addition: timetable.json, the GTFS subset and "
                       "gtfs_stop_map are unchanged and stay the source of truth.",
        "inferred": True,
        "inferred_how": RULE,
        "method": {
            "rule": RULE,
            "thresholds": {"best_max_deg": BEST_MAX, "margin_min_deg": MARGIN_MIN,
                           "confidence_high": f"best <= {HIGH_BEST_MAX:g} deg, margin >= {HIGH_MARGIN_MIN:g} deg, exactly two candidate edges, no edge of the stop without compass or coordinate",
                           "confidence_medium": "every other accepted match"},
            "candidates": "atlas BOARDING_PLATFORM edges of the stop's station that are valid during the feed and have a coordinate and compass_direction_deg",
            "bearing": "initial great-circle bearing from the candidate edge to the next stop coordinate of the trip (straight line, not track or road)",
            "unresolved_reasons": {
                "no_edge_at_stop": "atlas holds no boarding edge for the stop (the Matte lift stations, Bern Europaplatz whose edges atlas files under another service point)",
                "one_edge_only": "atlas holds a single edge; it is not assumed to be the one",
                "edges_without_compass_or_coordinates": "fewer than two edges have both a coordinate and a compass direction",
                "ambiguous": "best edge further than the threshold from the travel bearing, or the second-best too close",
                "last_stop_of_trip": "no next stop, so no travel bearing",
            },
        },
        "sources": [
            {"path": f"data/{args.feed}/timetable.json", "sha256": sha256(tt_path), "origin": doc["meta"]["source"]},
            {"path": "data/edges.geojson", "sha256": sha256(edges_path), "origin": "atlas traffic-point-v2"},
        ],
        "summary": summarise(records),
        "back_test": backtest,
        "records": records,
    }
    path = DATA / args.feed / "inferred_edges.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace('},{"stop_id"', '},\n{"stop_id"') + "\n", encoding="utf-8")
    print(json.dumps({"summary": out["summary"], "back_test": backtest}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
