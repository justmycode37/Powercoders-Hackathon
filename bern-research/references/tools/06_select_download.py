"""Classify, score, select and download a compact licensed subset; build the reference manifest.

Inputs : data/stations.json, data/commons_candidates.json, data/panoramax_items.json,
         ../transit/data/edge_lookup.json and ../transit/data/edges.geojson (read-only, for edge SLOIDs)
Outputs: images/<station number>/<file>.jpg   downloaded subset (scaled derivatives, see `download`)
         data/photo_records.json               every candidate photo with licence, station keys, tags, viewpoint
Usage  : python -I -X utf8 tools/06_select_download.py [--no-download]
"""
import sys, os, re, json, math, html, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, commons, load, save, sha256, ROOT

NO_DL = "--no-download" in sys.argv
TRANSIT = os.path.join(os.path.dirname(ROOT), "transit", "data")
ST = {s["number"]: s for s in load("stations.json")["stations"]}
CC = load("commons_candidates.json")
for k, (name, sloid) in CC.get("extra_service_points", {}).items():
    ST.setdefault(int(k), {"number": int(k), "sloid": sloid, "name": name, "lat": None, "lon": None, "municipality": "Bern",
                           "means_of_transport": "TRAIN", "note": "atlas service point, not a current stop point"})
PX = load("panoramax_items.json")
EDGE_LOOKUP = json.load(open(os.path.join(TRANSIT, "edge_lookup.json"), encoding="utf-8"))["stations"]
EDGES = collections.defaultdict(list)  # station number -> [(sloid, designation, lat, lon)]
for f in json.load(open(os.path.join(TRANSIT, "edges.geojson"), encoding="utf-8"))["features"]:
    p = f["properties"]
    if f.get("geometry") and p.get("station_number") and p.get("valid_today", True):
        lon, lat = f["geometry"]["coordinates"][:2]
        EDGES[p["station_number"]].append((p["sloid"], p.get("designation"), lat, lon))

FOCUS = [8507000, 8576646, 8507110, 8516161, 8588699]
HUB_CAP = {8507000: 34, 8576646: 16, 8507110: 12, 8516161: 12, 8588699: 6, 8590129: 4, 8504108: 8, 8580939: 4}
DEFAULT_CAP = 4
COMMONS_BUDGET = 125          # max Commons files downloaded
PANORAMAX_BUDGET = 22         # max Panoramax pictures downloaded
MAX_BYTES = 5 * 1024 * 1024   # contract: no single file above 5 MB

ALLOWED = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]?\d|cc[- ]by(-sa)?$|public domain|pd|attribution$|attribution-sharealike|cc-by-sa-4\.0|cc-by-4\.0)", re.I)

TAGS = [  # (tag, regex over title + description + categories)
    ("platform", r"\b(platform|perron|gleis|bahnsteig|quai|voie|track \d|gl\. ?\d)"),
    ("concourse", r"(concourse|halle\b|bahnhofhalle|passage|unterf[üu]hrung|underpass|christoffel|neuengasse|interior|innen|hall\b|shopping|ladenpassage)"),
    ("entrance", r"(entrance|eingang|zugang|welle|portal|access|ausgang|exit|treppenabgang)"),
    ("canopy", r"(baldachin|canopy|vordach|perrondach|roof|dach\b|überdachung|ueberdachung)"),
    ("tram_stop", r"(tram stop|tramhaltestelle|haltestelle|tram station|kante\b|bus stop|bushaltestelle|stop \(bern\))"),
    ("shelter", r"(shelter|wartehalle|wartehäuschen|unterstand|tramwartehalle)"),
    ("stairs_lift", r"(stair|treppe|rolltreppe|escalator|\blift\b|elevator|aufzug|rampe|ramp\b)"),
    ("signage", r"(sign\b|signage|schild|anzeige|display|abfahrt|departure|board\b|wegweiser|piktogramm)"),
    ("clock", r"(clock|uhr\b|bahnhofsuhr)"),
    ("ticket_machine", r"(ticket machine|billetautomat|fahrkartenautomat)"),
    ("bench", r"(bench|sitzbank|bank\b)"),
    ("facade", r"(facade|fassade|façade|front|exterior|aussen|bahnhofgebäude|station building|empfangsgebäude)"),
    ("square", r"(platz\b|bahnhofplatz|bubenbergplatz|hirschengraben|kornhausplatz|europaplatz|square)"),
    ("aerial", r"(aerial|luftbild|luftaufnahme|from above|von oben|drone|vogelschau|swissair photo)"),
    ("vehicle", r"(\btrain\b|\btram\b|\bbus\b|trolleybus|lok\b|locomotive|\bre ?\d|re 4/4|be \d|combino|tramlink|rabe|flirt|nina|ic2000|ec\b|ice\b|tgv|zug\b|triebzug|rbs\b.*(be|abe)|\bbe4/|mutz|twindexx)"),
    ("construction", r"(construction|baustelle|umbau|ausbau|bau\b|bauarbeiten|zukunft bahnhof|zbb|tiefbahnhof|neubau)"),
    ("night", r"(night|nacht|abend|evening|dusk|blue hour)"),
    ("map_plan", r"(map\b|plan\b|karte|netzplan|diagram|schema|gleisplan|lageplan)"),
    ("artwork", r"(skulptur|sculpture|plastik|kunst|artwork|wandmalerei|mural|brunnen|fountain|denkmal)"),
]
TAGS = [(t, re.compile(r, re.I)) for t, r in TAGS]
USE = {
    "platform": "platform edge line, canopy column spacing, sector signs and furniture placement along the platform",
    "concourse": "interior passage width/height, ceiling and lighting, shopfront rhythm, stair and escalator positions",
    "entrance": "entrance portal geometry and its relation to street level and to the passages",
    "canopy": "canopy outline, column count and spacing, roof material (glass/steel) and height",
    "tram_stop": "stop island layout, kerb, shelter type and position; match the edge letter to atlas edge SLOIDs",
    "shelter": "shelter dimensions and glazing (compare with assets/tram-bus-shelter)",
    "stairs_lift": "vertical circulation: stair widths, escalators, lifts, ramps",
    "signage": "placement and size of signs and displays (do not copy branded artwork as textures)",
    "clock": "clock mounting height and position",
    "ticket_machine": "ticket machine placement and size",
    "bench": "bench placement and size",
    "facade": "facade massing, materials, window rhythm for texturing",
    "square": "street-level layout of the square: islands, crossings, kerbs, street furniture",
    "aerial": "massing and roof layout seen from above",
    "vehicle": "vehicle scale and livery (low priority for station geometry)",
    "construction": "construction state (Zukunft Bahnhof Bern works); verify current state before modelling",
    "night": "lighting reference",
    "map_plan": "plan or diagram: layout and naming",
    "artwork": "public art at the station (usually not needed for transit geometry)",
}
DESIGNATION = [re.compile(r"\b(?:gleis|track|perron|platform|voie|gl\.)\s*(\d{1,2})\b", re.I),
               re.compile(r"\b(?:kante|edge)\s*([A-Z]\d?)\b")]


def strip_html(s):
    if not s:
        return None
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(re.sub(r"\s+", " ", s)).strip()
    return s or None


def parse_date(s):
    if not s:
        return None
    s = strip_html(s)
    m = re.search(r"(1[89]\d\d|20\d\d)[-:/](\d\d)[-:/](\d\d)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d\d)\.(\d\d)\.(1[89]\d\d|20\d\d)", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", s)
    return m.group(1) if m else None


def dist(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 6371000 * math.hypot(x, math.radians(lat2 - lat1))


def bearing(lat1, lon1, lat2, lon2):
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def edges_in_view(numbers, lat, lon, heading, fov, max_m=45):
    """atlas edges of the linked stations that lie within max_m of the camera and inside the horizontal field of view"""
    out = []
    for n in numbers:
        for sloid, des, elat, elon in EDGES.get(n, []):
            d = dist(lat, lon, elat, elon)
            if d > max_m:
                continue
            b = bearing(lat, lon, elat, elon)
            off = abs((b - heading + 540) % 360 - 180)
            if off <= (fov or 60) / 2:
                out.append({"edge_sloid": sloid, "designation": des, "station_number": n, "distance_m": round(d, 1), "bearing_offset_deg": round(off, 1)})
    return sorted(out, key=lambda e: e["distance_m"])[:6]


def resolve_designations(numbers, text):
    found = []
    for rx in DESIGNATION:
        for m in rx.finditer(text):
            des = m.group(1)
            for n in numbers:
                L = EDGE_LOOKUP.get(str(n), {}).get("by_designation", {})
                if des in L:
                    found.append({"designation": des, "station_number": n, "edge_sloids": L[des], "matched_text": m.group(0)})
    uniq = {(f["designation"], f["station_number"]): f for f in found}
    return list(uniq.values())


def station_ref(n, **kw):
    s = ST.get(n, {})
    return dict(number=n, sloid=s.get("sloid"), name=s.get("name"), **kw)


def heading_from_text(s):
    m = re.search(r"heading:\s*([0-9.]+|[NESW]{1,3})", s or "")
    if not m:
        return None
    v = m.group(1)
    if re.match(r"[0-9.]+$", v):
        return float(v) % 360
    comp = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5,
            "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}
    return comp.get(v)


now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
records = []

# ------------------------------------------------------------------------------------------ Commons
for c in CC["files"]:
    ii = c.get("imageinfo")
    if not ii:
        continue
    em = {k: v.get("value") for k, v in (ii.get("extmetadata") or {}).items()}
    lic = strip_html(em.get("LicenseShortName")) or ""
    desc = strip_html(em.get("ImageDescription")) or ""
    cats = [x.replace("Category:", "") for x in c.get("categories", [])]
    text = " ".join([c["title"], desc, " ".join(cats), " ".join(x.replace("Category:", "") for x in c["seed_categories"])])
    tags = [t for t, rx in TAGS if rx.search(text)]
    mime = ii.get("mime", "")
    # stations: category links first, then geosearch hits by distance
    st_links = []
    for n, v in c["stations"].items():
        st_links.append(station_ref(int(n), relation="+".join(v["via"]), distance_m=v.get("geo_dist_m")))
    st_links.sort(key=lambda s: (0 if "category" in s["relation"] else 1, s["distance_m"] if s["distance_m"] is not None else 0, 0 if s["number"] in FOCUS else 1))
    cam = None
    prim = [x for x in c.get("coordinates", []) if x.get("primary")]
    if em.get("GPSLatitude") and em.get("GPSLongitude"):
        try:
            cam = {"lat": round(float(em["GPSLatitude"]), 7), "lon": round(float(em["GPSLongitude"]), 7), "source": "Commons {{Location}} (camera position)"}
        except ValueError:
            cam = None
    if cam is None and prim:
        cam = {"lat": round(prim[0]["lat"], 7), "lon": round(prim[0]["lon"], 7), "source": "Commons primary coordinate (camera or object, not distinguished)"}
    date = parse_date(em.get("DateTimeOriginal"))
    year = int(date[:4]) if date else None
    w, h = ii.get("width", 0), ii.get("height", 0)
    allowed = bool(ALLOWED.match(lic)) and "nd" not in lic.lower() and "nc" not in lic.lower()
    is_image = mime in ("image/jpeg", "image/png", "image/tiff", "image/webp")
    # score
    s = c["relevance"] * 2
    s += sum({"platform": 3, "concourse": 3, "entrance": 3, "canopy": 3, "tram_stop": 3, "shelter": 2, "stairs_lift": 3, "square": 2,
              "facade": 1, "signage": 1, "aerial": 2, "map_plan": 1}.get(t, 0) for t in tags)
    s -= 3 if "artwork" in tags and not any(t in tags for t in ("platform", "concourse", "canopy", "tram_stop")) else 0
    s -= 2 if tags == ["vehicle"] else 0
    s += 3 if year and year >= 2015 else (1 if year and year >= 2008 else (-4 if year and year < 1990 else 0))
    s += 2 if cam else 0
    s += 1 if w * h >= 4e6 else 0
    near = [x for x in st_links if x["distance_m"] is not None]
    if near and not any("category" in x["relation"] for x in st_links):
        s += 2 if near[0]["distance_m"] < 40 else (1 if near[0]["distance_m"] < 100 else -1)
        if not tags:
            s -= 4  # geosearch-only photo with no transit keyword (e.g. old-town facades)
    numbers = [x["number"] for x in st_links]
    rec = {
        "id": f"commons:{c.get('pageid')}", "kind": "photo", "source": "Wikimedia Commons",
        "title": c["title"].replace("File:", ""), "source_page_url": ii.get("descriptionurl"),
        "original_url": ii.get("url"), "original_size_px": [w, h], "original_bytes": ii.get("size"), "original_sha1": ii.get("sha1"), "mime": mime,
        "author": strip_html(em.get("Artist")), "credit": strip_html(em.get("Credit")),
        "licence": lic or None, "licence_url": em.get("LicenseUrl"), "attribution_required": em.get("AttributionRequired"),
        "usage_terms": strip_html(em.get("UsageTerms")),
        "capture_date": date, "capture_date_source": "Commons DateTimeOriginal" if date else None,
        "uploaded": ii.get("timestamp"), "description": (desc[:500] if desc else None), "categories": cats,
        "stations": st_links, "feature_tags": tags, "feature_tags_inferred": True,
        "feature_tags_how": "keyword match over title, description and categories (tools/06_select_download.py)",
        "viewpoint": {"camera": cam, "heading_deg": None, "heading_source": None,
                      "setting": "aerial" if "aerial" in tags else ("interior" if "concourse" in tags else "street-level")},
        "edge_designations": resolve_designations(numbers, c["title"] + " " + desc),
        "model_use": "; ".join(USE[t] for t in tags if t in USE) or "context view; check visually",
        "redistributable": allowed, "redistributable_why": "licence allows redistribution with attribution" if allowed else f"licence '{lic}' not in the allowed set: link only",
        "score": s, "retrieved": CC["retrieved"], "_thumburl": ii.get("thumburl"), "_is_image": is_image,
        "inferred": True, "inferred_how": "station link by Commons category (hand-mapped) or GeoData distance; tags by keyword",
    }
    records.append(rec)

# ------------------------------------------------------------------------------------------ Panoramax
for it in PX["items"]:
    lic = it.get("licence") or ""
    allowed = bool(ALLOWED.match(lic))
    st_links = sorted([station_ref(int(n), relation="panoramax-radius", distance_m=d) for n, d in it["stations"].items()], key=lambda x: x["distance_m"])
    numbers = [x["number"] for x in st_links]
    ev = edges_in_view(numbers, it["lat"], it["lon"], it["azimuth_deg"], it["field_of_view_deg"]) if it.get("azimuth_deg") is not None else []
    date = (it.get("datetime") or "")[:10] or None
    s = 4 + (3 if ev else 0) + (2 if any(n in FOCUS for n in numbers) else 0) + (1 if (it.get("horizontal_accuracy_m") or 99) <= 5 else 0)
    records.append({
        "id": f"panoramax:{it['id']}", "kind": "streetlevel_photo", "source": "Panoramax",
        "title": f"Panoramax picture {it['id']}", "source_page_url": it["page_url"], "item_url": it["item_url"],
        "original_url": it["hd_url"], "original_size_px": None, "mime": "image/jpeg",
        "author": it.get("producer"), "credit": f"Panoramax ({(it.get('instance') or 'api.panoramax.xyz').replace('https://', '')})",
        "licence": lic.replace("CC-BY-SA-4.0", "CC BY-SA 4.0").replace("CC-BY-4.0", "CC BY 4.0") or None,
        "licence_url": {"CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/", "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/"}.get(lic),
        "capture_date": date, "capture_date_source": "Panoramax datetime (EXIF)", "camera_model": it.get("camera"),
        "stations": st_links, "feature_tags": ["street_level"] + (["tram_stop"] if ev and any(not e["designation"] or not e["designation"].isdigit() for e in ev) else []) + (["platform"] if ev and any((e["designation"] or "").isdigit() for e in ev) else []),
        "feature_tags_inferred": True, "feature_tags_how": "from edges in the camera field of view",
        "viewpoint": {"camera": {"lat": it["lat"], "lon": it["lon"], "source": "Panoramax GPS", "horizontal_accuracy_m": it.get("horizontal_accuracy_m")},
                      "heading_deg": it.get("azimuth_deg"), "heading_source": "Panoramax view:azimuth", "field_of_view_deg": it.get("field_of_view_deg"),
                      "setting": "street-level"},
        "edges_in_view": ev, "edges_in_view_inferred": True,
        "edges_in_view_how": "atlas edges (transit/data/edges.geojson) within 45 m of the camera and inside the horizontal field of view",
        "edge_designations": [],
        "model_use": "camera-pose reference (position + compass heading): photo-match street-level geometry, kerbs, shelters, signs and facades" +
                     ("; shows edges " + ", ".join(sorted({e['designation'] or e['edge_sloid'] for e in ev})) if ev else ""),
        "redistributable": allowed, "redistributable_why": "CC licence" if allowed else f"licence '{lic}' not allowed: link only",
        "score": s, "retrieved": PX["retrieved"], "_thumburl": it.get("sd_url"), "_is_image": True,
        "inferred": True, "inferred_how": "station link by distance from the atlas stop point",
    })

# ------------------------------------------------------------------------------------------ selection
def primary(r):
    return r["stations"][0]["number"] if r["stations"] else None


selected = []
per = collections.Counter()
cnt = collections.Counter()
for r in sorted(records, key=lambda r: -r["score"]):
    if not (r["redistributable"] and r["_is_image"] and r["_thumburl"]):
        continue
    if r["kind"] == "photo" and r["score"] < 6:
        continue
    if r["kind"] == "photo" and r["capture_date"] and r["capture_date"][:4].isdigit() and int(r["capture_date"][:4]) < 1990:
        continue
    budget = COMMONS_BUDGET if r["kind"] == "photo" else PANORAMAX_BUDGET
    if cnt[r["kind"]] >= budget:
        continue
    p = primary(r)
    cap = HUB_CAP.get(p, DEFAULT_CAP)
    if r["kind"] == "streetlevel_photo":
        cap = 4 if p in FOCUS else 2
    if per[(r["kind"], p)] >= cap:
        continue
    if r["kind"] == "streetlevel_photo":  # skip near-duplicate frames of the same sequence
        cam, hd = r["viewpoint"]["camera"], r["viewpoint"]["heading_deg"] or 0
        if any(q["kind"] == "streetlevel_photo" and dist(cam["lat"], cam["lon"], q["viewpoint"]["camera"]["lat"], q["viewpoint"]["camera"]["lon"]) < 10
               and abs(((q["viewpoint"]["heading_deg"] or 0) - hd + 540) % 360 - 180) < 40 for q in selected):
            continue
    per[(r["kind"], p)] += 1
    cnt[r["kind"]] += 1
    selected.append(r)
print("selected", dict(cnt), flush=True)

# headings for selected Commons files from {{Location ... heading:..}} in wikitext
sel_c = [r for r in selected if r["kind"] == "photo"]
for i in range(0, len(sel_c), 50):
    b = sel_c[i:i + 50]
    d = commons(action="query", titles="|".join("File:" + r["title"] for r in b), prop="revisions", rvprop="content", rvslots="main")
    by = {p["title"]: p for p in d["query"]["pages"]}
    for r in b:
        p = by.get("File:" + r["title"])
        try:
            txt = p["revisions"][0]["slots"]["main"]["content"]
        except Exception:
            continue
        loc = re.search(r"\{\{\s*(?:Location|Camera location)[^}]*\}\}", txt, re.I)
        hd = heading_from_text(loc.group(0)) if loc else None
        if hd is not None:
            r["viewpoint"]["heading_deg"] = hd
            r["viewpoint"]["heading_source"] = "Commons {{Location}} heading parameter"
        if loc and re.search(r"Object location", txt, re.I) and r["viewpoint"]["camera"]:
            pass
        cam = r["viewpoint"]["camera"]
        if cam and hd is not None:
            r["edges_in_view"] = edges_in_view([s["number"] for s in r["stations"]], cam["lat"], cam["lon"], hd, 65)
            r["edges_in_view_inferred"] = True
            r["edges_in_view_how"] = "atlas edges within 45 m and inside an assumed 65 degree field of view"

# ------------------------------------------------------------------------------------------ download
IMG = os.path.join(ROOT, "images")
total = 0
for r in selected:
    p = primary(r)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", r["title"])[:80].strip("_")
    if r["kind"] == "photo":
        url = r["_thumburl"]
        if p not in FOCUS:
            url = url.replace("/1280px-", "/960px-")
        name = f"c{r['id'].split(':')[1]}_{slug}"
    else:
        url = r["_thumburl"]
        name = f"px_{r['id'].split(':')[1][:8]}"
    if not name.lower().endswith((".jpg", ".jpeg")):
        name = re.sub(r"\.(png|tif|tiff|webp|jpe?g)$", "", name, flags=re.I) + ".jpg"
    rel = f"images/{p}/{name}"
    dest = os.path.join(ROOT, rel)
    if not NO_DL:
        try:
            b = http(url, binary=True, minint=1.0)
        except Exception as e:
            print("  ! download", r["id"], e, flush=True)
            r["download_error"] = str(e)
            continue
        if not (b[:3] == b"\xff\xd8\xff" or b[:8] == b"\x89PNG\r\n\x1a\n"):
            print("  ! not an image", r["id"], b[:80], flush=True)
            continue
        if b[:4] == b"\x89PNG":
            dest = dest[:-4] + ".png"; rel = rel[:-4] + ".png"
        if len(b) > MAX_BYTES:
            print("  ! too big", r["id"], len(b), flush=True)
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(b)
    if os.path.exists(dest):
        m = re.search(r"/(\d+)px-", url)
        r["download"] = {"file": rel, "derivative_url": url, "bytes": os.path.getsize(dest), "sha256": sha256(dest),
                         "scaled": (f"Commons thumbnail, width {m.group(1)} px (original {r['original_size_px'][0]}x{r['original_size_px'][1]})" if r["kind"] == "photo" and m
                                    else ("Panoramax SD derivative, width 2048 px" if r["kind"] == "streetlevel_photo" else "as served")),
                         "retrieved": now}
        total += r["download"]["bytes"]
print("downloaded bytes", total, flush=True)

for r in records:
    r.pop("_thumburl", None); r.pop("_is_image", None)
    r.setdefault("download", None)
    r.setdefault("edges_in_view", [])
save("photo_records.json", {"generated": now, "count": len(records), "downloaded": sum(1 for r in records if r["download"]),
                            "downloaded_bytes": total, "records": sorted(records, key=lambda r: -r["score"])})
