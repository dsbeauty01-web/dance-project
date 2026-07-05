// QA: 50/50 magic-stage layout in the game phase (?nonova&game=joined is a playable
// standalone game). Measures panel widths + screenshots for eyeballing.
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.css':'text/css','.mp3':'audio/mpeg' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1600, height: 900 } });
  const pg = await ctx.newPage();
  await pg.goto(`http://localhost:${port}/nova-joined.html?nonova&game=joined`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(7000);   // nonova auto-starts the game after 700ms + video load
  const m = await pg.evaluate(() => {
    const n = document.getElementById('nova-side'), c = document.getElementById('cam-side');
    const nv = document.getElementById('nova-video');
    return { nova: n && n.clientWidth, cam: c && c.clientWidth,
             fit: nv && getComputedStyle(nv).objectFit,
             stage: n && getComputedStyle(n).backgroundImage.includes('radial-gradient'),
             visible: n && n.offsetParent !== null };
  });
  const ratio = m.nova && m.cam ? (m.nova / (m.nova + m.cam) * 100).toFixed(1) : '?';
  console.log('panels:', JSON.stringify(m), '→ nova share:', ratio + '%');
  await pg.screenshot({ path: path.join(__dirname, 'shot-stage-5050.png') });
  const ok = m.visible && Math.abs(m.nova - m.cam) <= 12 && m.fit === 'contain' && m.stage;
  console.log(ok ? 'LAYOUT PASS ✅ (50/50, contain, stage backdrop)' : 'LAYOUT FAIL ❌');
  await b.close(); server.close(); process.exit(ok ? 0 : 1);
})();
