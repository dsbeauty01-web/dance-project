// RUNTIME self-test — drives the REAL page in headless system Chrome (playwright-core),
// fake camera, observes actual behavior. This is how the build is verified before delivery.
//   node tools/qa-runtime.js [game]        (default wavemagic)
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const GAME = process.argv[2] || 'wavemagic';
const FAKECAM = path.join(ROOT, 'tools', 'fakecam.y4m');
const URL = 'file:///' + path.join(ROOT, 'nova-commercial.html').replace(/\\/g, '/') + '?nonova&game=' + GAME;
const CHROME = [
  process.env['ProgramFiles'] + '\\Google\\Chrome\\Application\\chrome.exe',
  process.env['ProgramFiles(x86)'] + '\\Google\\Chrome\\Application\\chrome.exe',
  process.env['LOCALAPPDATA'] + '\\Google\\Chrome\\Application\\chrome.exe',
  process.env['ProgramFiles'] + '\\Microsoft\\Edge\\Application\\msedge.exe',
].find(p => p && fs.existsSync(p));

let pass = 0, fail = 0;
const ok = (n, c, d = '') => { c ? pass++ : fail++; console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); };

(async () => {
  if (!CHROME) { console.log('FAIL: no Chrome/Edge found'); process.exit(1); }
  const args = ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'];
  if (fs.existsSync(FAKECAM)) args.push('--use-file-for-fake-video-capture=' + FAKECAM.replace(/\\/g, '/'));

  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  console.log('LOADING ' + URL + '\n');
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });

  const snap = () => page.evaluate(() => {
    const a = window._audio;
    return {
      paused: a ? a.paused : null,
      cur: a ? +(a.currentTime || 0).toFixed(2) : null,
      phase: (document.querySelector('.phase.active') || {}).id || null,
      choreo: window.__choreoActive || null,
      loaded: (window.__choreoLoaded || []).length,
      cues: window.__cuesFired || 0,
      hasPop: typeof window.__novaPop === 'function',
    };
  });

  // ── PHASE A: watch the countdown gate (sample 500ms × 12 = 6s) ──
  const tl = [];
  for (let i = 0; i < 12; i++) { tl.push({ t: i * 0.5, ...(await snap()) }); await page.waitForTimeout(500); }
  console.log('=== first 6s (0.5s samples) ===');
  tl.forEach(s => console.log(`t+${s.t}s paused=${s.paused} clock=${s.cur} phase=${s.phase} choreo=${s.choreo} cues=${s.cues}`));

  const last = tl[tl.length - 1];
  ok('all 6 games loaded from data', last.loaded >= 6, last.loaded + ' loaded');
  ok('game is choreo-driven', tl.some(s => s.choreo === GAME));
  ok('POP function present', last.hasPop);

  // NO-AUTOPLAY: a countdown phase must appear, and audio must NOT advance while it's up.
  const sawCountdown = tl.some(s => s.phase === 'phase-countdown');
  ok('countdown phase runs before play', sawCountdown);
  const playedDuringCountdown = tl.some(s => s.phase === 'phase-countdown' && s.paused === false);
  ok('NO AUTOPLAY: audio stays paused during countdown', !playedDuringCountdown);
  const firstPlay = tl.find(s => s.paused === false);
  ok('audio eventually plays (game runs)', !!firstPlay, firstPlay ? `first play @t+${firstPlay.t}s` : 'never played');
  ok('audio did not start in first ~2s (no instant autoplay)', !tl.some(s => s.t <= 1.5 && s.paused === false),
     'earliest play t+' + (firstPlay ? firstPlay.t : '?') + 's');

  // ── PHASE B: seek to a cue and confirm cues fire on the video clock ──
  await page.evaluate(() => { if (window._audio) window._audio.currentTime = 37; });
  await page.waitForTimeout(2500);
  const afterSeek = await snap();
  ok('cues fire on the video clock (seek→37s)', afterSeek.cues > 0, 'cuesFired=' + afterSeek.cues);

  // ── PHASE C: POP renders when triggered ──
  await page.evaluate(() => window.__novaPop && window.__novaPop('THREE IN A ROW!'));
  await page.waitForTimeout(450);
  const popShown = await page.evaluate(() => {
    const el = document.getElementById('nova-pop');
    return !!(el && el.classList.contains('show') && el.querySelector('.txt') && el.querySelector('.txt').textContent);
  });
  ok('POP renders when triggered', popShown);
  try { await page.screenshot({ path: path.join(ROOT, 'tools', 'qa-runtime-' + GAME + '.png') }); console.log('   screenshot: tools/qa-runtime-' + GAME + '.png'); } catch (_) {}

  // ── errors ──
  const real = errors.filter(e => !/favicon|net::ERR|Failed to load resource|Loading CSS chunk/i.test(e));
  ok('no uncaught page errors', real.length === 0, real.slice(0, 3).join(' | '));
  if (errors.length) { console.log('\n=== page errors (incl. network) ==='); errors.slice(0, 6).forEach(e => console.log('  ' + e)); }

  await browser.close();
  console.log(`\nRUNTIME QA (${GAME}): ${pass} pass / ${fail} fail`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(2); });
