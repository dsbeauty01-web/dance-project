/* test/proof/perf.mjs — night item F: frame rate of every game with the CPU throttled 4× (a mid laptop), replay mode.
   Counts two things for 10 s mid-game: the light layer's frames (requestAnimationFrame) and the frames the game
   actually judged (play.js counts every onFrame call in window.__fedFrames). Target ≥ 24 fps.
   node test/proof/perf.mjs [throttle=4] */
import { serve, launch } from '../lib/browser.mjs';

const THROTTLE = +(process.argv[2] || 4);
const RUNS = [
  { game: 'freeze', path: 'beta/freeze3.html?replay=dance-hype&fast=1' },
  { game: 'copy',   path: 'beta/copy.html?replay=pose-armsup&poses=armsUp,star,bear' },
  { game: 'groove', path: 'beta/groove.html?replay=dance-hype' },
];
const { srv, url } = await serve(); const browser = await launch(); const rows = [];
try {
  for (const r of RUNS){
    const ctx = await browser.newContext({ viewport: { width: 432, height: 768 } }); const p = await ctx.newPage();
    const cdp = await ctx.newCDPSession(p); await cdp.send('Emulation.setCPUThrottlingRate', { rate: THROTTLE });
    await p.goto(`${url}/${r.path}&checked=1&autostart=1`); await p.waitForTimeout(4000);
    const m = await p.evaluate(() => new Promise(ok => {
      let raf = 0; const f0 = window.__fedFrames || 0, t0 = performance.now();
      const tick = () => { raf++; if (performance.now() - t0 < 10000) requestAnimationFrame(tick); else ok({ raf: raf / ((performance.now() - t0) / 1000), fed: ((window.__fedFrames || 0) - f0) / ((performance.now() - t0) / 1000) }); };
      requestAnimationFrame(tick); }));
    rows.push({ game: r.game, throttle: THROTTLE + '×', 'lights fps': m.raf.toFixed(1), 'judged fps': m.fed.toFixed(1), verdict: m.raf >= 24 && m.fed >= 24 ? 'PASS' : 'BELOW 24' });
    await ctx.close();
  }
} finally { await browser.close(); srv.close(); }
console.log('| game | CPU | lights fps | judged fps | ≥ 24? |\n|---|---|---|---|---|');
for (const r of rows) console.log(`| ${r.game} | ${r.throttle} | ${r['lights fps']} | ${r['judged fps']} | ${r.verdict} |`);
