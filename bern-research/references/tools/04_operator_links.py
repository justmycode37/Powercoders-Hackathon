"""Register of authoritative operator plans, planning documents and open datasets that inform station 3D
models but are NOT copied into the tree (link only, unless the licence is open and noted).
Every URL is checked live (HEAD, falling back to a ranged GET) and the result is stored.
SBB Trafimage station plans are read from the SBB data portal dataset `haltestelle-karte-trafimage`.
Writes data/operator_links.json.  Usage: python -I -X utf8 tools/04_operator_links.py
"""
import sys, os, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import http, save, UA

LINK_ONLY = "All rights reserved by the publisher (no open licence stated). Link only; do not redistribute."
SBB_TERMS = "SBB Open Data terms (https://data.sbb.ch/page/licence); open use with source attribution 'SBB'"
OTD_TERMS = "opentransportdata.swiss terms of use (https://opentransportdata.swiss/en/terms-of-use/), attribution"
SWISSTOPO = "swisstopo free geodata (OGD), attribution '© swisstopo' (https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-ogd)"

L = []


def add(id, title, url, publisher, kind, licence, stations, use_for_3d, **kw):
    L.append(dict(id=id, title=title, url=url, publisher=publisher, kind=kind, licence=licence,
                  redistribute=kw.pop("redistribute", False), stations=stations, use_for_3d=use_for_3d, **kw))


# --- SBB Trafimage station plans (authoritative passenger plans per station) ---------------------------
tra = http("https://data.sbb.ch/api/explore/v2.1/catalog/datasets/haltestelle-karte-trafimage/records?" +
           urllib.parse.urlencode({"where": 'bezeichnung_offiziell like "Bern"', "limit": "20"}), minint=0.5)
for r in tra["results"]:
    n = int(r["bpuic"])
    st = [{"number": n, "sloid": r.get("sloid")}]
    slug = r["url_format_a4"].rsplit("/", 1)[-1].replace(".pdf", "")
    add(f"sbb-trafimage-{slug}-{n}", f"SBB Bahnhofplan {r['bezeichnung_offiziell']} (A4)", r["url_format_a4"], "SBB (Trafimage)",
        "station_plan_pdf", LINK_ONLY + " Listed in the SBB open data portal index, but the plan PDF itself carries no open licence.", st,
        "Authoritative 2D layout: platform/track numbering, sectors, underpasses (Christoffel, Welle, Passage), entrances, stairs, lifts, "
        "ramps, bus/tram stops around the station. Trace footprints and vertical connections; check against atlas edge SLOIDs.")
    if r.get("url_oev_plakat"):
        add(f"sbb-trafimage-{slug}-poster-{n}", f"SBB Bahnhofplan {r['bezeichnung_offiziell']} (poster A1/A0)", r["url_oev_plakat"], "SBB (Trafimage)",
            "station_plan_pdf", LINK_ONLY, st, "Higher-detail poster version of the same plan: better for tracing small features (stairs, lifts).")
    if r.get("url_shopping_im_bahnhof_plakat"):
        add(f"sbb-trafimage-{slug}-shopping-{n}", f"SBB 'Shopping im Bahnhof' {r['bezeichnung_offiziell']}", r["url_shopping_im_bahnhof_plakat"], "SBB (Trafimage)",
            "station_plan_pdf", LINK_ONLY, st, "Shop/service unit layout of the concourse levels: subdivide the underground passages into frontage units.")
    if r.get("url_iabp_allgemein"):
        add(f"sbb-trafimage-{slug}-interactive-{n}", f"SBB interactive station plan {r['bezeichnung_offiziell']}", r["url_iabp_allgemein"], "SBB (Trafimage)",
            "interactive_plan", LINK_ONLY, st, "Interactive multi-level plan (levels switchable): use to understand which level each passage/stair belongs to.")
    if n == 8507000:
        BERN_A4 = r["url_format_a4"]

# --- BERNMOBIL kerb plans and network/zone plans -------------------------------------------------------
BM = "https://www.bernmobil.ch"
add("bernmobil-kanten-bahnhof-bern-2026", "BERNMOBIL Kantenplan Bern Bahnhof 2026", BM + "/sites/default/files/2026-07/Kanten_Bahnhof_Bern_2026.pdf",
    "BERNMOBIL", "kerb_plan_pdf", LINK_ONLY, [{"number": 8576646, "sloid": "ch:1:sloid:76646"}],
    "Letters of every tram/bus boarding edge around Bahnhofplatz/Bubenbergplatz/Hirschengraben with lines per edge: "
    "assign edge SLOIDs (atlas designation) to the canopy (Baldachin) and island platforms.")
add("bernmobil-kanten-zytglogge-k-2026", "BERNMOBIL Kantenplan Zytglogge (Kante K) 2026", BM + "/sites/default/files/2025-12/Kanten_Zytglogge_Kante%2520K_2026.pdf",
    "BERNMOBIL", "kerb_plan_pdf", LINK_ONLY, [{"number": 8507110, "sloid": "ch:1:sloid:7110"}],
    "Edge K (atlas ch:1:sloid:7110:0:17) position and served lines at Zytglogge/Kornhausplatz.")
add("bernmobil-kanten-wankdorf-2025", "BERNMOBIL Kantenplan Bahnhof Wankdorf 2025", BM + "/sites/default/files/2024-11/4_24317_BM_Kanten_Bahnhof_Wankdorf_A4_2025_DE.pdf",
    "BERNMOBIL", "kerb_plan_pdf", LINK_ONLY, [{"number": 8590129, "sloid": "ch:1:sloid:90129"}, {"number": 8516161, "sloid": "ch:1:sloid:16161"}],
    "Bus/tram edges at Bern Wankdorf, Bahnhof and their relation to the SBB station accesses.")
add("bernmobil-kantenplaene-index", "BERNMOBIL Kantenpläne (index page)", BM + "/de/fahrplan-netz/kantenplaene", "BERNMOBIL", "index_page", LINK_ONLY, [],
    "Landing page listing all current kerb plans (check here for newer editions).")
add("libero-netzplan-bern-2026", "Libero Netzplan Bern 2026", BM + "/sites/default/files/2025-11/Libero%20Netzplan%20Bern%202026.pdf", "Libero / BERNMOBIL",
    "network_map_pdf", LINK_ONLY, [], "Schematic network: line colours/numbers for signage textures (do not copy graphics; re-derive from GTFS route colours).")

# --- City of Bern standards and planning documents (dimensions and future state) -----------------------
BE = "https://www.bern.ch"
add("bern-normalien-2-5-3", "Stadt Bern Normalien 2.5.3: Tram-/Bus-Kombihaltestellen, Verkehrsinseln",
    BE + "/themen/planen-und-bauen/bern-baut/planen-und-projektieren/c-normalien/2-strassenbau/2-5-tram-bus-kombihaltestellen-verkehrsinseln-1/2-5-3.pdf/download",
    "Stadt Bern, Tiefbauamt", "design_standard_pdf", LINK_ONLY, [],
    "Standard cross-sections of combined tram/bus stops: kerb heights, platform widths, ramps. Use as the parameter source for generic stop platforms.")
add("bern-normalien-2-5-2-2-2", "Stadt Bern Normalien 2.5.2.2.2 (Haltestellen-Detail)",
    BE + "/themen/planen-und-bauen/bern-baut/planen-und-projektieren/c-normalien/2-strassenbau/2-5-tram-bus-kombihaltestellen-verkehrsinseln-1/2-5-2-2-2.pdf/download",
    "Stadt Bern, Tiefbauamt", "design_standard_pdf", LINK_ONLY, [], "Detail sheet for stop kerbs and island ends.")
add("bern-normalien-2-5-3-1-1", "Stadt Bern Normalien 2.5.3.1.1 (Haltestellen-Detail)",
    BE + "/themen/planen-und-bauen/bern-baut/Planungsgrundsaetze-Standards-Normalien/c-normalien/2-strassenbau/2-5-tram-bus-kombihaltestellen-verkehrsinseln-1/2-5-3-1-1.pdf/view",
    "Stadt Bern, Tiefbauamt", "design_standard_pdf", LINK_ONLY, [], "Detail sheet for combined stops.")
add("be-hindernisfreie-bushaltestellen-2017", "Kanton Bern AÖV: Arbeitshilfe hindernisfreie Bushaltestellen (2017)",
    "https://www.bvd.be.ch/content/dam/bvd/dokumente/de/aoev/mobilit%C3%A4t/%C3%B6ffentlicher-verkehr/aoev_Arbeitshilfe_Hindernisfreie%20Bushaltestellen_Juli%202017_definitiv_d.pdf",
    "Kanton Bern, Amt für öffentlichen Verkehr", "design_standard_pdf", LINK_ONLY, [],
    "Kerb heights (22 cm / Kasseler kerb), tactile lines, shelter clearances: parameters for bus-stop assets.")
add("be-grundlagen-hindernisfreie-bushaltestellen", "Kanton Bern AÖV: Grundlagenbericht hindernisfreie Bushaltestellen",
    "https://www.bvd.be.ch/content/dam/bvd/dokumente/de/aoev/mobilit%C3%A4t/%C3%B6ffentlicher-verkehr/aoev_Grundlagenbericht_Hindernisfreie_Bushaltestellen.pdf",
    "Kanton Bern, Amt für öffentlichen Verkehr", "design_standard_pdf", LINK_ONLY, [], "Background report for the same standard.")
add("bern-testplanung-stadtraum-bahnhof-uebersicht", "Stadt Bern: Übersichtsplan Testplanung Stadtraum Bahnhof Bern",
    BE + "/mediencenter/medienmitteilungen/aktuell_ptk/testplanung-zum-stadtraum-bahnhof-bern/dokumente/ubersichtsplan-testplanung-stadtraum-bahnhof-bern.pdf/download",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Perimeter and named public spaces around the station.")
add("bern-zbb-factsheet-massnahmen", "Stadt Bern: Factsheet Bau- und Verkehrsmassnahmen Zukunft Bahnhof Bern (ZBB)",
    BE + "/mediencenter/medienmitteilungen/aktuell_ptk/zukunft-bahnhof-bern-verkehrsmassnahmen-werden-aufgelegt/dokumente/factsheet-bau-und-verkehrsmassnahmen-zbb.pdf/download",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}, {"number": 8576646, "sloid": "ch:1:sloid:76646"}],
    "Future Bubenbergplatz/Hirschengraben layout and new access Bubenberg: model a 'future' variant separately from the current state.")
add("bern-zbb-kurzdossier-mitwirkung", "Stadt Bern: Kurzdossier Mitwirkung ZBB Verkehrsmassnahmen",
    BE + "/mediencenter/medienmitteilungen/aktuell_ptk/bahnhof-bern-verkehrsmassnahmen-gehen-in-die-mitwir-kung/dokumente/kurzdossier-mitwirkung-zbb.pdf/download",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Plans and visualisations of the access Bubenberg and Hirschengraben stop.")
add("bern-ueo-zbb-erlaeuterungsbericht", "Stadt Bern: Überbauungsordnung ZBB, Erläuterungsbericht",
    BE + "/themen/planen-und-bauen/mitwirkungen-und-offentliche-auflagen/abgeschlossene-mitwirkungen/2023/ueberbauungsordnung-zbb-stadt-bern-verkehrsmassnahmen/inhaltsverzeichnis/ueo-3-erlauterungsbericht.pdf/download",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Dimensions and phasing of the future station squares.")
add("bern-zukunftsbild-stadtraum-bahnhof-2035", "Stadt Bern: Zukunftsbild und Ziele Stadtraum Bahnhof Bern 2035ff",
    BE + "/mediencenter/medienmitteilungen/aktuell_ptk/stadtraum-bahnhof-gemeinderat-legt-eckwerte-fuer-richtplan-fest/dokumente/zukunftsbild-ziele-stadtraum-bahnhof-bern-2035ff.pdf/download",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Long-term target image (not current state).")
add("bern-zbb-broschuere-gesamtkonzept-2015", "Stadt Bern: Broschüre Gesamtkonzept (2015)",
    BE + "/mediencenter/medienmitteilungen/aktuell_ptk/der-erste-ausbauschritt-ist-in-sicht/listingblock.2015-06-11.5494697548/broschure-gesamtkonzept.pdf",
    "Stadt Bern", "planning_pdf", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Overall concept sections of the station expansion.")
add("rbs-unterbern-2018-01", "RBS Magazin UNTERBERN 01/2018", "https://www.rbs.ch/sites/default/files/2025/01-2018_UNTERBERN.pdf", "RBS", "project_magazine_pdf",
    LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Sections and renderings of the new RBS underground station below the SBB tracks.")
add("rbs-unterbern-2021-07", "RBS Magazin UNTERBERN 07/2021", "https://www.rbs.ch/sites/default/files/2025/07-2021_UNTERBERN.pdf", "RBS", "project_magazine_pdf",
    LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Construction progress photos and cavern cross-sections (RBS station).")
add("are-faktenblatt-wankdorf", "ARE Faktenblatt Verkehrsdrehscheibe Bern Wankdorf", "https://www.are.admin.ch/dam/de/sd-web/PH2wDWL8WVCV/faktenblatt-verkehrsdrehscheibe-bern-wankdorf.pdf",
    "Bundesamt für Raumentwicklung ARE", "planning_pdf", "Swiss federal publication; reuse terms not stated in the PDF. Link only.",
    [{"number": 8516161, "sloid": "ch:1:sloid:16161"}, {"number": 8590129, "sloid": "ch:1:sloid:90129"}], "Hub concept for Wankdorf: access points and modal interchange.")
add("sbb-bahnhof-bern-page", "SBB: Bahnhof Bern (services, accesses, orientation)", "https://www.sbb.ch/de/bahnhof-services/bahnhoefe/bahnhof-bern.html", "SBB",
    "web_page", LINK_ONLY, [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Current service locations and access descriptions.")

# --- Open datasets that inform station furniture and layout (fetched by other folders or here) ---------
SBBDS = "https://data.sbb.ch/explore/dataset/"
for ds, t, use in [
    ("mobiliar-im-bahnhof", "SBB: Mobiliar im Bahnhof (furniture inventory per station)", "Counts of benches, ticket machines, info points, recycling stations per station: drives how many parametric furniture assets to place (see assets/EVIDENCE)."),
    ("haltestelle-wartehallen", "SBB: Haltestelle Wartehallen (waiting shelters)", "Shelter positions and building type; fetched by stations/."),
    ("haltestelle-uhr", "SBB: Haltestelle Uhr (station clocks)", "Clock positions, mounting and lighting: place SBB clock assets; fetched by stations/."),
    ("billetautomat", "SBB: Billetautomat (ticket machines)", "Ticket machine positions; fetched by stations/."),
    ("sektortafel", "SBB: Sektortafel (sector boards)", "Sector board positions along platforms; fetched by stations/."),
    ("perron", "SBB: Perron (platforms)", "Platform attributes; fetched by stations/."),
    ("bilder-von-bahnhofen", "SBB: Bilder von Bahnhöfen (station photos)", "20 station photos; no Bern photo in this set (checked 2026-11-21)."),
    ("historische-bahnhofbilder", "SBB: Historische Bahnhofbilder", "Historic photo of Bern station, 1958-09-13 (SBB Historic F_116_00001_058): pre-1970s station, only for historic variants."),
]:
    add(f"sbb-dataset-{ds}", t, SBBDS + ds + "/", "SBB", "open_dataset", SBB_TERMS if ds != "mobiliar-im-bahnhof" else "Not stated in the dataset metadata (checked 2026-11-21). Link only; derived counts only.",
        [], use, redistribute=False)
add("sbb-historic-bern-1958", "SBB Historic: Bahnhof Bern 1958 (F_116_00001_058)", "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/historische-bahnhofbilder/files/9de687b4661e6b0ac3784b4488849d6b",
    "SBB Historic", "historic_photo", "Published in the SBB data portal under its portal terms; SBB Historic image rights not stated per image. Link only.",
    [{"number": 8507000, "sloid": "ch:1:sloid:7000"}], "Old station building (demolished 1957-1974): only relevant for a historic reconstruction.", capture_date="1958-09-13")
add("otd-traffic-point-v2", "opentransportdata.swiss: Traffic point elements (Haltekanten)", "https://data.opentransportdata.swiss/dataset/traffic-point-v2/permalink",
    "SBB / SKI (atlas)", "open_dataset", OTD_TERMS, [], "Edge SLOIDs and designations used as join keys for every image in this collection (fetched by transit/ and stations/).")
add("bern-geoportal-haltestellen", "Geoinformation Stadt Bern: Haltestellen (kerbs with letters)", "https://map.bern.ch/arcgis/rest/services/Geoportal/Haltestellen/MapServer/0",
    "Stadt Bern", "open_dataset", "open (opendata.swiss terms_open)", [], "Kerb letters and positions for city stops.")

# --- Imagery services --------------------------------------------------------------------------------
add("swisstopo-swissimage-wms", "swisstopo SWISSIMAGE 10 cm orthophoto (WMS)", "https://wms.geo.admin.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0",
    "swisstopo", "imagery_service", SWISSTOPO, [], "Top-down footprint of canopies, platforms, tram islands and road markings; crops for the hubs are stored in orthophoto/.", redistribute=True)
add("panoramax-api", "Panoramax (federated open street-level imagery, STAC API)", "https://api.panoramax.xyz/api", "Panoramax / OpenStreetMap France and contributors",
    "imagery_service", "Per picture, mostly CC BY-SA 4.0 (recorded per item)", [], "Georeferenced photos with compass azimuth: camera-pose references; see data/panoramax_items.json.", redistribute=True)
add("mapillary", "Mapillary street-level imagery", "https://www.mapillary.com/app/?lat=46.9488&lng=7.4391&z=17", "Mapillary (Meta)", "imagery_service",
    "CC BY-SA 4.0, but the API requires an access token", [], "Dense coverage of Bern; BLOCKED for harvesting (token needed, contract rule 9). Browse manually.", status_note="blocked: API key required")
add("kartaview", "KartaView street-level imagery", "https://kartaview.org/map/@46.9488,7.4391,17z", "KartaView (Grab)", "imagery_service",
    "CC BY-SA 4.0", [], "API at api.openstreetcam.org did not answer within 20 s on 2026-11-21; not harvested.", status_note="unavailable at harvest time")
add("commons-geosearch", "Wikimedia Commons map of geotagged files around Bern station", "https://commons.wikimedia.org/wiki/Special:Nearby#/coord/46.9488,7.4391",
    "Wikimedia Commons", "imagery_service", "Per file (recorded in data/commons_candidates.json)", [], "Browse further geotagged photos.")


BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"  # sbb.ch answers 403 to non-browser user agents


def check(u):
    err = None
    for ua in (UA, BROWSER_UA):
        for method in ("HEAD", "GET"):
            hd = {"User-Agent": ua}
            if method == "GET":
                hd["Range"] = "bytes=0-1023"
            req = urllib.request.Request(u, method=method, headers=hd)
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    h = r.headers
                    return {"http_status": r.status, "content_type": h.get("Content-Type"),
                            "content_length": h.get("Content-Length") if method == "HEAD" else None,
                            "last_modified": h.get("Last-Modified"), "final_url": r.geturl() if r.geturl() != u else None,
                            "check_note": "answered only to a browser user agent" if ua == BROWSER_UA else None}
            except Exception as e:
                err = str(e)
    return {"http_status": None, "error": err}


now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
for x in L:
    x["checked"] = now
    x.update({k: v for k, v in check(x["url"]).items() if v is not None})
    print(x.get("http_status"), x["id"], flush=True)
save("operator_links.json", {"generated": now, "count": len(L), "note": "Links only unless redistribute=true. Station keys are atlas number + SLOID.", "links": L})
print("saved", len(L))
