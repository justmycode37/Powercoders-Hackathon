#!/usr/bin/env python3
"""Write SOURCES.json: one record per input actually on disk in .cache/download/.

Fields per input: name, file, url, publisher, licence, retrieved, bytes, sha256,
used_for, filter.  Called at the end of fetch_sources.py; can be run on its own.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, ".cache")

OTD = "https://data.opentransportdata.swiss/en/dataset"
SBB = "https://data.sbb.ch/explore/dataset"
BERN = "https://map.bern.ch/arcgis/rest/services/Geoportal"
OVERPASS = "https://overpass.osm.ch/api/interpreter (fallback https://overpass-api.de/api/interpreter)"

OTD_TERMS = ("opentransportdata.swiss terms of use (https://opentransportdata.swiss/en/terms-of-use): "
             "free use, the source must be named")
SBB_TERMS = ("SBB open data licence (https://data.sbb.ch/page/licence), opendata.swiss terms_by: "
             "free use, the source must be named")
BERN_TERMS = ("opendata.swiss terms_open, publisher Geoinformation Stadt Bern: free use, naming the source is "
              "recommended. Listed distributions are WMS/WMTS/WFS; this project queried the same public ArcGIS service")
OSM_TERMS = "ODbL 1.0, (c) OpenStreetMap contributors (https://www.openstreetmap.org/copyright)"
SWISSTOPO_TERMS = "swisstopo open government data: free use, source 'swisstopo' must be named; API under fair use"

ATLAS_PUB = "SBB / Systemaufgaben Kundeninformation (opentransportdata.swiss, atlas)"
SBB_PUB = "SBB (data.sbb.ch)"
BERN_PUB = "Geoinformation Stadt Bern"
OSM_PUB = "OpenStreetMap contributors"

# (cache file prefix, name, publisher, url, licence, used_for)
REGISTRY = [
    ("atlas-service-point", "atlas service points (DiDok), actual date", ATLAS_PUB, f"{OTD}/service-point-v2", OTD_TERMS,
     "station ids (sloid, number), names, modes, coordinates"),
    ("atlas-traffic-point", "atlas traffic point elements (boarding edges and areas), actual date", ATLAS_PUB,
     f"{OTD}/traffic-point-v2", OTD_TERMS,
     "edge sloid, designation, coordinates, height, length, boarding height, compass direction"),
    ("atlas-sectors", "atlas sectors and sector groups, actual date", ATLAS_PUB, f"{OTD}/sectors-and-sector-groups-v2",
     OTD_TERMS, "sector marker points per edge"),
    ("atlas-prm-platform", "atlas PRM platform (accessibility per edge)", ATLAS_PUB, f"{OTD}/platform-v2", OTD_TERMS,
     "prm attributes on boarding edges"),
    ("atlas-prm-reference-point", "atlas PRM reference points", ATLAS_PUB, f"{OTD}/reference-point-v2", OTD_TERMS,
     "named access reference points (published without coordinates)"),
    ("atlas-prm-relation", "atlas PRM relations", ATLAS_PUB, f"{OTD}/relation-v2", OTD_TERMS,
     "step-free access between reference points and platforms"),
    ("atlas-prm-stop-point", "atlas PRM stop points", ATLAS_PUB, f"{OTD}/stop-point-v2", OTD_TERMS,
     "station-level accessibility notes"),
    ("sbb-21196_behig-haltekantepunkt", "BehiG Haltekantepunkt (kerb points every metre, LV95)", SBB_PUB,
     f"{SBB}/21196_behig-haltekantepunkt/", SBB_TERMS, "surveyed rail platform edge lines and kerb height classes"),
    ("sbb-21197_behig-haltekantesegment", "BehiG Haltekantesegment", SBB_PUB, f"{SBB}/21197_behig-haltekantesegment/",
     SBB_TERMS, "fetched for cross-checks; not used in the outputs yet"),
    ("sbb-sektortafel", "Haltestelle: Sektortafeln (sector boards)", SBB_PUB, f"{SBB}/sektortafel/", SBB_TERMS,
     "sector board positions per track"),
    ("sbb-perronoberflache", "Haltestelle: Perronoberflaeche", SBB_PUB, f"{SBB}/perronoberflache/", SBB_TERMS,
     "platform length cross-check in validate.py"),
    ("sbb-perron", "Haltestelle: Perronlaenge (Perronkoerper)", SBB_PUB, f"{SBB}/perron/", SBB_TERMS,
     "platform length cross-check in validate.py"),
    ("sbb-haltestelle-karte-trafimage", "Haltestelle: Uebersicht Bahnhofplaene Trafimage", SBB_PUB,
     f"{SBB}/haltestelle-karte-trafimage/", SBB_TERMS,
     "links to the official station plans (the plans themselves are linked, not copied)"),
    ("sbb-haltestelle-wartehallen", "Haltestelle: Wartehallen", SBB_PUB, f"{SBB}/haltestelle-wartehallen/", SBB_TERMS,
     "fetched; not used in the outputs yet"),
    ("sbb-haltestelle-uhr", "Haltestelle: Uhren", SBB_PUB, f"{SBB}/haltestelle-uhr/", SBB_TERMS,
     "clock points in focus stations"),
    ("sbb-billetautomat", "Haltestelle: Billettautomaten", SBB_PUB, f"{SBB}/billetautomat/", SBB_TERMS,
     "ticket machine points in focus stations"),
    ("sbb-haltestelle-visuell-taktile-sicherheitslinie", "Haltestelle: visuell-taktile Sicherheitslinie", SBB_PUB,
     f"{SBB}/haltestelle-visuell-taktile-sicherheitslinie/", SBB_TERMS, "fetched; not used in the outputs yet"),
    ("bern-haltestellen", "OeV-Haltestellen (kerb points with letter and lines)", BERN_PUB,
     f"{BERN}/Haltestellen/MapServer/0", BERN_TERMS, "cross-check of kerb letters; lines served per kerb"),
    ("bern-bahnhoefe", "Bahnhoefe", BERN_PUB, f"{BERN}/Bahnhoefe/MapServer/0", BERN_TERMS,
     "fetched; not used in the outputs yet"),
    ("bern-av-", "Amtliche Vermessung (cadastral survey), service 'Amtliche_Vermessung_farbig'", BERN_PUB,
     f"{BERN}/Amtliche_Vermessung_farbig/MapServer", BERN_TERMS,
     "surveyed outlines: Bahnsteig, Unterstand, Wichtige Treppe, Tunnel/Unterfuehrung, Unterirdisches Gebaeude, "
     "Gebaeude, Bruecke"),
    ("osm-city-transit", "OpenStreetMap via Overpass: platforms, stop positions, shelters, tracks", OSM_PUB, OVERPASS,
     OSM_TERMS, "platform lines and polygons, tram detection, shelters outside the city"),
    ("osm-city-roads", "OpenStreetMap via Overpass: road centrelines", OSM_PUB, OVERPASS, OSM_TERMS,
     "bearing and kerb side of constructed edges"),
    ("osm-detail-", "OpenStreetMap via Overpass: station detail (levels, indoor, steps, lifts, entrances, buildings)",
     OSM_PUB, OVERPASS, OSM_TERMS, "passages, stairs, escalators, lifts, entrances, levels, walk graph, building heights"),
]


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mtime(path: str) -> str:
    return dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_sources(study_area: dict | None = None) -> int:
    dl = os.path.join(CACHE, "download")
    rows = []
    for fn in sorted(os.listdir(dl)) if os.path.isdir(dl) else []:
        reg = next((r for r in REGISTRY if fn.startswith(r[0])), None)
        if not reg:
            continue
        path = os.path.join(dl, fn)
        rows.append(dict(
            name=reg[1] + (f" [{os.path.splitext(fn)[0]}]" if reg[0].endswith("-") else ""),
            file=f".cache/download/{fn}", url=reg[3], publisher=reg[2], licence=reg[4], retrieved=_mtime(path),
            bytes=os.path.getsize(path), sha256=_sha(path), used_for=reg[5],
            filter=("national file; trimmed to the study area in .cache/extract/" if fn.startswith("atlas-") else
                    "server-side bbox or radius query for the study area (see tools/fetch_sources.py)")))
    hc = os.path.join(CACHE, "extract", "swisstopo-heights.json")
    if os.path.exists(hc):
        rows.append(dict(
            name="swisstopo height service (swissALTI3D terrain, LN02), one request per point",
            file=".cache/extract/swisstopo-heights.json", url="https://api3.geo.admin.ch/rest/services/height",
            publisher="swisstopo", licence=SWISSTOPO_TERMS, retrieved=_mtime(hc), bytes=os.path.getsize(hc),
            sha256=_sha(hc), used_for="terrain_height_ln02_m on street-level edges, entrances and access points",
            filter="requested by tools/build_focus.py for exactly the points it needs; answers cached"))
    doc = dict(
        folder="bern-research/stations",
        generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        study_area=study_area,
        rebuild=["python tools/fetch_sources.py", "python tools/build_geometry.py", "python tools/build_focus.py",
                 "python tools/build_models.py", "python tools/validate.py"],
        note=("bytes and sha256 describe the files as downloaded into .cache/download/ (git-ignored). Overpass and "
              "ArcGIS answers are query results, so a later fetch can differ. Operator plans and photos are not "
              "inputs: see references.json (links only)."),
        sources=rows)
    with open(os.path.join(ROOT, "SOURCES.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"SOURCES.json: {len(rows)} inputs")
    return len(rows)


if __name__ == "__main__":
    write_sources()
