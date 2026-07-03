// PHASE 1 LOOP ENGINE — machine-checks the intro so PASS/FAIL comes from the script.
// Usage: node tools/phase1-loop.js [--local]        (needs the local server on :8850 for --local,
//        otherwise runs against the live GitHub Pages URL; the WORKER is always the real one)
// Requires: playwright-core + installed Chrome. Headed (headless webgl is uselessly slow).
const { chromium } = require('playwright-core');
const LOCAL = process.argv.includes('--local');
const URL = (LOCAL ? 'http://localhost:8850' : 'https://dsbeauty01-web.github.io/dance-project') + '/nova-joined.html';

const results = [];
const check = (name, pass, evidence) => { results.push({ name, pass, evidence }); console.log((pass===true?'PASS ':pass===false?'FAIL ':'?    ') + name + ' — ' + evidence); };

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40', '--window-size=1300,820'] });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1400, height: 800 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 4000));                       // prefetch + detector init

  // tap the orb → full real flow against the real worker
  await page.evaluate(() => { const b = document.getElementById('arrival-start-btn'); b && b.click(); });
  console.log('>>> tapped — waiting for the magic reveal (up to 90s)…');
  await page.waitForFunction(() => window.__revealAt, undefined, { timeout: 90000 }).catch(() => {});
  await page.waitForFunction(() => window.__firstWordAt, undefined, { timeout: 15000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 1000));                       // settle after the word

  const s = await page.evaluate(() => ({
    gate: window.__gate || {}, gateDoneAt: window.__gateDoneAt || null, revealAt: window.__revealAt || null,
    firstWordAt: window.__firstWordAt || null, revealToWordMs: window.__revealToWordMs,
    backend: window.__tfBackend, fps: window.__poseAttemptFPS || 0, fpsPeak: window.__poseAttemptFPSPeak || 0,
    uiMap: window.__UI_MAP || null, hasNameBtnFn: typeof showNameCaptureButtons === 'function',
    micDenied: window.__micDenied, camDenied: window.__camDenied,
    connectStart: window.__connectStartMs, firstWordMs: window.__firstWordMs,
  }));

  // (a) ready-gate: all 5 stamps present, reveal AFTER the last
  const keys = ['evi', 'cam', 'calib', 'vision', 'avatar'];
  const stamps = keys.map(k => s.gate[k] || null);
  const allStamped = stamps.every(Boolean);
  const lastGate = allStamped ? Math.max(...stamps) : null;
  check('(a) gate: 5 items stamped', allStamped, keys.map((k, i) => k + '=' + (stamps[i] ? 'ok' : 'MISSING')).join(' '));
  check('(a2) reveal after last gate', !!(allStamped && s.revealAt && s.revealAt >= lastGate), 'reveal ' + (s.revealAt && lastGate ? (s.revealAt - lastGate) + 'ms after last gate' : 'n/a'));
  // (b) first word vs reveal (reveal is voice-synced → gap should be ~0 or negative)
  const gap2 = (s.firstWordAt && s.revealAt) ? (s.firstWordAt - s.revealAt) : null;
  const gapOk = gap2 !== null && gap2 >= 0 && gap2 <= 1500;   // INTRO-FINAL: face leads, word 0..+1.5s after — NEVER negative
  check('(b) word 0..+1500ms after reveal', !!gapOk, 'delta=' + gap2 + 'ms (must be 0..1500, NEVER negative)');
  // (c) backend + fps
  check('(c) webgl + fps≥15', s.backend === 'webgl' && s.fpsPeak >= 15, 'backend=' + s.backend + ' fpsPeak=' + s.fpsPeak);
  // (d) console errors
  check('(d) no console errors', errors.length === 0, errors.length ? errors.slice(0, 3).join(' | ') : 'clean');
  // (e) name-button fallback exists
  await page.evaluate(() => { try { showNameCaptureButtons(); } catch (e) {} });
  const btns = await page.evaluate(() => !!document.getElementById('name-path-btns'));
  check('(e) name-button fallback', s.hasNameBtnFn && btns, 'fn=' + s.hasNameBtnFn + ' rendered=' + btns);
  // (f) UI_MAP exposed
  check('(f) UI_MAP exposed', !!(s.uiMap && /LEFT panel/.test(s.uiMap)), (s.uiMap || '').slice(0, 60) + '…');

  console.log('\nNEEDS-EYES (cannot be machine-checked):');
  ['voice content of every beat (name retry→friend, age default, adult flow, are-you-real line)',
   'vision detail actually spoken in her opener (needs a real colored shirt on camera)',
   'barge-in: interrupt her mid-sentence, she must not resume the old line',
   'returning-kid ≤25s intro with callback (needs a stored kid + real voice)',
  ].forEach(x => console.log('  NEEDS-EYES: ' + x));

  console.log('\nSUMMARY: ' + results.filter(r => r.pass === true).length + '/' + results.length + ' machine checks passed');
  try { await page.evaluate(() => { if (window.__novaSessionId) navigator.sendBeacon(CFG.RENDER_URL + '/end-session', new Blob([JSON.stringify({ sessionId: window.__novaSessionId })], { type: 'application/json' })); if (window.__novaRoom) window.__novaRoom.disconnect(); }); } catch (e) {}
  await new Promise(r => setTimeout(r, 1000));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
