// one-shot: screenshot the game picker (used for the PREGAMES-V1 5-card check)
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-app.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, {'Content-Type': MIME[path.extname(p).toLowerCase()]||'application/octet-stream'}); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const page = process.argv[2] || 'nova-app.html';
  const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions:['camera','microphone'], viewport:{width:1600,height:900} });
  const pg = await ctx.newPage();
  await pg.goto(`http://localhost:${port}/${page}?voiceonly`, {waitUntil:'domcontentloaded'});
  await pg.waitForTimeout(2500);
  await pg.evaluate(() => showPhase('phase-picker'));
  await pg.waitForTimeout(800);
  await pg.screenshot({ path: path.join(__dirname, 'pregames-out', 'picker-5cards.png') });
  await b.close(); server.close(); console.log('SHOT-OK');
})();
