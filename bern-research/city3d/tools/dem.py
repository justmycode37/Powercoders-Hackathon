"""swissALTI3D mosaic helper (2 m or 0.5 m): bilinear terrain height (LN02 m) at LV95 points."""
import glob, os
import numpy as np
import rasterio

class Dem:
    def __init__(self, src_dir, res=2.0):
        self.res = RES = float(res)
        tag = "0.5" if RES == 0.5 else "2"
        files = sorted(glob.glob(os.path.join(src_dir, f"*_{tag}_2056_5728.tif")))
        keys = [tuple(int(v) for v in os.path.basename(f).split("_")[2].split("-")) for f in files]
        self.E0 = min(k[0] for k in keys) * 1000
        self.E1 = (max(k[0] for k in keys) + 1) * 1000
        self.N0 = min(k[1] for k in keys) * 1000
        self.N1 = (max(k[1] for k in keys) + 1) * 1000
        self.W = int((self.E1 - self.E0) / RES)
        self.files = [os.path.basename(f) for f in files]
        self.H = int((self.N1 - self.N0) / RES)
        self.a = np.full((self.H, self.W), np.nan, dtype=np.float32)
        self.years = {}
        for f, k in zip(files, keys):
            self.years[f"{k[0]}-{k[1]}"] = int(os.path.basename(f).split("_")[1])
            with rasterio.open(f) as r:
                d = r.read(1).astype(np.float32)
                d[d == r.nodata] = np.nan
                x0 = int((r.bounds.left - self.E0) / RES)
                y0 = int((self.N1 - r.bounds.top) / RES)
                self.a[y0:y0 + d.shape[0], x0:x0 + d.shape[1]] = d

    def sample(self, e, n):
        RES = self.res
        e = np.asarray(e, dtype=np.float64); n = np.asarray(n, dtype=np.float64)
        fx = (e - self.E0) / RES - 0.5
        fy = (self.N1 - n) / RES - 0.5
        x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int)
        tx = fx - x0; ty = fy - y0
        ok = (x0 >= 0) & (y0 >= 0) & (x0 < self.W - 1) & (y0 < self.H - 1)
        x0 = np.clip(x0, 0, self.W - 2); y0 = np.clip(y0, 0, self.H - 2)
        a = self.a
        v = ((a[y0, x0] * (1 - tx) + a[y0, x0 + 1] * tx) * (1 - ty)
             + (a[y0 + 1, x0] * (1 - tx) + a[y0 + 1, x0 + 1] * tx) * ty)
        return np.where(ok, v, np.nan)

    def year_at(self, e, n):
        return self.years.get(f"{int(e // 1000)}-{int(n // 1000)}")
