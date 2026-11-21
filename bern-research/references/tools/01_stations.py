"""Fetch atlas/DiDok service points (stop points) for the City of Bern (BFS 351) and neighbours
from data.sbb.ch (dataset dienststellen-gemass-opentransportdataswiss) -> data/stations.json"""
import sys, os, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, save

DS = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/dienststellen-gemass-opentransportdataswiss/exports/json"
# Bern city plus the directly adjoining municipalities whose hubs serve Bern (Ittigen/Worblaufen, Ostermundigen, Muri/Guemligen, Koeniz/Wabern)
FSO = {"351": "Bern", "362": "Ittigen", "363": "Ostermundigen", "356": "Muri bei Bern", "355": "Köniz"}
where = "stoppoint=\"true\" and fsonumber in (" + ",".join(f'"{k}"' for k in FSO) + ")"
url = DS + "?" + urllib.parse.urlencode({"where": where, "select": "number,sloid,designationofficial,abbreviation,meansoftransport,municipalityname,fsonumber,geopos,height,businessorganisationabbreviationde,validfrom,validto"})
rows = http(url, minint=0.5)
today = datetime.date.today().isoformat()
out = []
for r in rows:
    if r.get("validto") and r["validto"] < today:
        continue
    g = r.get("geopos") or {}
    out.append({
        "number": int(r["number"]), "sloid": r["sloid"], "name": r["designationofficial"],
        "abbreviation": r.get("abbreviation"), "means_of_transport": r.get("meansoftransport"),
        "municipality": r.get("municipalityname"), "fso": r.get("fsonumber"),
        "lon": round(g["lon"], 7) if g else None, "lat": round(g["lat"], 7) if g else None,
        "height_m_ln02": r.get("height"), "operator": r.get("businessorganisationabbreviationde"), "stop_point": True,
        "source": "SBB data portal: dienststellen-gemass-opentransportdataswiss (atlas service points)",
        "inferred": False,
    })
# service points referenced by Commons categories or the SBB plan index that are not current stop points
SUPPLEMENT = [8504495, 8507081, 8507082]
url2 = DS + "?" + urllib.parse.urlencode({"where": "number in (" + ",".join(map(str, SUPPLEMENT)) + ")",
                                          "select": "number,sloid,designationofficial,abbreviation,meansoftransport,municipalityname,fsonumber,geopos,height,businessorganisationabbreviationde,validfrom,validto,stoppoint"})
for r in http(url2, minint=0.5):
    if r.get("validto") and r["validto"] < today:
        continue
    g = r.get("geopos") or {}
    out.append({
        "number": int(r["number"]), "sloid": r["sloid"], "name": r["designationofficial"],
        "abbreviation": r.get("abbreviation"), "means_of_transport": r.get("meansoftransport"),
        "municipality": r.get("municipalityname"), "fso": r.get("fsonumber"),
        "lon": round(g["lon"], 7) if g else None, "lat": round(g["lat"], 7) if g else None,
        "height_m_ln02": r.get("height"), "operator": r.get("businessorganisationabbreviationde"),
        "stop_point": False, "note": "atlas service point that is not a current stop point; kept because references point at it",
        "source": "SBB data portal: dienststellen-gemass-opentransportdataswiss (atlas service points)", "inferred": False,
    })
# de-duplicate on number (keep latest validity)
by = {}
for s in out:
    by[s["number"]] = s
out = sorted(by.values(), key=lambda s: (not s["stop_point"], s["municipality"] != "Bern", s["name"]))
# flag stations outside the transit/ coverage (transit tiers: bern, ring = up to 5 km outside the boundary, connected)
TS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "transit", "data", "stations.geojson")
if os.path.exists(TS):
    import json
    tnum = {f["properties"]["number"] for f in json.load(open(TS, encoding="utf-8"))["features"]}
    for s in out:
        s["in_transit_coverage"] = s["number"] in tnum
        if not s["in_transit_coverage"]:
            s["coverage_note"] = ("stop point of an adjoining municipality included in full here (Ittigen, Ostermundigen, Muri, Köniz) "
                                  "but outside transit/ tiers (not within 5 km of the Bern boundary and not on a trip serving Bern); "
                                  "no reference in this folder points at it")
save("stations.json", {"retrieved": today, "source_url": url, "licence": "SBB Open Data terms (https://data.sbb.ch/page/licence); atlas data originates from opentransportdata.swiss", "count": len(out), "stations": out})
print(len(out), "stop points;", sum(1 for s in out if s["municipality"] == "Bern"), "in Bern")
