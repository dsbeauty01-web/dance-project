// QA: typed chat against the REAL worker (2026-07-08) — repro "text not reached her".
// Full live intro (no ?nonova), fake cam+mic; types at 3 moments: name beat,
// challenge, after picker. Captures every console line on the typed path.
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const pg = await (await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1400, height: 900 } })).newPage();
  const t0 = Date.now(); const rel = () => ((Date.now()-t0)/1000).toFixed(1).padStart(5);
  pg.on('console', (m) => {
    const t = m.text();
    if (/TYPE|kid input|user-said|queued|flushed|CLIP ▶|V2V|reveal|GO-PICKER|go-picker|picker|badge|novaSend|ERROR|STT-ECHO|stt-echo/i.test(t) && !/POSE|telemetry/.test(t))
      console.log(`[C]${rel()} ${t.slice(0, 150)}`);
  });
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2500);
  await pg.mouse.click(700, 450);   // orb tap
  console.log(`[T]${rel()} tapped orb`);

  const typeNow = async (label, text) => {
    const st = await pg.evaluate((txt) => {
      const inp = document.getElementById('rec-input');
      const vis = inp && inp.offsetParent !== null;
      const phase = (typeof memory !== 'undefined' && memory) ? memory.phase : '?';
      const room = !!window.__novaRoom, v2v = !!window.__V2V;
      const pend = (window.__pendingTyped || []).length;
      if (inp) { inp.value = txt; try { window.sendChat(); } catch (e) { return { err: e.message }; } }
      return { vis, phase, room, v2v, pend, hasInput: !!inp };
    }, text);
    console.log(`[T]${rel()} TYPED "${text}" @${label} → ${JSON.stringify(st)}`);
  };

  await pg.waitForTimeout(20000); await typeNow('name-beat', 'im bobo');
  await pg.waitForTimeout(15000); await typeNow('challenge', 'can you hear me');
  await pg.waitForTimeout(35000); await typeNow('late/picker', 'hello are you there');
  await pg.waitForTimeout(15000);
  const fin = await pg.evaluate(() => ({ pend: (window.__pendingTyped || []).length, phase: (typeof memory!=='undefined'&&memory)?memory.phase:'?', room: !!window.__novaRoom }));
  console.log(`[T]${rel()} FINAL ${JSON.stringify(fin)}`);
  await b.close(); server.close(); process.exit(0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
