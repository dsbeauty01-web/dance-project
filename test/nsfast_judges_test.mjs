/* test/nsfast_judges_test.mjs — run: node test/nsfast_judges_test.mjs
   Feeds synthetic MoveNet-like frames (jitter + keypoint flips) through the SHIPPED judges.js. */
import { readFileSync } from 'fs';
import { createJudges } from '../beta/nsfast/judges.js';
const S = JSON.parse(readFileSync(new URL('../beta/nsfast/script.json', import.meta.url)));
const T = S.tune;
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const gauss = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2*Math.log(u)) * Math.cos(2*Math.PI*v) * s; };

// a child standing ~2m back: shoulder width 0.20 (normalized), center x 0.5, shoulders y 0.40
const SW = 0.20, CX = 0.5, SY = 0.40;
const POSE = {
  rest:        { lW:[CX+0.13, SY+0.30], rW:[CX-0.13, SY+0.30], lE:[CX+0.12, SY+0.15], rE:[CX-0.12, SY+0.15] },
  armsUp:      { lW:[CX+0.14, SY-0.26], rW:[CX-0.14, SY-0.26], lE:[CX+0.13, SY-0.10], rE:[CX-0.13, SY-0.10] },
  oneArm:      { lW:[CX+0.14, SY-0.26], rW:[CX-0.13, SY+0.30], lE:[CX+0.13, SY-0.10], rE:[CX-0.12, SY+0.15] },
  armsOut:     { lW:[CX+0.34, SY+0.02], rW:[CX-0.34, SY+0.02], lE:[CX+0.22, SY+0.01], rE:[CX-0.22, SY+0.01] },
  handsOnHead: { lW:[CX+0.06, SY-0.14], rW:[CX-0.06, SY-0.14], lE:[CX+0.16, SY-0.06], rE:[CX-0.16, SY-0.06] },
};
let SCALE = 1;
function frame(p, jitter = 0.004, flip = 0.02, noseVis = 0.9){
  const P = POSE[p]; const j = () => gauss(jitter);
  const k = { lShoulder:{x:CX+SW/2+j(), y:SY+j(), vis:0.9}, rShoulder:{x:CX-SW/2+j(), y:SY+j(), vis:0.9},
    lElbow:{x:P.lE[0]+j(), y:P.lE[1]+j(), vis:0.85}, rElbow:{x:P.rE[0]+j(), y:P.rE[1]+j(), vis:0.85},
    lWrist:{x:P.lW[0]+j(), y:P.lW[1]+j(), vis:0.8}, rWrist:{x:P.rW[0]+j(), y:P.rW[1]+j(), vis:0.8},
    nose:{x:CX+j(), y:SY-0.14+j(), vis:noseVis} };
  if (rnd() < flip) k.lWrist.x += (rnd() < .5 ? -1 : 1) * 0.25;   // a keypoint flip
  if (SCALE !== 1) for (const j in k){ k[j].x = 0.5 + (k[j].x - 0.5) * SCALE + gauss(jitter); k[j].y = 0.5 + (k[j].y - 0.5) * SCALE + gauss(jitter); }   // pixel noise stays the same size → relatively LARGER on a far child
  return k;
}
const lerp = (a,b,u) => a + (b-a)*u;
function blend(p1, p2, u){ const A = POSE[p1], B = POSE[p2], o = {}; for (const key in A) o[key] = [lerp(A[key][0],B[key][0],u), lerp(A[key][1],B[key][1],u)]; return o; }

// run one window: script = array of [fromPose, toPose, startS, durS] segments; fps
function runWindow(J, kind, cmd, dur, script, fps = 15){
  const t0 = J._t; const W = new J.Window(kind, cmd, t0, dur); let r = null;
  for (let f = 0; f <= Math.ceil((dur + 0.6) * fps); f++){
    const t = t0 + f / fps, rel = t - t0;
    let pose = 'rest';
    for (const [a, b, s, d] of script){ if (rel >= s){ const u = Math.min(1, (rel - s) / d); POSE._tmp = blend(a, b, u); pose = '_tmp'; } }
    const k = frame(pose); J.update(k, t); J._t = t;
    r = W.feed(k, t); if (r) break;
  }
  return r || W.timeout(J._t + 1);
}
function fresh(){
  const J = createJudges(T); J._t = 0;
  // calibration: 2s still, then a practice arms-up
  J.startSample('still'); for (let f = 0; f < 30; f++){ J._t = f/15; J.update(frame('rest'), J._t); } J.stopSample();
  J.startSample('reach'); for (let f = 0; f < 30; f++){ const u = Math.min(1, f/12); POSE._tmp = blend('rest','armsUp',u); J._t += 1/15; J.update(frame('_tmp'), J._t); } J.stopSample();
  for (let f = 0; f < 20; f++){ const u = Math.min(1, f/10); POSE._tmp = blend('armsUp','rest',u); J._t += 1/15; J.update(frame('_tmp'), J._t); }
  const cal = J.finishCalibration(); J._cal = cal; return J;
}
let pass = 0, fail = 0; const out = [];
function check(name, n, fn, want){ let ok = 0; for (let i = 0; i < n; i++){ if (fn() === want) ok++; }
  const pct = ok / n * 100; const good = pct >= (want === 'held' || want === 'miss' ? 98 : 90);
  good ? pass++ : fail++; out.push(`${good ? 'PASS' : 'FAIL'}  ${name.padEnd(46)} ${ok}/${n} (${pct.toFixed(0)}%) want ${want}`); }

const J0 = fresh(); console.log('[CAL]', JSON.stringify(J0._cal));
const CMDS = ['armsUp','oneArm','armsOut','handsOnHead'];
for (const c of CMDS){
  check(`real ${c}: child does it at 0.4s`, 60, () => { const J = fresh(); return runWindow(J,'real',c,2.0,[['rest',c,0.4,0.4]]); }, 'hit');
  check(`real ${c}: child stays still`, 60, () => { const J = fresh(); return runWindow(J,'real',c,2.0,[]); }, 'miss');
  check(`trick ${c}: child stays still`, 120, () => { const J = fresh(); return runWindow(J,'trick',c,2.0,[]); }, 'held');
  check(`trick ${c}: child does it (caught)`, 60, () => { const J = fresh(); return runWindow(J,'trick',c,2.0,[['rest',c,0.4,0.4]]); }, 'gotcha');
}
check('trick: child still lowering arms from last cmd', 60, () => { const J = fresh(); return runWindow(J,'trick','armsOut',2.0,[['armsUp','rest',0,0.6]]); }, 'held');
check('trick armsUp: child KEEPS arms up (didn\'t move)', 60, () => { const J = fresh(); return runWindow(J,'trick','armsUp',2.0,[['armsUp','armsUp',0,0.1]]); }, 'held');
check('real freeze: child holds still', 60, () => { const J = fresh(); return runWindow(J,'real','freeze',2.2,[]); }, 'hit');
check('real freeze: child keeps dancing', 60, () => { const J = fresh(); return runWindow(J,'real','freeze',2.2,[['rest','armsUp',0,0.5],['armsUp','armsOut',0.5,0.5],['armsOut','rest',1.0,0.5],['rest','armsUp',1.5,0.5]]); }, 'miss');
check('real armsUp at 8fps (slow laptop)', 60, () => { const J = fresh(); const t0=J._t; const W=new J.Window('real','armsUp',t0,2.0); let r=null; for(let f=0;f<=24;f++){ const t=t0+f/8, rel=t-t0; POSE._tmp=blend('rest','armsUp',Math.max(0,Math.min(1,(rel-0.4)/0.4))); const k=frame('_tmp'); J.update(k,t); r=W.feed(k,t); if(r) break;} return r; }, 'hit');
for (const [cmd, did] of [['armsUp','handsOnHead'],['handsOnHead','armsUp'],['armsOut','armsUp'],['armsUp','armsOut'],['handsOnHead','armsOut']])
  check(`real ${cmd}: child does ${did} instead`, 60, () => { const J = fresh(); return runWindow(J,'real',cmd,2.0,[['rest',did,0.4,0.4]]); }, 'miss');
check('real armsUp: wrists leave the TOP of the frame (close child)', 60, () => { const J = fresh(); const t0=J._t; const W=new J.Window('real','armsUp',t0,2.0); let r=null;
  for (let f=0; f<=40; f++){ const t=t0+f/15, rel=t-t0; POSE._tmp=blend('rest','armsUp',Math.max(0,Math.min(1,(rel-0.4)/0.4))); const k=frame('_tmp');
    if (rel > 0.7){ k.lWrist.vis = 0.1; k.rWrist.vis = 0.1; } J.update(k,t); r=W.feed(k,t); if(r) break; } return r; }, 'hit');
SCALE = 0.5;
for (const c of ['armsUp','armsOut','handsOnHead']){
  check(`FAR child (half size) real ${c}`, 60, () => { const J = fresh(); return runWindow(J,'real',c,2.0,[['rest',c,0.4,0.4]]); }, 'hit');
  check(`FAR child (half size) trick ${c}: still`, 120, () => { const J = fresh(); return runWindow(J,'trick',c,2.0,[]); }, 'held'); }
SCALE = 1;
console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
