"""Build MapLibre raster-dem tiles (Mapbox Terrain-RGB encoding, lossless WebP)
for Bern from swissALTI3D 2 m GeoTIFFs (EPSG:2056 / LN02 heights).

Usage:
  python -I make_terrain.py <dir with swissalti3d *_2_2056_5728.tif> <out dir> <terrarium cache dir> [dir with *_0.5_2056_5728.tif]

z8-15 cover the whole box from the 2 m tiles; z16-17 cover the central sample box only, from 0.5 m tiles.

Pixels outside the swissALTI3D mosaic are filled from the public AWS Terrarium
tiles (Mapzen/Tilezen, ~30 m) so low-zoom tiles do not drop to 0 m at the edge.

Elevation encoding (Mapbox): h = -10000 + (R*65536 + G*256 + B) * 0.1   [metres]
"""
import glob, io, math, os, sys, urllib.request
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem import Dem

src_dir, out_dir = sys.argv[1], sys.argv[2]
cache_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(out_dir, "..", "_terrarium_cache")
fine_dir = sys.argv[4] if len(sys.argv) > 4 else None   # swissALTI3D 0.5 m tiles for the central sample
os.makedirs(cache_dir, exist_ok=True)

TILE = 256
Z_ALL = range(8, 16)          # whole DEM box, from the 2 m mosaic
Z_CENTRAL = [16, 17]          # central sample only, from the 0.5 m mosaic where present (else 2 m)
# central sample (LV95): Bahnhof - Altstadt - Bärengraben - Bundeshaus - Marzili
CENTRAL = (2599000, 1198500, 2602000, 1201000)

coarse = Dem(src_dir, 2.0)
E0, E1, N0, N1 = coarse.E0, coarse.E1, coarse.N0, coarse.N1
print(f"2 m mosaic {coarse.W}x{coarse.H} px  LV95 E{E0}-{E1} N{N0}-{N1}")
fine = Dem(fine_dir, 0.5) if fine_dir else None
if fine:
    print(f"0.5 m mosaic {fine.W}x{fine.H} px  LV95 E{fine.E0}-{fine.E1} N{fine.N0}-{fine.N1}")

to_lv95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
to_wgs = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)

def lv95_bbox_to_wgs(b):
    xs = [b[0], b[2], b[0], b[2]]; ys = [b[1], b[1], b[3], b[3]]
    lo, la = to_wgs.transform(xs, ys)
    return min(lo), min(la), max(lo), max(la)

def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def tile_range(bb, z):
    x0, y0 = lonlat_to_tile(bb[0], bb[3], z)
    x1, y1 = lonlat_to_tile(bb[2], bb[1], z)
    return range(int(x0), int(x1) + 1), range(int(y0), int(y1) + 1)

def pixel_lonlat(z, x, y):
    n = 2 ** z
    px = (np.arange(TILE) + 0.5) / TILE
    gx, gy = np.meshgrid(x + px, y + px)
    lon = gx / n * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * gy / n))))
    return lon, lat

def sample_dem(lon, lat, z):
    e, n = to_lv95.transform(lon, lat)
    v = coarse.sample(e, n)
    if fine is not None and z >= 16:
        f = fine.sample(e, n)
        v = np.where(np.isfinite(f), f, v)
    return v.astype(np.float64)


def terrarium(z, x, y):
    zz = min(z, 15)
    f = 2 ** (z - zz)
    tx, ty = x // f, y // f
    p = os.path.join(cache_dir, f"{zz}_{tx}_{ty}.png")
    if not os.path.exists(p):
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zz}/{tx}/{ty}.png"
        with urllib.request.urlopen(url) as r, open(p, "wb") as o:
            o.write(r.read())
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    if f > 1:  # crop + nearest upsample
        s = TILE // f
        ox, oy = (x % f) * s, (y % f) * s
        h = h[oy:oy + s, ox:ox + s].repeat(f, 0).repeat(f, 1)
    return h

def encode(h):
    v = np.clip(np.round((h + 10000) * 10), 0, 2 ** 24 - 1).astype(np.uint32)
    rgb = np.stack([(v >> 16) & 255, (v >> 8) & 255, v & 255], -1).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")

def write(z, x, y, central=False):
    lon, lat = pixel_lonlat(z, x, y)
    h = sample_dem(lon, lat, z)
    miss = np.isnan(h)
    if miss.all() and central:
        return 0
    if miss.any():
        h[miss] = terrarium(z, x, y)[miss]
    d = os.path.join(out_dir, str(z), str(x)); os.makedirs(d, exist_ok=True)
    encode(h).save(os.path.join(d, f"{y}.webp"), "WEBP", lossless=True, quality=100, method=4)
    return 1

full_bb = lv95_bbox_to_wgs((E0, N0, E1, N1))
cen_bb = lv95_bbox_to_wgs(CENTRAL)
count = 0
for z in Z_ALL:
    xr, yr = tile_range(full_bb, z)
    for x in xr:
        for y in yr:
            count += write(z, x, y)
    print("z", z, "tiles so far", count)
for z in Z_CENTRAL:
    xr, yr = tile_range(cen_bb, z)
    for x in xr:
        for y in yr:
            count += write(z, x, y, central=True)
    print("z", z, "tiles so far", count)
print("WGS84 bounds full", [round(v, 5) for v in full_bb], "central", [round(v, 5) for v in cen_bb])
