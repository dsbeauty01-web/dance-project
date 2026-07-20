/** Which phase functions are reachable from window? (multiple script blocks, some module-scoped) */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project';
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r));
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader'] });
  const pg = await b.newPage();
  await pg.goto(`http://localhost:${server.address().port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(1500);
  const out = await pg.evaluate(() => {
    const names = ['goToPicker','pickGame','startCountdown','startGame','endGame','exitGame','showPhase',
                   'setAvatarCloseup','__startTransition','__setNovaState','toggleMic','_toggleMic','pickerBack','playAgainNow'];
    const r = {};
    for (const n of names) r[n] = typeof window[n];
    return r;
  });
  console.log(JSON.stringify(out, null, 2));
  await b.close(); server.close();
})();
