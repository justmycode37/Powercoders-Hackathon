"""Harvest Wikimedia Commons file metadata for Bern transit stations.

Sources of candidates:
  1. curated seed categories (mapped by hand to atlas station numbers), with direct sub-categories
  2. GeoData geosearch (list=geosearch, namespace 6) around every stop point in data/stations.json
For every candidate: imageinfo (url, size, mime, sha1, extmetadata licence/author/date), coordinates (all),
non-hidden categories. Writes data/commons_candidates.json. All API answers are cached under .cache/.
Usage: python -I -X utf8 tools/02_harvest_commons.py
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import commons, load, save

ST = {s["number"]: s for s in load("stations.json")["stations"]}
# service points that are not current stop points in atlas (kept so older photos can still be keyed)
EXTRA = {8504495: ("Bern Stöckacker", "ch:1:sloid:4495"), 8507081: ("Bern Fischermätteli", "ch:1:sloid:7081")}

# seed category -> (station numbers, include direct subcats?, relevance weight)
SEEDS = {
    "Category:Bern railway station": ([8507000], True, 3),
    "Category:New Bern station": ([8507000], False, 3),
    "Category:Christoffel-Unterführung (Bern)": ([8507000], True, 3),
    "Category:Bahnhofplatz (Bern)": ([8576646, 8507000], False, 3),
    "Category:Bubenbergplatz (Bern)": ([8576646, 8579896], False, 2),
    "Category:Hirschengraben (Bern)": ([8579896], False, 2),
    "Category:Bärenplatz (Bern)": ([8588989], False, 1),
    "Category:Kornhausplatz (Bern)": ([8507110], False, 1),
    "Category:Zytglogge tram stop (Bern)": ([8507110], False, 3),
    "Category:Guisanplatz (Bern)": ([8576990], False, 1),
    "Category:Bern Wankdorf railway station": ([8516161, 8590129], False, 3),
    "Category:Bern Europaplatz railway station": ([8504108, 8580939], True, 3),
    "Category:Bern-Ausserholligen": ([8504108], False, 1),
    "Category:Bern Ausserholligen SBB train station": ([8504108], False, 2),
    "Category:Bern Ausserholligen GBS train station": ([8504108], False, 2),
    "Category:Bern Brünnen Westside railway station": ([8516154], False, 3),
    "Category:Bern Bümpliz Nord railway station": ([8504489], False, 3),
    "Category:Bern Bümpliz Süd railway station": ([8504106], False, 3),
    "Category:Bern Felsenau railway station": ([8508051], False, 3),
    "Category:Bern Stöckacker railway station": ([8504495], False, 3),
    "Category:Bern Weissenbühl railway station": ([8507079], False, 3),
    "Category:Bern Riedbach railway station": ([8504488], False, 3),
    "Category:Bern Tiefenau railway station": ([8508052], False, 3),
    "Category:Bern Fischermätteli railway station": ([8507081], False, 3),
    "Category:Tram stops in Bern": ([], True, 3),
    "Category:Worblaufen railway station": ([8508054], False, 3),
    "Category:Ostermundigen railway station": ([8507002], False, 3),
    "Category:Wabern bei Bern railway station": ([8507078], False, 3),
    "Category:Ittigen bei Bern railway station": ([8507069], False, 3),
    "Category:Gümligen railway station": ([8507003], False, 2),
    "Category:Papiermühle railway station": ([8507096], False, 2),
}
SUBCAT_MAP = {  # subcategory -> station numbers (when the parent mapping is not right)
    "Category:Bern Bahnhof tram stop (Bern)": [8576646],
    "Category:Europaplatz Bahnhof tram stop (Bern)": [8580939],
    "Category:Fischermätteli tram stop (Bern)": [8590014],
    "Category:Gümligen Bahnhof tram stop (Bern)": [8595488],
    "Category:Helvetiaplatz tram stop (Bern)": [8507060],
    "Category:Saali tram stop (Bern)": [8589002],
    "Category:Zytglogge tram stop (Bern)": [8507110],
    "Category:Bern 2017 train derailment": [8507000],
}
SKIP_SUB = ("Brunnen", "Kalksteinskulptur", "Wandmalerei", "Burgerspital", "Heiliggeist", "Christophorus", "Hotel")
HUBS = {8507000: 330, 8576646: 200, 8507110: 120, 8516161: 250, 8588699: 150, 8590129: 150, 8504108: 200, 8580939: 120}


def members(cat):
    out, cont = [], {}
    while True:
        d = commons(action="query", list="categorymembers", cmtitle=cat, cmtype="subcat|file", cmprop="title|type", cmlimit="500", **cont)
        out += d["query"]["categorymembers"]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


cand = {}


def add(title, numbers, via, w=0, cat=None, dist=None):
    c = cand.setdefault(title, {"title": title, "seed_categories": [], "stations": {}, "relevance": 0})
    if cat:
        c["seed_categories"].append(cat)
    for n in numbers:
        s = c["stations"].setdefault(str(n), {"via": set()})
        s["via"].add(via)
        if dist is not None:
            s["geo_dist_m"] = min(s.get("geo_dist_m", 1e9), dist)
    c["relevance"] = max(c["relevance"], w)


for cat, (nums, subs, w) in SEEDS.items():
    print("cat", cat, flush=True)
    try:
        m = members(cat)
    except Exception as e:
        print("  !", e, flush=True)
        continue
    for x in m:
        if x["type"] == "file":
            add(x["title"], nums, "category", w, cat)
        elif subs and not any(k in x["title"] for k in SKIP_SUB):
            snums = SUBCAT_MAP.get(x["title"], nums)
            sw = 1 if ("Trains at" in x["title"] or "derailment" in x["title"]) else w
            for y in members(x["title"]):
                if y["type"] == "file":
                    add(y["title"], snums, "category", sw, x["title"])

# geosearch around stop points: hubs larger radius; ordinary Bern stops 60 m, train stations 120 m
for n, s in ST.items():
    if s["lat"] is None:
        continue
    r = HUBS.get(n)
    if r is None:
        mot = s["means_of_transport"] or ""
        if "TRAIN" not in mot and "TRAM" not in mot:
            continue  # bus-only stops: 60 m geosearch mostly returns old-town facades (skipped for rate limits)
        if s["municipality"] != "Bern" and "TRAIN" not in mot:
            continue
        r = 120 if "TRAIN" in mot else 60
    try:
        d = commons(action="query", list="geosearch", gscoord=f"{s['lat']}|{s['lon']}", gsradius=str(r), gsnamespace="6", gslimit="500", gsprimary="all")
    except Exception as e:
        print("  ! geo", n, e, flush=True)
        continue
    hits = d.get("query", {}).get("geosearch", [])
    print("geo", n, s["name"], r, "m:", len(hits), flush=True)
    for h in hits:
        add(h["title"], [n], "geosearch", 0, dist=round(h["dist"], 1))

print("candidates:", len(cand), flush=True)
titles = list(cand)
for i in range(0, len(titles), 50):
    batch = titles[i:i + 50]
    cont = {}
    while True:
        d = commons(action="query", titles="|".join(batch), prop="imageinfo|coordinates|categories",
                    iiprop="url|size|mime|sha1|timestamp|user|extmetadata", iiurlwidth="1280",
                    iiextmetadatafilter="LicenseShortName|LicenseUrl|License|Artist|Credit|AttributionRequired|Attribution|DateTimeOriginal|DateTime|ImageDescription|ObjectName|UsageTerms|Copyrighted|GPSLatitude|GPSLongitude|Restrictions",
                    iiextmetadatalanguage="en", coprimary="all", coprop="type|name|dim|globe", colimit="max",
                    clshow="!hidden", cllimit="max", **cont)
        for p in d["query"]["pages"]:
            c = cand.get(p["title"])
            if not c:
                continue
            if "imageinfo" in p and "imageinfo" not in c:
                c["imageinfo"] = p["imageinfo"][0]
            if "coordinates" in p:
                c.setdefault("coordinates", []).extend(p["coordinates"])
            if "categories" in p:
                c.setdefault("categories", []).extend(x["title"] for x in p["categories"])
            c["pageid"] = p.get("pageid")
        if "continue" not in d:
            break
        cont = dict(d["continue"])
    print("info", i + len(batch), "/", len(titles), flush=True)

for c in cand.values():
    for s in c["stations"].values():
        s["via"] = sorted(s["via"])
    c["categories"] = sorted(set(c.get("categories", [])))
    # de-duplicate coordinates
    seen, co = set(), []
    for x in c.get("coordinates", []):
        k = (x.get("lat"), x.get("lon"), x.get("primary", False))
        if k not in seen:
            seen.add(k)
            co.append(x)
    c["coordinates"] = co
save("commons_candidates.json", {"retrieved": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "count": len(cand),
                                 "extra_service_points": {str(k): v for k, v in EXTRA.items()}, "files": list(cand.values())})
print("saved", len(cand), flush=True)
