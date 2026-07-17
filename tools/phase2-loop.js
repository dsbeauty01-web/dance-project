// PHASE 2 LOOP ENGINE — machine-checks the button→game TRANSITION (the live bridge).
// Extends the phase1-loop pattern. PASS/FAIL comes from the script, with evidence.
//
// Usage:  node tools/phase2-loop.js
// Self-contained: starts its own static server on :8851 serving the dance-project dir,
// so it tests the LOCAL working tree (your un-deployed edits), not GitHub Pages.
// Requires: playwright-core + installed Chrome (same as phase1-loop). Headed (webgl).
//
// WORKER-INDEPENDENT BY DESIGN: the real worker (Render/EVI) is NOT needed. We stub the
// LiveKit data channel (window.__novaSend) and drive the readiness signals (speaking, pose)
// so every gate/budget/edge-case check is DETERMINISTIC. Voice *content* is NEEDS-EYES.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.resolve(__dirname, '..');            // dance-project/
const PORT = 8851;
const URL = `http://localhost:${PORT}/nova-joined.html`;

// ── tiny static server ────────────────────────────────────────────────────
const MIME = { '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript',
  '.css':'text/css', '.json':'application/json', '.mp4':'video/mp4', '.mp3':'audio/mpeg',
  '.png':'image/png', '.jpg':'image/jpeg', '.y4m':'video/x-raw', '.riv':'application/octet-stream' };
function startServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/nova-joined.html';
      const file = path.join(ROOT, p);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); return res.end('not found');
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}

// ── results ───────────────────────────────────────────────────────────────
const results = [];
const check = (name, pass, evidence) => {
  results.push({ name, pass, evidence });
  console.log((pass === true ? 'PASS ' : pass === false ? 'FAIL ' : '?    ') + name + ' — ' + evidence);
};

// ── page-context helpers (stringified, injected via addInitScript) ──────────
// Installed BEFORE any page script runs, so window.__novaSend is our stub from the start.
function benchInit() {
  window.__bench = { beats: [], phases: [] };
  window.__novaSpeakingNow = false;
  window.__transTest = {};
  // neutralize the real worker/room bring-up so nothing external is needed
  window.__initRunwayNova = () => {};
}

// The page module sets window.__novaSend = novaSend at init (the real, dead LiveKit
// sender). We must OVERWRITE it AFTER load with our recorder — which also pulses
// "speaking" so the bridge/handoff resolve on our synthetic voice.
function installSend() {
  window.__novaSend = (m) => {
    try {
      if (m && m.kind === 'game-event' && m.event) {
        if (m.event.event === 'bridge') window.__bench.beats.push(m.event.beat);
        if (m.event.event === 'phase') window.__bench.phases.push(m.event.phase);
        if (!window.__transTest.forceNoVoice) {
          window.__novaSpeakingNow = true;
          setTimeout(() => { window.__novaSpeakingNow = false; }, 160);
        }
      }
    } catch (e) {}
  };
}

// inject a fully-framed upper body (or clear it) into the pose stream
function benchFrame(on) {
  if (!on) { window.__lastPoseKeypoints = []; return; }
  const H = 480;
  window.__lastPoseKeypoints = [
    { name: 'nose', x: 320, y: H * 0.20, score: 0.95 },
    { name: 'left_shoulder', x: 260, y: H * 0.40, score: 0.92 },
    { name: 'right_shoulder', x: 380, y: H * 0.40, score: 0.92 },
    { name: 'left_hip', x: 285, y: H * 0.66, score: 0.72 },
    { name: 'right_hip', x: 355, y: H * 0.66, score: 0.72 },
  ];
}

// ── scenario driver ─────────────────────────────────────────────────────────
async function freshPage(ctx) {
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(benchInit);
  await page.addInitScript(`window.__benchFrame = ${benchFrame.toString()};`);
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.__startTransition === 'function', undefined, { timeout: 15000 });
  await page.evaluate(installSend);   // overwrite the page's real (dead) sender with our recorder
  page._errors = errors;
  return page;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const server = await startServer();
  console.log(`>>> static server on ${URL}`);
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40', '--window-size=1300,820'] });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1400, height: 800 } });

  try {
    // ═══ SCENARIO A — NORMAL: pick → bridge → framing → handoff ═══
    {
      const page = await freshPage(ctx);
      await page.evaluate(() => window.__benchFrame(false));
      await page.evaluate(() => window.__startTransition('wave'));
      await sleep(1600);
      await page.evaluate(() => window.__benchFrame(true));                 // kid steps back
      await page.waitForFunction(() => !!window.__readyAllAt, undefined, { timeout: 15000 }).catch(() => {});
      await page.waitForFunction(() => !!window.__mp4PlayAt, undefined, { timeout: 4000 }).catch(() => {}); // handoff plays MP4
      await sleep(200);
      const s = await page.evaluate(() => ({
        gate: window.__readyGate, preloadMs: window.__mp4PreloadDelayMs,
        readyAllAt: window.__readyAllAt, mp4PlayAt: window.__mp4PlayAt,
        beats: window.__bench.beats, phases: window.__bench.phases, log: window.__bridgeLog,
        faceHidden: (() => { const f = document.getElementById('nova-face-frame'); return f && getComputedStyle(f).display === 'none'; })(),
      }));
      // (1) preload starts ≤300ms after pick
      check('A1 MP4 preload ≤300ms after pick', s.preloadMs != null && s.preloadMs <= 300, 'preloadDelay=' + s.preloadMs + 'ms');
      // (2) ready gate: all 4 true, MP4 plays only AFTER handoff
      const g = s.gate || {};
      check('A2 ready gate all 4 true', !!(g.mp4 && g.cues && g.framed && g.bridge), JSON.stringify(g));
      check('A3 MP4 starts only after handoff', !!(s.mp4PlayAt && s.readyAllAt && s.mp4PlayAt >= s.readyAllAt),
        'playAt-readyAt=' + (s.mp4PlayAt && s.readyAllAt ? Math.round(s.mp4PlayAt - s.readyAllAt) + 'ms' : 'n/a'));
      // (3) bridge order: hype/tip → framing → framed, then go (phase:dance)
      const order = s.beats.join(',');
      check('A4 bridge beats present + go', /hype/.test(order) && /framed/.test(order) && s.phases.includes('dance'),
        'beats=[' + order + '] phases=[' + s.phases.join(',') + ']');
      // (5) face fully hidden during MP4
      check('A5 face hidden at handoff', s.faceHidden === true, 'nova-face-frame display=' + (s.faceHidden ? 'none' : 'VISIBLE'));
      // (3b) budget: ≤3 narration lines, NONE started after load-ready
      const narration = (s.log || []).filter(e => ['hype', 'tip', 'framing'].includes(e.beat));
      const afterReady = narration.filter(e => e.readyWhenStarted);
      check('A6 budget: ≤3 lines, none after ready', narration.length <= 3 && afterReady.length === 0,
        narration.length + ' narration lines, ' + afterReady.length + ' started after load-ready');
      check('A7 no uncaught page errors', page._errors.length === 0, page._errors.slice(0, 2).join(' | ') || 'clean');
      await page.close();
    }

    // ═══ SCENARIO B — CACHED: preloaded video + already framed → no hype/tip filler ═══
    {
      const page = await freshPage(ctx);
      // joined (nova-joined-small.mp4) is preloaded at boot — wait for it to buffer
      const buffered = await page.waitForFunction(() => {
        const v = document.getElementById('nova-video'); return v && v.readyState >= 4;
      }, undefined, { timeout: 10000 }).then(() => true).catch(() => false);
      await page.evaluate(() => window.__benchFrame(true));                 // already framed
      await page.evaluate(() => window.__startTransition('joined'));
      await page.waitForFunction(() => !!window.__readyAllAt, undefined, { timeout: 8000 }).catch(() => {});
      const s = await page.evaluate(() => ({ beats: window.__bench.beats, phases: window.__bench.phases, cachedReady: window.__readyAllAt }));
      if (!buffered) check('B1 cached → no hype/tip', null, 'video did not reach readyState 4 in 10s (cannot assert cached path)');
      else check('B1 cached → no hype/tip filler', !s.beats.includes('hype') && !s.beats.includes('tip') && !!s.cachedReady,
        'beats=[' + s.beats.join(',') + '] (fast path to go)');
      await page.close();
    }

    // ═══ SCENARIO D — LOAD FAIL: dead MP4 → warm line + back to picker ═══
    {
      const page = await freshPage(ctx);
      await page.evaluate(() => window.__benchFrame(true));
      await page.evaluate(() => {
        window.__startTransition('wave');
        // kill the URL right after preload starts → element fires 'error' → onLoadFail
        const v = document.getElementById('nova-video');
        v.src = 'this-file-does-not-exist-404.mp4'; v.load();
      });
      await page.waitForFunction(() => !!window.__loadFailed, undefined, { timeout: 8000 }).catch(() => {});
      await sleep(2200);
      const s = await page.evaluate(() => ({
        failed: window.__loadFailed, beats: window.__bench.beats,
        onPicker: document.getElementById('phase-picker').classList.contains('active'),
        started: !!window.__readyAllAt,
      }));
      check('D1 load-fail → fail line + picker', !!(s.failed && s.beats.includes('fail') && s.onPicker && !s.started),
        'failed=' + s.failed + ' fail-line=' + s.beats.includes('fail') + ' picker=' + s.onPicker + ' game-started=' + s.started);
      await page.close();
    }

    // ═══ SCENARIO E — CHANGE MIND: pick wave, then joined mid-load → one clean handoff ═══
    {
      const page = await freshPage(ctx);
      await page.evaluate(() => window.__benchFrame(false));
      await page.evaluate(() => window.__startTransition('wave'));
      await sleep(350);
      await page.evaluate(() => window.__startTransition('joined'));         // change mind
      await sleep(300);
      await page.evaluate(() => window.__benchFrame(true));
      await page.waitForFunction(() => !!window.__readyAllAt, undefined, { timeout: 12000 }).catch(() => {});
      const s = await page.evaluate(() => ({
        beats: window.__bench.beats, phases: window.__bench.phases, song: window.__selectedSongId,
      }));
      const danceHandoffs = s.phases.filter(p => p === 'dance').length;
      check('E1 change-mind: switch + single handoff', s.beats.includes('switch') && s.song === 'joined' && danceHandoffs === 1,
        'switch=' + s.beats.includes('switch') + ' song=' + s.song + ' dance-handoffs=' + danceHandoffs);
      await page.close();
    }

    // ═══ SCENARIO F — DANCE-ALONG: never framed → 2 prompts → start anyway, no scoring ═══
    {
      const page = await freshPage(ctx);
      await page.evaluate(() => window.__benchFrame(false));                 // never framed
      await page.evaluate(() => {
        window.__startTransition('wave');
        window.__readyGate.mp4 = true;                                       // force load ready so only framing blocks
      });
      await page.waitForFunction(() => !!window.__danceAlong, undefined, { timeout: 30000 }).catch(() => {});   // 2026-07-17: narration got longer (mouth rule delays prompt #2 to ~15s; dance-along ~19s)
      await sleep(400);
      const s = await page.evaluate(() => ({
        danceAlong: window.__danceAlong, scoring: window.__scoringEnabled,
        prompts: window.__framePrompts, beats: window.__bench.beats, started: !!window.__readyAllAt,
      }));
      check('F1 dance-along fallback (no scoring)', !!(s.danceAlong && s.scoring === false && s.prompts >= 2 && s.beats.includes('dancealong')),
        'danceAlong=' + s.danceAlong + ' scoring=' + s.scoring + ' prompts=' + s.prompts + ' started=' + s.started);
      await page.close();
    }

    // ═══ SCENARIO G — VOICE KILLED: no voice → captions carry it, game still starts ═══
    {
      const page = await freshPage(ctx);
      await page.evaluate(() => { window.__transTest.forceNoVoice = true; window.__benchFrame(false); });
      await page.evaluate(() => window.__startTransition('wave'));
      await sleep(1600);
      await page.evaluate(() => window.__benchFrame(true));
      await page.waitForFunction(() => !!window.__readyAllAt, undefined, { timeout: 15000 }).catch(() => {});
      const s = await page.evaluate(() => ({
        started: !!window.__readyAllAt,
        caption: (document.getElementById('trans-cap') || {}).textContent || '',
      }));
      check('G1 voice killed → captions carry, game starts', !!(s.started && s.caption && s.caption.length > 3),
        'started=' + s.started + ' lastCaption="' + s.caption + '"');
      await page.close();
    }

  } catch (e) {
    console.error('SCENARIO FATAL', e);
  }

  console.log('\nNEEDS-EYES (cannot be machine-checked):');
  [
    'handoff FEEL: press dance → hype → tip → step-back → "here we GO" → her face melts as music starts — one continuous alive moment',
    'voice CONTENT of each beat is on-persona (real worker + EVI/ElevenLabs voice)',
    'barge-in mid-bridge: talk over her → she stops, answers ≤1 line, continues to go',
    'framing gate with a REAL body on camera (this harness injects synthetic keypoints)',
  ].forEach(x => console.log('  NEEDS-EYES: ' + x));

  const passed = results.filter(r => r.pass === true).length;
  const failed = results.filter(r => r.pass === false).length;
  console.log(`\nSUMMARY: ${passed}/${results.length} machine checks passed` + (failed ? ` (${failed} FAILED)` : ''));

  await browser.close();
  server.close();
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
