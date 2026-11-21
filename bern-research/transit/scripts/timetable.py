"""Reference decoder for data/<feed>/timetable.json (stdlib only).

    from timetable import Timetable
    tt = Timetable.load("fp2026")
    for d in tt.departures(8507110, "2026-11-23", "08:00:00", limit=10):   # Bern, Zytglogge
        print(d["time"], d["route"], d["headsign"], d["platform"])

The JavaScript twin is web/bern-transit.js; both are checked against each other by validate.py.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from common import DATA, hms_to_sec, sec_to_hms


class Timetable:
    def __init__(self, doc: dict):
        self.doc = doc
        self.meta = doc["meta"]
        self.start = dt.date.fromisoformat(self.meta["feed_start_date"])
        self.end = dt.date.fromisoformat(self.meta["feed_end_date"])
        self.routes = doc["routes"]
        self.agencies = doc["agencies"]
        self.stops = doc["stops"]                # [stop_id, number, edge_sloid, platform_code, lon, lat]
        self.stations = doc["stations"]          # number -> [sloid, name, tier]
        self.patterns = doc["patterns"]
        self.headsigns = doc["headsigns"]
        self.hints = doc["hints"]
        self.service_ids = doc["services"]["ids"]
        self.masks = [int(m, 16) for m in doc["services"]["masks"]]
        self.freq = {(f[0], f[1]): f for f in doc["frequencies"]}
        self._by_number = None

    @classmethod
    def load(cls, feed: str, data_dir: Path = DATA) -> "Timetable":
        return cls(json.loads((data_dir / feed / "timetable.json").read_text(encoding="utf-8")))

    # ---- calendar ----
    def day_index(self, date) -> int:
        if isinstance(date, str):
            date = dt.date.fromisoformat(date)
        return (date - self.start).days

    def runs(self, service: int, day_index: int) -> bool:
        return day_index >= 0 and (self.masks[service] >> day_index) & 1 == 1

    def service_dates(self, service: int) -> list[str]:
        m = self.masks[service]
        return [(self.start + dt.timedelta(days=i)).isoformat() for i in range(m.bit_length()) if (m >> i) & 1]

    # ---- decoding ----
    def seq(self, p: dict) -> list[int]:
        return p.get("q") or list(range(1, len(p["s"]) + 1))

    def stop_times(self):
        """Yield every stop_time exactly as in GTFS:
        (trip_id, arrival, departure, stop_id, stop_sequence, pickup_type, drop_off_type)."""
        for p in self.patterns:
            seq = self.seq(p)
            pu = p.get("pu") or [0] * len(seq)
            do = p.get("do") or [0] * len(seq)
            sids = [self.stops[i][0] for i in p["s"]]
            t = p["t"]
            for k, tid in enumerate(t["id"]):
                st = t["st"][k]
                prof = p["p"][t["pf"][k]]
                for j, sid in enumerate(sids):
                    yield (tid, sec_to_hms(st + prof[2 * j]), sec_to_hms(st + prof[2 * j + 1]), sid, seq[j], pu[j], do[j])

    def trips(self):
        """Yield every trip as a dict with the GTFS trips.txt fields."""
        for p in self.patterns:
            r = self.routes[p["r"]]
            t = p["t"]
            bl = t.get("bl")
            for k, tid in enumerate(t["id"]):
                yield {"route_id": r[0], "service_id": self.service_ids[t["sv"][k]], "trip_id": tid,
                       "trip_headsign": self.headsigns[p["h"]], "trip_short_name": t["sn"][k],
                       "direction_id": "" if p["d"] is None else str(p["d"]), "block_id": bl[k] if bl else "",
                       "original_trip_id": t["oid"][k], "hints": self.hints[t["hi"][k]]}

    # ---- queries ----
    def _index(self):
        if self._by_number is None:
            idx: dict[int, list] = {}
            for pi, p in enumerate(self.patterns):
                for j, si in enumerate(p["s"]):
                    idx.setdefault(self.stops[si][1], []).append((pi, j))
            self._by_number = idx
        return self._by_number

    def departures(self, number: int, date: str, time: str = "00:00:00", limit: int = 20,
                   window_sec: int = 6 * 3600, include_frequency: bool = False) -> list[dict]:
        """Scheduled departures from station `number` on calendar `date` from `time` (local wall clock).

        Looks at the service day `date` and at the previous service day (trips running past midnight,
        GTFS times >= 24:00:00). Rows whose pickup_type is 1 (no boarding) and final stops are skipped.
        Wall-clock conversion is plain addition; on the two DST-change days per year GTFS counts from
        noon minus 12 h, which shifts early-morning times by one hour (handled in web/bern-transit.js).
        """
        t0 = hms_to_sec(time)
        day = self.day_index(date)
        out = []
        for pi, j in self._index().get(number, []):
            p = self.patterns[pi]
            if j == len(p["s"]) - 1:
                continue
            if p.get("pu") and p["pu"][j] == 1:
                continue
            t = p["t"]
            stop = self.stops[p["s"][j]]
            route = self.routes[p["r"]]
            last = self.stops[p["s"][-1]]
            for k in range(len(t["id"])):
                is_freq = (pi, k) in self.freq
                if is_freq and not include_frequency:
                    continue
                dep = t["st"][k] + p["p"][t["pf"][k]][2 * j + 1]
                for back in (0, 1):                      # 0 = service day `date`, 1 = the day before
                    wall = dep - back * 86400
                    if not t0 <= wall < t0 + window_sec:
                        continue
                    if not self.runs(t["sv"][k], day - back):
                        continue
                    out.append({
                        "wall_sec": wall,
                        "time": sec_to_hms(wall),
                        "gtfs_time": sec_to_hms(dep),
                        "service_date": (dt.date.fromisoformat(date) - dt.timedelta(days=back)).isoformat(),
                        "route": route[2],
                        "route_desc": route[4],
                        "route_type": route[5],
                        "agency": self.agencies[route[1]][1],
                        "headsign": self.headsigns[p["h"]],
                        "last_stop": self.stations[str(last[1])][1],
                        "platform": stop[3],
                        "stop_id": stop[0],
                        "edge_sloid": stop[2],
                        "trip_id": t["id"][k],
                        "trip_short_name": t["sn"][k],
                        "original_trip_id": t["oid"][k],
                        "direction_id": p["d"],
                        "frequency_based": is_freq,
                    })
        out.sort(key=lambda d: (d["wall_sec"], d["route"], d["headsign"], d["trip_id"]))
        return out[:limit]

    def trips_running(self, date: str) -> int:
        day = self.day_index(date)
        return sum(1 for p in self.patterns for sv in p["t"]["sv"] if self.runs(sv, day))
