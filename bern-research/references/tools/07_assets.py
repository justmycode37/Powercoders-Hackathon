"""Original parametric transit-furniture assets (glTF 2.0, embedded buffers, stdlib only).

Every asset is an APPROXIMATION built from simple primitives. Dimensions come from the evidence listed in
each sidecar (photos in this collection, SBB/Bern datasets, design standards) and are labelled approximate.
No operator artwork, logos or proprietary designs are reproduced (the station clock is a generic disc clock).

Conventions: glTF Y-up, right-handed, metres. Origin = centre of the footprint at ground level (y = 0).
+X = along the long side ("length"), +Z = front (passenger side), unless the sidecar says otherwise.
Writes assets/<id>.gltf + assets/<id>.json and data/assets.json.
Usage: python -I -X utf8 tools/07_assets.py
"""
import sys, os, json, math, struct, base64, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, save, sha256, load

OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)

MAT = {  # name: (rgba, metallic, roughness)
    "steel_grey": ((0.45, 0.47, 0.50, 1), 0.8, 0.4),
    "stainless": ((0.75, 0.76, 0.78, 1), 0.9, 0.3),
    "dark_grey": ((0.12, 0.13, 0.14, 1), 0.3, 0.6),
    "anthracite": ((0.20, 0.21, 0.22, 1), 0.5, 0.5),
    "glass": ((0.75, 0.85, 0.90, 0.30), 0.0, 0.05),
    "red": ((0.80, 0.05, 0.05, 1), 0.1, 0.5),
    "white": ((0.93, 0.93, 0.92, 1), 0.0, 0.6),
    "screen": ((0.02, 0.03, 0.06, 1), 0.2, 0.2),
    "concrete": ((0.62, 0.61, 0.58, 1), 0.0, 0.9),
    "asphalt": ((0.25, 0.25, 0.26, 1), 0.0, 0.95),
    "tactile_white": ((0.95, 0.95, 0.95, 1), 0.0, 0.7),
    "wood": ((0.55, 0.38, 0.22, 1), 0.0, 0.7),
    "blue_sign": ((0.10, 0.20, 0.45, 1), 0.1, 0.5),
}


class Mesh:
    def __init__(self):
        self.parts = {}  # material -> (positions, normals, indices)

    def tri(self, mat, a, b, c):
        p = self.parts.setdefault(mat, ([], [], []))
        n = norm(cross(sub(b, a), sub(c, a)))
        base = len(p[0])
        p[0].extend([a, b, c]); p[1].extend([n, n, n]); p[2].extend([base, base + 1, base + 2])

    def quad(self, mat, a, b, c, d):
        self.tri(mat, a, b, c); self.tri(mat, a, c, d)

    def box(self, mat, cx, cy, cz, sx, sy, sz):
        """axis-aligned box: centre (cx, cy, cz), size (sx, sy, sz)"""
        x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2
        v = lambda x, y, z: (x, y, z)
        self.quad(mat, v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1))  # +z
        self.quad(mat, v(x1, y0, z0), v(x0, y0, z0), v(x0, y1, z0), v(x1, y1, z0))  # -z
        self.quad(mat, v(x1, y0, z1), v(x1, y0, z0), v(x1, y1, z0), v(x1, y1, z1))  # +x
        self.quad(mat, v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1), v(x0, y1, z0))  # -x
        self.quad(mat, v(x0, y1, z1), v(x1, y1, z1), v(x1, y1, z0), v(x0, y1, z0))  # +y
        self.quad(mat, v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1))  # -y

    def cyl(self, mat, cx, cy, cz, r, h, axis="y", seg=20):
        """cylinder centred at (cx,cy,cz), along axis y or z"""
        def P(a, t):
            u, w = r * math.cos(a), r * math.sin(a)
            return (cx + u, cy + t, cz + w) if axis == "y" else (cx + u, cy + w, cz + t)
        for i in range(seg):
            a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            if axis == "y":
                self.quad(mat, P(a0, -h / 2), P(a0, h / 2), P(a1, h / 2), P(a1, -h / 2))
                self.tri(mat, (cx, cy + h / 2, cz), P(a1, h / 2), P(a0, h / 2))
                self.tri(mat, (cx, cy - h / 2, cz), P(a0, -h / 2), P(a1, -h / 2))
            else:
                self.quad(mat, P(a0, -h / 2), P(a1, -h / 2), P(a1, h / 2), P(a0, h / 2))
                self.tri(mat, (cx, cy, cz + h / 2), P(a0, h / 2), P(a1, h / 2))
                self.tri(mat, (cx, cy, cz - h / 2), P(a1, -h / 2), P(a0, -h / 2))

    def prism(self, mat, poly_xz, y0, y1, top_mat=None, sides=True):
        """extrude a simple polygon (list of (x,z), counter-clockwise seen from +y) between y0 and y1"""
        tm = top_mat or mat
        tris = earcut(poly_xz)
        for a, b, c in tris:
            A, B, C = poly_xz[a], poly_xz[b], poly_xz[c]
            self.tri(tm, (A[0], y1, A[1]), (C[0], y1, C[1]), (B[0], y1, B[1]))
            self.tri(mat, (A[0], y0, A[1]), (B[0], y0, B[1]), (C[0], y0, C[1]))
        if sides:
            n = len(poly_xz)
            for i in range(n):
                (x0, z0), (x1, z1) = poly_xz[i], poly_xz[(i + 1) % n]
                self.quad(mat, (x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0))


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    l = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1
    return (a[0] / l, a[1] / l, a[2] / l)


def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def earcut(poly):
    """ear clipping for a simple polygon in the x/z plane; returns index triples.
    Orientation is normalised so that triangles face +y when emitted as (a, c, b) in prism()."""
    idx = list(range(len(poly)))
    if area2(poly) < 0:
        idx.reverse()
    out = []

    def inside(p, a, b, c):
        def s(p1, p2, p3): return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((i0, i1, i2)); idx.pop(k); break
        else:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def write_gltf(asset_id, mesh, extras):
    blob = bytearray(); views = []; accs = []; prims = []; mats = []
    for mname, (pos, nor, ind) in mesh.parts.items():
        rgba, met, rough = MAT[mname]
        m = {"name": mname, "pbrMetallicRoughness": {"baseColorFactor": list(rgba), "metallicFactor": met, "roughnessFactor": rough}, "doubleSided": True}
        if rgba[3] < 1:
            m["alphaMode"] = "BLEND"
        mats.append(m)
        attrs = {}
        for key, data, comp in (("POSITION", pos, 3), ("NORMAL", nor, 3)):
            off = len(blob)
            for v in data:
                blob += struct.pack("<3f", *v)
            views.append({"buffer": 0, "byteOffset": off, "byteLength": len(blob) - off, "target": 34962})
            acc = {"bufferView": len(views) - 1, "componentType": 5126, "count": len(data), "type": "VEC3"}
            if key == "POSITION":
                acc["min"] = [min(v[i] for v in data) for i in range(3)]
                acc["max"] = [max(v[i] for v in data) for i in range(3)]
            accs.append(acc); attrs[key] = len(accs) - 1
        off = len(blob)
        for i in ind:
            blob += struct.pack("<I", i)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(blob) - off, "target": 34963})
        accs.append({"bufferView": len(views) - 1, "componentType": 5125, "count": len(ind), "type": "SCALAR"})
        prims.append({"attributes": attrs, "indices": len(accs) - 1, "material": len(mats) - 1})
        while len(blob) % 4:
            blob += b"\0"
    g = {"asset": {"version": "2.0", "generator": "bern-research/references/tools/07_assets.py", "copyright": "Original parametric approximation, CC0 1.0 (this repository)"},
         "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": asset_id, "mesh": 0, "extras": extras}],
         "meshes": [{"name": asset_id, "primitives": prims}], "materials": mats, "accessors": accs, "bufferViews": views,
         "buffers": [{"byteLength": len(blob), "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode()}]}
    p = os.path.join(OUT, asset_id + ".gltf")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(g, f, separators=(",", ":"))
    return p, sum(len(v[2]) // 3 for v in mesh.parts.values())


ASSETS = []


def asset(asset_id, title, params, evidence, build, notes=""):
    m = Mesh(); build(m, **params)
    extras = {"approximate": True, "units": "m", "up_axis": "+Y", "origin": "footprint centre at ground level", "params": params}
    p, ntri = write_gltf(asset_id, m, extras)
    bb = [[min(v[i] for part in m.parts.values() for v in part[0]) for i in range(3)], [max(v[i] for part in m.parts.values() for v in part[0]) for i in range(3)]]
    side = {"id": asset_id, "title": title, "file": f"assets/{asset_id}.gltf", "format": "glTF 2.0 (embedded buffer)",
            "approximate": True, "inferred": True, "inferred_how": "parametric primitives; dimensions estimated from the evidence listed, not measured",
            "units": "metre", "axes": "glTF: +Y up, right-handed; +X along the long side, +Z towards the passenger/front side",
            "origin": "centre of footprint at ground level (y = 0)", "parameters": params,
            "bbox_m": {"min": [round(x, 3) for x in bb[0]], "max": [round(x, 3) for x in bb[1]]}, "triangles": ntri,
            "evidence": evidence, "notes": notes, "licence": "CC0 1.0 (original work generated for this repository)",
            "bytes": os.path.getsize(p), "sha256": sha256(p), "source": "tools/07_assets.py"}
    json.dump(side, open(os.path.join(OUT, asset_id + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ASSETS.append(side)
    print(asset_id, ntri, "tris", flush=True)


# ---------------------------------------------------------------------------------------------- builders
def b_bench(m, length, seat_h, depth, back_h, legs):
    m.box("wood", 0, seat_h - 0.02, 0, length, 0.04, depth)  # seat slats as one slab
    m.box("wood", 0, seat_h + back_h / 2 + 0.05, -depth / 2 + 0.03, length, back_h, 0.04)
    for i in range(legs):
        x = -length / 2 + 0.15 + i * (length - 0.3) / max(1, legs - 1)
        m.box("steel_grey", x, (seat_h - 0.04) / 2, 0, 0.06, seat_h - 0.04, depth * 0.9)
        m.box("steel_grey", x, seat_h + back_h / 2 + 0.03, -depth / 2 + 0.06, 0.05, back_h + 0.1, 0.03)


def b_ticket_machine(m, width, depth, height, screen_w, screen_h):
    m.box("red", 0, height / 2, 0, width, height, depth)
    m.box("anthracite", 0, height - 0.08, 0.01, width + 0.04, 0.16, depth + 0.04)  # top cap
    m.box("screen", 0, 1.25, depth / 2 + 0.005, screen_w, screen_h, 0.01)
    m.box("dark_grey", 0, 0.95, depth / 2 + 0.04, width * 0.7, 0.10, 0.08)  # payment shelf


def b_recycling(m, bins, bin_w, depth, height):
    total = bins * bin_w
    for i in range(bins):
        x = -total / 2 + bin_w / 2 + i * bin_w
        m.box("stainless", x, height / 2, 0, bin_w - 0.02, height, depth)
        m.box("dark_grey", x, height - 0.12, depth / 2 + 0.003, bin_w * 0.6, 0.08, 0.006)  # slot
    m.box("stainless", 0, height + 0.01, 0, total, 0.02, depth + 0.02)


def b_info_stele(m, width, depth, height, panel_h):
    m.box("anthracite", 0, height / 2, 0, width, height, depth)
    m.box("white", 0, height - 0.15 - panel_h / 2, depth / 2 + 0.003, width - 0.06, panel_h, 0.006)
    m.box("white", 0, height - 0.15 - panel_h / 2, -depth / 2 - 0.003, width - 0.06, panel_h, 0.006)


def b_clock(m, diameter, mount_h, arm):
    m.box("dark_grey", 0, mount_h + diameter / 2 + 0.3, -arm, 0.06, 0.6, 0.06)  # hanger rod
    m.box("dark_grey", 0, mount_h + diameter + 0.6, -arm / 2, 0.06, 0.06, arm)
    m.cyl("white", 0, mount_h + diameter / 2, 0, diameter / 2, 0.08, axis="z", seg=40)
    m.cyl("dark_grey", 0, mount_h + diameter / 2, 0, diameter / 2 + 0.02, 0.06, axis="z", seg=40)
    c = mount_h + diameter / 2
    for i in range(12):  # hour marks on both faces
        a = 2 * math.pi * i / 12
        x, y = math.sin(a) * diameter * 0.40, c + math.cos(a) * diameter * 0.40
        for zf in (0.042, -0.042):
            m.box("dark_grey", x, y, zf, 0.02, 0.06, 0.004)
    for zf in (0.046, -0.046):
        m.box("dark_grey", 0, c + diameter * 0.15, zf, 0.025, diameter * 0.32, 0.004)  # hour hand at 12
        m.box("dark_grey", diameter * 0.18, c, zf, diameter * 0.38, 0.02, 0.004)        # minute hand at 3


def b_sector_sign(m, width, height, mount_h):
    m.box("blue_sign", 0, mount_h + height / 2, 0, width, height, 0.05)
    m.box("white", 0, mount_h + height / 2, 0.026, width * 0.45, height * 0.6, 0.002)  # letter field (no glyph)
    m.box("white", 0, mount_h + height / 2, -0.026, width * 0.45, height * 0.6, 0.002)
    m.box("dark_grey", -width * 0.3, mount_h + height + 0.4, 0, 0.03, 0.8, 0.03)
    m.box("dark_grey", width * 0.3, mount_h + height + 0.4, 0, 0.03, 0.8, 0.03)


def b_departure_board(m, width, height, depth, mount_h):
    m.box("blue_sign", 0, mount_h + height / 2, 0, width, height, depth)
    for zf in (depth / 2 + 0.003, -depth / 2 - 0.003):
        m.box("screen", 0, mount_h + height / 2, zf, width - 0.08, height - 0.08, 0.004)
    for x in (-width / 2 + 0.1, width / 2 - 0.1):
        m.box("dark_grey", x, mount_h + height + 0.5, 0, 0.04, 1.0, 0.04)


def b_shelter(m, length, depth, height, roof_overhang, back_glass, side_glass):
    t = 0.08
    for x in (-length / 2 + t, length / 2 - t):
        for z in (-depth / 2 + t,):
            m.box("anthracite", x, height / 2, z, t, height, t)
    m.box("anthracite", 0, height / 2, -depth / 2 + t, 0.06, height, t)
    m.box("anthracite", 0, height + 0.06, 0, length + 2 * roof_overhang, 0.12, depth + 2 * roof_overhang)
    m.box("glass", 0, height + 0.125, 0, length + 2 * roof_overhang - 0.1, 0.01, depth + 2 * roof_overhang - 0.1)
    if back_glass:
        m.box("glass", 0, 0.15 + (height - 0.3) / 2, -depth / 2 + t, length - 2 * t, height - 0.3, 0.012)
    if side_glass:
        for x in (-length / 2 + t, length / 2 - t):
            m.box("glass", x, 0.15 + (height - 0.3) / 2, -depth / 4 + t / 2, 0.012, height - 0.3, depth / 2)
    m.box("wood", 0, 0.46, -depth / 2 + 0.35, length * 0.5, 0.04, 0.35)  # bench inside


def b_island(m, length, width, kerb_h, ramp_len, tactile_offset):
    L = length / 2
    poly = [(-L - ramp_len, -width / 2), (L + ramp_len, -width / 2), (L + ramp_len, width / 2), (-L - ramp_len, width / 2)]
    m.box("concrete", 0, kerb_h / 2, 0, length, kerb_h, width)
    for s in (-1, 1):  # ramps at both ends (sloped top)
        x0, x1 = s * L, s * (L + ramp_len)
        a, b, c, d = (x0, kerb_h, -width / 2), (x1, 0.0, -width / 2), (x1, 0.0, width / 2), (x0, kerb_h, width / 2)
        if s > 0:
            m.quad("concrete", a, d, c, b)
        else:
            m.quad("concrete", a, b, c, d)
        m.tri("concrete", (x0, 0, -width / 2), (x0, kerb_h, -width / 2), (x1, 0, -width / 2))
        m.tri("concrete", (x0, 0, width / 2), (x1, 0, width / 2), (x0, kerb_h, width / 2))
    for zs in (-1, 1):  # tactile guidance lines along both kerbs
        m.box("tactile_white", 0, kerb_h + 0.003, zs * (width / 2 - tactile_offset), length, 0.006, 0.30)


def b_baldachin(m, outline_xz, height, roof_thick, columns):
    # canopy roof slab (glass) with a steel rim; columns along the long axis (approximate positions)
    m.prism("glass", outline_xz, height - roof_thick, height, sides=False)
    n = len(outline_xz)
    for i in range(n):
        (x0, z0), (x1, z1) = outline_xz[i], outline_xz[(i + 1) % n]
        m.quad("steel_grey", (x0, height - roof_thick - 0.4, z0), (x1, height - roof_thick - 0.4, z1), (x1, height, z1), (x0, height, z0))
    for (x, z, r) in columns:
        m.cyl("steel_grey", x, (height - roof_thick) / 2, z, r, height - roof_thick, seg=14)


# ---------------------------------------------------------------------------------------------- evidence
EVID_PHOTOS = "see data/manifest.json records whose features include the tag named here"
asset("sbb-platform-bench", "Platform bench (SBB style, generic)", dict(length=1.8, seat_h=0.45, depth=0.45, back_h=0.40, legs=2),
      [{"kind": "dataset", "ref": "sbb-dataset-mobiliar-im-bahnhof", "what": "'Sitzbank' is listed for Bern (8507000)"},
       {"kind": "photos", "ref": "tag:bench", "what": EVID_PHOTOS},
       {"kind": "standard", "what": "seat height 0.45 m is the usual ergonomic value (SN 640 075 style); not measured"}],
      b_bench, "Slat detail collapsed into slabs.")
asset("sbb-ticket-machine", "Ticket machine (red body, generic)", dict(width=0.62, depth=0.45, height=1.80, screen_w=0.40, screen_h=0.32),
      [{"kind": "dataset", "ref": "sbb-dataset-billetautomat", "what": "positions and type per machine (fetched by stations/)"},
       {"kind": "dataset", "ref": "sbb-dataset-mobiliar-im-bahnhof", "what": "'Billetautomat' listed for Bern"},
       {"kind": "photos", "ref": "tag:ticket_machine", "what": EVID_PHOTOS}],
      b_ticket_machine, "Red body and dark screen echo the common SBB machine; proportions estimated from photos, not measured. No logo.")
asset("sbb-recycling-station", "Recycling station, stainless steel, 4 openings", dict(bins=4, bin_w=0.36, depth=0.42, height=1.00),
      [{"kind": "dataset", "ref": "sbb-dataset-mobiliar-im-bahnhof", "what": "'Recyclingstation Chromstahl' listed for Bern (stainless = Chromstahl)"},
       {"kind": "photo", "ref": "commons:60777612", "what": "Bern station hall seen from above: two recycling stations with 4 round openings each, side panels printed"}],
      b_recycling, "Printed side panels (sorting pictograms) are not modelled; openings shown as slots.")
asset("sbb-info-stele", "Information stele (double-sided)", dict(width=0.55, depth=0.18, height=2.40, panel_h=1.40),
      [{"kind": "dataset", "ref": "sbb-dataset-mobiliar-im-bahnhof", "what": "'Stele' and 'Infopunkt' listed for Bern"},
       {"kind": "photos", "ref": "tag:signage", "what": EVID_PHOTOS}], b_info_stele)
asset("station-clock-generic", "Hanging double-sided station clock (generic, not the SBB design)", dict(diameter=0.80, mount_h=2.80, arm=0.5),
      [{"kind": "dataset", "ref": "sbb-dataset-haltestelle-uhr", "what": "clock positions, mounting type (befestigung), lighting; fetched by stations/"},
       {"kind": "photos", "ref": "tag:clock", "what": EVID_PHOTOS}],
      b_clock, "Deliberately generic dial: the SBB station clock design is protected; do not texture it with the original face.")
asset("platform-sector-sign", "Platform sector sign (letter field blank)", dict(width=0.60, height=0.50, mount_h=2.60),
      [{"kind": "dataset", "ref": "sbb-dataset-sektortafel", "what": "143 sector boards for Bern (BN) with positions (fetched by stations/)"},
       {"kind": "photo", "ref": "commons:179915274", "what": "blue sector signs with white track numbers and sector letter"}], b_sector_sign, "Apply the sector letter (A-E) as a texture or text at load time.")
asset("departure-display-hanging", "Hanging platform departure display", dict(width=2.40, height=0.55, depth=0.15, mount_h=2.70),
      [{"kind": "photo", "ref": "commons:179915274", "what": "Bern Perronhalle: blue hanging platform displays and blue sector signs (12 A 13), clocks on the same hangers"},
       {"kind": "dataset", "ref": "sbb-dataset-mobiliar-im-bahnhof", "what": "'BildschirmMonitor' and 'Videoanlage' listed for Bern"}], b_departure_board)
asset("tram-bus-shelter", "Tram/bus stop shelter (glass, flat roof)", dict(length=4.0, depth=1.6, height=2.5, roof_overhang=0.25, back_glass=True, side_glass=True),
      [{"kind": "dataset", "ref": "sbb-dataset-haltestelle-wartehallen", "what": "shelter inventory (rail stops)"},
       {"kind": "photos", "ref": "tag:shelter", "what": EVID_PHOTOS},
       {"kind": "standard", "ref": "be-hindernisfreie-bushaltestellen-2017", "what": "clear passage behind/around shelters"}], b_shelter,
      "Generic city-stop shelter; Bern uses several shelter generations, check the stop photos before placing.")
asset("tram-island-platform-30m", "Tram/bus island platform, 30 m, with end ramps", dict(length=30.0, width=3.0, kerb_h=0.27, ramp_len=4.0, tactile_offset=0.6),
      [{"kind": "standard", "ref": "bern-normalien-2-5-3", "what": "Stadt Bern standard cross-sections for combined tram/bus stops (kerb height, widths)"},
       {"kind": "standard", "ref": "be-hindernisfreie-bushaltestellen-2017", "what": "barrier-free boarding height for low-floor vehicles"},
       {"kind": "orthophoto", "ref": "ortho-8507110_bern-zytglogge", "what": "island widths visible top-down"}],
      b_island, "Kerb height 0.27 m and width 3.0 m are approximate typical values; length is a parameter (use atlas edge length when available).")

def b_hall_column(m, diameter, height, sleeve_h):
    m.cyl("white", 0, height / 2, 0, diameter / 2, height, seg=24)
    m.cyl("dark_grey", 0, sleeve_h / 2, 0, diameter / 2 + 0.02, sleeve_h, seg=24)


def b_ring_bench(m, r_inner, r_outer, seat_h, planter_h, seg=48):
    # sloped wooden planter cone from r_outer-0.35 (seat inner edge) up to r_inner at planter_h; seat ring at seat_h
    r_seat_in = r_outer - 0.45
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        P = lambda r, a, y: (r * math.cos(a), y, r * math.sin(a))
        m.quad("concrete", P(r_outer, a0, 0), P(r_outer, a0, seat_h), P(r_outer, a1, seat_h), P(r_outer, a1, 0))       # outer wall
        m.quad("concrete", P(r_outer, a0, seat_h), P(r_seat_in, a0, seat_h), P(r_seat_in, a1, seat_h), P(r_outer, a1, seat_h))  # seat
        m.quad("wood", P(r_seat_in, a0, seat_h), P(r_inner, a0, planter_h), P(r_inner, a1, planter_h), P(r_seat_in, a1, seat_h))  # slope
        m.quad("dark_grey", P(r_inner, a0, planter_h), P(0.25, a0, planter_h - 0.05), P(0.25, a1, planter_h - 0.05), P(r_inner, a1, planter_h))  # grille


asset("platform-hall-column", "Platform hall column (round, white, dark base sleeve)", dict(diameter=0.50, height=5.5, sleeve_h=1.6),
      [{"kind": "photo", "ref": "commons:179915274", "what": "Bern Perronhalle: white round columns with a dark lower sleeve along the platforms"},
       {"kind": "link", "ref": "sbb-trafimage-plan-bern-a4-8507000", "what": "platform positions for column rows"}],
      b_hall_column, "Diameter and height estimated from the photo against a 1.8 m person/ticket machine; spacing must come from plans or orthophoto.")
asset("hall-meeting-point-ring-bench", "Station hall meeting point: ring bench with tree planter", dict(r_inner=1.0, r_outer=2.3, seat_h=0.45, planter_h=0.95),
      [{"kind": "photo", "ref": "commons:60777612", "what": "Bern station hall from above: circular bench around a tree, wooden sloped planter, meeting-point sign posts"}],
      b_ring_bench, "Tree and the meeting-point sign posts are not modelled. Radii estimated from people seated on the ring (about 0.5 m per person).")

# Baldachin (Bahnhofplatz canopy, 2008): outline hand-traced from the SWISSIMAGE crop of Bahnhofplatz
ortho = {o["station"]["number"]: o for o in load("orthophotos.json")["items"]}[8576646]
minx, miny, maxx, maxy = ortho["bbox_lv95"]
px, py = ortho["metres_per_pixel"]
# pixel coordinates in the 2200x1800 crop (traced at 1/1.1 scale, then multiplied by 1.1)
traced = [(945, 800), (990, 775), (1060, 768), (1100, 800), (1150, 880), (1200, 960), (1250, 1060), (1290, 1160), (1325, 1260), (1340, 1360),
          (1330, 1440), (1290, 1500), (1220, 1540), (1140, 1545), (1060, 1520), (1000, 1470), (970, 1400), (962, 1250), (955, 1100), (945, 950)]
lv = [(minx + x * 1.1 * px, maxy - y * 1.1 * py) for x, y in traced]
ce = sum(p[0] for p in lv) / len(lv); cn = sum(p[1] for p in lv) / len(lv)
# local frame: +X = east, +Z = south (so that -Z = north); y up
outline = [(round(e - ce, 2), round(-(n - cn), 2)) for e, n in lv]
cols = [(round(e - ce, 2), round(-(n - cn), 2), 0.25) for e, n in
        [(ce - 5, cn + 28), (ce + 2, cn + 12), (ce + 6, cn - 4), (ce + 8, cn - 20)]]
asset("baldachin-bahnhofplatz-approx", "Baldachin Bahnhofplatz Bern (glass canopy), coarse approximation",
      dict(outline_xz=outline, height=9.0, roof_thick=0.6, columns=cols),
      [{"kind": "orthophoto", "ref": ortho["id"], "what": "outline hand-traced from SWISSIMAGE 0.1 m/px, estimated error 1.5 m"},
       {"kind": "photos", "ref": "tag:canopy", "what": "Commons photos of Bahnhofplatz/Baldachin: roof is a curved glass/steel shell; height and column positions are estimates"},
       {"kind": "link", "ref": "bernmobil-kanten-bahnhof-bern-2026", "what": "edges under/along the canopy"}],
      b_baldachin,
      "The real roof is a doubly curved shell; this is a flat slab at an estimated 9 m with 4 estimated columns. "
      "Local frame: +X east, -Z north, origin at outline centroid. LV95 of the origin is in 'anchor_lv95'.")
ASSETS[-1]["anchor_lv95"] = [round(ce, 2), round(cn, 2)]
ASSETS[-1]["footprint_lv95"] = [[round(e, 2), round(n, 2)] for e, n in lv]
json.dump(ASSETS[-1], open(os.path.join(OUT, "baldachin-bahnhofplatz-approx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

save("assets.json", {"generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "count": len(ASSETS),
                     "note": "All assets are approximate, original, CC0. See each sidecar for evidence.", "assets": ASSETS})
