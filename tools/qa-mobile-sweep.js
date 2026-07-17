// QA — MOBILE FULL-FLOW SWEEP (2026-07-17): every phase at phone sizes, EN+HE.
// Drives each phase with minimal state (fake cam via Chrome flags) and screenshots.
// Visual judgment is the human/agent step; this rig also asserts no page errors
// and no horizontal overflow per phase.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8856;
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
      const stat = fs.statSync(file);
      const range = req.headers.range;
      if (range) {
        const m = /bytes=(\d+)-(\d*)/.exec(range);
        const start = +m[1], end = m[2] ? +m[2] : stat.size - 1;
        res.writeHead(206, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
          'Content-Range': `bytes ${start}-${end}/${stat.size}`, 'Accept-Ranges': 'bytes',
          'Content-Length': end - start + 1 });
        return fs.createReadStream(file, { start, end }).pipe(res);
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const check = (n, p, e) => { results.push(p); console.log((p?'PASS ':'FAIL ') + n + (e?' — '+e:'')); };

// per-phase drivers run inside the page
const DRIVERS = {
  arrival:    `showPhase('phase-arrival')`,
  recognition:`showPhase('phase-recognition')`,
  picker:     `showPhase('phase-picker')`,
  transition: `showPhase('phase-transition'); try{ showPreDemo('joined'); }catch(e){}`,
  game:       `try{ setSelectedSong('joined'); }catch(e){}; showPhase('phase-game');
               try{ fitGamePanels(); }catch(e){}`,
  end:        `showPhase('phase-end')`,
};

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40'] });

  for (const [sizeName, vp] of [['390', { width: 390, height: 844 }], ['360', { width: 360, height: 640 }]]) {
    for (const lang of ['', 'he']) {
      const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: vp });
      const page = await ctx.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.addInitScript(() => { window.__initRunwayNova = () => {}; });
      await page.goto(`http://localhost:${PORT}/nova-app.html${lang ? '?lang=he' : ''}`, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => typeof showPhase === 'function', undefined, { timeout: 15000 });
      await sleep(1500);
      for (const [phase, drv] of Object.entries(DRIVERS)) {
        await page.evaluate(d => { try { eval(d); } catch(e){ console.log('drv err', e.message); } }, drv);
        await sleep(700);
        const tag = `${phase}-${sizeName}${lang ? '-he' : ''}`;
        await page.screenshot({ path: path.join(__dirname, `sweep/${tag}.png`) });
        const overflow = await page.evaluate(() =>
          document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
        check(`${tag} no horizontal overflow`, !overflow, '');
      }
      check(`errors ${sizeName}${lang ? '-he' : ''}`, errors.length === 0, errors.slice(0,2).join(' | ') || 'clean');
      await ctx.close();
    }
  }
  await browser.close(); server.close();
  const fails = results.filter(p => !p).length;
  console.log(`\n=== ${results.length - fails}/${results.length} PASS ===`);
  process.exit(fails ? 1 : 0);
})();
