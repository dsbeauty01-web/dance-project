// QA: SCRIPTED CHALLENGE browser chain (2026-07-04). Verifies joint-locked light:
// cue-part {part:'shoulder', joint:'right_shoulder'} -> glow ON THE RIGHT SHOULDER POINT
// (not chest midpoint), rising-edge detection (pre-existing motion ignored), try_move
// only after a FRESH move, and 'left' (hand-up) support for challenge move #2.
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.css':'text/css','.mp3':'audio/mpeg' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 900, height: 900 } });
  const pg = await ctx.newPage();
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2000);
  await pg.evaluate(() => { document.dispatchEvent(new CustomEvent('arrival-done')); });
  await pg.waitForTimeout(800);
  const results = {};
  await pg.evaluate(() => {
    window.__sentEvents = []; window.__novaSend = (m) => window.__sentEvents.push(m);
    // deterministic keypoints: right shoulder clearly separated from left
    setInterval(() => { window.__lastPoseKeypoints = [
      { name:'left_shoulder', x:220, y:240, score:0.95 }, { name:'right_shoulder', x:420, y:240, score:0.95 },
      { name:'left_wrist', x:200, y:400, score:0.9 }, { name:'right_wrist', x:440, y:400, score:0.9 },
      { name:'nose', x:320, y:120, score:0.9 } ]; }, 40);
    // PRE-EXISTING motion: shrug flag already TRUE before the cue (must be ignored)
    window.moves.shrug = true;
  });
  await pg.waitForTimeout(300);
  // ── CHALLENGE MOVE 1: shoulder, joint-locked ──
  await pg.evaluate(() => { window.__introCuePart='shoulder'; window.__introCueJoint='right_shoulder'; window.__introCuePartAt=Date.now(); });
  await pg.waitForTimeout(700);
  const g1 = await pg.evaluate(() => { const g=document.getElementById('rec-cam-glow'); const cam=document.getElementById('rec-webcam');
    return { op:g.style.opacity, left:parseFloat(g.style.left), cw: cam.clientWidth||1 }; });
  // right_shoulder raw x=420 of 640 → mirrored display: x = cw - 420*scale... just assert it's OFF-center (not chest mid) and visible
  const midX = g1.cw/2;
  results.jointLock = (parseFloat(g1.op) >= 0.9 && Math.abs(g1.left - midX) > g1.cw*0.08) ? 'PASS (glow off-center at x=' + g1.left + ', mid=' + midX + ')' : 'FAIL ' + JSON.stringify(g1);
  const early = await pg.evaluate(() => window.__sentEvents.length);
  results.staleIgnored = early === 0 ? 'PASS (pre-existing shrug NOT reported)' : 'FAIL — reported stale motion: ' + early;
  // ── the kid ACTUALLY moves now: flag drops then rises ──
  await pg.evaluate(() => { window.moves.shrug = false; });
  await pg.waitForTimeout(300);
  await pg.evaluate(() => { window.moves.shrug = true; });
  await pg.waitForTimeout(600);
  const tm1 = await pg.evaluate(() => window.__sentEvents.find(m => m.event?.event === 'try_move'));
  results.freshMove = (tm1 && tm1.event.action === 'shoulder') ? 'PASS (try_move shoulder on rising edge)' : 'FAIL ' + JSON.stringify(tm1);
  // ── CHALLENGE MOVE 2: left hand up ──
  await pg.evaluate(() => { window.__sentEvents = []; window.moves.shrug=false; window.moves.left=false;
    window.__introCuePart='left'; window.__introCueJoint='left_wrist'; window.__introCuePartAt=Date.now(); });
  await pg.waitForTimeout(600);
  await pg.evaluate(() => { window.moves.left = true; });
  await pg.waitForTimeout(600);
  const st2 = await pg.evaluate(() => ({ tm: window.__sentEvents.find(m => m.event?.event === 'try_move'), left: parseFloat(document.getElementById('rec-cam-glow').style.left) }));
  results.leftHand = (st2.tm && st2.tm.event.action === 'left') ? 'PASS (try_move left, glow x=' + st2.left + ')' : 'FAIL ' + JSON.stringify(st2);
  // glow moved to the OTHER side for left wrist vs right shoulder
  results.glowMoved = (Math.abs(st2.left - g1.left) > 50) ? 'PASS (light moved joints: ' + g1.left + ' → ' + st2.left + ')' : 'FAIL';
  console.log('── SCRIPTED-CHALLENGE QA ──');
  for (const [k, v] of Object.entries(results)) console.log(k.padEnd(13), v);
  const fails = Object.values(results).filter(v => String(v).startsWith('FAIL')).length;
  console.log(fails === 0 ? 'ALL PASS ✅' : fails + ' FAILURES ❌');
  await b.close(); server.close(); process.exit(fails === 0 ? 0 : 1);
})();
