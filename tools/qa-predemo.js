// QA — PRE-GAME DEMO VIDEO (FINISH-THE-GAME 2026-07-16)
// Machine-checks: pick → #pre-demo shows + plays the right recording (muted) →
// change-mind swaps it → leaving the transition kills it. phase2-loop pattern:
// local static server, stubbed __novaSend, no worker needed.
//
// Usage: node tools/qa-predemo.js

const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8853;
const URL = `http://localhost:${PORT}/nova-joined.html`;

const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
  '.json':'application/json', '.mp4':'video/mp4', '.mp3':'audio/mpeg',
  '.png':'image/png', '.jpg':'image/jpeg', '.riv':'application/octet-stream' };
function startServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/nova-joined.html';
      const file = path.join(ROOT, p);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); return res.end('not found');
      }
      const stat = fs.statSync(file);
      // range support so <video> can seek
      const range = req.headers.range;
      if (range) {
        const m = /bytes=(\d+)-(\d*)/.exec(range);
        const start = +m[1], end = m[2] ? +m[2] : stat.size - 1;
        res.writeHead(206, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
          'Content-Range': `bytes ${start}-${end}/${stat.size}`, 'Accept-Ranges': 'bytes',
          'Content-Length': end - start + 1 });
        return fs.createReadStream(file, { start, end }).pipe(res);
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
        'Accept-Ranges': 'bytes', 'Content-Length': stat.size });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}

const results = [];
const check = (name, pass, evidence) => {
  results.push({ name, pass });
  console.log((pass ? 'PASS ' : 'FAIL ') + name + ' — ' + evidence);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

function benchInit() {
  window.__initRunwayNova = () => {};
  window.__novaSpeakingNow = false;
}
function installSend() {
  window.__benchSent = [];
  window.__novaSend = (m) => { try { window.__benchSent.push(m); } catch (e) {} };
}

(async () => {
  const server = await startServer();
  console.log(`>>> static server on ${URL}`);
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40', '--window-size=1300,820'] });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1400, height: 800 } });

  try {
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(benchInit);
    await page.goto(URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => typeof window.__startTransition === 'function', undefined, { timeout: 15000 });
    await page.evaluate(installSend);

    // ── 1. pick 'joined' → picked event sent + pre-demo shows the upgroove recording
    await page.evaluate(() => pickGame('joined'));
    await sleep(2500);   // give the video time to buffer + start
    let s = await page.evaluate(() => {
      const v = document.getElementById('pre-demo');
      return { src: v.getAttribute('src'), showing: v.classList.contains('showing'),
        muted: v.muted, playing: !v.paused && v.currentTime > 0, t: v.currentTime,
        visible: !!(v.offsetParent || v.getClientRects().length),
        phase: (document.querySelector('.phase.active') || {}).id,
        picked: (window.__benchSent || []).filter(m => m.kind === 'game-event' && m.event && m.event.event === 'picked') };
    });
    check('1 picked event sent to worker', s.picked.length === 1 && s.picked[0].event.song === 'joined', JSON.stringify(s.picked));
    check('2 pre-demo = pre-upgroove.mp4, .showing', s.src === 'pre-upgroove.mp4' && s.showing, `src=${s.src} showing=${s.showing}`);
    check('3 pre-demo PLAYING and MUTED', s.playing && s.muted, `paused=${!s.playing} t=${s.t.toFixed(2)}s muted=${s.muted}`);
    check('4 on transition screen, video visible', s.phase === 'phase-transition' && s.visible, `phase=${s.phase} visible=${s.visible}`);

    // ── 2. change-mind → wave recording swaps in
    await page.evaluate(() => pickGame('wave'));
    await sleep(2000);
    s = await page.evaluate(() => {
      const v = document.getElementById('pre-demo');
      return { src: v.getAttribute('src'), showing: v.classList.contains('showing'), playing: !v.paused && v.currentTime > 0 };
    });
    check('5 change-mind swaps to pre-wave.mp4, still playing', s.src === 'pre-wave.mp4' && s.showing && s.playing, JSON.stringify(s));

    // ── 3. leaving the transition kills it
    await page.evaluate(() => showPhase('phase-game'));
    await sleep(300);
    s = await page.evaluate(() => {
      const v = document.getElementById('pre-demo');
      return { showing: v.classList.contains('showing'), paused: v.paused };
    });
    check('6 showPhase(game) → hidden + paused', !s.showing && s.paused, JSON.stringify(s));

    // ── 4. hello (no recording) → no crash, stays hidden
    await page.evaluate(() => { showPhase('phase-picker'); showPreDemo('hello'); });
    await sleep(200);
    s = await page.evaluate(() => document.getElementById('pre-demo').classList.contains('showing'));
    check('7 hello → no demo, no crash', s === false, `showing=${s}`);

    check('8 zero page errors', errors.length === 0, errors.join(' | ') || 'clean');

    // screenshot evidence of the PiP on the transition screen
    await page.evaluate(() => { showPhase('phase-transition'); showPreDemo('joined'); });
    await sleep(2000);
    await page.screenshot({ path: path.join(__dirname, 'shot-predemo.png') });
    console.log('>>> screenshot: tools/shot-predemo.png');
  } finally {
    await browser.close();
    server.close();
  }
  const fails = results.filter(r => !r.pass).length;
  console.log(`\n=== ${results.length - fails}/${results.length} PASS ===`);
  process.exit(fails ? 1 : 0);
})();
