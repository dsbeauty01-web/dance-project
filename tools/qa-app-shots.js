// QA — nova-app commercial polish shots: phone + desktop, EN + HE, arrival/picker,
// debug-gate check. Local server, no worker needed.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8854;
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
  '.mp4':'video/mp4', '.mp3':'audio/mpeg', '.png':'image/png', '.jpg':'image/jpeg' };
function startServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/nova-app.html';
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
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40'] });

  const shots = [
    { name: 'app-phone-arrival',    vp: { width: 390, height: 844 }, q: '',         drive: null },
    { name: 'app-phone-arrival-he', vp: { width: 390, height: 844 }, q: '?lang=he', drive: null },
    { name: 'app-phone-picker',     vp: { width: 390, height: 844 }, q: '',         drive: 'picker' },
    { name: 'app-phone-picker-he',  vp: { width: 390, height: 844 }, q: '?lang=he', drive: 'picker' },
    { name: 'app-desk-arrival',     vp: { width: 1400, height: 800 }, q: '',        drive: null },
    { name: 'app-desk-debug',       vp: { width: 1400, height: 800 }, q: '?debug=1', drive: null },
    { name: 'app-phone-legal',      vp: { width: 390, height: 844 }, q: '',         drive: 'legal' },
    { name: 'app-phone-legal-he',   vp: { width: 390, height: 844 }, q: '?lang=he', drive: 'legal' },
  ];
  for (const s of shots) {
    const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: s.vp });
    const page = await ctx.newPage();
    await page.addInitScript(() => { window.__initRunwayNova = () => {}; });
    await page.goto(`http://localhost:${PORT}/nova-app.html${s.q}`, { waitUntil: 'domcontentloaded' });
    await sleep(2000);
    if (s.drive === 'picker') { await page.evaluate(() => { try { showPhase('phase-picker'); } catch(e){} }); await sleep(600); }
    if (s.drive === 'legal')  { await page.evaluate(() => { try { showLegal('privacy'); } catch(e){} }); await sleep(600); }
    await page.screenshot({ path: path.join(__dirname, `shot-${s.name}.png`) });
    // debug-gate + hebrew facts on the plain-load shots
    if (!s.drive) {
      const f = await page.evaluate(() => ({
        vbanner: (() => { const e = document.getElementById('vbanner'); return e && getComputedStyle(e).display !== 'none'; })(),
        logActions: (() => { const e = document.getElementById('log-actions'); return e && getComputedStyle(e).display !== 'none'; })(),
        debugPanel: (() => { const e = document.getElementById('debug-panel'); return e && getComputedStyle(e).display !== 'none'; })(),
        lang: document.documentElement.lang, dir: document.documentElement.dir,
        tagline: (document.getElementById('arrival-tagline') || {}).textContent,
        aiNote: (document.getElementById('ai-note') || {}).textContent,
      }));
      console.log(s.name, JSON.stringify(f));
    } else console.log(s.name, 'shot taken');
    await ctx.close();
  }
  await browser.close(); server.close();
})();
