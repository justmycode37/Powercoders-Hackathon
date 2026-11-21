// Headless smoke test of the sample loaders. Node 22+ (built-in WebSocket and fetch) and Google Chrome.
//   node bern-research/lead/validate/smoke_sample.js [outDir]
// Starts a static server on bern-research/, opens lead/sample/ and city3d/, checks that the data loads and joins,
// writes screenshots and smoke_report.json, exits 1 on failure. Needs internet for the swisstopo base map.
const { spawn } = require('child_process'), http = require('http'), fs = require('fs'), path = require('path'), os = require('os');
const ROOT = path.resolve(__dirname, '..', '..');                       // bern-research/
const OUT = path.resolve(process.argv[2] || path.join(__dirname, 'smoke'));
const CHROME = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.geojson': 'application/geo+json', '.webp': 'image/webp', '.glb': 'model/gltf-binary', '.jpg': 'image/jpeg', '.png': 'image/png', '.css': 'text/css' };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const server = http.createServer((req, res) => {
  const p = path.normalize(path.join(ROOT, decodeURIComponent(req.url.split('?')[0])));
  if (!p.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  const f = fs.existsSync(p) && fs.statSync(p).isDirectory() ? path.join(p, 'index.html') : p;
  fs.readFile(f, (err, buf) => { if (err) { res.writeHead(404); return res.end('not found'); } res.writeHead(200, { 'content-type': MIME[path.extname(f).toLowerCase()] || 'application/octet-stream' }); res.end(buf); });
});

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'bern-smoke-'));
  const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=9391', '--user-data-dir=' + prof, '--no-first-run', '--window-size=1280,860', 'about:blank'], { stdio: 'ignore' });
  let tabs; for (let i = 0; i < 60; i++) { try { tabs = await (await fetch('http://127.0.0.1:9391/json')).json(); break; } catch (e) { await sleep(250); } }
  const ws = new WebSocket(tabs.find((t) => t.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const pend = new Map(); let errors = [], failed = [];
  ws.onmessage = (m) => { const d = JSON.parse(m.data);
    if (d.id && pend.has(d.id)) { pend.get(d.id)(d.result || d.error); pend.delete(d.id); }
    else if (d.method === 'Runtime.exceptionThrown') errors.push(String(d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description || d.params.exceptionDetails.text).slice(0, 300));
    else if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errors.push(d.params.args.map((a) => a.value || a.description).join(' ').slice(0, 300));
    else if (d.method === 'Network.responseReceived' && d.params.response.status >= 400 && !/favicon/.test(d.params.response.url)) failed.push(d.params.response.status + ' ' + d.params.response.url); };
  const send = (method, params) => new Promise((r) => { pend.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
  const evalJs = async (expression) => { const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result.value; };
  const shot = async (name) => fs.writeFileSync(path.join(OUT, name), Buffer.from((await send('Page.captureScreenshot', { format: 'png' })).data, 'base64'));
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 860, deviceScaleFactor: 1, mobile: false });
  const report = { run: new Date().toISOString(), checks: [] }; let ok = true;
  const check = (name, pass, detail) => { report.checks.push({ name, pass: !!pass, detail }); if (!pass) ok = false; console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + JSON.stringify(detail).slice(0, 400) : '')); };

  // 1. lead sample: edges + kerb lines + station detail + departures at Zytglogge edge K
  errors = []; failed = [];
  await send('Page.navigate', { url: base + '/lead/sample/' }); await sleep(9000);
  const s1 = await evalJs(`(async () => { const m = SAMPLE.map; const src = (n) => m.getSource(n) && m.getSource(n).serialize().data;
    const e = src('edges'), k = src('kerbs');
    const z = e.features.find((f) => f.properties.sloid === 'ch:1:sloid:7110:0:17');
    const dep = z ? await SAMPLE.departuresFor(z.properties, '2026-11-23', '08:00:00') : null;      // a Monday morning
    const ids = new Set(e.features.map((f) => f.properties.sloid));
    const onEdge = dep ? dep.all.filter((d) => d.edge_sloid && ids.has(d.edge_sloid)).length : 0;
    const perEdge = {}; if (dep) dep.all.forEach((d) => { const f = e.features.find((x) => x.properties.sloid === d.edge_sloid); const k = f ? f.properties.designation || '#' + f.properties.designation_operational : 'none'; perEdge[k] = (perEdge[k] || 0) + 1; });
    const sel = document.getElementById('focus'); sel.value = 'bern-bahnhof'; sel.dispatchEvent(new Event('change')); await new Promise((r) => setTimeout(r, 4000));
    const fo = src('focus');
    return { loaded: m.loaded(), edges: e.features.length, kerbs: k.features.length, zytgloggeK: z && { designation: z.properties.designation, station: z.properties.station_name, coords: z.geometry.coordinates },
      departures: dep && { feed: dep.feed, date: dep.now.date, time: dep.now.time, stationCount: dep.station, onKnownEdge: onEdge, perEdge, first: dep.all.slice(0, 3).map((d) => [d.time, d.route, d.headsign, d.platform]) },
      focusFeatures: fo.features.length, log: document.getElementById('log').textContent }; })()`);
  await shot('sample_bern_bahnhof.png');
  check('sample: page and base map load', s1.loaded && !/ERROR/.test(s1.log), { log: s1.log.split('\n').slice(0, 8) });
  check('sample: boarding edges loaded', s1.edges > 3000, s1.edges);
  check('sample: kerb and track lines loaded', s1.kerbs > 1000, s1.kerbs);
  check('sample: Zytglogge edge K resolves by SLOID', s1.zytgloggeK && s1.zytgloggeK.designation === 'K', s1.zytgloggeK);
  check('sample: timetable decodes, Zytglogge has departures on Mon 2026-11-23 from 08:00', s1.departures && s1.departures.stationCount > 50, s1.departures);
  check('sample: every one of those departures joins to a boarding edge with coordinates', s1.departures && s1.departures.onKnownEdge === s1.departures.stationCount, { onKnownEdge: s1.departures && s1.departures.onKnownEdge, of: s1.departures && s1.departures.stationCount });
  check('sample: Bern Bahnhof station detail loaded', s1.focusFeatures > 500, s1.focusFeatures);
  check('sample: no console errors or failed requests', !errors.length && !failed.length, { errors: errors.slice(0, 5), failed: failed.slice(0, 5) });

  // 2. city3d sample scene
  errors = []; failed = [];
  await send('Page.navigate', { url: base + '/city3d/index.html' }); await sleep(14000);
  const s2 = await evalJs(`(() => { const c = document.querySelector('canvas'); return { canvas: !!c, w: c && c.width, h: c && c.height, title: document.title, text: document.body.innerText.slice(0, 300) }; })()`);
  await shot('city3d_scene.png');
  check('city3d: scene page renders a canvas', s2.canvas && s2.w > 0, s2);
  check('city3d: no console errors or failed requests', !errors.length && !failed.length, { errors: errors.slice(0, 5), failed: failed.slice(0, 5) });

  report.ok = ok; fs.writeFileSync(path.join(OUT, 'smoke_report.json'), JSON.stringify(report, null, 1));
  ws.close(); chrome.kill(); server.close(); setTimeout(() => process.exit(ok ? 0 : 1), 400);
})().catch((e) => { console.error('smoke test crashed:', e); process.exit(2); });
