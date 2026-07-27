/*
 * qa-rec-smoke.js — boot both game files headless with the worker effectively
 * DOWN (no /api/v1 reachable) + faked camera/mic, and prove:
 *   - the page loads with no uncaught error ORIGINATING from the recording/ending code
 *   - window.NovaRec initialized (has a uuid id) and window.NovaEnding.show exists
 * This is the client half of the kill-the-worker test: a dead backend must not
 * break the page.
 */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.json': 'application/json', '.mp3': 'audio/mpeg', '.css': 'text/css', '.riv': 'application/octet-stream', '.mp4': 'video/mp4' };
const MINE = /nova-session-rec|nova-ending|NovaRec|NovaEnding|__showEndScreen|__endingSpeak|smart ending/i;

function serve() {
  return http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    fs.readFile(path.join(ROOT, p), (e, data) => {
      if (e) { res.writeHead(404); res.end('nf'); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
      res.end(data);
    });
  });
}

(async () => {
  const srv = serve();
  await new Promise(r => srv.listen(0, r));
  const port = srv.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] });

  let fail = false;
  for (const file of ['nova-commercial.html', 'animal-freeze.html']) {
    const page = await b.newPage({ viewport: { width: 900, height: 900 } });
    const mineErrors = [];
    page.on('pageerror', e => { if (MINE.test(e.message + (e.stack || ''))) mineErrors.push('pageerror: ' + e.message); });
    page.on('console', m => { if (m.type() === 'error' && MINE.test(m.text())) mineErrors.push('console: ' + m.text()); });
    await page.goto(`http://localhost:${port}/${file}`, { waitUntil: 'domcontentloaded' }).catch(() => {});
    await page.waitForTimeout(2500);
    const state = await page.evaluate(() => ({
      rec: !!(window.NovaRec && typeof window.NovaRec.id === 'string'),
      recId: window.NovaRec ? window.NovaRec.id : null,
      idLooksUuid: window.NovaRec ? /^[0-9a-f-]{36}$/.test(window.NovaRec.id) : false,
      ending: !!(window.NovaEnding && typeof window.NovaEnding.show === 'function'),
      speakFn: typeof window.__endingSpeak,   // commercial only
    })).catch(() => ({}));
    const ok = state.rec && state.idLooksUuid && state.ending && mineErrors.length === 0;
    if (!ok) fail = true;
    console.log(`\n[${file}]`);
    console.log('  NovaRec ready + uuid :', state.rec, state.idLooksUuid, `(${state.recId})`);
    console.log('  NovaEnding.show      :', state.ending);
    console.log('  my-code errors       :', mineErrors.length ? mineErrors : 'none');
    console.log('  =>', ok ? 'PASS' : 'FAIL');
    await page.close();
  }
  await b.close(); srv.close();
  console.log('\n=== ' + (fail ? 'FAIL' : 'ALL PASS') + ' ===');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
