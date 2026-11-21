"""Join atlas station numbers to Wikidata items (P954 = IBNR, same as the atlas `number` for Swiss stations).
Gives a Wikidata QID, Commons category (P373), lead image (P18) and opening date where present, so the Commons
harvest can be extended systematically. Writes data/wikidata_stations.json.
Usage: python -I -X utf8 tools/01b_wikidata.py
"""
import sys, os, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, load, save

ST = load("stations.json")["stations"]
nums = " ".join(f'"{s["number"]}"' for s in ST)
q = f"""SELECT ?item ?itemLabel ?ibnr ?commonscat ?image ?opened ?coord WHERE {{
  VALUES ?ibnr {{ {nums} }}
  ?item wdt:P954 ?ibnr .
  OPTIONAL {{ ?item wdt:P373 ?commonscat }}
  OPTIONAL {{ ?item wdt:P18 ?image }}
  OPTIONAL {{ ?item wdt:P1619 ?opened }}
  OPTIONAL {{ ?item wdt:P625 ?coord }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
}}"""
url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": q, "format": "json"})
d = http(url, minint=2.0)
by = {}
for b in d["results"]["bindings"]:
    n = int(b["ibnr"]["value"])
    e = by.setdefault(n, {"number": n, "wikidata": b["item"]["value"].rsplit("/", 1)[-1], "label": b.get("itemLabel", {}).get("value"),
                          "commons_category": None, "image": None, "opened": None})
    if "commonscat" in b:
        e["commons_category"] = "Category:" + b["commonscat"]["value"]
    if "image" in b:
        e["image"] = b["image"]["value"]
    if "opened" in b:
        e["opened"] = b["opened"]["value"][:10]
sl = {s["number"]: s["sloid"] for s in ST}
out = []
for n, e in sorted(by.items()):
    e["sloid"] = sl.get(n)
    e["source"] = "Wikidata (CC0) via query.wikidata.org, joined on P954 (IBNR) = atlas number"
    e["inferred"] = False
    out.append(e)
save("wikidata_stations.json", {"retrieved": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "licence": "CC0 1.0 (Wikidata)",
                                "query": q, "count": len(out), "stations": out})
print(len(out), "stations with a Wikidata item;", sum(1 for e in out if e["commons_category"]), "with a Commons category")
for e in out:
    print(e["number"], e["wikidata"], e["label"], e["commons_category"])
