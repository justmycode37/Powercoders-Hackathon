"""Shared loaders and GeoJSON helpers for the station geometry build."""
from __future__ import annotations

import csv
import html
import json
import os
import re

import geo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXTRACT = os.path.join(ROOT, ".cache", "extract")
DATA = os.path.join(ROOT, "data")

LICENCE = {
    "atlas": "opentransportdata.swiss terms of use (free use, source attribution)",
    "sbb": "SBB open data, opendata.swiss terms_by (free use, source attribution)",
    "bern": "Geoinformation Stadt Bern, opendata.swiss terms_open",
    "osm": "ODbL 1.0, (c) OpenStreetMap contributors",
    "constructed": "derived by this project from the cited inputs",
}

# Priority stations (tier 1), set by hand.  Everything else is selected by rule in focus_areas().
PRIORITY = {
    "bern-bahnhof": dict(title="Bern Bahnhof", numbers=["8507000", "8576646"],
                         centre_wgs=(46.94885, 7.43910), radius=430, tier=1),
    "zytglogge": dict(title="Bern, Zytglogge", numbers=["8507110"],
                      centre_wgs=(46.94790, 7.44765), radius=170, tier=1),
    "wankdorf": dict(title="Bern Wankdorf", numbers=["8516161", "8590129", "8595543"],
                     centre_wgs=(46.96770, 7.46540), radius=420, tier=1),
}
TIER2_MIN_EDGES = 4        # tram/bus stops with at least this many lettered kerbs become tier-2 focus areas
TIER2_RADIUS = dict(rail=230, hub=150)
_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "é": "e", "è": "e", "à": "a", "ß": "ss"})


def slugify(number: str, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.translate(_FOLD).lower()).strip("-")
    return f"{number}-{base}"


def focus_areas() -> dict:
    """Priority stations plus rule-based tier 2: every atlas rail station in the study area and every
    tram/bus stop with >= TIER2_MIN_EDGES lettered kerbs, unless it already lies inside another focus area."""
    areas = {k: dict(v) for k, v in PRIORITY.items()}
    try:
        sp = read_csv("atlas/service-point.csv")
        tp = read_csv("atlas/traffic-point.csv")
    except FileNotFoundError:
        return areas
    n_edges = {}
    for t in tp:
        if t["trafficPointElementType"] == "BOARDING_PLATFORM" and t["designation"].strip() and t["lv95East"]:
            n_edges[t["parentSloidServicePoint"]] = n_edges.get(t["parentSloidServicePoint"], 0) + 1
    centres = []
    for a in areas.values():
        lat, lon = a["centre_wgs"]
        centres.append((geo.wgs84_to_lv95(lon, lat), a["radius"]))
    taken = {n for a in areas.values() for n in a["numbers"]}
    cands = []
    for r in sp:
        if r["number"] in taken or not r["lv95East"]:
            continue
        rail = "TRAIN" in (r["meansOfTransport"] or "")
        k = n_edges.get(r["sloid"], 0)
        if (rail and r["stopPoint"] == "true") or k >= TIER2_MIN_EDGES:
            cands.append((0 if rail else 1, -k, r["number"], r, rail))
    for _, _, _, r, rail in sorted(cands, key=lambda c: c[:3]):
        P = (float(r["lv95East"]), float(r["lv95North"]))
        if any(geo.dist(P, c) < 0.6 * rad for c, rad in centres):
            continue            # already covered by a focus area
        rad = TIER2_RADIUS["rail" if rail else "hub"]
        lon, lat = geo.lv95_to_wgs84(*P)
        areas[slugify(r["number"], r["designationOfficial"])] = dict(
            title=r["designationOfficial"], numbers=[r["number"]], centre_wgs=(round(lat, 6), round(lon, 6)),
            radius=rad, tier=2, selected_because="atlas rail station" if rail else f"{n_edges.get(r['sloid'], 0)} lettered kerbs")
        centres.append((P, rad))
    return areas


def read_csv(name: str) -> list[dict]:
    with open(os.path.join(EXTRACT, name), encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def read_json(name: str):
    with open(os.path.join(EXTRACT, name), encoding="utf-8") as f:
        return json.load(f)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def strip_html(s: str | None) -> list[str]:
    """Stadt Bern 'Nummer_nach' is an HTML list -> plain list of 'line destination'."""
    if not s:
        return []
    items = re.findall(r"<li>(.*?)</li>", s, flags=re.S) or [s]
    return [html.unescape(re.sub(r"<[^>]+>", "", i)).strip() for i in items if i.strip()]


# --- OSM ---------------------------------------------------------------------
def osm_way_xy(el) -> list[tuple]:
    return [geo.wgs84_to_lv95(g["lon"], g["lat"]) for g in el.get("geometry", []) if g]


def osm_rings(el) -> list[list[tuple]]:
    """Outer rings (LV95) of a closed way or multipolygon relation."""
    if el["type"] == "way":
        xy = osm_way_xy(el)
        if len(xy) >= 4 and geo.dist(xy[0], xy[-1]) < 0.01:
            return [xy[:-1]]
        return []
    if el["type"] == "relation":
        parts = [osm_way_xy(m) for m in el.get("members", [])
                 if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
        rings, parts = [], [p for p in parts if len(p) >= 2]
        while parts:
            cur = parts.pop(0)
            changed = True
            while geo.dist(cur[0], cur[-1]) > 0.01 and changed:
                changed = False
                for i, p in enumerate(parts):
                    if geo.dist(cur[-1], p[0]) < 0.01:
                        cur += p[1:]
                    elif geo.dist(cur[-1], p[-1]) < 0.01:
                        cur += p[::-1][1:]
                    elif geo.dist(cur[0], p[-1]) < 0.01:
                        cur = p[:-1] + cur
                    elif geo.dist(cur[0], p[0]) < 0.01:
                        cur = p[::-1][:-1] + cur
                    else:
                        continue
                    parts.pop(i)
                    changed = True
                    break
            if len(cur) >= 4 and geo.dist(cur[0], cur[-1]) < 0.01:
                rings.append(cur[:-1])
        return rings
    return []


def osm_point(el):
    if el["type"] == "node":
        return geo.wgs84_to_lv95(el["lon"], el["lat"])
    return None


def osm_url(el) -> str:
    return f"https://www.openstreetmap.org/{el['type']}/{el['id']}"


def osm_id(el) -> str:
    return f"osm-{el['type']}-{el['id']}"


def parse_levels(v: str | None) -> list[float]:
    """OSM level tag ('-1;0', '0-2', '1.5') -> sorted list of numbers."""
    if v is None:
        return []
    out = set()
    for part in re.split(r"[;,]", str(v)):
        part = part.strip()
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", part)
        try:
            if m and float(m.group(1)) < float(m.group(2)):
                a, b = float(m.group(1)), float(m.group(2))
                x = a
                while x <= b:
                    out.add(x)
                    x += 1
            elif part:
                out.add(float(part))
        except ValueError:
            continue
    return sorted(int(x) if float(x).is_integer() else x for x in out)


# --- ArcGIS (Stadt Bern) ------------------------------------------------------
def esri_paths(f) -> list[list[tuple]]:
    g = f.get("geometry") or {}
    return [[(p[0], p[1]) for p in path] for path in g.get("paths", g.get("rings", []))]


def closed_ring(path, tol: float = 0.02):
    if len(path) >= 4 and geo.dist(path[0], path[-1]) <= tol:
        return path[:-1]
    return None


# --- GeoJSON out ---------------------------------------------------------------
def r7(v: float) -> float:
    return round(v, 7)


def to_wgs(p) -> list[float]:
    lon, lat = geo.lv95_to_wgs84(p[0], p[1])
    return [r7(lon), r7(lat)]


def gj_point(p):
    return {"type": "Point", "coordinates": to_wgs(p)}


def gj_line(line):
    return {"type": "LineString", "coordinates": [to_wgs(p) for p in line]}


def gj_polygon(ring, holes=()):
    def close(r):
        c = [to_wgs(p) for p in r]
        if c[0] != c[-1]:
            c.append(c[0])
        return c
    if geo.ring_area(ring) < 0:
        ring = ring[::-1]
    return {"type": "Polygon", "coordinates": [close(ring)] + [close(h) for h in holes]}


def write_geojson(path: str, features: list[dict], meta: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fc = {"type": "FeatureCollection", "name": os.path.splitext(os.path.basename(path))[0],
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
          "metadata": meta, "features": features}
    with open(path, "w", encoding="utf-8") as f:
        f.write('{"type":"FeatureCollection","name":%s,"crs":%s,"metadata":%s,"features":[\n' % (
            json.dumps(fc["name"]), json.dumps(fc["crs"]), json.dumps(meta, ensure_ascii=False)))
        for i, ft in enumerate(features):
            f.write(json.dumps(ft, ensure_ascii=False, separators=(",", ":")))
            f.write(",\n" if i < len(features) - 1 else "\n")
        f.write("]}\n")


def feature(geometry: dict, **props) -> dict:
    return {"type": "Feature", "id": props.get("id"), "geometry": geometry,
            "properties": {k: v for k, v in props.items() if v is not None}}


class Grid:
    """Tiny spatial index: items registered by bbox, queried by point + radius."""

    def __init__(self, cell: float = 50.0):
        self.cell = cell
        self.cells: dict[tuple, list] = {}

    def add(self, item, pts) -> None:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        c = self.cell
        for i in range(int(min(xs) // c), int(max(xs) // c) + 1):
            for j in range(int(min(ys) // c), int(max(ys) // c) + 1):
                self.cells.setdefault((i, j), []).append(item)

    def near(self, p, r: float) -> list:
        c = self.cell
        out, seen = [], set()
        for i in range(int((p[0] - r) // c), int((p[0] + r) // c) + 1):
            for j in range(int((p[1] - r) // c), int((p[1] + r) // c) + 1):
                for it in self.cells.get((i, j), ()):
                    if id(it) not in seen:
                        seen.add(id(it))
                        out.append(it)
        return out
