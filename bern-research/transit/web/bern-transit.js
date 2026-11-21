// Thin decoder for bern-research/transit/data/<feed>/timetable.json.
// Browser: <script src="bern-transit.js"></script> then  const tt = await BERN_TRANSIT.load('data/fp2026/timetable.json')
// Node:    const tt = require('./bern-transit.js').decode(JSON.parse(fs.readFileSync(path)))
// Same results as scripts/timetable.py (validate.py compares the two).
(function (root) {
  const DAY = 86400;
  const pad = (n) => String(n).padStart(2, '0');
  const hms = (s) => `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;   // may be >= 24:00:00
  const toSec = (t) => { const [h, m, s] = t.split(':').map(Number); return h * 3600 + m * 60 + (s || 0); };
  const dayNumber = (iso) => { const [y, m, d] = iso.split('-').map(Number); return Math.round(Date.UTC(y, m - 1, d) / 864e5); };
  const isoOf = (n) => new Date(n * 864e5).toISOString().slice(0, 10);

  // Europe/Zurich offset (minutes) at a UTC instant, without any library
  const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Zurich', hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  function zurichOffsetMin(utcMs) {
    const p = Object.fromEntries(fmt.formatToParts(new Date(utcMs)).map((x) => [x.type, Number(x.value)]));
    return (Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(utcMs / 1000) * 1000) / 60000;
  }
  // GTFS: a time counts from "noon minus 12 h" of the service day, which is what makes DST days come out right
  function epochMs(serviceDate, sec) {
    const [y, m, d] = serviceDate.split('-').map(Number);
    const noonGuess = Date.UTC(y, m - 1, d, 12);
    const noon = noonGuess - zurichOffsetMin(noonGuess) * 60000;
    return noon - 12 * 3600 * 1000 + sec * 1000;
  }

  function decode(doc) {
    const { meta, routes, agencies, stops, stations, patterns, headsigns, hints } = doc;
    const start = dayNumber(meta.feed_start_date);
    const masks = doc.services.masks;
    const freq = new Set(doc.frequencies.map((f) => `${f[0]}:${f[1]}`));
    // bit i of a hex mask, least significant bit = feed_start_date
    const runs = (service, dayIndex) => {
      if (dayIndex < 0) return false;
      const hex = masks[service];
      const pos = hex.length - 1 - (dayIndex >> 2);
      return pos >= 0 && ((parseInt(hex[pos], 16) >> (dayIndex & 3)) & 1) === 1;
    };
    const dayIndex = (iso) => dayNumber(iso) - start;
    const byNumber = new Map();
    patterns.forEach((p, pi) => p.s.forEach((si, j) => {
      const n = stops[si][1];
      if (!byNumber.has(n)) byNumber.set(n, []);
      byNumber.get(n).push([pi, j]);
    }));

    // Scheduled departures from station `number` on calendar day `date` from wall-clock `time`.
    function departures(number, date, time = '00:00:00', limit = 20, windowSec = 6 * 3600, includeFrequency = false) {
      const t0 = toSec(time), day = dayIndex(date), out = [];
      const daysAhead = Math.floor((t0 + windowSec) / DAY);   // a long window reaches into later service days
      for (const [pi, j] of byNumber.get(number) || []) {
        const p = patterns[pi];
        if (j === p.s.length - 1) continue;                 // final stop: nothing departs
        if (p.pu && p.pu[j] === 1) continue;                // no boarding here
        const t = p.t, stop = stops[p.s[j]], route = routes[p.r], last = stops[p.s[p.s.length - 1]];
        for (let k = 0; k < t.id.length; k++) {
          const isFreq = freq.has(`${pi}:${k}`);
          if (isFreq && !includeFrequency) continue;
          const dep = t.st[k] + p.p[t.pf[k]][2 * j + 1];
          for (let back = 1; back >= -daysAhead; back--) {  // 1 = service day before `date` (times >= 24:00), 0 = `date`, -1 = next day
            const wall = dep - back * DAY;
            if (wall < t0 || wall >= t0 + windowSec || !runs(t.sv[k], day - back)) continue;
            const serviceDate = isoOf(dayNumber(date) - back);
            out.push({
              wall_sec: wall, time: hms(wall), gtfs_time: hms(dep), service_date: serviceDate,
              epoch_ms: epochMs(serviceDate, dep),
              route: route[2], route_desc: route[4], route_type: route[5], agency: agencies[route[1]][1],
              headsign: headsigns[p.h], last_stop: stations[String(last[1])][1],
              platform: stop[3], stop_id: stop[0], edge_sloid: stop[2],
              trip_id: t.id[k], trip_short_name: t.sn[k], original_trip_id: t.oid[k],
              direction_id: p.d, frequency_based: isFreq,
            });
          }
        }
      }
      const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
      out.sort((a, b) => a.wall_sec - b.wall_sec || cmp(a.route, b.route) || cmp(a.headsign, b.headsign) || cmp(a.trip_id, b.trip_id));
      return out.slice(0, limit);
    }

    // Vehicles under way at wall-clock `time` on `date`: position interpolated on the straight line between stops.
    function vehiclesAt(date, time) {
      const now = toSec(time), day = dayIndex(date), out = [];
      patterns.forEach((p, pi) => {
        const t = p.t, n = p.s.length;
        for (let k = 0; k < t.id.length; k++) {
          if (freq.has(`${pi}:${k}`)) continue;
          const prof = p.p[t.pf[k]];
          for (const back of [0, 1]) {
            const s = now + back * DAY - t.st[k];           // seconds since first departure, in this trip's clock
            if (s < prof[1] || s > prof[2 * n - 2] || !runs(t.sv[k], day - back)) continue;
            let j = 0;
            while (j < n - 2 && s >= prof[2 * (j + 1) + 1]) j++;
            const a = stops[p.s[j]], b = stops[p.s[j + 1]];
            const depA = prof[2 * j + 1], arrB = prof[2 * (j + 1)];
            const f = s <= depA ? 0 : s >= arrB ? 1 : (s - depA) / Math.max(1, arrB - depA);
            out.push({ trip_id: t.id[k], route: routes[p.r][2], route_type: routes[p.r][5], headsign: headsigns[p.h],
              from: a[0], to: b[0], progress: f, lon: a[4] + (b[4] - a[4]) * f, lat: a[5] + (b[5] - a[5]) * f, dwelling: f === 0 || f === 1 });
            break;
          }
        }
      });
      return out;
    }

    return { meta, doc, runs, dayIndex, departures, vehiclesAt, epochMs, hms, hints };
  }

  const api = { decode, epochMs, load: async (url) => decode(await (await fetch(url)).json()) };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BERN_TRANSIT = api;
})(typeof window !== 'undefined' ? window : globalThis);
