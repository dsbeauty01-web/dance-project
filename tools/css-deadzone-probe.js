/**
 * Checks whether the .nova-state-badge / #rec-avatar-frame.closeup rules
 * actually reach the browser, or are swallowed by the unterminated
 * @keyframes loadDot block at nova-joined.html:407.
 */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project';
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav','.svg':'image/svg+xml' };

(async () => {
  const server = http.createServer((q, r) => {
    let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => {
      if (e) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d);
    });
  });
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;

  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader'] });
  const pg = await b.newPage();
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(600);

  const out = await pg.evaluate(() => {
    const res = {};

    // 1. Does the badge rule apply? position:absolute + the radius are unique to it.
    const badge = document.getElementById('rec-state-badge');
    if (badge) {
      const cs = getComputedStyle(badge);
      res.badge = { position: cs.position, borderRadius: cs.borderRadius, background: cs.backgroundColor, display: cs.display };
    } else res.badge = 'ELEMENT MISSING';

    // 2. Does .closeup change the frame width?
    const f = document.getElementById('rec-avatar-frame');
    if (f) {
      const before = getComputedStyle(f).borderColor;
      f.classList.add('closeup');
      const after = getComputedStyle(f).borderColor;
      f.classList.remove('closeup');
      res.closeupChangesBorder = before !== after;
      res.borderBefore = before; res.borderAfter = after;
    }

    // 3. Ask the CSSOM directly: is .nova-state-badge a top-level rule anywhere?
    let topLevelBadgeRules = 0, keyframeNames = [];
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules; } catch { continue; }
      for (const r of rules) {
        if (r.type === CSSRule.STYLE_RULE && r.selectorText && r.selectorText.includes('nova-state-badge')) topLevelBadgeRules++;
        if (r.type === CSSRule.KEYFRAMES_RULE) keyframeNames.push(r.name + '(' + r.cssRules.length + ' steps)');
      }
    }
    res.topLevelBadgeRules = topLevelBadgeRules;
    res.keyframes = keyframeNames;

    // SCOPE CHECK: #game-state-badge must stay exactly as it was (unstyled),
    // because the intro redesign is not allowed to change the game phase.
    const gb = document.getElementById('game-state-badge');
    if (gb) {
      const g = getComputedStyle(gb);
      res.gameBadge = { position: g.position, borderRadius: g.borderRadius, background: g.backgroundColor, display: g.display };
    } else res.gameBadge = 'ELEMENT MISSING';
    return res;
  });

  console.log(JSON.stringify(out, null, 2));
  await b.close(); server.close();
})();
