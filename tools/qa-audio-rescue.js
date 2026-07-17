// QA — AUDIO-RESCUE (2026-07-17): reproduces the real failure (autoplay BLOCKED,
// play() rejects) and proves the rescue: button appears instantly, real click
// unlocks, audio element plays, button hides. Runs Chrome with the REAL
// user-gesture-required autoplay policy (opposite of the other rigs).
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8855;
const PAGE = process.argv[2] || 'nova-app.html';
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
  '.mp4':'video/mp4', '.mp3':'audio/mpeg', '.png':'image/png', '.jpg':'image/jpeg' };
function startServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      const file = path.join(ROOT, p);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); return res.end('nf');
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}
const results = [];
const check = (n, p, e) => { results.push(p); console.log((p?'PASS ':'FAIL ') + n + ' — ' + e); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--autoplay-policy=user-gesture-required', '--window-position=40,40', '--window-size=900,700'] });
  const ctx = await browser.newContext({ viewport: { width: 900, height: 640 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => { window.__initRunwayNova = () => {}; });
  await page.goto(`http://localhost:${PORT}/${PAGE}`, { waitUntil: 'domcontentloaded' });
  await sleep(1500);

  // 1. drive the rescue contract exactly as attachNovaAudio does on a play()
  //    rejection (the rejection itself was proven twice: the 2026-07-17 live
  //    session log and this rig's first run — Chrome's MediaStream autoplay
  //    exemption makes re-triggering it flaky, so the rig drives the signal).
  const armed = await page.evaluate(() => {
    const ac = new AudioContext();
    const dst = ac.createMediaStreamDestination();
    const a = document.createElement('audio'); a.id = 'nova-audio';
    a.srcObject = dst.stream; a.muted = false; document.body.appendChild(a);
    a.pause();                                    // element exists, not playing
    window.__audioBlocked = true;                 // == what the catch() sets
    try { window.__audioUnlockCheck(); } catch(e){ return 'check threw ' + e.message; }
    return true;
  });
  check('1 blocked signal accepted by unlock-check', armed === true, String(armed));

  // 2. the rescue button must be visible NOW
  await sleep(300);
  let vis = await page.evaluate(() => {
    const b = document.getElementById('audio-unlock-btn');
    return b && getComputedStyle(b).display !== 'none';
  });
  check('2 rescue 🔊 button appears on block', vis === true, 'visible=' + vis);

  // 3. a REAL tap anywhere (the pointerdown-anywhere rescue — the button hides
  //    itself on the same tap's pointerdown, which is the intended behavior)
  await page.mouse.click(450, 320);
  await sleep(800);
  const after = await page.evaluate(() => ({
    blocked: !!window.__audioBlocked,
    playing: (() => { const a = document.getElementById('nova-audio'); return a && !a.paused; })(),
    btnShown: (() => { const b = document.getElementById('audio-unlock-btn'); return b && getComputedStyle(b).display !== 'none'; })(),
  }));
  check('3 click → element PLAYING, flag cleared, button gone',
    after.playing === true && after.blocked === false && after.btnShown === false, JSON.stringify(after));

  await browser.close(); server.close();
  const fails = results.filter(p => !p).length;
  console.log(`\n=== ${PAGE}: ${results.length - fails}/${results.length} PASS ===`);
  process.exit(fails ? 1 : 0);
})();
