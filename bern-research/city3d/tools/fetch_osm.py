"""Fetch OSM ways for Bern public paths and bridges via Overpass (ODbL).

Usage: python -I fetch_osm.py <out.json>
Box = swissALTI3D mosaic (LV95 E2589000-2606000 N1194000-1205000) in WGS84.
"""
import json, sys, time, urllib.parse, urllib.request

BBOX = (46.89702, 7.29401, 46.99603, 7.51751)  # S, W, N, E
Q = f"""[out:json][timeout:180][bbox:{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}];
(
  way["highway"~"^(footway|path|pedestrian|steps|cycleway|living_street|track|bridleway|corridor|elevator)$"];
  way["footway"];
  way["bridge"]["bridge"!="no"];
  way["man_made"="bridge"];
  way["tunnel"]["highway"];
  way["highway"="footway"]["footway"="crossing"];
  node["highway"="elevator"];
  node["highway"="steps"];
);
out body geom qt;"""
MIRRORS = [
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
out = sys.argv[1]
for m in MIRRORS:
    try:
        t = time.time()
        req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": Q}).encode(),
                                     headers={"User-Agent": "bern-city3d-research/0.1"})
        raw = urllib.request.urlopen(req, timeout=240).read()
        d = json.loads(raw)
        d["_mirror"] = m
        d["_query"] = Q
        d["_retrieved"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        json.dump(d, open(out, "w", encoding="utf-8"))
        print(m, len(d["elements"]), "elements", f"{time.time()-t:.1f}s", "osm3s", d.get("osm3s"))
        break
    except Exception as e:
        print("failed", m, e)
