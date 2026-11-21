"""Small pure-Python geometry helpers (no third-party dependencies).

Planar work is done in LV95 (EPSG:2056, metres).  The LV95 <-> WGS84 functions
implement the rigorous swisstopo formulas (oblique Mercator on Bessel 1841 plus
the 3-parameter CH1903+ -> ETRS89/WGS84 shift), accurate to a few millimetres.
"""
from __future__ import annotations

import math

# --- Swiss projection constants (Bessel 1841, fundamental point Bern) --------
_A = 6377397.155
_E2 = 0.006674372230614
_E = math.sqrt(_E2)
_PHI0 = math.radians(46 + 57 / 60 + 8.66 / 3600)
_LAM0 = math.radians(7 + 26 / 60 + 22.50 / 3600)
_R = _A * math.sqrt(1 - _E2) / (1 - _E2 * math.sin(_PHI0) ** 2)
_ALPHA = math.sqrt(1 + _E2 / (1 - _E2) * math.cos(_PHI0) ** 4)
_B0 = math.asin(math.sin(_PHI0) / _ALPHA)
_K = (math.log(math.tan(math.pi / 4 + _B0 / 2))
      - _ALPHA * math.log(math.tan(math.pi / 4 + _PHI0 / 2))
      + _ALPHA * _E / 2 * math.log((1 + _E * math.sin(_PHI0)) / (1 - _E * math.sin(_PHI0))))
# GRS80 / WGS84
_A_W = 6378137.0
_E2_W = 0.00669438002290
_DX, _DY, _DZ = 674.374, 15.056, 405.346


def _geo_to_xyz(phi, lam, h, a, e2):
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    return ((n + h) * math.cos(phi) * math.cos(lam),
            (n + h) * math.cos(phi) * math.sin(lam),
            (n * (1 - e2) + h) * math.sin(phi))


def _xyz_to_geo(x, y, z, a, e2):
    lam = math.atan2(y, x)
    p = math.hypot(x, y)
    phi = math.atan2(z, p * (1 - e2))
    h = 0.0
    for _ in range(8):
        n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
        h = p / math.cos(phi) - n
        phi = math.atan2(z, p * (1 - e2 * n / (n + h)))
    return phi, lam, h


def lv95_to_wgs84(e: float, n: float, h: float = 550.0) -> tuple[float, float]:
    """LV95 east/north (m) -> (lon, lat) in degrees.  h only matters at mm level."""
    y, x = e - 2600000.0, n - 1200000.0
    l_ = y / _R
    b_ = 2 * (math.atan(math.exp(x / _R)) - math.pi / 4)
    b = math.asin(math.cos(_B0) * math.sin(b_) + math.sin(_B0) * math.cos(b_) * math.cos(l_))
    l = math.atan2(math.sin(l_), math.cos(_B0) * math.cos(l_) - math.sin(_B0) * math.tan(b_))
    lam = _LAM0 + l / _ALPHA
    phi = b
    for _ in range(8):
        s = ((math.log(math.tan(math.pi / 4 + b / 2)) - _K) / _ALPHA
             + _E * math.log(math.tan(math.pi / 4 + math.asin(_E * math.sin(phi)) / 2)))
        phi = 2 * math.atan(math.exp(s)) - math.pi / 2
    X, Y, Z = _geo_to_xyz(phi, lam, h, _A, _E2)
    phi_w, lam_w, _ = _xyz_to_geo(X + _DX, Y + _DY, Z + _DZ, _A_W, _E2_W)
    return math.degrees(lam_w), math.degrees(phi_w)


def wgs84_to_lv95(lon: float, lat: float, h: float = 600.0) -> tuple[float, float]:
    """(lon, lat) degrees -> LV95 east/north (m)."""
    X, Y, Z = _geo_to_xyz(math.radians(lat), math.radians(lon), h, _A_W, _E2_W)
    phi, lam, _ = _xyz_to_geo(X - _DX, Y - _DY, Z - _DZ, _A, _E2)
    s = (_ALPHA * math.log(math.tan(math.pi / 4 + phi / 2))
         - _ALPHA * _E / 2 * math.log((1 + _E * math.sin(phi)) / (1 - _E * math.sin(phi))) + _K)
    b = 2 * (math.atan(math.exp(s)) - math.pi / 4)
    l = _ALPHA * (lam - _LAM0)
    l_ = math.atan2(math.sin(l), math.sin(_B0) * math.tan(b) + math.cos(_B0) * math.cos(l))
    b_ = math.asin(math.cos(_B0) * math.sin(b) - math.sin(_B0) * math.cos(b) * math.cos(l))
    y = _R * l_
    x = _R / 2 * math.log((1 + math.sin(b_)) / (1 - math.sin(b_)))
    return y + 2600000.0, x + 1200000.0


# --- planar helpers ----------------------------------------------------------
def dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def seg_project(p, a, b):
    """Closest point on segment ab to p -> (point, t in [0,1], distance)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
    q = (a[0] + t * dx, a[1] + t * dy)
    return q, t, dist(p, q)


def line_project(p, line):
    """Closest point on a polyline -> (distance, chainage along line, point, segment index)."""
    best = (float("inf"), 0.0, line[0], 0)
    run = 0.0
    for i in range(len(line) - 1):
        q, t, d = seg_project(p, line[i], line[i + 1])
        seg = dist(line[i], line[i + 1])
        if d < best[0]:
            best = (d, run + t * seg, q, i)
        run += seg
    return best


def line_length(line) -> float:
    return sum(dist(line[i], line[i + 1]) for i in range(len(line) - 1))


def line_interpolate(line, s: float):
    """Point at chainage s along a polyline (clamped)."""
    if s <= 0:
        return line[0]
    run = 0.0
    for i in range(len(line) - 1):
        seg = dist(line[i], line[i + 1])
        if run + seg >= s and seg > 0:
            t = (s - run) / seg
            return (line[i][0] + t * (line[i + 1][0] - line[i][0]),
                    line[i][1] + t * (line[i + 1][1] - line[i][1]))
        run += seg
    return line[-1]


def line_substring(line, s0: float, s1: float):
    """Part of a polyline between two chainages."""
    s0, s1 = max(0.0, min(s0, s1)), min(line_length(line), max(s0, s1))
    out = [line_interpolate(line, s0)]
    run = 0.0
    for i in range(len(line) - 1):
        run += dist(line[i], line[i + 1])
        if s0 < run < s1:
            out.append(line[i + 1])
    out.append(line_interpolate(line, s1))
    return out


def bearing(a, b) -> float:
    """Grid bearing in degrees clockwise from north, a -> b."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360


def line_bearing_at(line, s: float) -> float:
    a = line_interpolate(line, max(0.0, s - 2.0))
    b = line_interpolate(line, min(line_length(line), s + 2.0))
    return bearing(a, b) if a != b else 0.0


def angle_diff(a: float, b: float, axial: bool = False) -> float:
    """Smallest difference between two bearings (axial: ignore direction)."""
    d = abs((a - b + 180) % 360 - 180)
    return min(d, 180 - d) if axial else d


def offset_point(p, brg: float, d: float):
    r = math.radians(brg)
    return (p[0] + d * math.sin(r), p[1] + d * math.cos(r))


def ring_area(ring) -> float:
    """Signed area (positive = counter-clockwise)."""
    s = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        s += x0 * y1 - x1 * y0
    return s / 2


def ring_centroid(ring):
    a = ring_area(ring)
    if abs(a) < 1e-9:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    cx = cy = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        f = x0 * y1 - x1 * y0
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    return (cx / (6 * a), cy / (6 * a))


def point_in_ring(p, ring) -> bool:
    x, y = p
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def ring_distance(p, ring) -> float:
    """0 inside, else distance to the boundary."""
    if point_in_ring(p, ring):
        return 0.0
    return line_project(p, list(ring) + [ring[0]])[0]


def convex_hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def min_rect(pts):
    """Minimum-area bounding rectangle -> dict(centre, length, width, bearing, corners).

    bearing is the grid bearing of the long axis (0..180)."""
    hull = convex_hull(pts)
    if len(hull) < 2:
        p = hull[0]
        return dict(centre=p, length=0.0, width=0.0, bearing=0.0, corners=[p] * 4)
    best = None
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        d = dist(a, b)
        if d == 0:
            continue
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        us = [(p[0] - a[0]) * ux + (p[1] - a[1]) * uy for p in hull]
        vs = [-(p[0] - a[0]) * uy + (p[1] - a[1]) * ux for p in hull]
        w, h = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * h < best[0]:
            best = (w * h, a, ux, uy, min(us), max(us), min(vs), max(vs))
    _, a, ux, uy, u0, u1, v0, v1 = best

    def pt(u, v):
        return (a[0] + u * ux - v * uy, a[1] + u * uy + v * ux)

    corners = [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)]
    length, width = u1 - u0, v1 - v0
    brg = bearing((0, 0), (ux, uy))
    if width > length:
        length, width = width, length
        brg = (brg + 90) % 360
    return dict(centre=pt((u0 + u1) / 2, (v0 + v1) / 2), length=length, width=width,
                bearing=brg % 180, corners=corners)


def ribbon(line, width: float):
    """Buffer a polyline to a flat-capped polygon ring (simple mitre-less offset)."""
    if len(line) < 2:
        return []
    left, right = [], []
    for i, p in enumerate(line):
        a = line[max(0, i - 1)]
        b = line[min(len(line) - 1, i + 1)]
        d = dist(a, b) or 1.0
        nx, ny = -(b[1] - a[1]) / d, (b[0] - a[0]) / d
        left.append((p[0] + nx * width / 2, p[1] + ny * width / 2))
        right.append((p[0] - nx * width / 2, p[1] - ny * width / 2))
    return left + right[::-1]


def rect(centre, brg: float, length: float, width: float):
    a = offset_point(centre, brg, -length / 2)
    b = offset_point(centre, brg, length / 2)
    return ribbon([a, b], width)


def simplify(line, tol: float):
    """Douglas-Peucker."""
    if len(line) < 3:
        return list(line)
    keep = [False] * len(line)
    keep[0] = keep[-1] = True
    stack = [(0, len(line) - 1)]
    while stack:
        i, j = stack.pop()
        dmax, k = 0.0, None
        for m in range(i + 1, j):
            d = seg_project(line[m], line[i], line[j])[2]
            if d > dmax:
                dmax, k = d, m
        if k is not None and dmax > tol:
            keep[k] = True
            stack += [(i, k), (k, j)]
    return [p for p, f in zip(line, keep) if f]


def triangulate(ring):
    """Ear clipping for a simple polygon ring -> list of index triples (CCW)."""
    n = len(ring)
    if n < 3:
        return []
    idx = list(range(n))
    if ring_area(ring) < 0:
        idx.reverse()
    tris = []

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    guard = 0
    while len(idx) > 3 and guard < 10 * n * n:
        guard += 1
        m = len(idx)
        ear = False
        for i in range(m):
            ia, ib, ic = idx[i - 1], idx[i], idx[(i + 1) % m]
            a, b, c = ring[ia], ring[ib], ring[ic]
            if cross(a, b, c) <= 1e-12:
                continue
            ok = True
            for j in idx:
                if j in (ia, ib, ic):
                    continue
                p = ring[j]
                if cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0:
                    ok = False
                    break
            if ok:
                tris.append((ia, ib, ic))
                idx.pop(i)
                ear = True
                break
        if not ear:           # degenerate input: drop a vertex and carry on
            idx.pop(0)
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris
