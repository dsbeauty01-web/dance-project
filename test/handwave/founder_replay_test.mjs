/* THE FOUNDER'S REAL PLAY (13 Oct, his camera, his body) replayed through the engine.
   On v4.1 this run scored 16/22 — six steps died because his wrist was already up.
   v4.2's already-arrived rule must recover them. */
import { readFileSync } from 'node:fs';
import { HandWave, SONG_END, TARGETS } from '../../shared/handwave-core.js';
const d = JSON.parse(readFileSync(new URL('./founder_play.json', import.meta.url)));
const F = d.frames;
const kp = f => { const k = {}; for (const [n, v] of Object.entries(f)){ if (Array.isArray(v)) k[n] = { x: v[0], y: v[1], vis: v[2] }; } return k; };
const G = new HandWave();
for (const f of F.slice(0, 10)) G.calibrate(kp(f));
const evs = [];
for (const f of F){ if (G.ended) break; evs.push(...G.update(f.t, kp(f))); }
if (!G.ended) evs.push(...G.update(SONG_END + 2.7, kp(F.at(-1))));
const hits = evs.filter(e => e.type === 'hit'), S = (evs.find(e => e.type === 'end') || {}).summary || G.summary();
for (const c of TARGETS){
  const h = hits.find(h => h.target.idx === c.idx);
  console.log(`  step ${String(c.idx + 1).padStart(2)} ${c.joint.padEnd(9)} t=${c.t.toFixed(2)} → ${h ? `HIT at ${h.at >= 0 ? '+' : ''}${h.at} (${h.quality})` : 'MISS'}`);
}
console.log(`\nFOUNDER REPLAY: ${hits.length}/22 steps · ${S.stars}/${S.maxStars} stars · ${S.medal}  (was 16/22 on v4.1)`);
process.exit(hits.length >= 20 ? 0 : 1);
