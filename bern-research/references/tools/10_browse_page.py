"""Static browse page for humans: references/browse.html, grouped by station, every stored image with its
credit line, viewpoint and model-use note, plus linked operator plans. No scripts, no external resources.
Usage: python -I -X utf8 tools/10_browse_page.py
"""
import sys, os, json, html, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT

M = json.load(open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))
BS = json.load(open(os.path.join(ROOT, "by_station.json"), encoding="utf-8"))["stations"]
R = {r["id"]: r for r in M["references"]}
e = html.escape

out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
       "<title>Bern station references</title><style>",
       ":root{--bg:#fafaf8;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--line:#e3e2dc;--acc:#b5121b}",
       "@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mut:#a3a29b;--card:#20201e;--line:#34332f;--acc:#ff6b6b}}",
       "body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:16px}",
       "h1{font-size:22px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}",
       ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}",
       ".c{background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden}.c img{width:100%;height:180px;object-fit:cover;display:block}",
       ".c div{padding:8px}.m{color:var(--mut);font-size:12px}a{color:var(--acc)}ul{padding-left:18px}code{font-size:12px}",
       "</style></head><body><main>",
       f"<h1>Bern station references</h1><p class='m'>Generated {e(M['generated'])} from <code>manifest.json</code>. "
       f"{M['counts']['references']} references, {M['counts']['stored_files']} stored files. Stored images are scaled derivatives; "
       "credits are under each image and in <code>ATTRIBUTION.md</code>. Operator plans are links only.</p>"]
for num, st in BS.items():
    imgs = [R[i] for i in st["stored"] if R[i]["kind"] in ("photo", "streetlevel_photo", "orthophoto")]
    links = [R[i] for i in st["linked"] if R[i]["kind"] not in ("photo", "streetlevel_photo")]
    if not imgs and not links:
        continue
    out.append(f"<h2 id='s{num}'>{e(st['name'] or num)} <span class='m'>{num} · {e(st['sloid'] or '')}</span></h2>")
    if imgs:
        out.append("<div class='g'>")
        for r in imgs:
            vp = r.get("viewpoint") or {}
            hd = vp.get("heading_deg")
            ev = ", ".join(sorted({x.get("designation") or x["edge_sloid"] for x in r.get("edges_in_view") or []}))
            out.append(f"<div class='c'><a href='{e(r['file'])}'><img loading='lazy' src='{e(r['file'])}' alt='{e(r['title'])}'></a><div>"
                       f"<b>{e(r['title'][:90])}</b><br><span class='m'>{e(r.get('author') or '')[:80]} · "
                       f"<a href='{e(r.get('licence_url') or '#')}'>{e(r.get('licence') or '')}</a> · <a href='{e(r.get('source_page_url') or '#')}'>source</a>"
                       f"{' · ' + e(str(r.get('capture_date'))) if r.get('capture_date') else ''}"
                       f"{' · heading ' + str(round(hd)) + '°' if hd is not None else ''}{' · edges ' + e(ev) if ev else ''}</span>"
                       f"<br><span class='m'>{e(', '.join(r.get('feature_tags') or []))}</span></div></div>")
        out.append("</div>")
    if links:
        out.append("<ul>" + "".join(f"<li><a href='{e(l['original_url'])}'>{e(l['title'])}</a> <span class='m'>({e(l['kind'])}, link only)</span></li>" for l in links) + "</ul>")
out.append("</main></body></html>")
open(os.path.join(ROOT, "browse.html"), "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("browse.html written")
