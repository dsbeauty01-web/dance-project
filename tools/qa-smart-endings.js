/*
 * qa-smart-endings.js — screenshot the shared Smart Ending for every game.
 * Uses playwright-core + installed Chrome (same pattern as the other rigs).
 * Serves the repo root statically so /tools/endings-preview.html loads /nova-ending.js.
 *
 *   node tools/qa-smart-endings.js
 * Outputs tools/end-<game>.png (faces stage) + tools/end-<game>-hook.png (hook stage).
 */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');

const ROOT = path.join(__dirname, '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.json': 'application/json', '.mp3': 'audio/mpeg', '.css': 'text/css' };

const GAMES = [
  { game: 'joined', name: 'Maya', best: 'that RIB slide — you SNAPPED it 4 times in a row!' },
  { game: 'hello', name: 'Sam', best: 'your BIG hello wave — the whole room felt it!' },
  { game: 'wave', name: 'Leo', best: 'that GIANT arm wave — smooth like water!' },
  { game: 'wavemagic', name: 'Ari', best: 'both hands sparkling right on the beat — MAGIC!' },
  { game: 'freeze', name: null, best: 'that FLAMINGO freeze — 4.2 seconds of pure STATUE!' },
  { game: 'bounce', name: 'Noa', best: 'your bounce landed ON the beat every single time!' },
  { game: 'joined', name: 'Dana', best: '', label: 'zero-check' },   // no data -> presence, NEVER a zero
];

function serve() {
  return http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    const fp = path.join(ROOT, p);
    fs.readFile(fp, (e, data) => {
      if (e) { res.writeHead(404); res.end('nf'); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
      res.end(data);
    });
  });
}

(async () => {
  const srv = serve();
  await new Promise(r => srv.listen(0, r));
  const port = srv.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await b.newPage({ viewport: { width: 900, height: 1000 } });
  page.on('console', m => { if (m.type() === 'error') console.log('  [console.error]', m.text()); });
  page.on('pageerror', e => console.log('  [PAGEERROR]', e.message));

  const results = [];
  for (const g of GAMES) {
    const tag = g.label || g.game;
    const qs = new URLSearchParams({ game: g.game, lang: 'en' });
    if (g.name) qs.set('name', g.name);
    qs.set('best', g.best);   // present (maybe empty) -> exercises presence fallback when empty
    const url = `http://localhost:${port}/tools/endings-preview.html?${qs}`;
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction('window.__endingReady === true');
    // faces stage: her moment + ask + 3 faces are in
    await page.waitForSelector('#nova-ending .ne-face', { timeout: 4000 });
    await page.waitForTimeout(400);
    const moment = await page.textContent('#nova-ending .ne-moment');
    const faceCount = await page.$$eval('#nova-ending .ne-face', els => els.length);
    // NO-ZERO assertion: the visible ending text must contain no "0 pts"/"0 of"/bare zero score
    const bodyText = await page.textContent('#nova-ending');
    const hasZero = /\b0\s*(pts|points|of)\b/i.test(bodyText) || /\bscore\b/i.test(bodyText);
    await page.screenshot({ path: path.join(__dirname, `end-${tag}.png`) });

    // hook stage: tap the love face, wait through "tell me one thing" to the hook
    const faces = await page.$$('#nova-ending .ne-face');
    if (faces[0]) await faces[0].click();
    await page.waitForSelector('#nova-ending .ne-hook.in', { timeout: 9000 }).catch(() => {});
    await page.waitForTimeout(300);
    const hook = await page.textContent('#nova-ending .ne-hook');
    const btns = await page.$$eval('#nova-ending .ne-btn', els => els.map(e => e.textContent));
    await page.screenshot({ path: path.join(__dirname, `end-${tag}-hook.png`) });

    results.push({ tag, faces: faceCount, hasZero, moment: (moment || '').trim(), hook: (hook || '').trim(), buttons: btns });
    console.log(`✓ ${tag.padEnd(11)} faces=${faceCount} zero=${hasZero ? 'FAIL' : 'ok'} btns=${btns.length}`);
    console.log(`    moment: ${(moment || '').trim()}`);
    console.log(`    hook:   ${(hook || '').trim()}  buttons: ${JSON.stringify(btns)}`);
  }

  await b.close(); srv.close();
  const anyZero = results.some(r => r.hasZero);
  const allFaces = results.every(r => r.faces === 3);
  const allBtns = results.every(r => r.buttons.length === 2);
  console.log('\n=== SUMMARY ===');
  console.log('no zeros anywhere :', anyZero ? 'FAIL' : 'PASS');
  console.log('3 faces every game:', allFaces ? 'PASS' : 'FAIL');
  console.log('exactly 2 buttons :', allBtns ? 'PASS' : 'FAIL');
  fs.writeFileSync(path.join(__dirname, 'smart-endings-qa.json'), JSON.stringify(results, null, 2));
  process.exit(anyZero || !allFaces || !allBtns ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
