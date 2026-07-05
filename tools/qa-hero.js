const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1600, height: 900 } });
  const pg = await ctx.newPage();
  await pg.goto(`http://localhost:${port}/nova-joined.html?nonova&game=hello`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(9000);
  await pg.screenshot({ path: path.join(__dirname, 'shot-hero-head.png'), clip: { x: 0, y: 0, width: 800, height: 900 } });
  console.log('shot saved');
  await b.close(); server.close();
})();
