# Validation report

Generated 2026-11-21T02:17:31+01:00 by `scripts/validate.py` `--online` `--node`.

**74 of 78 checks passed, 4 warnings, 0 failed.**

| Result | Check | Detail |
|---|---|---|
| pass | source gtfs_fp2026: cached file matches recorded sha256 | gtfs_fp2026_20261118.zip |
| pass | source gtfs_fp2027: cached file matches recorded sha256 | gtfs_fp2027_20261118.zip |
| pass | source atlas_traffic_point: cached file matches recorded sha256 | actual-date-world-traffic-point.csv |
| pass | source atlas_service_point: cached file matches recorded sha256 | actual-date-swiss-service-point.csv |
| pass | source atlas_traffic_point_years: cached file matches recorded sha256 | timetable-years-world-traffic-point.csv |
| pass | source atlas_service_point_years: cached file matches recorded sha256 | timetable-years-swiss-service-point.csv |
| pass | source atlas_prm_platform: cached file matches recorded sha256 | actual-date-platform.csv |
| pass | source atlas_prm_stop_point: cached file matches recorded sha256 | actual-date-stop-point.csv |
| pass | source atlas_sectors: cached file matches recorded sha256 | actual-date-sectors-and-sector-groups.csv |
| pass | source atlas_prm_reference_point: cached file matches recorded sha256 | actual-date-reference-point.csv |
| pass | source atlas_prm_toilet: cached file matches recorded sha256 | actual-date-toilet.csv |
| pass | source atlas_prm_parking_lot: cached file matches recorded sha256 | actual-date-parking-lot.csv |
| pass | source atlas_prm_contact_point: cached file matches recorded sha256 | actual-date-contact-point.csv |
| pass | source atlas_prm_relation: cached file matches recorded sha256 | actual-date-relation.csv |
| pass | source bfr_wheelchair: cached file matches recorded sha256 | bfr_haltestellendaten.csv |
| pass | source boundary_bern: cached file matches recorded sha256 | bern_351.geojson |
| pass | stations: unique number | 1123 stations |
| pass | stations: unique sloid |  |
| pass | edges: unique sloid | 3483 edges and areas |
| pass | edges: every edge has a parent station in stations.geojson | 0 orphans |
| pass | edges: tier equals the parent station tier |  |
| pass | edges: edge sloid starts with the station sloid | 0 exceptions |
| pass | coverage: all 'bern' stations (atlas fsoNumber 351) lie inside the swisstopo boundary polygon | 208 stations, outside: [] |
| pass | coverage: no station of another tier lies inside the Bern polygon | [] |
| warn | coverage: no edge of a non-Bern station lies inside the (generalised) Bern polygon | border stops atlas attributes to the neighbouring municipality: ['Liebefeld, Lerbermatt', 'Ostermundigen, Waldeck']; trips serving them are included |
| pass | coverage: every 'ring' station is within 5 km of the boundary |  |
| warn | edges (bern): every edge lies within 400 m of its station coordinate | median 27 m, max 445 m, far: [['ch:1:sloid:7000:55:49', 'Bern', 445], ['ch:1:sloid:7000:55:50', 'Bern', 427]] |
| pass | edge_lookup: every referenced edge exists in edges.geojson |  |
| pass | accessibility: every edge key exists in edges.geojson | 2902 edges |
| pass | accessibility: every station key exists in stations.geojson | 1112 stations |
| warn | accessibility: PLATFORM relations point at edges in edges.geojson | 14 relations name an edge that is not in atlas traffic-point-v2 |
| pass | sectors: every sector belongs to an edge in edges.geojson | 1803 sectors |
| pass | sectors: a sector point lies within 450 m of its edge point | median 80 m, max 372 m over 1797 sectors |
| pass | fp2026: stop_times rows of a trip are contiguous and every trip id is in trips.txt |  |
| pass | fp2026: subset zip passes CRC test | 17,788,850 bytes |
| pass | fp2026: routes -> agency | 166 routes, 19 agencies |
| pass | fp2026: trips -> routes | 140,500 trips |
| pass | fp2026: trips -> calendar or calendar_dates | 8,839 services |
| pass | fp2026: stops -> parent_station | 3,415 stops |
| pass | fp2026: agency_timezone has Zurich rules | source says ['Europe/Berlin']; Europe/Berlin and Europe/Zurich share offset and DST dates, outputs are labelled Europe/Zurich |
| pass | fp2026: stop_times -> trips and stops | 2,066,447 rows |
| pass | fp2026: times never run backwards within a trip, stop_sequence strictly increasing | 0 violations |
| pass | fp2026: times at or after 24:00:00 are preserved | 123,886 rows, latest 29:45:00 |
| pass | fp2026: timetable.json decodes to exactly the stop_times of the GTFS subset | 2,066,447 rows compared field by field |
| pass | fp2026: timetable.json decodes to exactly the trips of the GTFS subset | 140,500 trips, all 9 columns |
| pass | fp2026: routes preserved |  |
| pass | fp2026: service-day bitmasks equal calendar.txt + calendar_dates.txt for every service | 8,839 services, 381,133 service-days, 1,154,155 exceptions |
| pass | fp2026: every timetable stop resolves to an edge SLOID or a station SLOID | 2388 of 2392 resolve; 4 are stations atlas does not hold (number only) |
| pass | fp2026: every timetable stop has a station record |  |
| pass | fp2026: GTFS stop coordinates agree with atlas edge coordinates (95 % within 5 m) | median 0.18 m, p95 0.40 m, 0 of 1950 differ by more than 25 m |
| pass | fp2026: every edge used by the timetable is in edges.geojson | 1 GTFS station(s) use edges that atlas files under another service point: [['Bern Europaplatz', 'Bern Europaplatz Süd']] |
| pass | fp2026: every atlas stop in Bern municipality has scheduled trips | 204 of 204; missing: [] |
| pass | fp2026: at least one trip runs on every day of the feed | 364 days, min 6,453 / max 10,618 trips per day |
| pass | fp2027: stop_times rows of a trip are contiguous and every trip id is in trips.txt |  |
| pass | fp2027: subset zip passes CRC test | 3,890,046 bytes |
| pass | fp2027: routes -> agency | 123 routes, 18 agencies |
| pass | fp2027: trips -> routes | 32,473 trips |
| pass | fp2027: trips -> calendar or calendar_dates | 1,858 services |
| pass | fp2027: stops -> parent_station | 3,084 stops |
| pass | fp2027: agency_timezone has Zurich rules | source says ['Europe/Berlin']; Europe/Berlin and Europe/Zurich share offset and DST dates, outputs are labelled Europe/Zurich |
| pass | fp2027: stop_times -> trips and stops | 444,996 rows |
| pass | fp2027: times never run backwards within a trip, stop_sequence strictly increasing | 0 violations |
| pass | fp2027: times at or after 24:00:00 are preserved | 23,160 rows, latest 29:25:00 |
| pass | fp2027: timetable.json decodes to exactly the stop_times of the GTFS subset | 444,996 rows compared field by field |
| pass | fp2027: timetable.json decodes to exactly the trips of the GTFS subset | 32,473 trips, all 9 columns |
| pass | fp2027: routes preserved |  |
| pass | fp2027: service-day bitmasks equal calendar.txt + calendar_dates.txt for every service | 1,858 services, 120,943 service-days, 227,829 exceptions |
| pass | fp2027: every timetable stop resolves to an edge SLOID or a station SLOID | 2111 of 2113 resolve; 2 are stations atlas does not hold (number only) |
| pass | fp2027: every timetable stop has a station record |  |
| pass | fp2027: GTFS stop coordinates agree with atlas edge coordinates (95 % within 5 m) | median 0.17 m, p95 0.39 m, 0 of 1756 differ by more than 25 m |
| pass | fp2027: every edge used by the timetable is in edges.geojson | 1 GTFS station(s) use edges that atlas files under another service point: [['Bern Europaplatz', 'Bern Europaplatz Süd']] |
| warn | fp2027: every atlas stop in Bern municipality has scheduled trips | 200 of 204; missing: [[8510471, 'Bern, Kunstmuseum'], [8511982, 'Bern, Bundesgasse'], [8512116, 'Bern, Waisenhausplatz'], [8512525, 'Bern, Berner Fachhochschule']] |
| pass | fp2027: at least one trip runs on every day of the feed | 364 days, min 6,669 / max 9,452 trips per day |
| pass | fp2026: departures at focus stations (Bern, Bern Bahnhof, Zytglogge, Wankdorf) agree with transport.opendata.ch stationboard (>= 95 % of API departures found) | 15 boards: 575 of 575 API departures found at the same minute and line; 0 of ours not in the API list; platform equal for 563 of 563 |
| pass | fp2026: departures at 40 random Bern stops agree with transport.opendata.ch stationboard (>= 95 % of API departures found) | 40 boards: 1466 of 1466 API departures found at the same minute and line; 0 of ours not in the API list; platform equal for 306 of 306 |
| pass | fp2027: departures at focus stations (Bern, Bern Bahnhof, Zytglogge, Wankdorf) agree with transport.opendata.ch stationboard (>= 95 % of API departures found) | 10 boards: 387 of 387 API departures found at the same minute and line; 0 of ours not in the API list; platform equal for 385 of 385 |
| pass | fp2027: departures at 40 random Bern stops agree with transport.opendata.ch stationboard (>= 95 % of API departures found) | 40 boards: 1470 of 1470 API departures found at the same minute and line; 0 of ours not in the API list; platform equal for 308 of 308 |
| pass | web/bern-transit.js returns the same departures as scripts/timetable.py | 1294 departures over 25 queries |

Numbers behind the checks are in `report.json`; sample departures in `sample_departures.md`.
