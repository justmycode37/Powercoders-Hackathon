"""Assemble the machine-readable outputs of references/:

  manifest.json          one list of every reference (photo, street-level photo, orthophoto, operator plan/link, asset)
                         with a common core schema (see HANDOFF.md) plus kind-specific fields
  references.geojson     camera positions (Point, WGS84, 7 decimals) of every photo with a position, heading as property
  by_station.json        station number -> sloid, name, counts and reference ids (downloaded first)
  ATTRIBUTION.md         human-readable credits for every file stored in this folder
  SOURCES.json           provenance of the inputs (contract rule 5)
Usage: python -I -X utf8 tools/08_build_manifest.py
"""
import sys, os, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, ROOT, sha256

now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
ST = {s["number"]: s for s in load("stations.json")["stations"]}
photos = load("photo_records.json")["records"]
orthos = load("orthophotos.json")["items"]
links = load("operator_links.json")["links"]
assets = load("assets.json")["assets"]

refs = []
for r in photos:
    d = r.get("download")
    refs.append({**r, "stored": bool(d), "file": d["file"] if d else None})
for o in orthos:
    refs.append({"id": o["id"], "kind": "orthophoto", "source": o["source"], "title": f"SWISSIMAGE crop {o['station']['name']}",
                 "source_page_url": "https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10", "original_url": o["source_url"],
                 "author": o["publisher"], "licence": o["licence"], "licence_url": o["licence_url"], "attribution": o["attribution"],
                 "capture_date": None, "capture_date_note": o["capture_date_note"],
                 "stations": [{"number": o["station"]["number"], "sloid": o["station"]["sloid"], "name": o["station"]["name"], "relation": "crop centre"}],
                 "feature_tags": ["aerial", "orthophoto"], "viewpoint": {"setting": "top-down orthophoto", "bbox_lv95": o["bbox_lv95"], "bbox_wgs84": o["bbox_wgs84"]},
                 "model_use": o["model_use"] + " Feature focus: " + o["feature"],
                 "redistributable": True, "stored": True, "file": o["file"], "world_file": o["world_file"],
                 "download": {"file": o["file"], "bytes": o["bytes"], "sha256": o["sha256"], "scaled": f"WMS GetMap at {o['metres_per_pixel'][0]} m/px", "retrieved": o["retrieved"]},
                 "inferred": False, "retrieved": o["retrieved"]})
for l in links:
    refs.append({"id": "link:" + l["id"], "kind": l["kind"], "source": l["publisher"], "title": l["title"], "source_page_url": l["url"],
                 "original_url": l["url"], "author": l["publisher"], "licence": l["licence"], "licence_url": None,
                 "stations": [{**s, "name": ST.get(s["number"], {}).get("name"), "relation": "covers"} for s in l["stations"]],
                 "feature_tags": [], "model_use": l["use_for_3d"], "redistributable": l.get("redistribute", False), "stored": False, "file": None,
                 "link_check": {k: l.get(k) for k in ("checked", "http_status", "content_type", "content_length", "last_modified", "final_url", "check_note", "error") if l.get(k) is not None},
                 "capture_date": l.get("capture_date"), "status_note": l.get("status_note"), "inferred": False})
for a in assets:
    refs.append({"id": "asset:" + a["id"], "kind": "parametric_asset", "source": a["source"], "title": a["title"], "file": a["file"], "stored": True,
                 "author": "generated for this repository", "licence": a["licence"], "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                 "stations": [{"number": 8576646, "sloid": "ch:1:sloid:76646", "name": "Bern, Bahnhof", "relation": "models"}] if "baldachin" in a["id"] else [],
                 "feature_tags": [], "model_use": a["title"] + " (approximate)", "approximate": True, "evidence": a["evidence"],
                 "redistributable": True, "download": {"file": a["file"], "bytes": a["bytes"], "sha256": a["sha256"], "scaled": None, "retrieved": now},
                 "inferred": True, "inferred_how": a["inferred_how"], "units": a["units"], "axes": a["axes"], "origin": a["origin"]})

kinds = collections.Counter(r["kind"] for r in refs)
stored = [r for r in refs if r.get("stored")]
manifest = {
    "name": "Bern station reference collection", "generated": now, "schema_version": "1.0",
    "station_keys": "atlas `number` and `sloid` (stations), atlas edge `sloid` + `designation` (edges); joins with transit/ and stations/",
    "counts": {"references": len(refs), "by_kind": dict(kinds), "stored_files": len(stored),
               "stored_bytes": sum((r.get("download") or {}).get("bytes", 0) for r in stored)},
    "licence_note": "Stored files keep their own licences (per record). Records with stored=false are links only.",
    "references": refs,
}
json.dump(manifest, open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)

# GeoJSON of camera positions
feats = []
for r in refs:
    cam = (r.get("viewpoint") or {}).get("camera")
    if not cam:
        continue
    feats.append({"type": "Feature", "id": r["id"], "geometry": {"type": "Point", "coordinates": [round(cam["lon"], 7), round(cam["lat"], 7)]},
                  "properties": {"id": r["id"], "kind": r["kind"], "title": r["title"], "stored": r.get("stored"), "file": r.get("file"),
                                 "heading_deg": r["viewpoint"].get("heading_deg"), "field_of_view_deg": r["viewpoint"].get("field_of_view_deg"),
                                 "position_source": cam.get("source"), "capture_date": r.get("capture_date"),
                                 "station_number": r["stations"][0]["number"] if r["stations"] else None,
                                 "station_sloid": r["stations"][0]["sloid"] if r["stations"] else None,
                                 "edges_in_view": [e["edge_sloid"] for e in r.get("edges_in_view", [])],
                                 "feature_tags": r.get("feature_tags"), "licence": r.get("licence"), "author": r.get("author"),
                                 "source_page_url": r.get("source_page_url"), "source": r["source"],
                                 "inferred": True, "inferred_how": "camera position as published by the source; station link and tags inferred"}})
json.dump({"type": "FeatureCollection", "name": "bern_reference_viewpoints", "crs_note": "WGS84 (EPSG:4326), lon/lat", "generated": now, "features": feats},
          open(os.path.join(ROOT, "references.geojson"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False)

# by station
bs = {}
for r in refs:
    for i, s in enumerate(r.get("stations") or []):
        n = s["number"]
        e = bs.setdefault(str(n), {"number": n, "sloid": s.get("sloid") or ST.get(n, {}).get("sloid"), "name": s.get("name") or ST.get(n, {}).get("name"),
                                   "counts": collections.Counter(), "stored": [], "linked": []})
        e["counts"][r["kind"] + (":stored" if r.get("stored") else ":linked")] += 1
        (e["stored"] if r.get("stored") else e["linked"]).append(r["id"])
for e in bs.values():
    e["counts"] = dict(e["counts"])
    e["linked"] = e["linked"][:60]
    e["linked_truncated"] = True if len(e["linked"]) == 60 else False
json.dump({"generated": now, "stations": dict(sorted(bs.items(), key=lambda kv: -len(kv[1]["stored"])))},
          open(os.path.join(ROOT, "by_station.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)

# attribution
L = ["# Attribution", "", f"Generated {now} by `tools/08_build_manifest.py` from `manifest.json`. Every file stored under",
     "`references/` is listed with its author, licence and source. Commons and Panoramax images are scaled-down derivatives",
     "of the originals (no other change). CC BY-SA images remain under CC BY-SA; reuse must credit the author and keep the licence.", ""]
groups = collections.defaultdict(list)
for r in stored:
    groups[r["kind"]].append(r)
for k, title in [("photo", "Wikimedia Commons photos"), ("streetlevel_photo", "Panoramax street-level photos"),
                 ("orthophoto", "swisstopo orthophoto crops"), ("parametric_asset", "Parametric assets (original, CC0)")]:
    if not groups.get(k):
        continue
    L += [f"## {title} ({len(groups[k])})", ""]
    for r in sorted(groups[k], key=lambda r: r["file"]):
        lic = f"[{r['licence']}]({r['licence_url']})" if r.get("licence_url") else (r.get("licence") or "?")
        auth = (r.get("author") or "unknown").replace("|", "/")
        L.append(f"- `{r['file']}`: \"{r['title']}\" by {auth}, {lic}, source: {r.get('source_page_url') or r.get('source')}")
    L.append("")
open(os.path.join(ROOT, "ATTRIBUTION.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L))

# sources
def fsize(rel):
    p = os.path.join(ROOT, rel)
    return (os.path.getsize(p), sha256(p)) if os.path.exists(p) else (None, None)

S = []
for name, url, pub, lic, rel, used in [
    ("atlas service points (stop points, Bern + neighbours)", "https://data.sbb.ch/explore/dataset/dienststellen-gemass-opentransportdataswiss/", "SBB / atlas", "SBB Open Data terms", "data/stations.json", "station keys (number, sloid, coordinates)"),
    ("Wikimedia Commons API (categories, geosearch, imageinfo)", "https://commons.wikimedia.org/w/api.php", "Wikimedia Foundation / contributors", "per file (in manifest)", "data/commons_candidates.json", "photo candidates and licence metadata"),
    ("Panoramax STAC search", "https://api.panoramax.xyz/api/search", "Panoramax federation / contributors", "per picture (in manifest)", "data/panoramax_items.json", "georeferenced street-level photos with heading"),
    ("SBB Trafimage plan index + operator link checks", "https://data.sbb.ch/explore/dataset/haltestelle-karte-trafimage/", "SBB and others", "per link (in manifest)", "data/operator_links.json", "link register"),
    ("swisstopo SWISSIMAGE WMS", "https://wms.geo.admin.ch/", "swisstopo", "swisstopo free geodata (OGD)", "data/orthophotos.json", "orthophoto crops"),
    ("transit/ edge lookup and edges (read-only)", "../transit/data/edge_lookup.json; ../transit/data/edges.geojson", "this repository (transit/)", "see transit/", None, "edge SLOIDs for designations and edges in view"),
]:
    b, h = fsize(rel) if rel else (None, None)
    S.append({"name": name, "url": url, "publisher": pub, "licence": lic, "retrieved": now[:10], "derived_file": rel, "bytes": b, "sha256": h, "used_for": used})
json.dump({"generated": now, "rebuild": "see HANDOFF.md (python -I -X utf8 tools/01..09 in order)", "sources": S},
          open(os.path.join(ROOT, "SOURCES.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(json.dumps(manifest["counts"], indent=1))
