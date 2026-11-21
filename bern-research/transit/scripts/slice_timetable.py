#!/usr/bin/env python3
"""Cut a date window out of data/<feed>/timetable.json: a smaller file with the same schema.

Usage:  python scripts/slice_timetable.py --feed fp2026 [--from 2026-11-21] [--to 2026-12-12]

Keeps every trip whose service runs on at least one day of the window, plus the day before
the window (trips that started the evening before and are still running after midnight).
Defaults: from = the day the GTFS file was retrieved, to = feed_end_date. For fp2026 that is
the rest of the 2026 timetable year, about a fifth of the full file.

Output: data/<feed>/timetable_<from>_<to>.json. Same structure and same reader as
timetable.json; meta.window says for which dates the file is complete. Service masks are
unchanged, so runs() answers correctly for any date, but trips that never run inside the
window are absent.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from common import CACHE, DATA


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True, choices=["fp2026", "fp2027"])
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    args = ap.parse_args()
    doc = json.loads((DATA / args.feed / "timetable.json").read_text(encoding="utf-8"))
    meta = doc["meta"]
    start = dt.date.fromisoformat(meta["feed_start_date"])
    end = dt.date.fromisoformat(meta["feed_end_date"])
    retrieved = json.loads((CACHE / f"gtfs_{args.feed}" / "source.json").read_text(encoding="utf-8"))["fetched_at_utc"][:10]
    d0 = max(start, dt.date.fromisoformat(args.date_from or retrieved))
    d1 = min(end, dt.date.fromisoformat(args.date_to or meta["feed_end_date"]))
    if d0 > d1:
        sys.exit(f"window {d0}..{d1} is empty for feed {args.feed} ({start}..{end})")
    i0, i1 = (d0 - start).days, (d1 - start).days
    window = 0
    for i in range(max(0, i0 - 1), i1 + 1):          # one day earlier: trips still running after midnight
        window |= 1 << i

    masks = [int(m, 16) for m in doc["services"]["masks"]]
    keep_service = [bool(m & window) for m in masks]
    new_service = {}
    patterns, pattern_map = [], {}
    for pi, p in enumerate(doc["patterns"]):
        t = p["t"]
        idx = [k for k, sv in enumerate(t["sv"]) if keep_service[sv]]
        if not idx:
            continue
        prof_map = {}
        q = {k: v for k, v in p.items() if k not in ("p", "t")}
        nt = {key: [vals[k] for k in idx] for key, vals in t.items()}
        nt["sv"] = [new_service.setdefault(sv, len(new_service)) for sv in nt["sv"]]
        nt["pf"] = [prof_map.setdefault(pf, len(prof_map)) for pf in nt["pf"]]
        q["p"] = [p["p"][old] for old, _ in sorted(prof_map.items(), key=lambda kv: kv[1])]
        q["t"] = nt
        pattern_map[pi] = (len(patterns), {old: new for new, old in enumerate(idx)})
        patterns.append(q)

    freqs = []
    for f in doc["frequencies"]:
        if f[0] in pattern_map and f[1] in pattern_map[f[0]][1]:
            freqs.append([pattern_map[f[0]][0], pattern_map[f[0]][1][f[1]], *f[2:]])
    order = sorted(new_service.items(), key=lambda kv: kv[1])
    n_trips = sum(len(p["t"]["id"]) for p in patterns)
    n_st = sum(len(p["s"]) * len(p["t"]["id"]) for p in patterns)
    out = dict(doc)
    out["meta"] = dict(meta, title=meta["title"] + f", window {d0} to {d1}",
                       window={"from": d0.isoformat(), "to": d1.isoformat(),
                               "note": "complete for these dates (including trips of the previous evening that run past midnight); "
                                       "trips that never run in the window are left out",
                               "derived_from": f"data/{args.feed}/timetable.json"},
                       counts=dict(meta["counts"], trips=n_trips, stop_times=n_st, patterns=len(patterns),
                                   time_profiles=sum(len(p["p"]) for p in patterns), services=len(order), frequencies=len(freqs)))
    out["services"] = {"ids": [doc["services"]["ids"][old] for old, _ in order], "masks": [doc["services"]["masks"][old] for old, _ in order]}
    out["patterns"] = patterns
    out["frequencies"] = freqs
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    text = text.replace(',"agencies":', ',\n"agencies":').replace(',"routes":', ',\n"routes":').replace(',"stations":', ',\n"stations":') \
               .replace(',"stops":[[', ',\n"stops":[[').replace(',"services":', ',\n"services":').replace(',"headsigns":', ',\n"headsigns":') \
               .replace(',"patterns":', ',\n"patterns":').replace('},{"r":', '},\n{"r":').replace(',"frequencies":', ',\n"frequencies":')
    path = DATA / args.feed / f"timetable_{d0}_{d1}.json"
    path.write_text(text + "\n", encoding="utf-8")
    print(f"{path.name}: {n_trips:,} of {meta['counts']['trips']:,} trips, {n_st:,} stop_times, {len(patterns):,} patterns, "
          f"{len(order):,} services, {path.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
