"""Validate references/ against the lead contract. Exit code 1 on any error.
Checks: every stored file exists, sha256 matches, size <= 5 MB, total stored bytes <= 60 MB; every stored
record has licence, author/publisher, source URL and at least one station with a valid atlas number+sloid
(assets exempt); licences of stored third-party files are in the allowed set; no stored file is unlisted;
GeoJSON coordinates have at most 7 decimals and lie in the Bern area; edge SLOIDs exist in transit/edges.geojson.
Writes validation/report.json and validation/report.md.  Usage: python -I -X utf8 tools/09_validate.py
"""
import sys, os, re, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, sha256, load

TRANSIT = os.path.join(os.path.dirname(ROOT), "transit", "data")
M = json.load(open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))
ST = {s["number"]: s for s in load("stations.json")["stations"]}
EXTRA = {}  # non-stop service points are now part of data/stations.json (stop_point = false)
EDGE_SLOIDS = {f["properties"]["sloid"] for f in json.load(open(os.path.join(TRANSIT, "edges.geojson"), encoding="utf-8"))["features"]}
ALLOWED = re.compile(r"^(CC0|CC BY(-SA)? \d|CC BY(-SA)?$|Public domain|PD|Attribution|swisstopo free geodata|CC0 1\.0)", re.I)

err, warn = [], []
total = 0
listed = set()
for r in M["references"]:
    rid = r["id"]
    for s in r.get("stations") or []:
        n = s["number"]
        exp = ST.get(n, {}).get("sloid") or EXTRA.get(n)
        if exp is None:
            err.append(f"{rid}: station {n} not in data/stations.json")
        elif s.get("sloid") != exp:
            err.append(f"{rid}: station {n} sloid {s.get('sloid')} != {exp}")
    for e in r.get("edges_in_view") or []:
        if e["edge_sloid"] not in EDGE_SLOIDS:
            err.append(f"{rid}: edge {e['edge_sloid']} not in transit edges")
    for d in r.get("edge_designations") or []:
        for s in d["edge_sloids"]:
            if s not in EDGE_SLOIDS:
                warn.append(f"{rid}: designation edge {s} not in transit edges.geojson (lookup only)")
    if not r.get("stored"):
        continue
    f = r["file"]
    listed.add(f.replace("\\", "/"))
    if r.get("world_file"):
        listed.add(r["world_file"]); listed.add(f[:-4] + ".json")
    if r["kind"] == "parametric_asset":
        listed.add(f[:-5] + ".json")
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        err.append(f"{rid}: missing file {f}"); continue
    b = os.path.getsize(p); total += b
    if b > 5 * 1024 * 1024:
        err.append(f"{rid}: {f} is {b} bytes (> 5 MB)")
    if sha256(p) != r["download"]["sha256"]:
        err.append(f"{rid}: sha256 mismatch for {f}")
    for k in ("licence", "author"):
        if not r.get(k):
            err.append(f"{rid}: stored file without {k}")
    if not (r.get("source_page_url") or r["kind"] == "parametric_asset"):
        err.append(f"{rid}: stored file without source_page_url")
    if r["kind"] != "parametric_asset" and not r.get("stations"):
        err.append(f"{rid}: stored file without station key")
    if not ALLOWED.match(r.get("licence") or ""):
        err.append(f"{rid}: licence '{r.get('licence')}' not in the allowed set")
    if r["kind"] in ("photo", "streetlevel_photo") and r.get("author") in (None, "", "unknown"):
        err.append(f"{rid}: no author")
    if not r.get("licence_url"):
        err.append(f"{rid}: stored file without licence_url")
    if r.get("relevance_unverified"):
        err.append(f"{rid}: stored file whose station link is unverified")
    if any(set((s.get("relation") or "").split("+")) <= {"search"} for s in r.get("stations") or []) and not r.get("relevance_check"):
        err.append(f"{rid}: stored search hit without relevance_check")
if total > 60 * 1024 * 1024:
    err.append(f"total stored bytes {total} > 60 MB")

for sub in ("images", "orthophoto", "assets"):
    for dp, _, fs in os.walk(os.path.join(ROOT, sub)):
        for fn in fs:
            rel = os.path.relpath(os.path.join(dp, fn), ROOT).replace("\\", "/")
            if rel not in listed:
                err.append(f"unlisted file in tree: {rel}")

SRC = json.load(open(os.path.join(ROOT, "SOURCES.json"), encoding="utf-8"))["sources"]
for x in SRC:
    if not x.get("sha256"):
        err.append(f"SOURCES.json: '{x['name']}' has no sha256")
TS = {f["properties"]["number"] for f in json.load(open(os.path.join(TRANSIT, "stations.geojson"), encoding="utf-8"))["features"]}
used = {s["number"] for r in M["references"] for s in r.get("stations") or []}
for n, st in ST.items():
    if n not in TS and not st.get("coverage_note"):
        err.append(f"data/stations.json: {n} not in transit stations and no coverage_note")
    if n not in TS and n in used:
        warn.append(f"station {n} is referenced but outside transit coverage")
unver = [r for r in M["references"] if r.get("relevance_unverified")]

G = json.load(open(os.path.join(ROOT, "references.geojson"), encoding="utf-8"))
for f in G["features"]:
    lon, lat = f["geometry"]["coordinates"]
    if len(repr(lon).split(".")[-1]) > 7 or len(repr(lat).split(".")[-1]) > 7:
        err.append(f"{f['id']}: more than 7 decimals")
    if not (7.25 <= lon <= 7.6 and 46.85 <= lat <= 47.05):
        warn.append(f"{f['id']}: camera outside Bern area ({lon}, {lat})")

kinds = collections.Counter(r["kind"] for r in M["references"])
stored_k = collections.Counter(r["kind"] for r in M["references"] if r.get("stored"))
rep = {"checked": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "ok": not err, "errors": err, "warnings": warn[:200],
       "warnings_total": len(warn), "references": len(M["references"]), "by_kind": dict(kinds), "stored_by_kind": dict(stored_k),
       "stored_bytes": total, "geojson_points": len(G["features"]), "relevance_unverified_linked": len(unver),
       "search_linked_verified": sum(1 for r in M["references"] if r.get("relevance_check") and not r.get("relevance_unverified"))}
os.makedirs(os.path.join(ROOT, "validation"), exist_ok=True)
json.dump(rep, open(os.path.join(ROOT, "validation", "report.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
md = [f"# references/ validation", "", f"Checked {rep['checked']}: **{'OK' if rep['ok'] else 'FAILED'}**", "",
      f"- references: {rep['references']} ({', '.join(f'{k} {v}' for k, v in kinds.items())})",
      f"- stored files: {sum(stored_k.values())} ({', '.join(f'{k} {v}' for k, v in stored_k.items())}), {total / 1048576:.1f} MiB",
      f"- viewpoint points in references.geojson: {rep['geojson_points']}",
      f"- search-only station links: {rep['search_linked_verified']} confirmed by category or coordinates, {rep['relevance_unverified_linked']} flagged relevance_unverified (link only)", f"- errors: {len(err)}, warnings: {len(warn)}", ""]
md += ["## Errors", ""] + [f"- {e}" for e in err[:100]] + [""] if err else []
md += ["## Warnings (first 30)", ""] + [f"- {w}" for w in warn[:30]] if warn else []
open(os.path.join(ROOT, "validation", "report.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
print("\n".join(md[:8]))
for e in err[:20]:
    print("ERR", e)
sys.exit(1 if err else 0)
