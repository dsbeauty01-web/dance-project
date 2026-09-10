#!/usr/bin/env node
// test/novasays_smoke.js — NOVA-SAYS full-session page smoke (beta-b0.21-novasays).
// Serves the repo statically, drives beta/novasays.html?test=1 in headless Chrome with an
// IN-PAGE synthetic-pose driver (all 12 commands, tricks held/neutral, freeze hold, typed
// boss commands), records video + screenshots + the page's __test log to ~/Downloads.
// No pod needed: the page runs lights-only (voice notes are logged, not spoken).
//   node test/novasays_smoke.js
import http from 'http';
import { readFile } from 'fs/promises';
import { existsSync, mkdirSync, copyFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join, extname } from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require(join(dirname(fileURLToPath(import.meta.url)), '..', 'tools', 'node_modules', 'playwright-core'));

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DL = join(process.env.USERPROFILE || process.env.HOME, 'Downloads');
const MIME = { '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.css':'text/css', '.mp3':'audio/mpeg', '.mp4':'video/mp4', '.json':'application/json', '.png':'image/png', '.task':'application/octet-stream', '.wasm':'application/wasm' };

const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p === '/health') { res.writeHead(404); res.end(); return; }               // no pod in the smoke → lights-only path
  try {
    const body = await readFile(join(ROOT, p.replace(/^\/+/, '')));
    res.writeHead(200, { 'Content-Type': MIME[extname(p)] || 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, r));
const PORT = server.address().port;

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: DL, size: { width: 1280, height: 720 } } });
const page = await context.newPage();
const consoleErrs = [];
page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text()); });
page.on('pageerror', e => consoleErrs.push('PAGEERROR ' + e.message));
await page.goto(`http://localhost:${PORT}/beta/novasays.html?test=1`);
await page.click('#start');

// ── the in-page driver: synthetic kid ──────────────────────────────────────
await page.evaluate(() => {
  const V = 1;
  const BASE = {
    nose:{x:.50,y:.20,vis:V}, lShoulder:{x:.42,y:.35,vis:V}, rShoulder:{x:.58,y:.35,vis:V},
    lElbow:{x:.38,y:.50,vis:V}, rElbow:{x:.62,y:.50,vis:V},
    lWrist:{x:.35,y:.62,vis:V}, rWrist:{x:.65,y:.62,vis:V},
    lIndex:{x:.34,y:.66,vis:V}, rIndex:{x:.66,y:.66,vis:V},
    lHip:{x:.45,y:.62,vis:V}, rHip:{x:.55,y:.62,vis:V},
    lKnee:{x:.46,y:.80,vis:V}, rKnee:{x:.54,y:.80,vis:V},
  };
  const TGT = {                                                     // per-command kid answer (page coords)
    armsUp:  { lWrist:{x:.40,y:.18}, rWrist:{x:.60,y:.18}, lIndex:{x:.40,y:.14}, rIndex:{x:.60,y:.14} },
    leftUp:  { lWrist:{x:.38,y:.18}, lIndex:{x:.38,y:.14} },
    rightUp: { rWrist:{x:.62,y:.18}, rIndex:{x:.62,y:.14} },
    clap:    { lWrist:{x:.49,y:.50}, rWrist:{x:.51,y:.50} },
    head:    { lWrist:{x:.47,y:.22}, rWrist:{x:.53,y:.22} },
    hips:    { lWrist:{x:.44,y:.63}, rWrist:{x:.56,y:.63} },
    knees:   { lWrist:{x:.46,y:.78}, rWrist:{x:.54,y:.78} },
    freeze:  {},                                                    // stillness IS the answer
    jump:    null, headSide: null, shoulders: null, wave: null,     // handled procedurally below
  };
  const clone = o => JSON.parse(JSON.stringify(o));
  let lastCmd = null, p = 0, osc = 0, waveT = 0;
  const BOSS = ['Nova says jump', 'clap!', 'Nova says arms up', 'wave your arm', 'Nova says touch your knees', 'banana dance', 'Nova says clap', 'hands on your head'];
  let bossI = 0, bossTimer = 0;
  window.__driver = setInterval(() => {
    const s = window.__test.state();
    if (s.phase === 'boss') {                                       // typed boss commands
      if (++bossTimer % 3 === 0 && bossI < BOSS.length * 3) window.__test.kid(BOSS[bossI++ % BOSS.length]);
      window.__test.pose(clone(BASE));
      return;
    }
    const f = clone(BASE);
    const key = (s.phase === 'game' && s.inWindow && !s.trick) ? s.cmdId : null;
    if (key !== lastCmd) { lastCmd = key; p = 0; osc = 0; waveT = 0; }
    if (key && TGT[key]) {                                          // ramp to a static target over ~8 frames, then hold
      p = Math.min(1, p + 0.125);
      for (const [n, t] of Object.entries(TGT[key])) { f[n].x = BASE[n].x + (t.x - BASE[n].x) * p; f[n].y = BASE[n].y + (t.y - BASE[n].y) * p; }
    } else if (key === 'jump') {
      p = Math.min(1, p + 0.34);
      for (const n of ['lHip','rHip','lShoulder','rShoulder','nose']) f[n].y = BASE[n].y - 0.09 * p;
    } else if (key === 'headSide') {
      osc += 0.5; f.nose.x = BASE.nose.x + 0.06 * Math.sin(osc);
    } else if (key === 'shoulders') {
      p = Math.min(1, p + 0.25);
      for (const n of ['lShoulder','rShoulder']) f[n].y = BASE[n].y - 0.045 * p;
    } else if (key === 'wave') {                                    // traveling peak down the right arm chain
      waveT += 33;
      const chain = ['rShoulder','rElbow','rWrist','rIndex'];
      chain.forEach((n, i) => { const c = (waveT - 150 - i * 130) / 90; f[n].y = BASE[n].y - 0.06 * Math.exp(-c * c); });
    }
    window.__test.pose(f);
  }, 33);
});

// ── watch the run, screenshot the moments ──────────────────────────────────
const shots = [];
async function shot(name) { const f = join(DL, name); await page.screenshot({ path: f }); shots.push(f); }
const t0 = Date.now();
let got = { intro: false, game: false, card: false, boss: false, done: false };
while (Date.now() - t0 < 120000) {
  const s = await page.evaluate(() => ({ ...window.__test.state(), card: !document.getElementById('card').classList.contains('hidden'), finale: !document.getElementById('finale').classList.contains('hidden') })).catch(() => null);
  if (!s) break;
  if (!got.intro && s.phase === 'intro') { got.intro = true; await shot('NOVASAYS-1-intro.png'); }
  if (!got.game && s.phase === 'game' && s.inWindow && !s.trick && s.lightsActive) { got.game = true; await shot('NOVASAYS-2-command-light.png'); }
  if (!got.card && s.card) { got.card = true; await shot('NOVASAYS-3-round-card.png'); }
  if (!got.boss && s.phase === 'boss') { got.boss = true; await shot('NOVASAYS-4-boss.png'); }
  if (s.finale) { got.done = true; await shot('NOVASAYS-5-finale.png'); break; }
  await new Promise(r => setTimeout(r, 120));
}

const log = await page.evaluate(() => window.__test.log);
const state = await page.evaluate(() => window.__test.state());
await page.evaluate(() => clearInterval(window.__driver));
await context.close();                                              // finalizes the video
const video = await page.video()?.path?.() ?? null;
await browser.close(); server.close();
if (video && existsSync(video)) copyFileSync(video, join(DL, 'NOVASAYS-SMOKE-RUN.webm'));

// ── grade the run ──────────────────────────────────────────────────────────
let pass = 0, fail = 0;
const ok = (c, n, d = '') => { c ? pass++ : fail++; console.log((c ? '  ✅ ' : '  ❌ ') + n + (c || !d ? '' : ' — ' + d)); };
const ev = k => log.filter(e => e.ev === k);
const resolves = ev('resolve').map(e => e.d);
const ends = ev('endRound').map(e => e.d);
console.log('\n── novasays_smoke: full 4-round session ──');
ok(got.done, 'session reached the finale scorecard');
ok(ends.length === 4 && ends.map(e => e.n).join(',') === '1,2,3,4', 'all 4 rounds completed in order', JSON.stringify(ends.map(e => e.n)));
ok(resolves.some(r => r.event === 'hit'), 'real commands were hit', `${resolves.filter(r => r.event === 'hit').length} hits`);
ok(resolves.some(r => r.event === 'trickHeld'), 'at least one trick was HELD (kid listened)');
ok(resolves.every(r => r.pts >= 0), 'no negative points anywhere');
const phases = ev('phase').map(e => e.d);
ok(['intro','game','between','boss','ending'].every(p => phases.includes(p)), 'phase machine walked intro→game→between→boss→ending', phases.join(','));
const bossEv = ev('boss').map(e => e.d);
ok(bossEv.filter(b => b.parsed).length >= 2, 'boss round parsed typed kid commands', `${bossEv.filter(b => b.parsed).length} parsed`);
ok(ev('pulse').length === 1, 'PULSE row fired at the finale');
const trickLights = log.filter((e, i) => e.ev === 'light' && log[i - 1]?.ev === 'say' && !/nova says|נובה אומרת/i.test(log[i - 1].d));
ok(trickLights.length === 0, 'tricks never lit a cue', trickLights.length + ' violations');
ok(consoleErrs.filter(e => !/net::|Failed to load resource|favicon|fonts|jsdelivr|AudioContext|play\(\)/i.test(e)).length === 0, 'no page errors', consoleErrs.slice(0, 3).join(' | '));
console.log(`\n  score=${state.score} tricksCaught=${state.tricksCaught} stars=${JSON.stringify(ends.map(e => e.stars))}`);
console.log(`  evidence: ${shots.length} screenshots + NOVASAYS-SMOKE-RUN.webm + NOVASAYS-SMOKE-LOG.json → Downloads`);
writeFileSync(join(DL, 'NOVASAYS-SMOKE-LOG.json'), JSON.stringify({ state, ends, resolves, phases, bossEv, consoleErrs, log }, null, 2));
console.log(`\n══ novasays_smoke: ${pass} passed, ${fail} failed ══`);
process.exit(fail ? 1 : 0);
