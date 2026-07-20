/** Picker shots at desktop + phone, EN and HE, with card/emoji/overflow audit. */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', SCR = __dirname;
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'] });

  for (const [label, w, h, q] of [['desk', 1366, 768, ''], ['wide', 1920, 1080, ''], ['phone', 412, 915, ''], ['he', 1366, 768, '?lang=he']]) {
    const pg = await b.newPage(); await pg.setViewportSize({ width: w, height: h });
    await pg.goto(`http://localhost:${port}/nova-joined.html${q}`, { waitUntil: 'domcontentloaded' });
    await pg.waitForTimeout(1200);
    // jump straight to the picker — no need to walk the intro
    await pg.evaluate(() => { if (typeof window.goToPicker === 'function') window.goToPicker(); });
    await pg.waitForTimeout(2500);
    const info = await pg.evaluate(() => {
      const cards = [...document.querySelectorAll('.picker-card')];
      const emo = cards.map(c => c.querySelector('.picker-emoji')?.textContent.trim());
      const names = cards.map(c => c.querySelector('.picker-name')?.textContent.trim());
      const subtext = cards.reduce((n, c) => n + c.querySelectorAll('.picker-tag,.picker-desc').length, 0);
      const recIdx = cards.findIndex(c => c.classList.contains('recommended'));
      const rects = cards.map(c => { const r = c.getBoundingClientRect(); return { t: Math.round(r.top), l: Math.round(r.left) }; });
      const rows = [...new Set(rects.map(r => r.t))].length;
      return { count: cards.length, emo, names, uniqueEmo: new Set(emo).size === emo.length,
               subtext, recIdx, recLabel: cards[recIdx]?.getAttribute('data-pick-label') || null, rows,
               sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
               pickerActive: !!document.querySelector('#phase-picker.active'),
               subtitle: document.getElementById('picker-subtitle')?.textContent.trim() };
    });
    console.log(label.padEnd(6), JSON.stringify(info));
    await pg.screenshot({ path: path.join(SCR, `picker-v114-${label}.png`) });
    await pg.close();
  }
  await b.close(); server.close();
})();
