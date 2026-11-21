"""Stadt Bern kerb points ('OeV-Haltestellen', one point per kerb) as a second official position source.

Three uses, all reported in data/build-report.json under 'city_kerb_check':

1. Edges for which atlas publishes no coordinate: take the position of a city kerb of the same stop if exactly one
   city kerb carries the edge's public letter or operational number.  Nothing else is accepted as geometry.  When the
   stop has exactly one such edge and exactly one city kerb that no located atlas edge is nearest to, that kerb is
   recorded as 'city_kerb_candidate' (a property, not geometry): elimination is weaker than a matching label.
2. Located edges without a public letter in atlas: 'city_kerb_letter' when a lettered city kerb is the edge's nearest
   kerb, the edge is that kerb's nearest edge, and they are at most LETTER_M apart.  atlas 'designation' is untouched.
3. Independent check of the atlas coordinates: distance between each atlas edge and the city kerb it is paired with.
"""
from __future__ import annotations

import collections

import geo
from common import LICENCE, gj_point

LETTER_M = 6.0          # "a few metres": largest edge-to-kerb distance for adopting a city letter
PAIR_LINE_M = 6.0       # pairing by position: city kerb point to the edge line (less than a carriageway width)
PAIR_POINT_M = 12.0     # ... or to the atlas point when the edge has no line
CLAIM_M = 40.0          # a city kerb counts as taken when a located atlas edge has it as nearest kerb within this
CITY_SRC = "Stadt Bern OeV-Haltestellen (kerb points, Geoinformation Stadt Bern)"


def _edge_dist(e, q):
    """Distance from point q to an edge: to its line if it has one, else to its atlas point."""
    if e.get("_line"):
        return geo.line_project(q, e["_line"])[0]
    return geo.dist(q, e["_P"])


def _pct(v, q):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(len(v) * q))], 1) if v else None


def apply_city_kerbs(edges: list[dict], kerbs_by_station: dict) -> dict:
    by_station = collections.defaultdict(list)
    for e in edges:
        by_station[e["properties"]["station_number"]].append(e)

    filled, not_filled, candidates, letters, disagreements = [], [], [], [], []
    n_by_letter = n_by_position = 0
    name_diffs, unpaired = [], []
    pairs_letter, pairs_mutual = [], []
    letter_sets = []
    for num, es in by_station.items():
        ks = kerbs_by_station.get(num, [])
        located = [e for e in es if e.get("_P")]
        missing = [e for e in es if e["geometry"] is None]

        # nearest city kerb of every located edge, nearest located edge of every city kerb
        near_k = {}
        for e in located:
            if ks:
                k = min(ks, key=lambda k: _edge_dist(e, k["xy"]))
                near_k[id(e)] = (k, _edge_dist(e, k["xy"]))
        near_e = {}
        for k in ks:
            if located:
                e = min(located, key=lambda e: _edge_dist(e, k["xy"]))
                near_e[k["oid"]] = (e, _edge_dist(e, k["xy"]))
        claimed = {k["oid"] for k, d in near_k.values() if d <= CLAIM_M}

        # 1) edges without atlas coordinates
        for e in missing:
            p = e["properties"]
            labels = {x for x in (p.get("designation"), p.get("designation_operational")) if x}
            hits = [k for k in ks if k["kante"] and k["kante"] in labels]
            row = dict(edge_sloid=p["edge_sloid"], station_number=num, station_name=p["station_name"],
                       designation=p.get("designation"), designation_operational=p.get("designation_operational"),
                       city_kerbs_at_stop=len(ks), city_kerb_labels=sorted({k["kante"] for k in ks if k["kante"]}))
            if len(hits) == 1:
                k = hits[0]
                e["geometry"] = gj_point(k["xy"])
                p.update(geometry_method="city_kerb_point", geometry_quality="official_city_point",
                         source=CITY_SRC, source_id=f"Objectid {k['oid']}", licence=LICENCE["bern"], inferred=True,
                         inferred_how=("atlas publishes no coordinate for this edge; position taken from the only city kerb "
                                       f"point of the same stop (Id_opendata {num}) whose label '{k['kante']}' equals the "
                                       "edge's designation or operational designation"),
                         lv95_e=round(k["xy"][0], 3), lv95_n=round(k["xy"][1], 3),
                         position_note="lv95_e / lv95_n are the city kerb point, not an atlas coordinate",
                         lines_at_kerb=k["lines"] or None,
                         lines_at_kerb_source="Stadt Bern Haltestellen (Nummer_nach)" if k["lines"] else None)
                p.pop("note", None)
                e["_P"] = k["xy"]
                filled.append(dict(row, city_objectid=k["oid"], city_label=k["kante"]))
                continue
            if not ks:
                why = "the city layer has no kerb point for this stop number"
            elif len(hits) > 1:
                why = f"{len(hits)} city kerbs of this stop carry a matching label; ambiguous"
            elif not any(k["kante"] for k in ks):
                why = (f"the city layer has {len(ks)} kerb point(s) for this stop but none carries a letter or number, "
                       "so nothing can be matched to the edge's designation")
            else:
                why = (f"none of the city kerb labels {sorted({k['kante'] for k in ks if k['kante']})} equals the edge's "
                       f"designation {sorted(labels) or 'none'}")
            p["no_geometry_reason"] = "atlas publishes no coordinate; " + why
            row["reason"] = why
            free = [k for k in ks if k["oid"] not in claimed]
            if len(missing) == 1 and len(free) == 1:
                k = free[0]
                lon, lat = geo.lv95_to_wgs84(*k["xy"])
                p["city_kerb_candidate"] = dict(
                    lon=round(lon, 7), lat=round(lat, 7), lv95_e=round(k["xy"][0], 3), lv95_n=round(k["xy"][1], 3),
                    objectid=k["oid"], label=k["kante"] or None, lines=k["lines"] or None, source=CITY_SRC,
                    rule=("by elimination, not by label: this is the stop's only edge without an atlas coordinate, and this "
                          f"is the stop's only city kerb point that no located atlas edge is nearest to (within {CLAIM_M:g} m). "
                          "Not used as geometry"))
                row["city_kerb_candidate_objectid"] = k["oid"]
                candidates.append(row)
            not_filled.append(row)

        # pairing by position, for edges that were not paired by letter in the main loop: the city kerb nearest to
        # the edge (to its line, if it has one), provided the edge is also that kerb's nearest edge.  The paired kerb
        # supplies 'lines_at_kerb' (lines and destinations served at that kerb).
        lettered = {k["kante"] for k in ks if k["kante"]}
        for e in located:
            p = e["properties"]
            if p.get("designation") and p["designation"] in lettered:
                n_by_letter += 1
                continue
            if id(e) not in near_k:
                continue
            k, d = near_k[id(e)]
            back, dback = near_e[k["oid"]]
            limit = PAIR_LINE_M if e.get("_line") else PAIR_POINT_M
            mutual = back is e or abs(dback - d) <= 0.5
            if d <= limit and mutual:
                p["verified_against"] = (p.get("verified_against") or []) + [dict(
                    source="Stadt Bern Haltestellen",
                    match="same station number; nearest city kerb point to the edge and the edge is that kerb's nearest edge",
                    kante=k["kante"] or None, dist_m=round(d, 1),
                    atlas_point_dist_m=round(geo.dist(e["_P"], k["xy"]), 1), objectid=k["oid"])]
                if k["lines"]:
                    p["lines_at_kerb"] = k["lines"]
                    p["lines_at_kerb_source"] = ("Stadt Bern Haltestellen (Nummer_nach), kerb paired by position "
                                                 f"({d:.1f} m from the edge, mutual nearest)")
                n_by_position += 1
                pairs_mutual.append(dict(edge_sloid=p["edge_sloid"], station_name=p["station_name"],
                                         atlas_point_to_city_kerb_m=round(geo.dist(e["_P"], k["xy"]), 1),
                                         edge_geometry_to_city_kerb_m=round(d, 1), geometry_method=p["geometry_method"]))
                if p.get("designation") and k["kante"] and k["kante"] != p["designation"]:
                    name_diffs.append(dict(edge_sloid=p["edge_sloid"], station_name=p["station_name"],
                                           atlas_designation=p["designation"], city_kerb_letter=k["kante"], dist_m=round(d, 1)))
            else:
                unpaired.append(dict(edge_sloid=p["edge_sloid"], station_name=p["station_name"],
                                     nearest_city_kerb_m=round(d, 1), mutual_nearest=mutual))

        # 2) city letter for located edges that have none in atlas
        for e in located:
            p = e["properties"]
            if p.get("designation") or id(e) not in near_k:
                continue
            k, d = near_k[id(e)]
            if not k["kante"] or d > LETTER_M:
                continue
            # the kerb's nearest edge must be this edge, or a record lying at the same place (duplicate atlas records)
            back, dback = near_e[k["oid"]]
            if back is not e and abs(_edge_dist(e, k["xy"]) - dback) > 0.5:
                continue
            twin = next((o["properties"]["edge_sloid"] for o in located
                         if o is not e and o["properties"].get("designation") == k["kante"]), None)
            p["city_kerb_letter"] = k["kante"]
            p["city_kerb_letter_dist_m"] = round(d, 1)
            p["city_kerb_letter_source"] = CITY_SRC + f", Objectid {k['oid']}"
            p["city_kerb_letter_how"] = (
                f"nearest city kerb point of this stop, {d:.1f} m from the edge (limit {LETTER_M:g} m), and no other located "
                "edge of the stop is nearer to that kerb; atlas has no public letter for this edge"
                + (f". atlas edge {twin} carries the same letter as its designation" if twin else ""))
            letters.append(dict(edge_sloid=p["edge_sloid"], station_name=p["station_name"],
                                designation_operational=p.get("designation_operational"), city_kerb_letter=k["kante"],
                                dist_m=round(d, 1), atlas_edge_with_same_letter=twin))

        # 3) accuracy pairs and letter disagreements
        lettered_k = {k["kante"]: k for k in ks if k["kante"]}
        atlas_letters = sorted({e["properties"]["designation"] for e in located if e["properties"].get("designation")})
        if lettered_k and atlas_letters:
            letter_sets.append(dict(station_number=num, station_name=es[0]["properties"]["station_name"],
                                    atlas=atlas_letters, city=sorted(lettered_k),
                                    only_atlas=sorted(set(atlas_letters) - set(lettered_k)),
                                    only_city=sorted(set(lettered_k) - set(atlas_letters))))
        for e in located:
            p = e["properties"]
            dg = p.get("designation")
            if dg and dg in lettered_k:
                k = lettered_k[dg]
                d_pt, d_ln = geo.dist(e["_P"], k["xy"]), _edge_dist(e, k["xy"])
                pairs_letter.append(dict(edge_sloid=p["edge_sloid"], station_name=p["station_name"], letter=dg,
                                         atlas_point_to_city_kerb_m=round(d_pt, 1), edge_geometry_to_city_kerb_m=round(d_ln, 1),
                                         geometry_method=p["geometry_method"]))
                # disagreement: another lettered city kerb is clearly nearer to this edge than its own letter
                other = min((o for o in lettered_k.values() if o is not k), key=lambda o: _edge_dist(e, o["xy"]), default=None)
                if other and _edge_dist(e, other["xy"]) + 5.0 < d_ln:
                    disagreements.append(dict(
                        edge_sloid=p["edge_sloid"], station_name=p["station_name"], atlas_letter=dg,
                        city_kerb_of_that_letter_m=round(d_ln, 1), nearest_city_kerb_letter=other["kante"],
                        nearest_city_kerb_m=round(_edge_dist(e, other["xy"]), 1)))

    def dist_summary(pairs):
        a = [x["atlas_point_to_city_kerb_m"] for x in pairs]
        b = [x["edge_geometry_to_city_kerb_m"] for x in pairs]
        return dict(
            n=len(pairs),
            atlas_point_to_city_kerb_m=dict(median=_pct(a, .5), p75=_pct(a, .75), p90=_pct(a, .9), p95=_pct(a, .95), max=max(a) if a else None),
            edge_geometry_to_city_kerb_m=dict(median=_pct(b, .5), p75=_pct(b, .75), p90=_pct(b, .9), p95=_pct(b, .95), max=max(b) if b else None),
            within_m={f"{t}": sum(1 for x in a if x <= t) for t in (2, 5, 10, 20, 30)},
            worst_ten=sorted(pairs, key=lambda x: -x["atlas_point_to_city_kerb_m"])[:10])

    n_kerbs = sum(len(v) for v in kerbs_by_station.values())
    return dict(
        source=CITY_SRC, licence=LICENCE["bern"],
        city_layer=dict(kerb_points=n_kerbs, with_letter=sum(1 for v in kerbs_by_station.values() for k in v if k["kante"]),
                        stops=len(kerbs_by_station),
                        note="the layer carries a kerb letter only at stops with several lettered kerbs; it has no kerb numbers"),
        edges_without_atlas_coordinates=dict(
            total=len(filled) + len(not_filled), filled_from_city_kerb=len(filled), left_without_geometry=len(not_filled),
            rule="exactly one city kerb of the same stop carries the edge's designation or operational designation",
            filled=filled, not_filled=not_filled,
            candidates_by_elimination=dict(count=len(candidates), note="recorded as the property 'city_kerb_candidate', not as geometry",
                                           edges=[c["edge_sloid"] for c in candidates])),
        pairing=dict(
            by_station_and_letter=n_by_letter, by_position=n_by_position,
            rule_by_position=(f"city kerb point nearest to the edge, at most {PAIR_LINE_M:g} m from its line ({PAIR_POINT_M:g} m from "
                              "the atlas point when the edge has no line), and the edge is that kerb's nearest edge"),
            located_edges_at_city_stops_left_unpaired=len(unpaired),
            unpaired_note="no city kerb within the limit, or the nearest kerb is nearer to another edge; these edges get no lines_at_kerb",
            unpaired_nearest_city_kerb_m=dict(median=_pct([u["nearest_city_kerb_m"] for u in unpaired], .5),
                                              p90=_pct([u["nearest_city_kerb_m"] for u in unpaired], .9),
                                              over_40_m=sum(1 for u in unpaired if u["nearest_city_kerb_m"] > 40)),
            unpaired_farthest_ten=sorted(unpaired, key=lambda u: -u["nearest_city_kerb_m"])[:10],
            same_kerb_other_letter=name_diffs),
        city_kerb_letters_added=dict(count=len(letters), limit_m=LETTER_M, edges=letters),
        atlas_vs_city_distance=dict(
            note=("independent check of the atlas coordinates. Pairs by letter are independent of position, so their "
                  "distances are an unbiased check; pairs by position were selected within the pairing limit of the edge "
                  "line, so only their atlas-point distance is informative. The city point and the atlas point need not "
                  "mark the same place along a kerb. 'edge_geometry_to_city_kerb_m' is the distance from the city point "
                  "to this folder's edge line."),
            same_station_and_letter=dist_summary(pairs_letter),
            paired_by_position=dist_summary(pairs_mutual)),
        letter_disagreements=dict(
            rule="an edge whose atlas letter exists in the city layer, but another lettered city kerb is more than 5 m nearer to the edge",
            count=len(disagreements), edges=disagreements),
        letter_sets_per_stop=letter_sets)
