// QA: pause/resume 3-2-1 + chat input wiring (2026-07-06)
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
  const R = {};
  await pg.goto(`http://localhost:${port}/nova-joined.html?nonova&game=joined`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(6000);   // nonova auto-starts the game
  // ── chat wiring ──
  R.chatGlobals = await pg.evaluate(() => typeof window.sendChat === 'function' && typeof window.toggleMic === 'function' ? 'PASS' : 'FAIL');
  R.chatSend = await pg.evaluate(() => {
    window.__sent = []; window.__novaSend = m => window.__sent.push(m);
    const inp = document.getElementById('rec-input'); if (!inp) return 'FAIL no input';
    inp.value = 'hello nova test';
    window.sendChat();
    const ok = window.__sent.some(m => m.kind === 'user-said' && /hello nova test/.test(m.text));
    return ok ? 'PASS (user-said packet sent)' : 'FAIL — sent: ' + JSON.stringify(window.__sent);
  });
  // ── pause ──
  await pg.waitForTimeout(4000);
  const p1 = await pg.evaluate(() => { window.togglePauseGame(); const a = window.__songAudio, v = document.getElementById('nova-video');
    return { audioPaused: a && a.paused, vidPaused: v ? v.paused : null, overlay: document.getElementById('pause-overlay').classList.contains('show'),
             btn: document.getElementById('game-pause-btn').textContent, t: a && a.currentTime }; });
  R.pause = (p1.audioPaused && p1.overlay && p1.btn === '▶') ? `PASS (audio+overlay, clip paused=${p1.vidPaused})` : 'FAIL ' + JSON.stringify(p1);
  await pg.waitForTimeout(1500);
  const frozen = await pg.evaluate(() => window.__songAudio.currentTime);
  R.clockFrozen = Math.abs(frozen - p1.t) < 0.05 ? 'PASS (music clock frozen)' : 'FAIL drift ' + (frozen - p1.t);
  // ── resume with 3-2-1 ──
  await pg.evaluate(() => window.togglePauseGame());
  await pg.waitForTimeout(400);
  const counting = await pg.evaluate(() => ({ counting: document.getElementById('pause-overlay').classList.contains('counting'),
    num: document.getElementById('pause-count').textContent }));
  await pg.waitForTimeout(2600);
  const after = await pg.evaluate(() => ({ playing: !window.__songAudio.paused, overlay: document.getElementById('pause-overlay').classList.contains('show'),
    btn: document.getElementById('game-pause-btn').textContent }));
  R.resume = (counting.counting && after.playing && !after.overlay && after.btn === '⏸') ? `PASS (counted from ${counting.num}, playing again)` : 'FAIL ' + JSON.stringify({counting, after});
  await pg.screenshot({ path: path.join(__dirname, 'shot-pause.png') });
  console.log('── PAUSE+CHAT QA ──'); for (const [k, v] of Object.entries(R)) console.log(k.padEnd(12), v);
  const fails = Object.values(R).filter(v => String(v).startsWith('FAIL')).length;
  console.log(fails === 0 ? 'ALL PASS ✅' : fails + ' FAILURES ❌');
  await b.close(); server.close(); process.exit(fails ? 1 : 0);
})();
