/* test/freeze2_hold_test.mjs — node test/freeze2_hold_test.mjs */
import { readFileSync } from 'fs';
import { createJudges } from '../beta/freeze2/judges.js';
import { Hold } from '../beta/freeze2/hold.js';
const S = JSON.parse(readFileSync(new URL('../beta/freeze2/script.json', import.meta.url))); const T = S.tune;
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const gauss = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)*s; };
const SW = 0.2, CX = 0.5, SY = 0.4;
// pose(t): arms swinging while dancing, still otherwise
function frame(dancing, t, jitter = 0.004, flip = 0.02, visible = true){
  const amp = dancing === 'fidget' ? 0.12 : 1;
  const a = dancing ? Math.sin(t * 7) * 0.12 * amp : 0, b = dancing ? Math.cos(t * 5) * 0.06 * amp : 0; const j = () => gauss(jitter);
  const v = visible ? 0.85 : 0.1;
  const k = { lShoulder:{x:CX+SW/2+j()+b*0.3,y:SY+j(),vis:v}, rShoulder:{x:CX-SW/2+j()+b*0.3,y:SY+j(),vis:v},
    lElbow:{x:CX+0.12+j()+b,y:SY+0.15-a+j(),vis:v}, rElbow:{x:CX-0.12+j()+b,y:SY+0.15+a+j(),vis:v},
    lWrist:{x:CX+0.13+j()+b,y:SY+0.3-2*a+j(),vis:v}, rWrist:{x:CX-0.13+j()+b,y:SY+0.3+2*a+j(),vis:v}, nose:{x:CX+j(),y:SY-0.14+j(),vis:v} };
  if (rnd() < flip) k.lWrist.x += (rnd() < .5 ? -1 : 1) * 0.25;
  return k;
}
// a scenario: dance until the stop, then behave per `after(tRel)` → {dancing, visible}
function run(after, hold = 2.5, fps = 15){
  const J = createJudges(T); let t = 0;
  J.startSample('still'); for (let f = 0; f < 30; f++){ t += 1/fps; J.update(frame(false, t), t); } J.stopSample(); J.finishCalibration();
  for (let f = 0; f < 45; f++){ t += 1/fps; J.update(frame(true, t), t); }                 // 3s of dancing before the stop
  const t0 = t, H = new Hold(J, t0, hold, T);
  for (let f = 0; f <= Math.ceil((hold + 0.3) * fps); f++){ t += 1/fps; const s = after(t - t0); const k = frame(s.dancing, t, 0.004, 0.02, s.visible !== false); J.update(k, t); const r = H.feed(k, t); if (r) return r; }
  return H.finish();
}
let pass = 0, fail = 0; const out = [];
function check(name, n, fn, want, minPct = 95){ let ok = 0; for (let i = 0; i < n; i++) if (fn() === want) ok++;
  const p = ok/n*100, good = p >= minPct; good ? pass++ : fail++; out.push(`${good?'PASS':'FAIL'}  ${name.padEnd(52)} ${ok}/${n} (${p.toFixed(0)}%) want ${want}`); }
check('stops within 0.4s (normal kid) → held', 80, () => run(tr => ({ dancing: tr < 0.4 })), 'held');
check('stops at 0.55s (slow to stop, inside grace) → held', 80, () => run(tr => ({ dancing: tr < 0.55 })), 'held');
check('perfectly still all hold → held', 80, () => run(() => ({ dancing: false })), 'held');
check('starts dancing again at 1.8s (late break) → almost', 80, () => run(tr => ({ dancing: tr < 0.3 || tr > 1.8 })), 'almost');
check('keeps dancing through the whole hold → missed', 80, () => run(() => ({ dancing: true })), 'missed');
check('breaks at 1.0s → missed', 80, () => run(tr => ({ dancing: tr < 0.3 || tr > 1.0 })), 'missed');
check('walks out of frame → noshow', 40, () => run(tr => ({ dancing: false, visible: false })), 'noshow');
check('star freeze 5s, still → held', 60, () => run(tr => ({ dancing: tr < 0.4 }), 5.0), 'held');
check('star freeze 5s, breaks at 3.5s → almost', 60, () => run(tr => ({ dancing: tr < 0.4 || tr > 3.5 }), 5.0), 'almost');
check('slow laptop 8fps, still → held', 60, () => run(tr => ({ dancing: tr < 0.4 }), 2.5, 8), 'held');
check('fidgets a little while frozen (wobbly kid) → held', 80, () => run(tr => ({ dancing: tr < 0.4 ? true : 'fidget' })), 'held');
// confidence for praise specificity
{ let hi=0,n=60; for(let i=0;i<n;i++){ const J=createJudges(T); let t=0; J.startSample('still'); for(let f=0;f<30;f++){t+=1/15;J.update(frame(false,t),t);} J.stopSample(); J.finishCalibration();
    const H=new Hold(J,t,2.5,T); for(let f=0;f<=45;f++){t+=1/15;const k=frame(false,t);J.update(k,t);H.feed(k,t);} H.finish(); if(H.confidence()>=0.8) hi++; }
  const ok=hi/n>=0.9; ok?pass++:fail++; out.push(`${ok?'PASS':'FAIL'}  still child → high confidence (specific praise)          ${hi}/${n}`); }
{ const J=createJudges(T); let t=0; J.startSample('still'); for(let f=0;f<30;f++){t+=1/15;J.update(frame(false,t),t);} J.stopSample(); J.finishCalibration();
  const H=new Hold(J,t,2.5,T); for(let f=0;f<=45;f++){t+=1/15;const k=frame(false,t,0.004,0.02,false);J.update(k,t);H.feed(k,t);} H.finish();
  const ok=H.confidence()<=0.3; ok?pass++:fail++; out.push(`${ok?'PASS':'FAIL'}  out of frame → low confidence (stay quiet)`); }
console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
