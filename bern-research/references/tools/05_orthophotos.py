"""Georeferenced swisstopo SWISSIMAGE orthophoto crops around station hubs (top-down footprint references).
WMS GetMap in LV95 (EPSG:2056), JPEG, with an ESRI world file (.jgw) and a .json sidecar per crop.
Writes orthophoto/<number>_<slug>.jpg|.jgw|.json and data/orthophotos.json.
Usage: python -I -X utf8 tools/05_orthophotos.py
"""
import sys, os, json, re, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, load, save, sha256, ROOT

ST = {s["number"]: s for s in load("stations.json")["stations"]}
OUT = os.path.join(ROOT, "orthophoto")
WMS = "https://wms.geo.admin.ch/"
LAYER = "ch.swisstopo.swissimage"
# number -> (half-width m, half-height m, metres per pixel, centre offset east m, north m, note)
CROPS = {
    8507000: (260, 170, 0.2, -60, 0, "Bern station: track hall roof, Welle (west access), Bollwerk, Schanzenbrücke"),
    8576646: (110, 90, 0.1, 0, 0, "Bahnhofplatz: Baldachin canopy, tram/bus islands, Bubenbergplatz/Hirschengraben edge"),
    8507110: (80, 70, 0.1, 0, 0, "Zytglogge/Kornhausplatz/Theaterplatz tram stop islands"),
    8516161: (170, 130, 0.15, 0, 0, "Bern Wankdorf station platforms, underpass exits, bus/tram stop"),
    8588699: (90, 80, 0.1, 0, 0, "Wankdorf Center tram stop"),
    8504108: (130, 110, 0.12, 0, 0, "Europaplatz: S-Bahn viaduct station, tram stop below, House of Religions"),
    8516154: (130, 100, 0.12, 0, 0, "Brünnen Westside: covered station below Westside centre, tram terminus"),
    8504489: (110, 80, 0.12, 0, 0, "Bümpliz Nord station"),
    8504106: (110, 80, 0.12, 0, 0, "Bümpliz Süd station"),
    8507079: (110, 80, 0.12, 0, 0, "Weissenbühl station (BLS)"),
    8508051: (90, 80, 0.12, 0, 0, "Felsenau station (RBS)"),
    8508052: (90, 80, 0.12, 0, 0, "Tiefenau station (RBS)"),
    8504488: (90, 80, 0.12, 0, 0, "Riedbach station"),
    8576990: (90, 80, 0.1, 0, 0, "Guisanplatz Expo tram/bus stop"),
    8507060: (80, 70, 0.1, 0, 0, "Helvetiaplatz tram stop"),
    8508054: (110, 90, 0.12, 0, 0, "Worblaufen station (RBS junction)"),
}


def wgs84_to_lv95(lat, lon):
    """swisstopo approximate formulas (accuracy about 1 m)."""
    p = (lat * 3600 - 169028.66) / 10000
    l = (lon * 3600 - 26782.5) / 10000
    e = 2600072.37 + 211455.93 * l - 10938.51 * l * p - 0.36 * l * p * p - 44.54 * l ** 3
    n = 1200147.07 + 308807.95 * p + 3745.25 * l * l + 76.63 * p * p - 194.56 * l * l * p + 119.79 * p ** 3
    return e, n


def lv95_to_wgs84(e, n):
    y = (e - 2600000) / 1e6
    x = (n - 1200000) / 1e6
    lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y ** 3
    lat = 16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x ** 3
    return lat * 100 / 36, lon * 100 / 36


os.makedirs(OUT, exist_ok=True)
rec = []
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
for n, (hw, hh, mpp, de, dn, note) in CROPS.items():
    s = ST[n]
    e0, n0 = wgs84_to_lv95(s["lat"], s["lon"])
    e0 += de
    n0 += dn
    minx, miny, maxx, maxy = round(e0 - hw), round(n0 - hh), round(e0 + hw), round(n0 + hh)
    w, h = round((maxx - minx) / mpp), round((maxy - miny) / mpp)
    q = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": LAYER, "STYLES": "", "CRS": "EPSG:2056",
         "BBOX": f"{minx},{miny},{maxx},{maxy}", "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/jpeg"}
    url = WMS + "?" + urllib.parse.urlencode(q)
    b = http(url, binary=True, minint=1.0)
    if not b.startswith(b"\xff\xd8"):
        print("  ! not a JPEG for", n, b[:200]); continue
    slug = re.sub(r"[^a-z0-9]+", "-", s["name"].lower().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")).strip("-")
    base = f"{n}_{slug}"
    p = os.path.join(OUT, base + ".jpg")
    open(p, "wb").write(b)
    # world file: pixel size x, rotation, rotation, -pixel size y, centre of upper-left pixel
    px, py = (maxx - minx) / w, (maxy - miny) / h  # actual pixel size after rounding the image size
    with open(os.path.join(OUT, base + ".jgw"), "w", newline="\n") as f:
        f.write(f"{px:.6f}\n0\n0\n{-py:.6f}\n{minx + px / 2:.4f}\n{maxy - py / 2:.4f}\n")
    sw = lv95_to_wgs84(minx, miny)
    ne = lv95_to_wgs84(maxx, maxy)
    r = {
        "id": f"ortho-{base}", "file": f"orthophoto/{base}.jpg", "world_file": f"orthophoto/{base}.jgw",
        "station": {"number": n, "sloid": s["sloid"], "name": s["name"]}, "feature": note,
        "bbox_lv95": [minx, miny, maxx, maxy], "crs": "EPSG:2056",
        "bbox_wgs84": [round(sw[1], 7), round(sw[0], 7), round(ne[1], 7), round(ne[0], 7)],
        "bbox_wgs84_note": "converted with swisstopo approximate formulas (about 1 m)",
        "metres_per_pixel": [round(px, 6), round(py, 6)], "width_px": w, "height_px": h, "bytes": len(b), "sha256": sha256(p),
        "source": "swisstopo SWISSIMAGE (WMS layer ch.swisstopo.swissimage)", "source_url": url,
        "publisher": "Federal Office of Topography swisstopo", "licence": "swisstopo free geodata (OGD)",
        "licence_url": "https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-ogd", "attribution": "© swisstopo",
        "capture_date": None, "capture_date_note": "SWISSIMAGE flight year varies per area; look up in map.geo.admin.ch layer ch.swisstopo.images-swissimage-dop10.metadata",
        "retrieved": now, "inferred": False,
        "model_use": "Top-down footprint: canopy outlines, platform edges, tram islands, kerbs, road markings; drape on terrain or trace in a GIS (world file + EPSG:2056).",
    }
    json.dump(r, open(os.path.join(OUT, base + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rec.append(r)
    print(n, s["name"], w, "x", h, len(b) // 1024, "KiB", flush=True)
save("orthophotos.json", {"generated": now, "count": len(rec), "items": rec})
