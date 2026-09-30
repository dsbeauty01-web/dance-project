/* test/motion_detect_test.mjs — node test/motion_detect_test.mjs */
import { WaveDetector, BounceDetector, scoreHit, WAVE_CHAIN, ARM_CHAINS } from '../shared/motion-detect.js';
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const g = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * s; };
let pass = 0, fail = 0; const out = [];
function check(name, n, fn, want = true, minPct = 90){ let ok = 0; for (let i = 0; i < n; i++) if (fn() === want) ok++;
  const good = ok / n * 100 >= minPct; good ? pass++ : fail++; out.push(`${good ? 'PASS' : 'FAIL'}  ${name.padEnd(60)} ${ok}/${n}`); }

/* a child with arms held OUT (the wave start pose); SW = shoulder width, scale = distance from camera */
function armsOut(scale = 1, cx = 0.5){ const SW = 0.18 * scale, y = 0.38;
  return { lShoulder:{x:cx+SW/2,y}, rShoulder:{x:cx-SW/2,y}, lElbow:{x:cx+SW*1.2,y}, rElbow:{x:cx-SW*1.2,y}, lWrist:{x:cx+SW*1.9,y}, rWrist:{x:cx-SW*1.9,y},
    lHip:{x:cx+SW*0.35,y:y+SW*1.6}, rHip:{x:cx-SW*0.35,y:y+SW*1.6}, nose:{x:cx,y:y-SW*0.8}, SW }; }
function frame(base, lifts, jit = 0.004){ const k = {}; for (const n of Object.keys(base)) if (n !== 'SW'){ const p = base[n]; k[n] = { x: p.x + g(jit), y: p.y + g(jit), vis: 0.85 }; }
  WAVE_CHAIN.forEach((n, i) => { k[n].y -= (lifts[i] || 0) * base.SW; }); return k; }
/* a bump travelling along the chain: dir +1 = lWrist→rWrist; amplitude in shoulder widths; durS = travel time */
function runWave({ dir = 1, amp = 0.35, durS = 1.4, fps = 15, scale = 1, jit = 0.004, settle = 1.5, mode = 'wave' } = {}){
  const W = new WaveDetector({ mode: 'body' }), base = armsOut(scale); let t = 0, done = null;
  for (let f = 0; f < settle * fps; f++){ t += 1 / fps; W.update(frame(base, [], jit), t); }        // hold arms out
  const total = durS + 0.8;
  for (let f = 0; f < total * fps; f++){ t += 1 / fps; const u = (f / fps) / durS;
    let lifts;
    if (mode === 'wave'){ const pos = dir === 1 ? u * 5 : 5 - u * 5; lifts = WAVE_CHAIN.map((_, i) => u <= 1 ? amp * Math.exp(-Math.pow(i - pos, 2) / 0.8) * (i === 2 || i === 3 ? 0.5 : 1) : 0); }
    if (mode === 'rightArm'){ lifts = [0, 0, 0, 0, amp * Math.min(1, u * 3), amp * Math.min(1, u * 3)]; }
    if (mode === 'bothUp'){ lifts = WAVE_CHAIN.map(() => amp * Math.min(1, u * 3)); }
    if (mode === 'bothUpDown'){ lifts = WAVE_CHAIN.map(() => amp * Math.max(0, Math.sin(Math.PI * Math.min(1, u)))); }
    if (mode === 'still'){ lifts = []; }
    if (mode === 'wiggle'){ if (!runWave.r || f === 0) runWave.r = WAVE_CHAIN.map(() => ({ t0: rnd() * total, d: 0.3 + rnd() * 0.4 })); lifts = WAVE_CHAIN.map((_, i) => { const r = runWave.r[i], x = (f / fps - r.t0) / r.d; return x > 0 && x < 1 ? amp * Math.sin(Math.PI * x) : 0; }); }   // each joint bumps once at a RANDOM time
    const r = W.update(frame(base, lifts, jit), t); if (r.done) done = r.done; }
  return done;
}
check('BODY wave left→right is detected', 60, () => runWave({ dir: 1 })?.dir === 'L→R');
check('BODY wave right→left is detected', 60, () => runWave({ dir: -1 })?.dir === 'R→L');
check('slow wave (2.6s) is detected', 40, () => !!runWave({ durS: 2.6 }));
check('KNOWN LIMIT — small wave (0.2 shoulder widths): caught ≥ 65%', 40, () => !!runWave({ amp: 0.2 }), true, 65);
check('KNOWN LIMIT — far child (half size): caught ≥ 70% (fix: "come closer" cue)', 40, () => !!runWave({ scale: 0.5 }), true, 70);
check('slow laptop 8fps is detected', 40, () => !!runWave({ fps: 8 }));
check('raising one arm is NOT a wave', 60, () => !runWave({ mode: 'rightArm' }));
check('both arms up together is NOT a wave', 60, () => !runWave({ mode: 'bothUp' }));
check('both arms up then down together is NOT a wave', 60, () => !runWave({ mode: 'bothUpDown' }));
check('standing still is NOT a wave', 60, () => !runWave({ mode: 'still' }));
check('random bumps on random joints are NOT a wave (most of the time)', 60, () => !runWave({ mode: 'wiggle', amp: 0.35 }), true, 80);

/* bouncing child: mid-body goes down by `dip` torso-lengths at each beat */
function runBounce({ bpm = 64, dipAmp = 0.08, offsetMs = 0, fps = 15, beats = 12, jit = 0.004, mode = 'bounce', scale = 1, noHips = false } = {}){
  const B = new BounceDetector(), period = 60 / bpm, base = armsOut(scale), torsoPx = base.SW * 1.6; const hits = []; let t = 0;
  const beatAt = 1.0;
  for (let f = 0; f < (beatAt + beats * period + 0.5) * fps; f++){ t += 1 / fps;
    let d = 0;
    if (mode === 'bounce'){ const ph = ((t - beatAt - offsetMs / 1000) / period) % 1; const p = ph < 0 ? ph + 1 : ph; d = dipAmp * Math.pow(Math.cos(Math.PI * p), 2) * (t > beatAt - 0.3 ? 1 : 0); }  // deepest AT the beat
    if (mode === 'sway'){ d = 0.01 * Math.sin(t * 2); }
    const k = frame(base, [], jit); for (const n of ['lShoulder','rShoulder','lHip','rHip','lElbow','rElbow','lWrist','rWrist','nose']) k[n].y += d * torsoPx;
    if (noHips){ k.lHip.vis = 0.05; k.rHip.vis = 0.05; }
    const h = B.update(k, t); if (h) hits.push(h.t); }
  return { hits, beatAt, period };
}
const graded = (r, lat = 0) => r.hits.map(h => scoreHit(h + lat, r.beatAt, r.period, { latencyS: lat }).grade);
check('bouncing on the beat → ≥ 9 of 12 hits graded "on"', 40, () => graded(runBounce({})).filter(x => x === 'on').length >= 9);
check('bouncing 300ms late → mostly NOT "on"', 40, () => { const gr = graded(runBounce({ offsetMs: 300 })); return gr.filter(x => x === 'on').length <= 2; });
check('fast song (100 bpm) on the beat → ≥ 9 of 12 "on"', 40, () => graded(runBounce({ bpm: 100 })).filter(x => x === 'on').length >= 9);
check('far child bouncing → ≥ 9 of 12 "on"', 40, () => graded(runBounce({ scale: 0.5 })).filter(x => x === 'on').length >= 9);
check('8fps laptop bouncing → ≥ 8 of 12 "on"', 40, () => graded(runBounce({ fps: 8 })).filter(x => x === 'on').length >= 8);
check('standing still → no bounces at all', 40, () => runBounce({ mode: 'sway' }).hits.length === 0);
check('tiny dips (0.02) are ignored', 40, () => runBounce({ dipAmp: 0.02 }).hits.length === 0);
check('hips out of frame → bounce still graded from the shoulders (≥ 9 of 12 on)', 40, () => graded(runBounce({ noHips: true })).filter(x => x === 'on').length >= 9);
check('hips out of frame + standing still → no bounces', 40, () => runBounce({ mode: 'sway', noHips: true }).hits.length === 0);
check('camera latency is compensated (hits seen 80ms late still "on")', 40, () => graded(runBounce({}), 0.08).filter(x => x === 'on').length >= 9);


/* ───── ONE-ARM wave (the game's real wave) ───── */
function frameArm(base, side, lifts, jit = 0.004){ const k = {}; for (const n of Object.keys(base)) if (n !== 'SW'){ const p = base[n]; k[n] = { x: p.x + g(jit), y: p.y + g(jit), vis: 0.85 }; }
  ARM_CHAINS[side].forEach((n, i) => { k[n].y -= (lifts[i] || 0) * base.SW; }); return k; }
function runArm({ side = 'right', dir = 'out', amps = [0.15, 0.3, 0.35], durS = 0.9, fps = 15, scale = 1, jit = 0.004, mode = 'wave' } = {}){
  const W = new WaveDetector(), base = armsOut(scale); let t = 0, done = null, fronts = 0;
  for (let f = 0; f < 1.5 * fps; f++){ t += 1 / fps; W.update(frameArm(base, side, []), t); }
  const total = durS + 1.2;
  for (let f = 0; f < total * fps; f++){ t += 1 / fps; const u = (f / fps) / durS; let lifts = [];
    if (mode === 'wave'){ const pos = dir === 'out' ? u * 2 : 2 - u * 2; lifts = [0, 1, 2].map(i => u <= 1 ? amps[i] * Math.exp(-Math.pow(i - pos, 2) / 0.35) : 0); }
    if (mode === 'raise'){ lifts = [0, amps[1], amps[2]].map(a => a * Math.max(0, Math.sin(Math.PI * Math.min(1, u)))); }       // lift the arm up and down (elbow + wrist together)
    if (mode === 'shrug'){ lifts = [amps[0] * 1.5 * Math.max(0, Math.sin(Math.PI * Math.min(1, u))), 0.05, 0.05]; }
    const r = W.update(frameArm(base, side, lifts, jit), t); if (r.front != null) fronts++; if (r.done) done = r.done; }
  return { done, fronts };
}
check('ARM wave, right arm, shoulder→wrist ("out") is detected', 60, () => { const d = runArm({}).done; return d?.arm === 'right' && d?.dir === 'out'; });
check('ARM wave, left arm, wrist→shoulder ("in") is detected', 60, () => { const d = runArm({ side: 'left', dir: 'in' }).done; return d?.arm === 'left' && d?.dir === 'in'; });
check('ARM wave, slow (1.8s) is detected', 40, () => !!runArm({ durS: 1.8 }).done);
check('ARM wave, fast (0.5s) is detected', 40, () => !!runArm({ durS: 0.5 }).done, true, 85);
check('ARM wave, slow laptop 8fps is detected', 40, () => !!runArm({ fps: 8 }).done);
check('ARM wave, far child (half size) is detected', 40, () => !!runArm({ scale: 0.5 }).done);
check('ARM wave drives the comet (a front is reported during the wave)', 40, () => runArm({}).fronts >= 6);
check('raising the arm up and down is NOT a wave', 60, () => !runArm({ mode: 'raise' }).done);
check('a shoulder shrug is NOT a wave', 60, () => !runArm({ mode: 'shrug' }).done);
check('a slow arm raise (1.8s) is NOT a wave', 60, () => !runArm({ mode: 'raise', durS: 1.8 }).done);
check('ARM wave with almost no shoulder pop (elbow→wrist only) is detected', 40, () => !!runArm({ amps: [0.06, 0.3, 0.35] }).done);
check('arm raise on an 8fps laptop is NOT a wave', 60, () => !runArm({ mode: 'raise', fps: 8 }).done);
check('arm raise by a far child is NOT a wave', 60, () => !runArm({ mode: 'raise', scale: 0.5 }).done, true, 90);
check('fast arm raise (0.4s) is NOT a wave', 60, () => !runArm({ mode: 'raise', durS: 0.4 }).done);

console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
