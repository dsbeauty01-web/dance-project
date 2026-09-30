/* test/wave_onearm_probe.mjs — node test/wave_onearm_probe.mjs
   WHY THIS EXISTS: motion_detect_test.mjs only ever feeds WaveDetector a bump that travels the WHOLE
   6-joint chain (lWrist→lElbow→lShoulder→rShoulder→rElbow→rWrist) — a cross-body wave. The Wave game
   (beta/wave.html) asks for something else: Nova waves ONE arm and says "let it travel: fingers, wrist,
   elbow", and the certified judge (WaveRule) watches one arm's 3 joints.
   This probe feeds a *travelling single-arm* wave — the real game's move, which the suite never tests —
   and records what WaveDetector does with it. Same generator style as the suite. */
import { WaveDetector, WAVE_CHAIN } from '../shared/motion-detect.js';

let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const g = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * s; };
function armsOut(scale = 1, cx = 0.5){ const SW = 0.18 * scale, y = 0.38;
  return { lShoulder:{x:cx+SW/2,y}, rShoulder:{x:cx-SW/2,y}, lElbow:{x:cx+SW*1.2,y}, rElbow:{x:cx-SW*1.2,y}, lWrist:{x:cx+SW*1.9,y}, rWrist:{x:cx-SW*1.9,y},
    lHip:{x:cx+SW*0.35,y:y+SW*1.6}, rHip:{x:cx-SW*0.35,y:y+SW*1.6}, nose:{x:cx,y:y-SW*0.8}, SW }; }
function frame(base, lifts, jit = 0.004){ const k = {}; for (const n of Object.keys(base)) if (n !== 'SW'){ const p = base[n]; k[n] = { x:p.x+g(jit), y:p.y+g(jit), vis:0.85 }; }
  WAVE_CHAIN.forEach((n, i) => { k[n].y -= (lifts[i] || 0) * base.SW; }); return k; }

/* one arm only: the bump travels shoulder→elbow→wrist (the game's "let it travel" move).
   arm 'R' = chain indices 3,4,5 · arm 'L' = 2,1,0 */
function runOneArm({ arm = 'R', amp = 0.35, durS = 0.9, fps = 15, jit = 0.004, settle = 1.5 } = {}){
  const W = new WaveDetector(), base = armsOut(); let t = 0, done = null;
  const idx = arm === 'R' ? [3, 4, 5] : [2, 1, 0];
  for (let f = 0; f < settle * fps; f++){ t += 1 / fps; W.update(frame(base, [], jit), t); }
  const total = durS + 0.8;
  for (let f = 0; f < total * fps; f++){ t += 1 / fps; const u = (f / fps) / durS;
    const pos = u * 2;                                                        // 0→2 across the 3 joints
    const lifts = WAVE_CHAIN.map((_, i) => { const k = idx.indexOf(i); return (k < 0 || u > 1) ? 0 : amp * Math.exp(-Math.pow(k - pos, 2) / 0.5); });
    const r = W.update(frame(base, lifts, jit), t); if (r.done) done = r.done; }
  return done;
}

let caught = 0; const N = 60;
for (let i = 0; i < N; i++) if (runOneArm({ arm: i % 2 ? 'R' : 'L' })) caught++;

const span = WAVE_CHAIN.length - 1, o = new WaveDetector().o;
console.log(`WAVE_CHAIN (${WAVE_CHAIN.length} joints, span ${span}): ${WAVE_CHAIN.join(' → ')}`);
console.log(`thresholds: minJoints=${o.minJoints}  coverMin=${o.coverMin}  → a run must touch ≥${o.minJoints} joints AND span ≥${(o.coverMin * span).toFixed(1)} of ${span}`);
console.log(`one arm can only ever offer 3 joints spanning 2 of ${span} = cover ${(2 / span).toFixed(2)}`);
console.log(`\ntravelling SINGLE-ARM wave (shoulder→elbow→wrist), amp 0.35, 0.9s, 15fps: caught ${caught}/${N}`);
console.log(caught === 0
  ? '\nRESULT: 0/60 — WaveDetector cannot score a one-arm wave BY CONSTRUCTION, not by tuning.\n'
    + 'The Wave game and Nova\'s own demo clip are one-arm waves, so the new judge must stay on lights only\n'
    + 'until the founder decides whether the game should ask for a cross-body wave instead.'
  : `\nRESULT: ${caught}/${N} caught — re-read the thresholds above, this contradicts the arithmetic.`);
process.exit(0);
