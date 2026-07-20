/**
 * Watches the REAL readiness path (no force-clearing): which gates stamp, how
 * long handoffFromIntro() takes, and whether the intro overlay clears on its own
 * or only via the 30s safety at nova-joined.html:6272.
 */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', SCR = __dirname;
const Y4M = path.join(SCR, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav' };

(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;

  const args = ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader','--use-gl=angle'];
  if (fs.existsSync(Y4M)) args.push('--use-file-for-fake-video-capture=' + Y4M);
  const b = await chromium.launch({ channel: 'chrome', headless: true, args });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1366, height: 768 } });
  const pg = await ctx.newPage();

  const interesting = /GATE|BODY|INTRO|safety|handoff|reveal|avatar|stream/i;
  const t0 = Date.now();
  pg.on('console', m => { const t = m.text(); if (interesting.test(t)) console.log(`  +${((Date.now()-t0)/1000).toFixed(1)}s ${t.slice(0, 150)}`); });

  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(800);
  await pg.click('#arrival-start-btn').catch(() => {});
  console.log('--- arrival tapped, watching the real readiness path for 65s ---');

  let clearedAt = null;
  for (let i = 0; i < 65; i++) {
    await pg.waitForTimeout(1000);
    const clear = await pg.evaluate(() => {
      const ov = document.getElementById('intro-overlay');
      if (!ov) return true;
      const cs = getComputedStyle(ov);
      return !ov.classList.contains('show') || cs.display === 'none' || cs.opacity === '0';
    });
    if (clear) { clearedAt = i + 1; break; }
  }

  const final = await pg.evaluate(() => ({
    gates: window.__gateStamps || window.__gates || null,
    handoffStarted: !!window.__handoffStarted,
    greeted: !!window._greeted,
    revealAt: window.__revealAt || null,
    avatarMode: window.__avatarMode || null,
    hasStage: !!document.getElementById('nova-stage'),
    danceBtnReady: !!document.querySelector('#rec-dance-btn.ready'),
    phase: [...document.querySelectorAll('.phase.active')].map(p => p.id),
    phaseLog: window.__phaseLog || [],
  }));

  console.log('\n=== RESULT ===');
  console.log('overlay cleared naturally at:', clearedAt ? clearedAt + 's' : 'NEVER within 65s');
  console.log(JSON.stringify(final, null, 2));
  await pg.screenshot({ path: path.join(SCR, 'gate-timing.png') });
  await b.close(); server.close();
})();
