/** Why is the Nova panel black when the pod is down? Dump the frame's children. */
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
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(800);
  await pg.click('#arrival-start-btn').catch(() => {});
  // wait for the voice-only reveal (avatar gate fires ~24s when the pod is down)
  await pg.waitForTimeout(42000);

  const out = await pg.evaluate(() => {
    const frame = document.getElementById('rec-avatar-frame');
    const dump = el => { if (!el) return null; const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
      return { id: el.id || el.className, display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
               bg: cs.backgroundImage.slice(0, 46) || cs.backgroundColor, w: Math.round(r.width), h: Math.round(r.height) }; };
    return {
      frameClasses: frame ? frame.className : 'MISSING',
      frameChildren: frame ? [...frame.children].map(dump) : [],
      faceFrame: dump(document.getElementById('nova-face-frame')),
      avatarMode: window.__avatarMode ?? null,
      hasStage: !!document.getElementById('nova-stage'),
      videoSrc: document.getElementById('rec-avatar-video')?.currentSrc || null,
    };
  });
  console.log(JSON.stringify(out, null, 2));
  await b.close(); server.close();
})();
