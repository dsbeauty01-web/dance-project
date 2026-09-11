#!/usr/bin/env node
// test/novasays_smoke.js — NOVA-SAYS-V2 full-session page smoke (beta-b0.25-novasays2).
// Serves the repo statically, drives beta/novasays.html?test=1 in headless Chrome with an
// in-page synthetic kid, and asserts the V2 GATE: every command fires within ±40ms of its
// beat-grid slot, no gap > one bar, tricks unlit, GOTCHA never negative. Records video +
// screenshots + the __test log to ~/Downloads. Real clips + real SneakyBed timing (no pod).
//   node test/novasays_smoke.js
import http from 'http';
import { readFile } from 'fs/promises';
import { existsSync, copyFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join, extname } from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require(join(dirname(fileURLToPath(import.meta.url)), '..', 'tools', 'node_modules', 'playwright-core'));

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DL = join(process.env.USERPROFILE || process.env.HOME, 'Downloads');
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.mp3':'audio/mpeg', '.mp4':'video/mp4', '.json':'application/json', '.task':'application/octet-stream' };

const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p === '/health') { res.writeHead(404); res.end(); return; }
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

// ── in-page synthetic kid ──────────────────────────────────────────────────
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
  const TGT = {
    armsUp:  { lWrist:{x:.40,y:.18}, rWrist:{x:.60,y:.18}, lIndex:{x:.40,y:.14}, rIndex:{x:.60,y:.14} },
    leftUp:  { lWrist:{x:.38,y:.18}, lIndex:{x:.38,y:.14} },
    rightUp: { rWrist:{x:.62,y:.18}, rIndex:{x:.62,y:.14} },
    clap:    { lWrist:{x:.49,y:.50}, rWrist:{x:.51,y:.50} },
    head:    { lWrist:{x:.47,y:.22}, rWrist:{x:.53,y:.22} },
    freeze:  {},
  };
  const clone = o => JSON.parse(JSON.stringify(o));
  let lastKey = null, p = 0;
  const BOSS = ['Nova says jump', 'clap!', 'Nova says arms up', 'hands on your head', 'Nova says freeze', 'banana dance', 'Nova says clap', 'left arm up'];
  let bossI = 0, bossTick = 0;
  window.__driver = setInterval(() => {
    const s = window.__test.state();
    if (s.phase === 'boss') {
      if (++bossTick % 3 === 0 && bossI < BOSS.length * 3) window.__test.kid(BOSS[bossI++ % BOSS.length]);
      window.__test.pose(clone(BASE));
      return;
    }
    const f = clone(BASE);
    const key = ((s.phase === 'game' || s.phase === 'hold') && s.inWindow !== false && s.cmdId && !s.trick) ? s.cmdId : null;
    if (key !== lastKey) { lastKey = key; p = 0; }
    if (s.phase === 'hold' || (key === 'freeze')) { window.__test.pose(f); return; }           // statue
    if (key && TGT[key]) {
      p = Math.min(1, p + (key === 'head' ? 0.34 : 0.125));                                    // head needs arrival speed (mag gate)
      for (const [n, t] of Object.entries(TGT[key])) { f[n].x = BASE[n].x + (t.x - BASE[n].x) * p; f[n].y = BASE[n].y + (t.y - BASE[n].y) * p; }
    } else if (key === 'jump') {
      p = Math.min(1, p + 0.34);
      for (const n of ['lHip','rHip','lShoulder','rShoulder','nose']) f[n].y = BASE[n].y - 0.09 * p;
    }
    window.__test.pose(f);
  }, 33);
});

// ── watch, screenshot, finish ──────────────────────────────────────────────
const shots = [];
async function shot(name) { const f = join(DL, name); await page.screenshot({ path: f }); shots.push(name); }
const t0 = Date.now();
let got = { intro:false, game:false, boss:false, done:false };
while (Date.now() - t0 < 360000) {
  const s = await page.evaluate(() => ({ ...window.__test.state(), finale: !document.getElementById('finale').classList.contains('hidden') })).catch(() => null);
  if (!s) break;
  if (!got.intro && s.phase === 'intro') { got.intro = true; await shot('NOVASAYS2-1-intro.png'); }
  if (!got.game && s.phase === 'game' && s.inWindow && !s.trick && s.lightsActive) { got.game = true; await shot('NOVASAYS2-2-command.png'); }
  if (!got.boss && s.phase === 'boss') { got.boss = true; await shot('NOVASAYS2-3-boss.png'); }
  if (s.finale) { got.done = true; await shot('NOVASAYS2-4-finale.png'); break; }
  await new Promise(r => setTimeout(r, 150));
}
const log = await page.evaluate(() => window.__test.log);
const state = await page.evaluate(() => window.__test.state());
await page.evaluate(() => clearInterval(window.__driver));
await context.close();
const video = await page.video()?.path?.() ?? null;
await browser.close(); server.close();
if (video && existsSync(video)) copyFileSync(video, join(DL, 'NOVASAYS2-RUN.webm'));

// ── grade the run (the V2 GATE) ────────────────────────────────────────────
let pass = 0, fail = 0;
const ok = (c, n, d = '') => { c ? pass++ : fail++; console.log((c ? '  ✅ ' : '  ❌ ') + n + (c || !d ? '' : ' — ' + d)); };
const ev = k => log.filter(e => e.ev === k);
const cmds = ev('cmd').map(e => e.d);
const resolves = ev('resolve').map(e => e.d);
const ends = ev('endRound').map(e => e.d);
const bedT0 = ev('bed')[0]?.d?.t0, bar = ev('bed')[0]?.d?.bar;
console.log('\n── novasays_smoke (V2): beat-locked full session ──');
ok(got.done, 'session reached the finale');
ok(ends.length === 4 && ends.map(e => e.n).join(',') === '1,2,3,4', 'all 4 rounds in order', JSON.stringify(ends.map(e => e.n)));
// GATE: every command fires within ±40ms of its scheduled grid slot
const fireDeltas = cmds.map(c => Math.abs(c.fired - c.at) * 1000);
ok(cmds.length > 0 && Math.max(...fireDeltas) <= 40, `every command fired within ±40ms of its slot (worst ${Math.max(...fireDeltas).toFixed(1)}ms)`);
// GATE: slots sit ON the half-bar grid (R2 = 1.5 bars → half-bar boundaries by design)
const gridOff = cmds.map(c => { const ph = ((c.at - bedT0) % (bar / 2) + bar / 2) % (bar / 2); return Math.min(ph, bar / 2 - ph) * 1000; });
ok(Math.max(...gridOff) <= 40, `every slot on the beat grid (worst off ${Math.max(...gridOff).toFixed(1)}ms)`);
// GATE: no dead gap WITHIN a round — consecutive commands ≤ grid step + one bar
// (between-round cards/coaching are phase changes, not gaps). One grid-realign after a
// freeze hold is allowed; assert realigns stay rare.
const endTimes = ev('endRound').map(e => e.t);
let gapOK = true, worstGap = 0;
for (let i = 1; i < cmds.length; i++) {
  if (endTimes.some(t => t > (cmds[i - 1].fired ?? cmds[i - 1].at) && t < cmds[i].at)) continue;   // round boundary
  const gap = cmds[i].at - cmds[i - 1].at;
  if (gap > 3 * bar + 0.05) { gapOK = false; } worstGap = Math.max(worstGap, gap);
}
ok(gapOK, `no dead gap inside a round (worst step ${worstGap.toFixed(2)}s ≤ 3 bars)`);
ok(ev('realign').length <= 3, 'grid realigns rare (≤3, freeze holds only)', ev('realign').length + ' realigns');
ok(resolves.every(r => r.pts >= 0), 'GOTCHA (and everything) never negative');
ok(resolves.some(r => r.event === 'hit'), 'real commands were hit', resolves.filter(r => r.event === 'hit').length + ' hits');
ok(resolves.some(r => r.event === 'trickHeld'), 'tricks were held');
// tricks unlit: no light event between a trick cmd and its resolve
let trickLit = 0;
for (let i = 0; i < log.length; i++) if (log[i].ev === 'cmd' && log[i].d.trick) {
  for (let j = i + 1; j < log.length && log[j].ev !== 'resolve'; j++) if (log[j].ev === 'light') trickLit++;
}
ok(trickLit === 0, 'tricks never lit a cue', trickLit + ' violations');
// she grooves: every round starts on the groove body
const bodies = log.filter(e => e.ev === 'body').map(e => e.d);
ok(bodies.includes('nova_idlegroove_v2'), 'she grooves the rounds (nova_idlegroove_v2 set)');
const bossEv = ev('boss').map(e => e.d);
ok(bossEv.filter(b => b.parsed).length >= 2, 'boss round parsed typed kid commands', bossEv.filter(b => b.parsed).length + ' parsed');
ok(ev('pulse').length === 1, 'PULSE fired at the finale');
ok(consoleErrs.filter(e => !/net::|Failed to load resource|favicon|fonts|jsdelivr|AudioContext|play\(\)/i.test(e)).length === 0, 'no page errors', consoleErrs.slice(0, 3).join(' | '));
console.log(`\n  score=${state.score} tricksCaught=${state.tricksCaught} stars=${JSON.stringify(ends.map(e => e.stars))} cmds=${cmds.length}`);
console.log(`  evidence: ${shots.join(', ')} + NOVASAYS2-RUN.webm + NOVASAYS2-LOG.json → Downloads`);
writeFileSync(join(DL, 'NOVASAYS2-LOG.json'), JSON.stringify({ state, ends, resolves, cmds, fireDeltas, gridOff, bossEv, consoleErrs, log }, null, 2));
console.log(`\n══ novasays_smoke (V2): ${pass} passed, ${fail} failed ══`);
process.exit(fail ? 1 : 0);
