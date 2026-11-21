"""Cross-folder join checks, loaded by validate.py. Each check yields (level, message)."""
import math

FOCUS = {'8507000': 'Bern (rail)', '8576646': 'Bern, Bahnhof (tram/bus)', '8507110': 'Bern, Zytglogge',
         '8516161': 'Bern Wankdorf (rail)', '8588699': 'Bern, Wankdorf Center'}


def _pt_to_geom(lon, lat, geom):
    """Distance in metres from a point to the nearest part of a Point / LineString / Polygon geometry."""
    kx = 111320 * math.cos(math.radians(lat)); ky = 110574; best = float('inf')

    def lines(g):
        t, c = g['type'], g['coordinates']
        if t == 'Point': yield [c, c]
        elif t in ('LineString', 'MultiPoint'): yield c
        elif t in ('Polygon', 'MultiLineString'): yield from c
        elif t == 'MultiPolygon':
            for poly in c: yield from poly
    for ln in lines(geom):
        for a, b in zip(ln, ln[1:] or ln):
            ax, ay, bx, by = (a[0] - lon) * kx, (a[1] - lat) * ky, (b[0] - lon) * kx, (b[1] - lat) * ky
            ux, uy = bx - ax, by - ay; L2 = ux * ux + uy * uy
            t = 0 if L2 == 0 else max(0, min(1, -(ax * ux + ay * uy) / L2))
            best = min(best, math.hypot(ax + ux * t, ay + uy * t))
    return best


def run(ROOT, load):
    st, ed = load('transit/data/stations.geojson'), load('transit/data/edges.geojson')
    if not st or not ed:
        yield 'WARN', 'transit/data/stations.geojson or edges.geojson not present, joins skipped'; return
    S = {f['properties']['sloid']: f for f in st['features'] if f['properties'].get('sloid')}
    N = {str(f['properties']['number']): f for f in st['features']}
    E = {f['properties']['sloid']: f for f in ed['features']}
    no_sloid = [f['properties'].get('name') for f in st['features'] if not f['properties'].get('sloid')]
    if no_sloid: yield 'WARN', f'transit stations: {len(no_sloid)} stations have no SLOID (foreign stations on through trips: {no_sloid[:4]})'
    if len(S) + len(no_sloid) != len(st['features']): yield 'FAIL', f'transit stations: {len(st["features"]) - len(S) - len(no_sloid)} duplicate station SLOIDs'
    if len(N) != len(st['features']): yield 'FAIL', f'transit stations: {len(st["features"]) - len(N)} duplicate station numbers'
    if len(E) != len(ed['features']): yield 'FAIL', f'transit edges: {len(ed["features"]) - len(E)} duplicate edge SLOIDs'
    orphans = [s for s, f in E.items() if f['properties'].get('station_sloid') not in S]
    yield ('FAIL' if orphans else 'OK'), f'transit: {len(E)} edges, {len(orphans)} without a parent in stations.geojson' + (f' (e.g. {orphans[:3]})' if orphans else '')
    tiers = {}
    for f in st['features']: tiers[f['properties'].get('tier')] = tiers.get(f['properties'].get('tier'), 0) + 1
    bern_e = [f for f in ed['features'] if f['properties'].get('tier') == 'bern']
    nogeo = sum(1 for f in bern_e if not f.get('geometry')); rounded = sum(1 for f in bern_e if f['properties'].get('coord_rounded'))
    nodes = sum(1 for f in bern_e if not f['properties'].get('designation'))
    yield 'OK', (f'transit: stations by tier {tiers}; tier bern has {len(bern_e)} edges/areas, {nogeo} without geometry, '
                 f'{rounded} with rounded coordinates, {nodes} without a public designation')
    bern_st = [f for f in st['features'] if f['properties'].get('tier') == 'bern']
    few = sum(1 for f in bern_st if (f['properties'].get('edge_count') or 0) < 2); none = sum(1 for f in bern_st if not (f['properties'].get('edge_count') or 0))
    yield ('WARN' if none else 'OK'), f'transit: of {len(bern_st)} tier-bern stations, {none} have no boarding edge and {few} have fewer than two'

    lk = load('transit/data/edge_lookup.json')
    if lk:
        miss = total = 0
        for num, v in (lk.get('stations') or {}).items():
            for group in ('by_designation', 'by_designation_operational', 'by_gtfs_platform_code'):
                for ids in (v.get(group) or {}).values():
                    for i in (ids if isinstance(ids, list) else [ids]):
                        total += 1; miss += i not in E
        yield ('FAIL' if miss else 'OK'), f'transit edge_lookup: {total} references, {miss} point at an edge that is not in edges.geojson'

    for feed in ('fp2026', 'fp2027'):
        mp = load(f'transit/data/gtfs_stop_map_{feed}.json')
        if not mp: continue
        stops = mp.get('stops') or {}; items = list(stops.items()) if isinstance(stops, dict) else [(x.get('stop_id'), x) for x in stops]
        n = bad_e = bad_s = unres = 0
        for sid, v in items:
            if not isinstance(v, dict): continue
            n += 1; e, s = v.get('edge_sloid'), v.get('station_sloid')
            if e and e not in E: bad_e += 1
            if s and s not in S: bad_s += 1
            if not e and not s: unres += 1
        yield ('FAIL' if bad_e or bad_s else 'OK'), (f'transit stop map {feed}: {n} GTFS stop ids, {bad_e} with an unknown edge, '
                                                     f'{bad_s} with an unknown station, {unres} resolve to neither (foreign or unmatched)')

    for num, label in FOCUS.items():
        if num not in N: yield 'FAIL', f'focus station {num} {label} missing from transit stations'; continue
        es = [e for e in ed['features'] if str(e['properties'].get('station_number')) == num]
        geo = sum(1 for e in es if e.get('geometry'))
        yield ('OK' if geo else 'FAIL'), f'focus {num} {label}: {len(es)} edges/areas in transit, {geo} with coordinates'

    be = load('stations/data/boarding_edges.geojson')
    if be:
        unknown = far15 = far50 = n = 0; worst = []; unknown_ids = []
        for f in be['features']:
            p = f['properties']; e = p.get('edge_sloid'); n += 1
            if e not in E: unknown += 1; unknown_ids.append((e, p.get('station_name'))); continue
            a = E[e].get('geometry')
            if not a or not f.get('geometry'): continue
            d = _pt_to_geom(a['coordinates'][0], a['coordinates'][1], f['geometry'])
            if d > 15: far15 += 1
            if d > 50: far50 += 1; worst.append((round(d), e, p.get('station_name')))
        worst.sort(reverse=True)
        yield ('FAIL' if unknown else 'OK'), f'stations boarding_edges: {n} features, {unknown} with an edge SLOID unknown to transit' + (f' ({unknown_ids[:3]})' if unknown_ids else '')
        yield ('WARN' if far50 else 'OK'), (f'stations boarding_edges: {far15} lie more than 15 m from the atlas edge point, {far50} more than 50 m'
                                           + (f'; worst {worst[:5]}' if worst else ''))
        have = {f['properties'].get('edge_sloid') for f in be['features']}
        missing = [f['properties']['sloid'] for f in bern_e if f['properties'].get('type') == 'BOARDING_PLATFORM' and f['properties']['sloid'] not in have]
        yield ('WARN' if missing else 'OK'), (f'stations boarding_edges: {len(missing)} tier-bern boarding platforms from transit have no geometry feature in stations'
                                             + (f' (e.g. {missing[:3]})' if missing else ''))
    ss = load('stations/data/stations.geojson')
    if ss:
        ids = [f['properties'].get('sloid') or f['properties'].get('station_sloid') for f in ss['features']]
        miss = [i for i in ids if i not in S]
        yield ('WARN' if miss else 'OK'), f'stations stations.geojson: {len(ids)} stations, {len(miss)} not in transit stations' + (f' (e.g. {miss[:3]})' if miss else '')
    for name in ('bern-bahnhof', 'zytglogge', 'wankdorf'):
        fo = load(f'stations/data/focus/{name}.geojson')
        if not fo: yield 'WARN', f'stations focus/{name}.geojson not present'; continue
        kinds = {}; inferred = 0
        for f in fo['features']:
            k = f['properties'].get('feature_type'); kinds[k] = kinds.get(k, 0) + 1; inferred += bool(f['properties'].get('inferred'))
        yield 'OK', (f'stations focus/{name}: {len(fo["features"])} features, {inferred} flagged inferred; '
                     + ', '.join(f'{k} {v}' for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:8]))

    rs = load('references/data/stations.json')
    if rs:
        lst = rs.get('stations') or []; miss = [x.get('number') for x in lst if str(x.get('number')) not in N]
        yield ('WARN' if miss else 'OK'), f'references stations.json: {len(lst)} stations, {len(miss)} not in transit stations' + (f' (e.g. {miss[:3]})' if miss else '')
