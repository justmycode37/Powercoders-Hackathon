"""swissBUILDINGS3D 3.0 (CityGML 2.0, LV95 / LN02) -> Bern building outputs.

Usage:
  python -I make_buildings.py <dir with *.citygml.zip> <boundary_lv95.geojson> <out dir> [work dir]

Outputs (out dir):
  bern_buildings.geojson        footprint per building (WGS84, 7 dp) + EGID + LN02 heights, whole coverage box
  central_lod2.glb              triangulated LOD2 roofs/walls/ground for the central sample box
  central_lod2.meta.json        origin, axes, units, per-building index table for the GLB

The zips are streamed (no unzip). Each sheet is parsed in its own process.
"""
import glob, json, math, os, pickle, struct, sys, zipfile
from multiprocessing import Pool

import numpy as np

BOX = (2589000, 1194000, 2606000, 1205000)          # coverage box LV95
CENTRAL = (2599600, 1199100, 2601800, 1200400)      # GLB sample: Bahnhof - Altstadt - Bärengraben - Bundeshaus
ORIGIN = (2600700.0, 1199750.0, 500.0)              # GLB local origin (LV95 E, N, LN02 H)

NS_B = "{http://www.opengis.net/citygml/building/2.0}"
NS_G = "{http://www.opengis.net/gml}"
NS_GEN = "{http://www.opengis.net/citygml/generics/2.0}"
SURF = {NS_B + "RoofSurface": "roof", NS_B + "WallSurface": "wall", NS_B + "GroundSurface": "ground"}
ATTR_TAGS = {NS_GEN + t for t in ("stringAttribute", "intAttribute", "doubleAttribute", "measureAttribute")}


def direct_attrs(el):
    out = {}
    for c in el:
        if c.tag in ATTR_TAGS:
            v = c.findtext(NS_GEN + "value")
            out[c.get("name")] = v
    return out


def poslist(ring):
    t = ring.findtext(".//" + NS_G + "posList")
    if t is None:
        pts = [p.text for p in ring.iter(NS_G + "pos")]
        t = " ".join(pts)
    a = np.array(t.split(), dtype=np.float64).reshape(-1, 3)
    if len(a) > 1 and np.allclose(a[0], a[-1]):
        a = a[:-1]
    return a


def polygons(surface):
    for poly in surface.iter(NS_G + "Polygon"):
        ext = poly.find(NS_G + "exterior")
        if ext is None:
            continue
        rings = [poslist(ext)]
        for i in poly.findall(NS_G + "interior"):
            rings.append(poslist(i))
        if len(rings[0]) >= 3:
            yield rings


def triangulate(rings):
    import mapbox_earcut as earcut
    ext = rings[0]
    # Newell normal
    n = np.zeros(3)
    for i in range(len(ext)):
        a, b = ext[i], ext[(i + 1) % len(ext)]
        n += [(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])]
    ln = np.linalg.norm(n)
    if ln < 1e-9:
        return None
    n /= ln
    drop = int(np.argmax(np.abs(n)))
    keep = [i for i in range(3) if i != drop]
    verts = np.vstack(rings)
    v2 = verts[:, keep] - verts[0, keep]
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(v2, ends)
    if len(idx) == 0:
        return None
    tris = np.asarray(idx, dtype=np.int64).reshape(-1, 3)
    # keep winding consistent with the polygon normal
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    flip = np.einsum("ij,j->i", np.cross(b - a, c - a), n) < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    return verts, tris, n


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def process_sheet(path):
    from lxml import etree
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely.validation import make_valid

    sheet = os.path.basename(path).split("_")[4]
    edition = os.path.basename(path).split("_")[3]
    z = zipfile.ZipFile(path)
    f = z.open([n for n in z.namelist() if n.endswith(".gml")][0])
    recs, mesh = [], []
    for _, el in etree.iterparse(f, events=("end",), tag=NS_B + "Building", huge_tree=True):
        gid = el.get(NS_G + "id")
        attrs = direct_attrs(el)
        if not attrs:
            p = el.find(".//" + NS_B + "BuildingPart")
            if p is not None:
                attrs = direct_attrs(p)
        polys = {"roof": [], "wall": [], "ground": []}
        roof_attrs = None
        for s in el.iter(*SURF.keys()):
            k = SURF[s.tag]
            if k == "roof" and roof_attrs is None:
                roof_attrs = direct_attrs(s)
            polys[k].extend(polygons(s))
        if not attrs and roof_attrs:
            attrs = roof_attrs
        allpts = [r[0] for v in polys.values() for r in v]
        if not allpts:
            el.clear(); continue
        foot_src = "GroundSurface" if polys["ground"] else "RoofSurface projection"
        shp = []
        for rings in (polys["ground"] or polys["roof"]):
            try:
                g = Polygon(rings[0][:, :2], [r[:, :2] for r in rings[1:]])
                if not g.is_valid:
                    g = make_valid(g)
                if g.area > 0.01:
                    shp.append(g)
            except Exception:
                pass
        if not shp:
            el.clear(); continue
        fp = unary_union(shp)
        if fp.geom_type not in ("Polygon", "MultiPolygon"):
            fp = make_valid(fp)
            parts = [g for g in getattr(fp, "geoms", [fp]) if g.geom_type in ("Polygon", "MultiPolygon")]
            fp = unary_union(parts) if parts else None
        if fp is None or fp.is_empty:
            el.clear(); continue
        c = fp.representative_point()
        if not (BOX[0] <= c.x <= BOX[2] and BOX[1] <= c.y <= BOX[3]):
            el.clear(); continue
        zs_all = np.concatenate([r[:, 2] for v in polys.values() for rs in v for r in rs])
        ground_z = min(float(r[:, 2].min()) for rs in polys["ground"] for r in rs) if polys["ground"] else None
        roof_z = np.concatenate([r[:, 2] for rs in polys["roof"] for r in rs]) if polys["roof"] else zs_all
        rec = {
            "gml_id": gid, "sheet": sheet, "edition": edition,
            "egid": attrs.get("EGID"), "objektart": attrs.get("OBJEKTART"),
            "dach_max": fnum(attrs.get("DACH_MAX")), "dach_min": fnum(attrs.get("DACH_MIN")),
            "gelaendepunkt": fnum(attrs.get("GELAENDEPUNKT")),
            "herkunft": attrs.get("HERKUNFT"), "herkunft_jahr": attrs.get("HERKUNFT_JAHR"),
            "revision_jahr": attrs.get("REVISION_JAHR"),
            "ground_z": ground_z, "roof_max_z": float(roof_z.max()), "roof_min_z": float(roof_z.min()),
            "min_z": float(zs_all.min()),
            "n_roof": len(polys["roof"]), "n_wall": len(polys["wall"]), "n_ground": len(polys["ground"]),
            "footprint_from": foot_src, "footprint_lv95": fp.wkb, "centroid": (c.x, c.y),
        }
        recs.append(rec)
        if CENTRAL[0] <= c.x <= CENTRAL[2] and CENTRAL[1] <= c.y <= CENTRAL[3]:
            tri = {}
            for k, v in polys.items():
                out = []
                for rings in v:
                    t = triangulate(rings)
                    if t is not None:
                        out.append(t)
                tri[k] = out
            mesh.append((gid, tri))
        el.clear()
        while el.getprevious() is not None:
            del el.getparent()[0]
    return sheet, recs, mesh


def write_glb(path, mesh_items, meta):
    """mesh_items: list of (building_index, {roof|wall|ground: [(verts, tris, normal)]})"""
    colors = {"roof": [0.72, 0.33, 0.25, 1], "wall": [0.93, 0.91, 0.87, 1], "ground": [0.55, 0.55, 0.55, 1]}
    bin_parts, views, accessors, prims, materials = [], [], [], [], []
    offset = 0

    def add_view(arr, target):
        nonlocal offset
        b = arr.tobytes()
        pad = (-len(b)) % 4
        bin_parts.append(b + b"\0" * pad)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(b), "target": target})
        offset += len(b) + pad
        return len(views) - 1

    # ground faces are left out of the GLB (they lie on the terrain; footprints are in the GeoJSON);
    # normals are left out too (flat per polygon, the renderer computes them) to keep the file < 25 MB
    for k in ("roof", "wall"):
        P, N, F, I = [], [], [], []
        base = 0
        for bi, tri in mesh_items:
            for verts, tris, n in tri.get(k, []):
                loc = np.empty_like(verts)
                loc[:, 0] = verts[:, 0] - ORIGIN[0]
                loc[:, 1] = verts[:, 2] - ORIGIN[2]
                loc[:, 2] = -(verts[:, 1] - ORIGIN[1])
                P.append(loc); N.append(np.tile([n[0], n[2], -n[1]], (len(verts), 1)))
                F.append(np.full(len(verts), bi)); I.append(tris + base)
                base += len(verts)
        if not P:
            continue
        P = np.vstack(P).astype(np.float32)
        F = np.concatenate(F).astype(np.float32); I = np.vstack(I).astype(np.uint32).ravel()
        materials.append({"name": k, "pbrMetallicRoughness": {"baseColorFactor": colors[k], "metallicFactor": 0,
                                                              "roughnessFactor": 0.9}, "doubleSided": True})
        a = len(accessors)
        accessors += [
            {"bufferView": add_view(P, 34962), "componentType": 5126, "count": len(P), "type": "VEC3",
             "min": P.min(0).tolist(), "max": P.max(0).tolist()},
            {"bufferView": add_view(F, 34962), "componentType": 5126, "count": len(F), "type": "SCALAR"},
            {"bufferView": add_view(I, 34963), "componentType": 5125, "count": len(I), "type": "SCALAR"},
        ]
        prims.append({"attributes": {"POSITION": a, "_BUILDING_INDEX": a + 1}, "indices": a + 2,
                      "material": len(materials) - 1, "mode": 4})
        meta.setdefault("counts", {})[k] = {"vertices": int(len(P)), "triangles": int(len(I) // 3)}
    gltf = {"asset": {"version": "2.0", "generator": "bern-research/city3d/tools/make_buildings.py"},
            "scene": 0, "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "swissBUILDINGS3D_central_LOD2", "mesh": 0}],
            "meshes": [{"name": "buildings", "primitives": prims}],
            "materials": materials, "accessors": accessors, "bufferViews": views,
            "buffers": [{"byteLength": offset}],
            "extras": {k: meta[k] for k in ("origin_lv95_ln02", "axes", "units", "source", "licence")}}
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    binb = b"".join(bin_parts)
    with open(path, "wb") as o:
        o.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)))
        o.write(struct.pack("<II", len(js), 0x4E4F534A)); o.write(js)
        o.write(struct.pack("<II", len(binb), 0x004E4942)); o.write(binb)


def main():
    src, boundary, out = sys.argv[1], sys.argv[2], sys.argv[3]
    work = sys.argv[4] if len(sys.argv) > 4 else os.path.join(src, "..", "work")
    os.makedirs(out, exist_ok=True); os.makedirs(work, exist_ok=True)
    from pyproj import Transformer
    from shapely import wkb
    from shapely.geometry import shape, mapping
    from shapely.ops import transform  # noqa
    from shapely.prepared import prep

    zips = sorted(glob.glob(os.path.join(src, "*_2021_*citygml.zip")))
    todo = [z for z in zips if not os.path.exists(os.path.join(work, os.path.basename(z) + ".pkl"))]
    with Pool(min(6, max(1, len(todo)))) as pool:
        for sheet, recs, mesh in pool.imap_unordered(process_sheet, todo):
            zname = [z for z in todo if f"_{sheet}_" in z][0]
            pickle.dump((sheet, recs, mesh), open(os.path.join(work, os.path.basename(zname) + ".pkl"), "wb"))
            print("sheet", sheet, len(recs), "buildings", len(mesh), "central", flush=True)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dem import Dem
    dem = Dem(os.path.join(src, "..", "swissalti3d"))
    bern = prep(shape(json.load(open(boundary))["geometry"]))
    tr = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
    to_wgs = lambda x, y, z=None: tr.transform(x, y)
    seen, feats, mesh_all = set(), [], []
    stats = {"sheets": [], "buildings": 0, "in_municipality": 0, "with_egid": 0, "footprint_from_roof": 0}
    for z in zips:
        sheet, recs, mesh = pickle.load(open(os.path.join(work, os.path.basename(z) + ".pkl"), "rb"))
        stats["sheets"].append({"sheet": sheet, "file": os.path.basename(z), "buildings_in_box": len(recs)})
        central_ids = {g for g, _ in mesh}
        for r in recs:
            if r["gml_id"] in seen:
                continue
            seen.add(r["gml_id"])
            fp = wkb.loads(r["footprint_lv95"])
            g = transform(to_wgs, fp.simplify(0.05, preserve_topology=True))  # drop collinear vertices (5 cm)
            gj = json.loads(json.dumps(mapping(g)), parse_float=lambda s: round(float(s), 7))
            terr = float(dem.sample([r["centroid"][0]], [r["centroid"][1]])[0])
            # swissBUILDINGS3D 3.0 extends walls/GroundSurface ~3 m below the terrain (median -3.4 m vs GELAENDEPUNKT
            # on sheet 1166-42), so heights are measured from the terrain point, not from the GroundSurface.
            if r["gelaendepunkt"]:
                base, base_how = r["gelaendepunkt"], "GELAENDEPUNKT"
            elif terr == terr:
                base, base_how = terr, "swissALTI3D 2 m at footprint point"
            else:
                base, base_how = r["min_z"], "lowest LOD2 vertex"
            roof_max = r["dach_max"] if r["dach_max"] is not None else r["roof_max_z"]
            inm = bern.contains(fp.representative_point())
            inferred = r["footprint_from"] != "GroundSurface" or base_how != "GELAENDEPUNKT"
            how = []
            if r["footprint_from"] != "GroundSurface":
                how.append("footprint = union of roof polygons projected to 2D (no GroundSurface)")
            if base_how != "GELAENDEPUNKT":
                how.append("height_m measured from " + base_how + " (no GELAENDEPUNKT attribute)")
            props = {
                "id": "swissbuildings3d:" + r["gml_id"].removeprefix("ID_"),
                "egid": int(r["egid"]) if r["egid"] and r["egid"].isdigit() else None,
                "objektart": r["objektart"],
                "terrain_point_z_m": round(r["gelaendepunkt"], 2) if r["gelaendepunkt"] else None,
                "terrain_z_m": round(terr, 2) if terr == terr else None,
                "ground_surface_z_m": round(r["ground_z"], 2) if r["ground_z"] is not None else None,
                "roof_min_z_m": round(r["dach_min"], 2) if r["dach_min"] is not None else round(r["roof_min_z"], 2),
                "roof_max_z_m": round(roof_max, 2),
                "height_m": round(roof_max - base, 2),
                "height_base": base_how,
                "footprint_area_m2": round(fp.area, 1),
                "footprint_from": r["footprint_from"],
                "n_roof": r["n_roof"], "n_wall": r["n_wall"],
                "capture_year": int(r["herkunft_jahr"]) if r["herkunft_jahr"] else None,
                "revision_year": int(r["revision_jahr"]) if r["revision_jahr"] else None,
                "lv95_e": round(r["centroid"][0], 2), "lv95_n": round(r["centroid"][1], 2),
                "in_municipality_bern": bool(inm),
                "in_central_glb": r["gml_id"] in central_ids,
                "sheet": r["sheet"],
                "source": f"swissBUILDINGS3D 3.0 {r['edition']}",
                "inferred": inferred,
            }
            if inferred:
                props["inferred_how"] = "; ".join(how)
            feats.append({"type": "Feature", "properties": props, "geometry": gj})
            stats["buildings"] += 1
            stats["in_municipality"] += int(inm)
            stats["with_egid"] += int(props["egid"] is not None)
            stats["footprint_from_roof"] += int(r["footprint_from"] != "GroundSurface")
        mesh_all.extend(mesh)

    head = {"type": "FeatureCollection",
          "crs_note": "Geometry WGS84 (EPSG:4326) lon/lat, 7 decimals. Heights *_z_m are LN02 metres above sea "
                      "level (swissBUILDINGS3D is LV95/LN02). height_m = roof_max_z_m - terrain_point_z_m "
                      "(GELAENDEPUNKT), else - terrain_z_m (swissALTI3D 2 m at lv95_e/lv95_n); see height_base. "
                      "ground_surface_z_m is the source GroundSurface, which swissBUILDINGS3D 3.0 places ~3 m below "
                      "the terrain (walls are extended underground), so it is not a ground level. Footprints are the union of "
                      "GroundSurface polygons (else roof polygons), simplified with a 5 cm tolerance.",
          "licence": "swisstopo open government data (OGD), free use with attribution '© swisstopo'",
          "source": "swissBUILDINGS3D 3.0 Beta, CityGML edition 2021, LK25 sheets 1166-12..44 and 1167-11..33 "
                    "(https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d_3_0)",
          "coverage_lv95": BOX}
    for name, sel in (("bern_buildings_municipality", True), ("bern_buildings_ring", False)):
        fc = {**head, "name": name,
              "selection": "representative point inside Bern municipality (BFS 351, swissBOUNDARIES3D 2026)" if sel
              else "representative point inside the coverage box but outside Bern municipality",
              "features": [f for f in feats if f["properties"]["in_municipality_bern"] == sel]}
        with open(os.path.join(out, name + ".geojson"), "w", encoding="utf-8") as o:
            json.dump(fc, o, ensure_ascii=False, separators=(",", ":"))

    # GLB
    id_index = {}
    items = []
    for gid, tri in mesh_all:
        if gid in id_index:
            continue
        id_index[gid] = len(id_index)
        items.append((id_index[gid], tri))
    by_id = {f["properties"]["id"]: f["properties"] for f in feats}
    table = []
    for gid, i in sorted(id_index.items(), key=lambda kv: kv[1]):
        p = by_id.get("swissbuildings3d:" + gid.removeprefix("ID_"), {})
        table.append({"index": i, "id": "swissbuildings3d:" + gid.removeprefix("ID_"), "egid": p.get("egid"),
                      "objektart": p.get("objektart"), "height_m": p.get("height_m")})
    meta = {
        "file": "central_lod2.glb",
        "origin_lv95_ln02": {"E": ORIGIN[0], "N": ORIGIN[1], "H": ORIGIN[2], "crs": "EPSG:2056 + LN02"},
        "axes": "glTF +X = East (LV95 E - origin E), +Y = Up (LN02 H - origin H), +Z = South (-(LV95 N - origin N))",
        "units": "metres",
        "central_box_lv95": CENTRAL,
        "source": "swissBUILDINGS3D 3.0 Beta CityGML, edition 2021 (swisstopo), LOD2 Roof/Wall/GroundSurface",
        "licence": "swisstopo OGD, attribution '© swisstopo'",
        "inferred": False,
        "note": "Geometry is the source LOD2 Roof and Wall polygons triangulated (earcut); no simplification. "
                "GroundSurface and normals are omitted (compute flat normals on load). Per-vertex float attribute "
                "_BUILDING_INDEX maps to the buildings table below.",
        "buildings": table,
    }
    write_glb(os.path.join(out, "central_lod2.glb"), items, meta)
    meta["glb_bytes"] = os.path.getsize(os.path.join(out, "central_lod2.glb"))
    json.dump(meta, open(os.path.join(out, "central_lod2.meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    stats["central_glb_buildings"] = len(items)
    stats["glb_counts"] = meta.get("counts")
    json.dump(stats, open(os.path.join(out, "buildings_stats.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k != "sheets"}, indent=1))


if __name__ == "__main__":
    main()
