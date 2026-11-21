"""Surveyed kerb candidates for tram and bus edges inside the city of Bern.

The cadastral survey (Amtliche Vermessung) maps pavements ('Trottoir') and traffic islands ('Verkehrsinsel') as
land-cover polygons.  Where such a polygon boundary runs parallel to a boarding edge line and close to it, that
boundary stretch is the surveyed pavement edge next to the stop.  It is offered as a separate feature
('surveyed_kerb_candidate'), not as the edge geometry, because the survey does not say which boundary is the
boarding kerb and which is the back of the pavement.
"""
from __future__ import annotations

import collections

import geo
from common import LICENCE, Grid, closed_ring, esri_paths, feature, gj_line, read_json

SEARCH_M = 3.5        # a boundary must be this close to a sample point of the edge line
MIN_SHARE = 0.6       # share of sample points that must hit the same polygon ring
STEP_M = 2.0


def _ring_arc(closed, total, s0, s1, forward):
    if not forward:
        return _ring_arc(closed, total, s1, s0, True)[::-1]
    if s1 >= s0:
        return geo.line_substring(closed, s0, s1)
    return geo.line_substring(closed, s0, total) + geo.line_substring(closed, 0.0, s1)[1:]


def kerb_candidates(edges: list[dict]) -> tuple[list[dict], collections.Counter]:
    """edges: boarding-edge features that still carry '_line' (LV95).  Returns (features, counters) and writes a
    pointer onto each edge that got a candidate."""
    rep = collections.Counter()
    try:
        polys = read_json("bern/av-bb_trottoir_insel.json")["features"]
    except FileNotFoundError:
        return [], rep
    grid = Grid(40)
    for f in polys:
        a = f["attributes"]
        for path in esri_paths(f):
            ring = closed_ring(path)
            if not ring or len(ring) < 3:
                continue
            closed = ring + [ring[0]]
            grid.add(dict(oid=a["Objectid"], art=a["Art_beschrieb"].split("] ")[-1], closed=closed,
                          total=geo.line_length(closed)), ring)
    out = []
    for e in edges:
        p, line = e["properties"], e.get("_line")
        if not line or p["geometry_method"] not in ("osm_platform", "constructed") or "TRAIN" in (p.get("station_modes") or ""):
            continue
        rep["edges_tested"] += 1
        L = geo.line_length(line)
        n = max(4, int(L / STEP_M) + 1)
        samples = [(L * i / (n - 1), geo.line_interpolate(line, L * i / (n - 1))) for i in range(n)]
        hits = []
        for ch, q in samples:
            best = None
            for r in grid.near(q, SEARCH_M + 1):
                d, s, pt, _ = geo.line_project(q, r["closed"])
                if d <= SEARCH_M and (best is None or d < best[0]):
                    best = (d, r, s, pt, ch, q)
            hits.append(best)
        count = collections.Counter(id(h[1]) for h in hits if h)
        if not count:
            continue
        rid, k = count.most_common(1)[0]
        if k / n < MIN_SHARE:
            rep["rejected_too_few_samples_on_one_boundary"] += 1
            continue
        mine = [h for h in hits if h and id(h[1]) == rid]
        ring = mine[0][1]
        s0, s1 = mine[0][2], mine[-1][2]
        span = mine[-1][4] - mine[0][4]                      # length of the edge line between first and last hit
        fwd, back = (s1 - s0) % ring["total"], (s0 - s1) % ring["total"]
        forward = abs(fwd - span) <= abs(back - span)
        arc_len = fwd if forward else back
        if abs(arc_len - span) > max(6.0, 0.35 * span) or arc_len < 4.0:
            rep["rejected_boundary_not_parallel"] += 1
            continue
        arc = _ring_arc(ring["closed"], ring["total"], s0, s1, forward)
        ds = [h[0] for h in mine]
        mean_d = sum(ds) / len(ds)
        mid = mine[len(mine) // 2]
        side = None
        if p.get("platform_side_bearing_deg") is not None and geo.dist(mid[5], mid[3]) > 0.4:
            towards_platform = geo.angle_diff(geo.bearing(mid[5], mid[3]), p["platform_side_bearing_deg"]) < 90
            side = "towards the waiting area" if towards_platform else "towards the vehicle"
        elif geo.dist(mid[5], mid[3]) <= 0.4:
            side = "on the edge line"
        fid = f"{p['station_number']}:surveyed_kerb_candidate:{p['edge_sloid']}"
        out.append(feature(
            gj_line(geo.simplify(arc, 0.02)), id=fid, feature_type="surveyed_kerb_candidate",
            station_sloid=p["station_sloid"], station_number=p["station_number"], station_name=p["station_name"],
            edge_sloid=p["edge_sloid"], edge_designation=p.get("designation"), land_cover=ring["art"],
            length_m=round(arc_len, 1), edge_length_m=round(L, 1), share_of_edge_matched=round(k / n, 2),
            mean_offset_m=round(mean_d, 2), max_offset_m=round(max(ds), 2), offset_direction=side,
            edge_geometry_method=p["geometry_method"],
            geometry_quality="surveyed", dim_quality="surveyed",
            source="Stadt Bern Amtliche Vermessung, Bodenbedeckung '" + ring["art"] + "'",
            source_id=f"Objectid {ring['oid']}", licence=LICENCE["bern"], inferred=True,
            inferred_how=(f"stretch of the surveyed {ring['art']} boundary that runs within {SEARCH_M} m of the edge line "
                          f"for at least {int(MIN_SHARE * 100)} % of its length. The survey does not record whether this "
                          "boundary is the boarding kerb or the back of the pavement: check offset_direction and the "
                          "offsets before using it as the kerb")))
        p["surveyed_kerb_candidate"] = dict(id=fid, mean_offset_m=round(mean_d, 2), offset_direction=side,
                                            land_cover=ring["art"])
        if p["geometry_method"] == "osm_platform" and mean_d <= 1.0:
            p["verified_against"] = (p.get("verified_against") or []) + [dict(
                source="Stadt Bern Amtliche Vermessung, Bodenbedeckung '" + ring["art"] + "'",
                match="a surveyed pavement / traffic-island boundary runs along the OSM line",
                mean_offset_m=round(mean_d, 2), objectid=ring["oid"])]
            rep["osm_edges_confirmed_within_1m"] += 1
        rep["candidates"] += 1
        rep[f"candidates_for_{p['geometry_method']}"] += 1
    return out, rep
