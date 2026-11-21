// Independent cross-check of the committed timetable against the live Swiss journey API (transport.opendata.ch).
//   node bern-research/lead/validate/crosscheck_stationboard.js [YYYY-MM-DD] [HH:MM]
// For each focus station it asks the API for the next departures and looks each one up in
// transit/data/<feed>/timetable.json by minute and line, then compares the platform or kerb.
// Needs internet. Writes crosscheck_stationboard_<date>_<time>.json next to this file. Exit 1 if any station is below 90 % matched.
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const date = process.argv[2] || '2026-11-23', time = process.argv[3] || '08:00';
const feed = date > '2026-12-12' ? 'fp2027' : 'fp2026';
const STATIONS = [['8507110', 'Bern, Zytglogge'], ['8576646', 'Bern, Bahnhof'], ['8507000', 'Bern'], ['8516161', 'Bern Wankdorf'], ['8590129', 'Bern, Wankdorf Bahnhof']];
const BT = require(path.join(ROOT, 'transit', 'web', 'bern-transit.js'));
const tt = BT.decode(JSON.parse(fs.readFileSync(path.join(ROOT, 'transit', 'data', feed, 'timetable.json'), 'utf8')));
const norm = (s) => String(s || '').replace(/\s+/g, '').toUpperCase();
const clock = (sec) => { const t = ((sec % 86400) + 86400) % 86400; return String(Math.floor(t / 3600)).padStart(2, '0') + ':' + String(Math.floor((t % 3600) / 60)).padStart(2, '0'); };

(async () => {
  const out = { run: new Date().toISOString(), date, time, feed, api: 'https://transport.opendata.ch/v1/stationboard', stations: [] }; let ok = true;
  for (const [num, name] of STATIONS) {
    const url = `https://transport.opendata.ch/v1/stationboard?id=${num}&datetime=${encodeURIComponent(date + ' ' + time)}&limit=40`;
    let api; try { api = (await (await fetch(url)).json()).stationboard || []; } catch (e) { out.stations.push({ num, name, error: String(e) }); ok = false; continue; }
    let ours = tt.departures(Number(num), date, time + ':00', 5000, 10 * 3600); if (!ours.length) ours = tt.departures(num, date, time + ':00', 5000, 10 * 3600);   // 10 h window: at night 40 API departures span several hours
    let matched = 0, platSame = 0, platBoth = 0; const misses = [], platDiff = [];
    for (const a of api) {
      const hhmm = (a.stop.departure || '').slice(11, 16), line = norm(a.number), cat = norm(a.category);
      const cand = ours.filter((o) => clock(o.wall_sec) === hhmm && [line, cat + line].includes(norm(o.route)));   // our times may read 24:01, the API says 00:01
      if (!cand.length) { misses.push(`${hhmm} ${a.category}${a.number} -> ${a.to}`); continue; }
      matched++;
      const ap = norm(a.stop.platform); if (!ap) continue;
      const withPlat = cand.filter((o) => o.platform); if (!withPlat.length) continue;
      platBoth++;
      if (withPlat.some((o) => norm(o.platform) === ap)) platSame++; else platDiff.push(`${hhmm} ${a.category}${a.number}: api ${a.stop.platform}, ours ${[...new Set(withPlat.map((o) => o.platform))].join('/')}`);
    }
    const share = api.length ? matched / api.length : 0; if (share < 0.9) ok = false;
    out.stations.push({ num, name, api_departures: api.length, ours_in_window: ours.length, matched, share_matched: +share.toFixed(3), platform_compared: platBoth, platform_same: platSame, misses: misses.slice(0, 8), platform_differences: platDiff.slice(0, 8) });
    console.log(`${share >= 0.9 ? 'PASS' : 'FAIL'} ${num} ${name}: ${matched}/${api.length} API departures found in our timetable; platform equal ${platSame}/${platBoth}` + (misses.length ? ` | misses: ${misses.slice(0, 3).join('; ')}` : '') + (platDiff.length ? ` | platform diffs: ${platDiff.slice(0, 3).join('; ')}` : ''));
  }
  out.ok = ok; fs.writeFileSync(path.join(__dirname, `crosscheck_stationboard_${date}_${time.replace(':', '')}.json`), JSON.stringify(out, null, 1));
  process.exit(ok ? 0 : 1);
})();
