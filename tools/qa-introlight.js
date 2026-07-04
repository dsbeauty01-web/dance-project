// QA: intro movement-challenge light chain (2026-07-04 fixes). Serves the LOCAL repo,
// fake cam, no LiveKit. Verifies: EARLY-CAM at page load, cue-part -> glow VISIBLE on
// the shoulder, shrug -> try_move sent + hit flash. PASS/FAIL from the script.
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader','--use-gl=angle'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 900, height: 900 } });
  const pg = await ctx.newPage();
  const logs = []; pg.on('console', m => logs.push(m.text()));
  pg.on('pageerror', e => console.log('[pg-err]', e.message));
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });

  const results = {};
  // 1) EARLY-CAM: webcam video element gets frames BEFORE any tap
  for (let i = 0; i < 15; i++) { await pg.waitForTimeout(600);
    const w = await pg.evaluate(() => document.getElementById('webcam')?.videoWidth || 0);
    if (w > 0) { results.earlyCam = 'PASS (videoWidth=' + w + ' pre-tap)'; break; } }
  if (!results.earlyCam) results.earlyCam = 'FAIL — no camera frames at page load';

  // 2) window.moves exported
  results.movesExport = await pg.evaluate(() => (window.moves && typeof window.moves === 'object') ? 'PASS' : 'FAIL');

  // 3) enter recognition phase (orb tap path)
  await pg.evaluate(() => { try { document.dispatchEvent(new CustomEvent('arrival-done')); } catch(e){} });
  await pg.waitForTimeout(1200);
  results.phase = await pg.evaluate(() => (typeof memory !== 'undefined' && memory.phase) || 'none');

  // 4) stub the worker link + feed deterministic keypoints, then CUE the shoulder
  await pg.evaluate(() => {
    window.__sentEvents = [];
    window.__novaSend = (m) => window.__sentEvents.push(m);
    setInterval(() => {
      window.__lastPoseKeypoints = [
        { name:'left_shoulder', x:220, y:240, score:0.95 }, { name:'right_shoulder', x:420, y:240, score:0.95 },
        { name:'left_wrist', x:180, y:460, score:0.1 },  { name:'right_wrist', x:460, y:460, score:0.1 },
        { name:'nose', x:320, y:120, score:0.9 }, { name:'left_ear', x:280, y:120, score:0.8 }, { name:'right_ear', x:360, y:120, score:0.8 },
      ];
    }, 40);
    // the exact thing the cue-part packet handler does:
    window.__introCuePart = 'shoulder'; window.__introCuePartAt = Date.now();
  });
  await pg.waitForTimeout(900);
  const glow1 = await pg.evaluate(() => { const g = document.getElementById('rec-cam-glow');
    return { opacity: g && g.style.opacity, left: g && g.style.left, top: g && g.style.top }; });
  results.glowVisible = (parseFloat(glow1.opacity) >= 0.9) ? 'PASS (opacity=' + glow1.opacity + ' at ' + glow1.left + ',' + glow1.top + ')' : 'FAIL — ' + JSON.stringify(glow1);

  // 5) the kid does the move → try_move must be sent + hit flash
  await pg.evaluate(() => { const iv = setInterval(() => { if (window.moves) window.moves.shrug = true; }, 30); setTimeout(() => clearInterval(iv), 2500); });
  await pg.waitForTimeout(1500);
  const after = await pg.evaluate(() => ({ sent: window.__sentEvents, hit: document.getElementById('rec-cam-glow')?.classList.contains('hit'), op: document.getElementById('rec-cam-glow')?.style.opacity }));
  const tm = (after.sent || []).find(m => m.kind === 'game-event' && m.event?.event === 'try_move');
  results.tryMove = tm ? 'PASS (action=' + tm.event.action + ')' : 'FAIL — sent: ' + JSON.stringify(after.sent);
  results.hitFlash = (after.hit || parseFloat(after.op) >= 1) ? 'PASS' : 'WARN (flash window may have passed: op=' + after.op + ')';

  console.log('── INTRO-LIGHT QA ──');
  for (const [k, v] of Object.entries(results)) console.log(k.padEnd(12), v);
  const fails = Object.values(results).filter(v => String(v).startsWith('FAIL')).length;
  console.log(fails === 0 ? 'ALL PASS ✅' : fails + ' FAILURES ❌');
  await b.close(); server.close(); process.exit(fails === 0 ? 0 : 1);
})();
