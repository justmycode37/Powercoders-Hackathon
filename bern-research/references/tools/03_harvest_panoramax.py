"""Harvest georeferenced street-level photos from the Panoramax federation (STAC API, no key needed)
around every stop point in data/stations.json. Records position, compass azimuth, field of view,
capture time, licence and producer per picture. Writes data/panoramax_items.json.
Usage: python -I -X utf8 tools/03_harvest_panoramax.py
"""
import sys, os, math, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, load, save

API = "https://api.panoramax.xyz/api/search"
ST = load("stations.json")["stations"]
HUBS = {8507000: 300, 8576646: 200, 8507110: 120, 8516161: 250, 8588699: 150, 8590129: 150, 8504108: 200, 8580939: 120}


def bbox(lat, lon, r):
    dlat = r / 111320.0
    dlon = r / (111320.0 * math.cos(math.radians(lat)))
    return [round(lon - dlon, 6), round(lat - dlat, 6), round(lon + dlon, 6), round(lat + dlat, 6)]


def dist(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371000 * math.hypot(x, y)


items = {}
capped = []
for s in ST:
    if s["lat"] is None:
        continue
    mot = s["means_of_transport"] or ""
    r = HUBS.get(s["number"])
    if r is None:
        if s["municipality"] != "Bern" and "TRAIN" not in mot:
            continue
        r = 120 if "TRAIN" in mot else 50
    b = bbox(s["lat"], s["lon"], r)
    url = API + "?" + urllib.parse.urlencode({"bbox": ",".join(map(str, b)), "limit": "500"})
    try:
        d = http(url, minint=0.4)
    except Exception as e:
        print("  !", s["number"], e, flush=True)
        continue
    fs = d.get("features", [])
    if len(fs) >= 500:
        capped.append(s["number"])
    n_in = 0
    for f in fs:
        lon, lat = f["geometry"]["coordinates"][:2]
        dd = dist(s["lat"], s["lon"], lat, lon)
        if dd > r:
            continue
        n_in += 1
        p = f["properties"]
        it = items.get(f["id"])
        if it is None:
            io = p.get("pers:interior_orientation") or {}
            via = next((l for l in f.get("links", []) if l.get("rel") == "via"), {})
            it = items[f["id"]] = {
                "id": f["id"], "collection": f.get("collection"),
                "lon": round(lon, 7), "lat": round(lat, 7),
                "azimuth_deg": p.get("view:azimuth"), "field_of_view_deg": io.get("field_of_view"),
                "camera": " ".join(x for x in [io.get("camera_manufacturer"), io.get("camera_model")] if x) or None,
                "datetime": p.get("datetimetz") or p.get("datetime"),
                "licence": p.get("license"),
                "producer": (f.get("providers") or [{}])[0].get("name") or p.get("geovisio:producer"),
                "horizontal_accuracy_m": p.get("quality:horizontal_accuracy"),
                "instance": via.get("href"),
                "page_url": f"https://api.panoramax.xyz/#focus=pic&pic={f['id']}",
                "item_url": next((l["href"] for l in f.get("links", []) if l.get("rel") == "self"), None),
                "sd_url": f.get("assets", {}).get("sd", {}).get("href"),
                "hd_url": f.get("assets", {}).get("hd", {}).get("href"),
                "thumb_url": f.get("assets", {}).get("thumb", {}).get("href"),
                "stations": {},
            }
        it["stations"][str(s["number"])] = round(dd, 1)
    if n_in:
        print("pnx", s["number"], s["name"], r, "m:", n_in, flush=True)

save("panoramax_items.json", {"retrieved": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                              "api": API, "count": len(items), "capped_queries": capped,
                              "items": sorted(items.values(), key=lambda x: (x["datetime"] or "", x["id"]))})
print("saved", len(items), "capped", capped, flush=True)
