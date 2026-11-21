"""Shared constants and helpers for the Bern transit feed pipeline (stdlib only)."""
from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # bern-research/transit
CACHE = ROOT / ".cache"                                # raw official downloads (git-ignored)
DATA = ROOT / "data"                                   # compact integration-ready outputs
VALIDATION = ROOT / "validation"

USER_AGENT = "bern-transit-research/1.0"
TIMEZONE = "Europe/Zurich"

BERN_FSO = "351"                                       # BFS/FSO municipality number of Bern
BERN_NAME = "Bern"
RING_KM = 5.0                                          # "adjacent" = within this distance of the municipal boundary

OTD = "https://data.opentransportdata.swiss"
LICENCE_OTD = ("Terms of use of the Open data platform mobility Switzerland "
               "(https://opentransportdata.swiss/en/terms-of-use/): open data, free to obtain, use and publish, "
               "raw or processed; the URL opentransportdata.swiss must be cited as the source")
LICENCE_SWISSTOPO = ("Terms of use for free geodata and geoservices of swisstopo "
                     "(https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices): may be used, "
                     "distributed, processed and used commercially; source reference mandatory "
                     "(Federal Office of Topography swisstopo, or: (c) swisstopo)")
SKI = "Business office SKI (on behalf of the Swiss Federal Office of Transport)"
ATLAS = "atlas (SKI Business Platform)"


def _otd(title, slug, path, used_for, publisher=ATLAS, file=None):
    url = f"{OTD}/dataset/{path}"
    return {"title": title, "landing": f"{OTD}/en/dataset/{slug}", "url": url, "file": file or path.rsplit("/", 1)[-1],
            "publisher": publisher, "licence": LICENCE_OTD, "used_for": used_for}


SOURCES = {
    "gtfs_fp2026": _otd("Timetable 2026 (GTFS2020), valid 2025-12-14 to 2026-12-12", "timetable-2026-gtfs2020",
                        "timetable-2026-gtfs2020/permalink", "routes, trips, stop_times, calendars, transfers of the current timetable year",
                        SKI, "gtfs.zip"),
    "gtfs_fp2027": _otd("Timetable 2027 (GTFS2020), valid 2026-12-13 to 2027-12-11", "timetable-2027-gtfs2020",
                        "timetable-2027-gtfs2020/permalink", "the same for the timetable year that starts on 2026-12-13",
                        SKI, "gtfs.zip"),
    "atlas_traffic_point": _otd(
        "atlas traffic-point-v2 (boarding edges and boarding areas), valid on the retrieval date", "traffic-point-v2",
        "b06d90be-91c6-440e-ab97-09f579d2fad0/resource/c2cda870-8f8e-4463-984b-7351d7107228/download/actual-date-world-traffic-point.csv",
        "boarding edges: SLOID, designation, coordinates, height, compass direction"),
    "atlas_service_point": _otd(
        "atlas service-point-v2 (DiDok service points), valid on the retrieval date", "service-point-v2",
        "39e5f264-257a-4f3f-bccc-5322c37058c5/resource/a5ea1c50-15fd-41d2-8ddc-511ac8ca26a3/download/actual-date-swiss-service-point.csv",
        "stations: SLOID, number, name, municipality (coverage rule), coordinates, means of transport"),
    "atlas_traffic_point_years": _otd(
        "atlas traffic-point-v2, all versions valid in the current and next timetable year", "traffic-point-v2",
        "b06d90be-91c6-440e-ab97-09f579d2fad0/resource/7aed7977-522a-431e-b39b-be0dcf12307b/download/timetable-years-world-traffic-point.csv",
        "edges that are not valid on the retrieval date (temporary, expired, opening at the timetable change)"),
    "atlas_service_point_years": _otd(
        "atlas service-point-v2, all versions valid in the current and next timetable year", "service-point-v2",
        "39e5f264-257a-4f3f-bccc-5322c37058c5/resource/5887a585-8827-455a-a4e0-69df749c6854/download/timetable-years-swiss-service-point.csv",
        "stations that are not valid on the retrieval date (temporary, expired, opening at the timetable change)"),
    "atlas_prm_platform": _otd(
        "atlas platform-v2 (accessibility of boarding edges), valid on the retrieval date", "platform-v2",
        "8e5931a6-b4aa-456a-9be4-498f28168861/resource/19c170d0-b0a1-4837-8bbd-9c2704dc9131/download/actual-date-platform.csv",
        "accessibility attributes per boarding edge"),
    "atlas_prm_stop_point": _otd(
        "atlas stop-point-v2 (accessibility at stop level), valid on the retrieval date", "stop-point-v2",
        "e73d185a-e445-450f-9800-f485c7721a37/resource/7df2dfcd-2c9d-47cf-a00a-f9bcabee6d15/download/actual-date-stop-point.csv",
        "accessibility attributes per station"),
    "atlas_sectors": _otd(
        "atlas sectors-and-sector-groups-v2, valid on the retrieval date", "sectors-and-sector-groups-v2",
        "52c157d0-e6bc-406b-8e7d-63713aa28585/resource/be07f0bd-96c5-44d3-9896-cd46b32857c6/download/actual-date-sectors-and-sector-groups.csv",
        "platform sectors (A, B, C ...) per boarding edge"),
    "atlas_prm_reference_point": _otd(
        "atlas reference-point-v2, valid on the retrieval date", "reference-point-v2",
        "11e86379-d543-40cc-9d58-11fc805946c1/resource/e080fe3a-10d8-451a-b9ba-6a86f40544da/download/actual-date-reference-point.csv",
        "reference points of stations (main entrances, assistance points)"),
    "atlas_prm_toilet": _otd(
        "atlas toilet-v2, valid on the retrieval date", "toilet-v2",
        "bc740b09-42ba-425b-9986-490d8938135c/resource/0c9e45fc-a3cd-432a-a1fc-41b48fde2cba/download/actual-date-toilet.csv",
        "toilets at stations and their wheelchair accessibility"),
    "atlas_prm_parking_lot": _otd(
        "atlas parking-lot-v2, valid on the retrieval date", "parking-lot-v2",
        "917db6c8-e240-4846-855f-fcc02856600e/resource/c1cc05a6-9d81-469d-96ed-0f499bd8f146/download/actual-date-parking-lot.csv",
        "parking at stations for people with reduced mobility"),
    "atlas_prm_contact_point": _otd(
        "atlas contact-point-v2, valid on the retrieval date", "contact-point-v2",
        "4deb3709-fda7-42b1-ba0a-b8d303330382/resource/59ed0554-2343-4652-80a8-76e3a8f0bab8/download/actual-date-contact-point.csv",
        "ticket counters and information desks and their accessibility"),
    "atlas_prm_relation": _otd(
        "atlas relation-v2, valid on the retrieval date", "relation-v2",
        "fbc9efa2-eeb1-4d17-b94d-8b49e699149d/resource/6d6bc670-3df4-4485-b869-75779c8927d3/download/actual-date-relation.csv",
        "step-free and tactile connections between reference points and edges, toilets, parking, contact points"),
    "bfr_wheelchair": _otd(
        "Accessible travel - wheelchair accessibility per stop place and boarding area (BfR_Haltestellendaten)", "bfr-rollstuhl",
        "8456c028-4d73-4f2e-8127-9ce8ec889c9d/resource/fbe94403-85da-4ecd-b1ef-ff79f6c9a8d3/download/bfr_haltestellendaten.csv",
        "wheelchair boarding classification per boarding edge", SKI),
    "boundary_bern": {
        "title": "swissBOUNDARIES3D municipality polygon of Bern (BFS 351), generalised web geometry",
        "landing": "https://www.swisstopo.admin.ch/en/landscape-model-swissboundaries3d",
        "url": "https://api3.geo.admin.ch/rest/services/api/MapServer/"
               "ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill/351?geometryFormat=geojson&sr=4326",
        "file": "bern_351.geojson",
        "publisher": "Federal Office of Topography swisstopo",
        "licence": LICENCE_SWISSTOPO,
        "used_for": "cross-check of the atlas municipality attribute and the 5 km ring",
    },
}

FEEDS = {"fp2026": "gtfs_fp2026", "fp2027": "gtfs_fp2027"}


def gtfs_zip(feed: str) -> zipfile.ZipFile:
    return zipfile.ZipFile(CACHE / FEEDS[feed] / "gtfs.zip")


def read_table(zf: zipfile.ZipFile, name: str):
    """Yield dict rows of a GTFS table (UTF-8 with BOM, quoted CSV)."""
    with zf.open(name) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig", newline=""))


def read_atlas(source: str):
    path = CACHE / source / SOURCES[source]["file"]
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh, delimiter=";")


def hms_to_sec(t: str) -> int:
    """GTFS time 'HH:MM:SS' -> seconds after service-day midnight. HH may be >= 24."""
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def sec_to_hms(sec: int) -> str:
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def haversine_m(lon1, lat1, lon2, lat2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lon1, lat1, lon2, lat2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


class Boundary:
    """Municipal polygon with point-in-polygon and distance-to-boundary (metres, local equirectangular)."""

    def __init__(self, geojson_path: Path):
        gj = json.loads(geojson_path.read_text(encoding="utf-8"))
        geom = gj["feature"]["geometry"] if "feature" in gj else gj.get("geometry") or gj["features"][0]["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        self.polys = polys
        lats = [pt[1] for poly in polys for ring in poly for pt in ring]
        lons = [pt[0] for poly in polys for ring in poly for pt in ring]
        self.bbox = (min(lons), min(lats), max(lons), max(lats))
        self.lat0 = sum(lats) / len(lats)
        self.kx = 111320.0 * math.cos(math.radians(self.lat0))
        self.ky = 110540.0
        self.segs = []
        for poly in polys:
            for ring in poly:
                pts = [((p[0]) * self.kx, p[1] * self.ky) for p in ring]
                self.segs.extend(zip(pts, pts[1:]))

    @staticmethod
    def _in_ring(x, y, ring) -> bool:
        inside = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside

    def contains(self, lon: float, lat: float) -> bool:
        for poly in self.polys:
            if self._in_ring(lon, lat, poly[0]) and not any(self._in_ring(lon, lat, h) for h in poly[1:]):
                return True
        return False

    def distance_m(self, lon: float, lat: float) -> float:
        """Distance to the boundary line (0 is on the line); combine with contains() for signed use."""
        px, py = lon * self.kx, lat * self.ky
        best = float("inf")
        for (ax, ay), (bx, by) in self.segs:
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
            d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d < best:
                best = d
        return math.sqrt(best)
