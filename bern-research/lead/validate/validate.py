"""Lead validation for bern-research/. Python 3.11, standard library only.

    python bern-research/lead/validate/validate.py            # all folders, writes REPORT.md next to this file
    python bern-research/lead/validate/validate.py transit    # one folder

Generic checks run on whatever is present; the cross-folder joins run when the files named in JOINS exist.
Exit code 1 if any check is a FAIL. WARN lines are for the handoff, they do not block a commit.
"""
import csv, hashlib, json, os, re, subprocess, sys, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))        # bern-research/
REPO = os.path.dirname(ROOT)
AREAS = ['transit', 'city3d', 'stations', 'references', 'lead']
MAX_COMMIT_BYTES = 25 * 1024 * 1024
CH = (5.9, 45.8, 10.5, 47.9)             # Switzerland lon/lat sanity box
BERN = (7.20, 46.85, 7.70, 47.10)        # generous Bern box, for reporting only
SLOID = re.compile(r'^ch:1:sloid:\d+(:\d+)*$')
SECRET = re.compile(r'(eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|'
                    r'(?i:authorization)\s*[:=]\s*["\']?(?i:bearer)\s+[A-Za-z0-9._-]{20,}|'
                    r'(?i:api[_-]?key|token|secret|password)["\']?\s*[:=]\s*["\'][A-Za-z0-9/+_-]{24,}["\'])')
TEXT_EXT = {'.json', '.geojson', '.csv', '.txt', '.md', '.py', '.js', '.html', '.yml', '.yaml', '.toml', '.cfg', '.sh', '.ps1'}

out, fails = [], 0
def line(level, area, msg):
    global fails
    if level == 'FAIL': fails += 1
    out.append((level, area, msg))

def candidates(area):
    """Files git would add for this folder: untracked-and-not-ignored plus tracked."""
    p = 'bern-research/' + area
    r = subprocess.run(['git', '-C', REPO, 'ls-files', '--cached', '--others', '--exclude-standard', '--', p],
                       capture_output=True, text=True, encoding='utf-8')
    return [os.path.join(REPO, f) for f in r.stdout.splitlines() if f and os.path.isfile(os.path.join(REPO, f))]

def coords(geom):
    if not geom: return
    if geom.get('type') == 'GeometryCollection':
        for g in geom.get('geometries', []): yield from coords(g)
        return
    def walk(c):
        if c and isinstance(c[0], (int, float)): yield c
        else:
            for x in c or []: yield from walk(x)
    yield from walk(geom.get('coordinates'))

def check_geojson(area, rel, d):
    feats = d.get('features') if d.get('type') == 'FeatureCollection' else ([d] if d.get('type') == 'Feature' else None)
    if feats is None: return
    n = len(feats); swapped = outside_ch = outside_bern = pts = 0; no_source = no_inferred = bad_sloid = 0; sloids = 0
    for f in feats:
        p = f.get('properties') or {}
        if 'source' not in p: no_source += 1
        if 'inferred' not in p: no_inferred += 1
        for k, v in p.items():
            if 'sloid' in k.lower() and isinstance(v, str) and v:
                sloids += 1
                if not SLOID.match(v): bad_sloid += 1
        for c in coords(f.get('geometry')):
            pts += 1; x, y = c[0], c[1]
            if x > 40 and y < 20: swapped += 1
            elif not (CH[0] <= x <= CH[2] and CH[1] <= y <= CH[3]): outside_ch += 1
            elif not (BERN[0] <= x <= BERN[2] and BERN[1] <= y <= BERN[3]): outside_bern += 1
    line('OK', area, f'{rel}: {n} features, {pts} vertices, {sloids} SLOID values')
    if swapped: line('FAIL', area, f'{rel}: {swapped} vertices look like lat/lon instead of lon/lat')
    if outside_ch: line('FAIL', area, f'{rel}: {outside_ch} vertices outside Switzerland (wrong CRS?)')
    if outside_bern: line('WARN', area, f'{rel}: {outside_bern} of {pts} vertices outside the Bern box {BERN}')
    if bad_sloid: line('FAIL', area, f'{rel}: {bad_sloid} values in sloid properties do not look like SLOIDs')
    if n and no_source: line('WARN', area, f'{rel}: {no_source} of {n} features have no `source`')
    if n and no_inferred: line('WARN', area, f'{rel}: {no_inferred} of {n} features have no `inferred` flag')

def check_manifest(area, rel, d):
    entries = d if isinstance(d, list) else d.get('sources') or d.get('inputs') or d.get('items') or d.get('files') or [d]
    if isinstance(entries, dict): entries = list(entries.values())
    entries = [e for e in entries if isinstance(e, dict)]
    need = {'url': ('url', 'source_url', 'download_url', 'original_url'), 'licence': ('licence', 'license', 'license_name', 'rights'),
            'retrieved': ('retrieved', 'retrieved_at', 'fetched', 'fetched_at', 'downloaded', 'downloaded_at', 'accessed'),
            'sha256': ('sha256', 'checksum', 'hash')}
    miss = {k: sum(1 for e in entries if not any(e.get(a) for a in alts)) for k, alts in need.items()}
    bad = {k: v for k, v in miss.items() if v}
    line('WARN' if bad else 'OK', area, f'{rel}: {len(entries)} manifest entries' + (f', missing {bad}' if bad else ', all with url, licence, date, checksum'))

def check_area(area):
    base = os.path.join(ROOT, area)
    if not os.path.isdir(base): line('WARN', area, 'folder does not exist yet'); return
    files = candidates(area)
    total = sum(os.path.getsize(f) for f in files)
    line('OK', area, f'{len(files)} files, {total / 1048576:.1f} MB would be committed')
    for name in ('STATUS.md', 'HANDOFF.md'):
        if area != 'lead' and not os.path.isfile(os.path.join(base, name)): line('WARN', area, f'no {name} yet')
    manifests = 0
    for f in files:
        rel = os.path.relpath(f, ROOT).replace(os.sep, '/'); size = os.path.getsize(f); ext = os.path.splitext(f)[1].lower()
        if size == 0: line('FAIL', area, f'{rel}: empty file'); continue
        if size > MAX_COMMIT_BYTES: line('FAIL', area, f'{rel}: {size / 1048576:.1f} MB is above the 25 MB commit limit'); continue
        if '__pycache__' in rel or ext in ('.pyc', '.tif', '.tiff', '.gdb', '.zip') and '.cache' in rel:
            line('FAIL', area, f'{rel}: cache or build file is not ignored')
        if ext in TEXT_EXT and size < 8 * 1048576:
            try: text = open(f, encoding='utf-8').read()
            except UnicodeDecodeError: line('FAIL', area, f'{rel}: not valid UTF-8'); continue
            m = SECRET.search(text)
            if m: line('FAIL', area, f'{rel}: looks like a credential near offset {m.start()}')
        if ext in ('.json', '.geojson') and size < 80 * 1048576:
            try: d = json.load(open(f, encoding='utf-8'))
            except Exception as e: line('FAIL', area, f'{rel}: does not parse as JSON ({e})'); continue
            base_name = os.path.basename(f).lower()
            if isinstance(d, dict) and d.get('type') in ('FeatureCollection', 'Feature'): check_geojson(area, rel, d)
            if base_name in ('sources.json', 'source.json', 'manifest.json') or base_name.endswith('manifest.json'):
                manifests += 1; check_manifest(area, rel, d)
        if ext == '.csv' and size < 80 * 1048576:
            with open(f, encoding='utf-8-sig', newline='') as fh:
                sample = fh.read(4096); fh.seek(0)
                delim = ';' if sample.count(';') > sample.count(',') else ','
                r = csv.reader(fh, delimiter=delim); hdr = next(r, None); rows = bad = 0
                for row in r:
                    rows += 1
                    if len(row) != len(hdr): bad += 1
            line('FAIL' if bad else 'OK', area, f'{rel}: {rows} rows, {len(hdr or [])} columns' + (f', {bad} rows with a different column count' if bad else ''))
    if area != 'lead' and not manifests: line('WARN', area, 'no source manifest (SOURCES.json / source.json / manifest.json) among committable files')

def load(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p, encoding='utf-8')) if os.path.isfile(p) else None

def joins():
    """Cross-folder checks. Filled in by the lead as the folders publish their file names (see JOINS.md)."""
    try:
        import joins as j                                   # bern-research/lead/validate/joins.py, optional
    except ImportError:
        line('WARN', 'joins', 'no cross-folder join checks configured yet'); return
    for level, msg in j.run(ROOT, load): line(level, 'joins', msg)

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(__file__))
    areas = [a for a in sys.argv[1:] if a in AREAS] or AREAS
    for a in areas: check_area(a)
    if len(areas) > 1: joins()
    order = {'FAIL': 0, 'WARN': 1, 'OK': 2}
    head = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    md = [f'# Validation report', '', f'Run {datetime.datetime.now().astimezone().isoformat(timespec="seconds")} on HEAD `{head}`, folders: {", ".join(areas)}.', '',
          f'**{sum(1 for o in out if o[0] == "FAIL")} FAIL, {sum(1 for o in out if o[0] == "WARN")} WARN, {sum(1 for o in out if o[0] == "OK")} OK**', '']
    for a in areas + ['joins']:
        rows = sorted([o for o in out if o[1] == a], key=lambda o: order[o[0]])
        if not rows: continue
        md += [f'## {a}', ''] + [f'- **{lv}** {msg}' for lv, _, msg in rows] + ['']
    if len(areas) == len(AREAS): open(os.path.join(os.path.dirname(__file__), 'REPORT.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md))
    print('\n'.join(l for l in md if not l.startswith('- **OK**') or len(out) < 60))
    sys.exit(1 if fails else 0)
