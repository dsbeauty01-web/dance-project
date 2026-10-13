/* NOVA REPLAYS HER OWN GAME (v4 chain) — her real clip (856 tracked frames), mirrored to child space. */
import { readFileSync } from 'node:fs';
import { HandWave, TARGETS, SONG_END } from '../../shared/handwave-core.js';
const frames = JSON.parse(readFileSync(new URL('./her_frames.json', import.meta.url)));
const W = 720;
const SWAP = { lWrist:'rWrist', rWrist:'lWrist', lElbow:'rElbow', rElbow:'lElbow', lShoulder:'rShoulder', rShoulder:'lShoulder', nose:'nose' };
const mirror = r => { const k = {}; for (const [n, v] of Object.entries(r)){ if (n === 't') continue; const m = SWAP[n]; if (m) k[m] = { x: W - v[0], y: v[1], vis: v[2] }; } return k; };
const G = new HandWave();
G.calibrate(mirror(frames[0]));
const evs = [];
for (const r of frames){ if (G.ended) break; evs.push(...G.update(r.t, mirror(r))); }
if (!G.ended) evs.push(...G.update(SONG_END + 2.7, mirror(frames.at(-1))));
const hits = evs.filter(e => e.type === 'hit'), S = (evs.find(e => e.type === 'end') || {}).summary || G.summary();
let pass = 0, fail = 0; const out = [];
const ok = (n, c, x='') => { c ? pass++ : fail++; out.push(`${c?'PASS':'FAIL'}  ${n}${c?'':'   ← '+String(x).slice(0,160)}`); };
for (const c of TARGETS){
  const h = hits.find(h => h.target.idx === c.idx);
  out.push(`  step ${String(c.idx+1).padStart(2)} ${c.joint.padEnd(9)} t=${c.t.toFixed(2)} → ${h ? `HIT at ${h.at>=0?'+':''}${h.at}s (${h.quality})` : 'MISS'}`);
}
ok('Nova hits ≥ 20 of her own 22 steps', hits.length >= 20, 'hits='+hits.length+' missed='+TARGETS.filter(c=>!hits.find(h=>h.target.idx===c.idx)).map(c=>c.idx+':'+c.joint));
ok('Nova scores GOLD on her own game', S.medal === 'gold', `stars=${S.stars}/${S.maxStars}`);
ok('the game ends', G.ended);
console.log(out.join('\n'));
console.log(`\nNOVA REPLAY v4: ${S.stars}/${S.maxStars} stars · ${S.medal} · ${hits.length}/22 steps\n${pass} pass · ${fail} fail`);
process.exit(fail ? 1 : 0);
