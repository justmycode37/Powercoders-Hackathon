#!/usr/bin/env python3
"""Fetch and trim the open source data used for the Bern station geometry.

Downloads go to .cache/download/ (git-ignored), study-area extracts to
.cache/extract/.  The run rewrites SOURCES.json (name, url, publisher, licence,
retrieved, bytes, sha256, used_for) from what is actually on disk.

Usage:  python tools/fetch_sources.py [--only atlas,sbb,osm,bern,photos] [--refresh]

Pure standard library; safe to re-run (cache is reused unless --refresh).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, ".cache")
RAW = os.path.join(CACHE, "extract")
UA = "Mozilla/5.0 (compatible; bern-station-geometry/0.1; open-data research client)"

# Study area: city of Bern plus the inner BERNMOBIL/RBS/BLS agglomeration ring.
BBOX_WGS = dict(south=46.895, west=7.335, north=46.995, east=7.520)
BBOX_LV95 = dict(e_min=2591500, e_max=2605800, n_min=1194000, n_max=1205200)



def detail_areas() -> dict:
    """slug -> (lat, lon, radius m) for the detailed OSM / cadastral pulls: the three priority stations plus the
    rule-based tier-2 list (needs the atlas extract, so the atlas part has to run first)."""
    import common
    return {slug: (a["centre_wgs"][0], a["centre_wgs"][1], a["radius"]) for slug, a in common.focus_areas().items()}


OTD = "https://data.opentransportdata.swiss/dataset"
ATLAS = {
    "service-point": f"{OTD}/39e5f264-257a-4f3f-bccc-5322c37058c5/resource/a5ea1c50-15fd-41d2-8ddc-511ac8ca26a3/download/actual-date-swiss-service-point.csv",
    "traffic-point": f"{OTD}/b06d90be-91c6-440e-ab97-09f579d2fad0/resource/c2cda870-8f8e-4463-984b-7351d7107228/download/actual-date-world-traffic-point.csv",
    "sectors": f"{OTD}/52c157d0-e6bc-406b-8e7d-63713aa28585/resource/be07f0bd-96c5-44d3-9896-cd46b32857c6/download/actual-date-sectors-and-sector-groups.csv",
    "prm-platform": f"{OTD}/8e5931a6-b4aa-456a-9be4-498f28168861/resource/19c170d0-b0a1-4837-8bbd-9c2704dc9131/download/actual-date-platform.csv",
    "prm-reference-point": f"{OTD}/11e86379-d543-40cc-9d58-11fc805946c1/resource/e080fe3a-10d8-451a-b9ba-6a86f40544da/download/actual-date-reference-point.csv",
    "prm-relation": f"{OTD}/fbc9efa2-eeb1-4d17-b94d-8b49e699149d/resource/6d6bc670-3df4-4485-b869-75779c8927d3/download/actual-date-relation.csv",
    "prm-stop-point": f"{OTD}/e73d185a-e445-450f-9800-f485c7721a37/resource/7df2dfcd-2c9d-47cf-a00a-f9bcabee6d15/download/actual-date-stop-point.csv",
}

SBB_API = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets"
# dataset id -> geo field used for the bbox filter (None = filter client side)
SBB = {
    "perron": "geopos",
    "perronoberflache": "geopos",
    "21196_behig-haltekantepunkt": "geopos",
    "21197_behig-haltekantesegment": "geopos",
    "sektortafel": "geopos",
    "haltestelle-karte-trafimage": "geopos",
    "haltestelle-wartehallen": "geopos",
    "haltestelle-uhr": "geopos",
    "billetautomat": "geopos",
    "haltestelle-visuell-taktile-sicherheitslinie": "geopos",
}

OVERPASS = [
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]


def http_get(url: str, data: bytes | None = None, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def cached(cache: str, name: str, url: str, refresh: bool, data: bytes | None = None) -> bytes:
    path = os.path.join(cache, name)
    if os.path.exists(path) and not refresh:
        with open(path, "rb") as f:
            return f.read()
    blob = http_get(url, data)
    with open(path, "wb") as f:
        f.write(blob)
    return blob


def in_lv95(e: str, n: str) -> bool:
    try:
        e_, n_ = float(e), float(n)
    except (TypeError, ValueError):
        return False
    b = BBOX_LV95
    return b["e_min"] <= e_ <= b["e_max"] and b["n_min"] <= n_ <= b["n_max"]


def write_csv(path: str, header: list[str], rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fetch_atlas(cache: str, refresh: bool, log: dict) -> None:
    out = os.path.join(RAW, "atlas")
    tables: dict[str, tuple[list[str], list[dict]]] = {}
    for name, url in ATLAS.items():
        blob = cached(cache, f"atlas-{name}.csv", url, refresh)
        rd = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")), delimiter=";")
        tables[name] = (rd.fieldnames or [], list(rd))
        print(f"  atlas {name}: {len(tables[name][1])} rows national")

    # operating points that are not stop points can still own boarding edges (e.g. Bern Europaplatz Sued)
    edge_parents = {r["parentSloidServicePoint"] for r in tables["traffic-point"][1]
                    if r["trafficPointElementType"] == "BOARDING_PLATFORM" and in_lv95(r["lv95East"], r["lv95North"])}
    hdr, rows = tables["service-point"]
    sp = [r for r in rows if in_lv95(r["lv95East"], r["lv95North"])
          and (r["stopPoint"] == "true" or r["trafficPoint"] == "true" or r["sloid"] in edge_parents)]
    sp_sloids = {r["sloid"] for r in sp}
    sp_numbers = {r["number"] for r in sp}
    write_csv(os.path.join(out, "service-point.csv"), hdr, sp)

    hdr, rows = tables["traffic-point"]
    tp = [r for r in rows if r["parentSloidServicePoint"] in sp_sloids]
    tp_sloids = {r["sloid"] for r in tp}
    write_csv(os.path.join(out, "traffic-point.csv"), hdr, tp)

    hdr, rows = tables["sectors"]
    sec = [r for r in rows if r["trafficPointSloid"] in tp_sloids]
    write_csv(os.path.join(out, "sectors.csv"), hdr, sec)

    counts = {"service-point": len(sp), "traffic-point": len(tp), "sectors": len(sec)}
    for name, key in (("prm-platform", "parentSloidServicePoint"),
                      ("prm-reference-point", "parentSloidServicePoint"),
                      ("prm-relation", "parentSloidServicePoint")):
        hdr, rows = tables[name]
        keep = [r for r in rows if r[key] in sp_sloids]
        write_csv(os.path.join(out, f"{name}.csv"), hdr, keep)
        counts[name] = len(keep)
    hdr, rows = tables["prm-stop-point"]
    keep = [r for r in rows if r["sloid"] in sp_sloids or r["number"] in sp_numbers]
    write_csv(os.path.join(out, "prm-stop-point.csv"), hdr, keep)
    counts["prm-stop-point"] = len(keep)
    log["atlas"] = {"urls": ATLAS, "rows_kept": counts}
    print("  atlas kept:", counts)


def fetch_sbb(cache: str, refresh: bool, log: dict) -> None:
    out = os.path.join(RAW, "sbb")
    os.makedirs(out, exist_ok=True)
    b = BBOX_WGS
    counts = {}
    for ds, geo in SBB.items():
        where = f"in_bbox({geo}, {b['south']}, {b['west']}, {b['north']}, {b['east']})"
        url = f"{SBB_API}/{ds}/exports/json?" + urllib.parse.urlencode({"where": where, "limit": -1})
        try:
            blob = cached(cache, f"sbb-{ds}.json", url, refresh)
            recs = json.loads(blob)
        except Exception as ex:  # noqa: BLE001 - report and continue
            print(f"  sbb {ds}: FAILED {ex}")
            counts[ds] = f"failed: {ex}"
            continue
        with open(os.path.join(out, f"{ds}.json"), "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, separators=(",", ":"))
        counts[ds] = len(recs)
        print(f"  sbb {ds}: {len(recs)} records")
    log["sbb"] = {"api": SBB_API, "bbox_wgs84": BBOX_WGS, "records": counts}


def overpass(query: str, cache: str, name: str, refresh: bool) -> dict:
    path = os.path.join(cache, name)
    if os.path.exists(path) and not refresh:
        with open(path, "rb") as f:
            return json.loads(f.read())
    last = None
    for ep in OVERPASS:
        for attempt in range(2):
            try:
                blob = http_get(ep, urllib.parse.urlencode({"data": query}).encode(), timeout=400)
                d = json.loads(blob)
                if "elements" in d:
                    with open(path, "wb") as f:
                        f.write(blob)
                    return d
            except Exception as ex:  # noqa: BLE001
                last = ex
                time.sleep(5)
    raise RuntimeError(f"overpass failed for {name}: {last}")


def fetch_osm(cache: str, refresh: bool, log: dict) -> None:
    out = os.path.join(RAW, "osm")
    os.makedirs(out, exist_ok=True)
    b = BBOX_WGS
    bb = f"({b['south']},{b['west']},{b['north']},{b['east']})"
    city_q = f"""[out:json][timeout:300];
(
  nwr["public_transport"~"^(platform|stop_position|station|stop_area)$"]{bb};
  nwr["railway"~"^(platform|platform_edge|station|halt|tram_stop|subway_entrance|stop)$"]{bb};
  nwr["highway"~"^(bus_stop|platform)$"]{bb};
  nwr["amenity"="bus_station"]{bb};
  nwr["amenity"="shelter"]{bb};
  way["railway"~"^(tram|rail|light_rail|narrow_gauge)$"]{bb};
);
out body geom;"""
    d = overpass(city_q, cache, "osm-city-transit.json", refresh)
    with open(os.path.join(out, "city-transit.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    counts = {"city-transit": len(d["elements"])}
    print(f"  osm city-transit: {len(d['elements'])} elements")

    road_q = f"""[out:json][timeout:300];
way["highway"~"^(trunk|primary|secondary|tertiary|unclassified|residential|living_street|busway|service|pedestrian|trunk_link|primary_link|secondary_link|tertiary_link)$"]{bb};
out tags geom;"""
    d = overpass(road_q, cache, "osm-city-roads.json", refresh)
    slim = [dict(type="way", id=e["id"], tags={k: v for k, v in e.get("tags", {}).items()
                                                 if k in ("highway", "name", "oneway", "bus", "psv", "layer", "tunnel", "bridge")},
                 geometry=[dict(lat=round(g["lat"], 7), lon=round(g["lon"], 7)) for g in e["geometry"]])
            for e in d["elements"] if e.get("geometry")]
    with open(os.path.join(out, "city-roads.json"), "w", encoding="utf-8") as f:
        json.dump(dict(osm3s=d.get("osm3s"), elements=slim), f, ensure_ascii=False, separators=(",", ":"))
    counts["city-roads"] = len(slim)
    print(f"  osm city-roads: {len(slim)} ways")

    areas = detail_areas()
    for slug, (lat, lon, rad) in areas.items():
        ar = f"(around:{rad},{lat},{lon})"
        q = f"""[out:json][timeout:300];
(
  nwr["indoor"]{ar};
  nwr["level"]{ar};
  nwr["highway"~"^(footway|steps|pedestrian|elevator|corridor|path|service|platform|bus_stop)$"]{ar};
  nwr["entrance"]{ar};
  nwr["door"]{ar};
  nwr["building"]{ar};
  nwr["building:part"]{ar};
  nwr["conveying"]{ar};
  nwr["railway"]{ar};
  nwr["public_transport"]{ar};
  nwr["amenity"~"^(shelter|bus_station|taxi|bicycle_parking|toilets|ticket_validator|vending_machine)$"]{ar};
  nwr["man_made"="bridge"]{ar};
  nwr["covered"]{ar};
  nwr["bridge"]["highway"]{ar};
  nwr["tunnel"]["highway"]{ar};
);
out body geom;"""
        d = overpass(q, cache, f"osm-detail-{slug}.json", refresh)
        with open(os.path.join(out, f"detail-{slug}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        counts[f"detail-{slug}"] = len(d["elements"])
    print(f"  osm detail: {len(areas)} areas, {sum(v for k, v in counts.items() if k.startswith('detail-'))} elements")
    log["osm"] = {"endpoints": OVERPASS, "bbox_wgs84": BBOX_WGS, "detail_areas": areas, "elements": counts}


BERN_GIS = "https://map.bern.ch/arcgis/rest/services/Geoportal"
AV = f"{BERN_GIS}/Amtliche_Vermessung_farbig/MapServer"
# Cadastral survey (Amtliche Vermessung) layers.  "city" layers are pulled for
# the whole municipality, "focus" layers only around the priority stations.
AV_LAYERS = {
    "eo_flaeche_linie": (91, "city"),      # outlines: Bahnsteig, Unterstand, Treppe, Tunnel/Unterfuehrung, ...
    "eo_unterirdisch": (100, "city"),      # underground buildings (polygons)
    "eo_linie": (86, "city"),              # line objects (walls, narrow stairs ...)
    "eo_linie_bruecke": (87, "city"),
    "eo_flaeche_bahnbruecke": (92, "city"),
    "strassenbruecken": (94, "city"),
    "bahnbruecken": (95, "city"),
    "bb_gebaeude": (99, "focus"),          # building footprints
}
CITY_ENV = (2594000, 1196500, 2605000, 1204500)   # LV95 envelope of the municipality (generous)


def arcgis_query(layer_url: str, env: tuple, depth: int = 0) -> list[dict]:
    """Query one envelope; split into quadrants when the server truncates."""
    params = {
        "geometry": ",".join(str(v) for v in env), "geometryType": "esriGeometryEnvelope",
        "inSR": 2056, "outSR": 2056, "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*", "returnGeometry": "true", "f": "json",
    }
    d = json.loads(http_get(layer_url + "/query?" + urllib.parse.urlencode(params), timeout=120))
    if "error" in d:
        raise RuntimeError(str(d["error"]))
    feats = d.get("features", [])
    if d.get("exceededTransferLimit") or len(feats) >= 1000:
        if depth > 7:
            raise RuntimeError("too many features in a tiny envelope")
        x0, y0, x1, y1 = env
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        out = []
        for sub in ((x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)):
            out += arcgis_query(layer_url, sub, depth + 1)
        return out
    return feats


def lv95_env(lat: float, lon: float, rad: float) -> tuple:
    # good to ~1 m for this purpose (approximate swisstopo formulas)
    p = (lat * 3600 - 169028.66) / 10000
    l = (lon * 3600 - 26782.5) / 10000
    e = 2600072.37 + 211455.93 * l - 10938.51 * l * p - 0.36 * l * p * p - 44.54 * l ** 3
    n = 1200147.07 + 308807.95 * p + 3745.25 * l * l + 76.63 * p * p - 194.56 * l * l * p + 119.79 * p ** 3
    return (round(e - rad), round(n - rad), round(e + rad), round(n + rad))


def fetch_bern(cache: str, refresh: bool, log: dict) -> None:
    out = os.path.join(RAW, "bern")
    os.makedirs(out, exist_ok=True)
    counts = {}
    jobs = [("haltestellen", f"{BERN_GIS}/Haltestellen/MapServer/0", [(2590000, 1192000, 2608000, 1207000)]),
            ("bahnhoefe", f"{BERN_GIS}/Bahnhoefe/MapServer/0", [(2590000, 1192000, 2608000, 1207000)])]
    for name, (lid, scope) in AV_LAYERS.items():
        envs = [CITY_ENV]
        if scope != "city":         # only areas that touch the municipality envelope
            envs = [e for e in (lv95_env(la, lo, r + 60) for la, lo, r in detail_areas().values())
                    if e[2] > CITY_ENV[0] and e[0] < CITY_ENV[2] and e[3] > CITY_ENV[1] and e[1] < CITY_ENV[3]]
        jobs.append((f"av-{name}", f"{AV}/{lid}", envs))
    for name, url, envs in jobs:
        path = os.path.join(cache, f"bern-{name}.json")
        old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
        if old and not refresh and old.get("envelopes", [list(e) for e in envs]) == [list(e) for e in envs]:
            feats = old["features"]
        else:
            seen, feats = set(), []
            for env in envs:
                for f in arcgis_query(url, env):
                    oid = f["attributes"].get("Objectid", f["attributes"].get("OBJECTID"))
                    if oid in seen:
                        continue
                    seen.add(oid)
                    feats.append(f)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"layer": url, "crs": "EPSG:2056", "envelopes": [list(e) for e in envs], "features": feats}, fh,
                          ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(out, f"{name}.json"), "w", encoding="utf-8") as fh:
            json.dump({"layer": url, "crs": "EPSG:2056", "features": feats}, fh,
                      ensure_ascii=False, separators=(",", ":"))
        counts[name] = len(feats)
        print(f"  bern {name}: {len(feats)} features")
    log["bern"] = {"service": BERN_GIS, "features": counts}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.path.join(CACHE, "download"))
    ap.add_argument("--only", default="atlas,sbb,osm,bern")
    ap.add_argument("--refresh", action="store_true", help="ignore cache and download again")
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    log_path = os.path.join(RAW, "fetch-log.json")
    log = {}
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            log = json.load(f)
    log["retrieved_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log["bbox_lv95"] = BBOX_LV95
    for part in [x for x in a.only.split(",") if x and x != "none"]:
        print(f"[{part}]")
        {"atlas": fetch_atlas, "sbb": fetch_sbb, "osm": fetch_osm, "bern": fetch_bern}[part](a.cache, a.refresh, log)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    import sources_manifest
    sources_manifest.write_sources(dict(bbox_wgs84=BBOX_WGS, bbox_lv95=BBOX_LV95))
    return 0


if __name__ == "__main__":
    sys.exit(main())
