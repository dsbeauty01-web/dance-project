// QA — ZONE 2: DUCKING IS A REFCOUNT, NOT A BOOLEAN (delicate-zones, commercial-v1)
// Proves the one ducking engine on nova-commercial.html:
//   1. restore ONLY at zero — a source ending while another still speaks does NOT
//      un-duck (the boolean bug); two overlapping sources don't get stuck down.
//   2. the spec test — a live source acquired 200ms before a baked line ends keeps
//      the MUSIC ducked through both, then restores ONCE (no pump) — measured on the
//      real #nova-video.volume glide (gameTick is the single writer).
//   3. guaranteed release — an un-released source auto-releases after maxMs + 1s.
//   4. implicit level sources (her live voice / clip playback) still count.
// Usage:  NODE_PATH=$(npm root -g) node tools/qa-zone2-duck.js [file]
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
    let p = decodeURIComponent(q.url.split('?')[0]);
    const fp = path.join(ROOT, p);
    fs.stat(fp, (e, st) => {
      if (e || !st.isFile()) { r.writeHead(404); return r.end(); }
      const type = MIME[path.extname(p).toLowerCase()] || 'application/octet-stream';
      const range = q.headers.range;
      if (range) {
        const m = /bytes=(\d*)-(\d*)/.exec(range) || [];
        const start = m[1] ? parseInt(m[1], 10) : 0;
        const end = m[2] ? parseInt(m[2], 10) : st.size - 1;
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
  page.on('pageerror', e => console.log('  [pageerror] ' + e.message));

  try {
    await page.goto(`http://localhost:${port}/${FILE}?nonova&game=wavemagic`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-game', undefined, { timeout: 60000 });
    await page.waitForFunction(() => window.__duck && window.__gamePos && window.__gamePos() > 0.6, undefined, { timeout: 30000 });
    console.log('  game running; duck engine present');

    // TEST 1 — restore ONLY at zero (pure refcount semantics, no timing)
    const rc = await page.evaluate(() => {
      const D = window.__duck; D.reset();
      const base = D.base, ducked = +(D.base * D.depth).toFixed(4);
      const t0 = +D.target().toFixed(4);                 // idle → base
      D.acquire('baked', 20000);
      const t1 = +D.target().toFixed(4);                 // one source → ducked
      D.acquire('live', 20000);
      const t2 = +D.target().toFixed(4);                 // two sources → still ducked
      D.release('baked');                                // baked ends first…
      const t3 = +D.target().toFixed(4);                 // …live still holds → STILL ducked (the whole point)
      D.release('live');
      const t4 = +D.target().toFixed(4);                 // zero → restored
      D.reset();
      return { base, ducked, t0, t1, t2, t3, t4 };
    });
    check('idle target = base (un-ducked)', Math.abs(rc.t0 - rc.base) < 1e-3, `t0=${rc.t0} base=${rc.base}`);
    check('one source ducks; a second holds ducked', rc.t1 === rc.ducked && rc.t2 === rc.ducked, `t1=${rc.t1} t2=${rc.t2}`);
    check('source ending while another speaks does NOT un-duck', rc.t3 === rc.ducked, `t3=${rc.t3} (ducked=${rc.ducked})`);
    check('restores to base only when count hits zero', Math.abs(rc.t4 - rc.base) < 1e-3, `t4=${rc.t4}`);

    // TEST 2 — THE SPEC TEST on real volume: live acquired 200ms before baked ends →
    // music stays ducked through both, restores ONCE, no pump. Sample #nova-video.volume.
    const pump = await page.evaluate(async () => {
      const D = window.__duck; const v = document.getElementById('nova-video');
      D.reset();
      const base = D.base, ducked = D.base * D.depth;
      const samples = [];
      let running = true;
      const iv = setInterval(() => samples.push({ t: performance.now(), vol: v.volume }), 40);
      const wait = ms => new Promise(r => setTimeout(r, ms));

      D.acquire('baked', 8000);           // baked line starts
      await wait(1800);                    // glide settles to ducked (headless gameTick throttles, so allow the full down-glide)
      const settledIdx = samples.length;   // mark: from here music is held down
      D.acquire('live', 8000);             // live reaction fires 200ms before baked ends
      await wait(200);
      D.release('baked');                  // baked line ends — but live still talking
      const releaseAIdx = samples.length;
      await wait(400);                     // <-- if boolean-buggy, music would pump UP here
      D.release('live');                   // now everything done
      await wait(2500);                    // glide restores to base (headless gameTick can throttle, so allow more)
      running = false; clearInterval(iv);

      // held window = from settled(after baked dip) until live released
      const held = samples.slice(settledIdx, releaseAIdx + Math.round(400/40));
      const heldMax = Math.max(...held.map(s => s.vol));
      const finalVol = samples[samples.length - 1].vol;
      const minVol = Math.min(...samples.map(s => s.vol));
      D.reset();
      return { base, ducked, heldMax, finalVol, minVol, n: samples.length };
    });
    check('music actually ducked (dipped toward base*depth)', pump.minVol < pump.ducked + 0.06,
      `min=${pump.minVol.toFixed(3)} duckedTarget=${pump.ducked.toFixed(3)}`);
    check('NO PUMP — music stays down through the overlap (no rise while a source is active)',
      pump.heldMax < pump.ducked + 0.07, `heldMax=${pump.heldMax.toFixed(3)} (ceiling=${(pump.ducked+0.07).toFixed(3)})`);
    check('restores to base once both sources end', pump.finalVol > pump.base - 0.05,
      `final=${pump.finalVol.toFixed(3)} base=${pump.base}`);

    // TEST 3 — guaranteed release: an un-released source auto-releases after maxMs+1s
    const guard = await page.evaluate(async () => {
      const D = window.__duck; D.reset();
      D.acquire('zombie', 200);           // guard fires at 200+1000 = 1200ms
      const activeNow = D.active();
      await new Promise(r => setTimeout(r, 1500));
      const activeAfter = D.active();
      D.reset();
      return { activeNow, activeAfter };
    });
    check('un-released source auto-releases via watchdog (no stuck-down music)',
      guard.activeNow === true && guard.activeAfter === false, `active ${guard.activeNow}→${guard.activeAfter}`);

    // TEST 4 — implicit level sources (her live voice / clip flags) still count
    const implicit = await page.evaluate(() => {
      const D = window.__duck; D.reset();
      const idle = D.active();
      window.__novaSpeakingNow = true;    const speaking = D.active();
      D.acquire('baked', 20000);          const both = D.count();
      window.__novaSpeakingNow = false;   const afterVoice = D.active();   // baked still holds
      D.release('baked');                 const afterAll = D.active();
      window.__novaSpeakingNow = false; D.reset();
      return { idle, speaking, both, afterVoice, afterAll };
    });
    check('her live voice ducks implicitly; baked + voice count together',
      implicit.idle === false && implicit.speaking === true && implicit.both === 2, `count(both)=${implicit.both}`);
    check('voice ending while baked holds stays ducked; all-clear restores',
      implicit.afterVoice === true && implicit.afterAll === false);

  } catch (e) {
    check('harness ran to completion', false, e.message);
  } finally {
    await ctx.close(); await b.close(); server.close();
  }

  const passed = results.filter(r => r.pass).length, total = results.length;
  console.log(`\nZONE 2 — DUCKING REFCOUNT: ${passed}/${total} PASS`);
  console.log(passed === total ? 'RESULT: PASS ✅' : 'RESULT: FAIL ❌ (' + results.filter(r=>!r.pass).map(r=>r.name).join('; ') + ')');
  process.exit(passed === total ? 0 : 1);
})();
