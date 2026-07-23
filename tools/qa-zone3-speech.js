// QA — ZONE 3: SPEECH COLLISION — one mouth, a queue, a drop rule (delicate-zones)
// Proves the SpeechArbiter on nova-commercial.html:
//   1. bakedActiveAt() oracle honours the ±300ms margin both sides of a baked window.
//   2. a local reaction plays when the mouth is free.
//   3. one mouth — while a reaction plays, a new one is QUEUED, never started on top.
//   4. queue holds max ONE, newest wins, older dropped WITH a log line (no stacking).
//   5. a baked window starting mid-reaction FADES it out in 150ms (baked wins), no overlap.
//   6. the queued reaction DRAINS once the baked window passes.
// Driven deterministically: __gamePos is stubbed to controlled positions and reactions
// are synthetic {start/stop} probes, so the logic is proven without real TTS/audio.
// Usage:  NODE_PATH=$(npm root -g) node tools/qa-zone3-speech.js [file]
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const FILE = process.argv[2] || 'nova-commercial.html';
const Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg','.riv':'application/octet-stream','.wav':'audio/wav','.y4m':'video/x-yuv4mpeg' };

const results = [];
const check = (name, pass, detail) => { results.push({ name, pass: !!pass, detail: detail || '' });
  console.log(`  ${pass ? 'PASS' : 'FAIL'} · ${name}${detail ? ' — ' + detail : ''}`); };

(async () => {
  const server = http.createServer((q, r) => {
    let p = decodeURIComponent(q.url.split('?')[0]); const fp = path.join(ROOT, p);
    fs.stat(fp, (e, st) => {
      if (e || !st.isFile()) { r.writeHead(404); return r.end(); }
      const type = MIME[path.extname(p).toLowerCase()] || 'application/octet-stream';
      const range = q.headers.range;
      if (range) {
        const m = /bytes=(\d*)-(\d*)/.exec(range) || [];
        const start = m[1] ? parseInt(m[1], 10) : 0, end = m[2] ? parseInt(m[2], 10) : st.size - 1;
        r.writeHead(206, { 'Content-Type': type, 'Accept-Ranges': 'bytes',
          'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Content-Length': end - start + 1 });
        fs.createReadStream(fp, { start, end }).pipe(r);
      } else {
        r.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': st.size });
        fs.createReadStream(fp).pipe(r);
      }
    });
  });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;

  const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--window-size=1400,820',
    '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--use-file-for-fake-video-capture=' + Y4M,
    '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1400, height: 800 } });
  const page = await ctx.newPage();
  const speechLog = [];
  page.on('console', m => { const t = m.text(); if (/\[SPEECH\]/.test(t)) speechLog.push(t); });
  page.on('pageerror', e => console.log('  [pageerror] ' + e.message));

  try {
    await page.goto(`http://localhost:${port}/${FILE}?nonova&game=wavemagic`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-game', undefined, { timeout: 60000 });
    await page.waitForFunction(() => window.__speech && window.__gamePos, undefined, { timeout: 30000 });
    console.log('  game running; speech arbiter present');

    // configure a known baked window and take over the clock deterministically
    const suite = await page.evaluate(() => {
      const S = window.__speech;
      const realGamePos = window.__gamePos;
      let POS = 0; window.__gamePos = () => POS;          // deterministic clock
      const setPos = p => { POS = p; };
      const mk = (label) => ({ label, started: false, faded: null, _done: false,
        start() { this.started = true; },
        stop(ms) { this.faded = ms; this._finish(); },
        _finish() { if (this._done) return; this._done = true; window.__speech.done(this); } });

      S.reset(); S.setBaked([{ start: 10, end: 14 }]);
      const out = {};

      // 1) margin oracle (±0.3s)
      out.margin = {
        justBefore: !!S.bakedActiveAt(9.75),   // 9.75 >= 10-0.3 → active
        clearBefore: !!S.bakedActiveAt(9.6),    // outside
        justAfter: !!S.bakedActiveAt(14.25),    // <= 14+0.3 → active
        clearAfter: !!S.bakedActiveAt(14.4),    // outside
        inside: !!S.bakedActiveAt(12),
      };

      // 2) plays when mouth free
      S.reset(); setPos(5);
      const free = mk('free'); const playedFree = S.request(free);
      out.playsFree = playedFree === true && free.started === true;

      // 3) one mouth — new request while one plays is queued, not started
      const second = mk('second'); const playedSecond = S.request(second);
      out.oneMouth = playedSecond === false && second.started === false && S._playing === free;

      // 5) collision fade — baked window starts while 'free' is playing
      setPos(10.1);
      S.onTick(10.1);
      out.fade = { faded: free.faded, playingCleared: S._playing === null };

      // after the fade, 'second' was pending; but we're still inside the baked window,
      // so it must NOT drain yet (mouth still baked-busy)
      out.heldDuringBaked = S._pending === second && second.started === false;

      // 6) drain once the window passes
      setPos(15); S.onTick(15);
      out.drained = second.started === true && S._pending === null;

      // 4) queue max ONE, newest wins, older dropped — inside a baked window
      S.reset(); setPos(11);
      const rA = mk('rA'); S.request(rA);          // queued (baked-busy)
      const rB = mk('rB'); S.request(rB);          // should DROP rA, keep rB
      out.newestWins = S._pending === rB && rA.started === false && rB.started === false;

      window.__gamePos = realGamePos;              // restore the real clock
      return out;
    });

    check('bakedActiveAt honours ±300ms margin (both sides)',
      suite.margin.justBefore && !suite.margin.clearBefore && suite.margin.justAfter && !suite.margin.clearAfter && suite.margin.inside,
      JSON.stringify(suite.margin));
    check('reaction plays when the mouth is free', suite.playsFree);
    check('one mouth — a second reaction is queued, never started on top', suite.oneMouth);
    check('baked window mid-reaction fades it out in 150ms (baked wins)',
      suite.fade.faded === 150 && suite.fade.playingCleared, `faded=${suite.fade.faded}`);
    check('queued reaction is HELD while the baked window is active', suite.heldDuringBaked);
    check('queued reaction drains once the baked window passes', suite.drained);
    check('queue holds max ONE, newest wins (older dropped)', suite.newestWins);
    check('the dropped reaction was logged (no silent stacking)',
      speechLog.some(l => /drop stale 'rA' — newest wins/.test(l)), `${speechLog.length} SPEECH log lines`);
    check('the baked-collision fade was logged', speechLog.some(l => /baked wins/.test(l)));

  } catch (e) {
    check('harness ran to completion', false, e.message);
  } finally {
    await ctx.close(); await b.close(); server.close();
  }

  const passed = results.filter(r => r.pass).length, total = results.length;
  console.log(`\nZONE 3 — SPEECH COLLISION: ${passed}/${total} PASS`);
  console.log(passed === total ? 'RESULT: PASS ✅' : 'RESULT: FAIL ❌ (' + results.filter(r=>!r.pass).map(r=>r.name).join('; ') + ')');
  process.exit(passed === total ? 0 : 1);
})();
