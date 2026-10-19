# ENGINE-DETECT — the joint-mover engine (one shared DETECTION engine for every game · full code · CLI deploys)

Read `.claude/skills/movement-tracking/SKILL.md` first. Builds `shared/mover-engine.js` on top of `shared/pose-adapter.js` (named joints — MoveNet or MediaPipe, engine-agnostic). Touch no game page in this session; ship the engine + its test harness + evidence. Tag `beta-b0.11`.

## THE IDEA
Every frame, for every named joint: **where** (smoothed), **which way + how fast** (velocity → L/R/UP/DOWN), **how big** (relative to THIS kid's calibrated range), **isolated?** (did reference joints stay still). Every dance move = a one-line RULE on top. Games never touch raw joints again.

## 1 · shared/mover-engine.js (complete)
```js
// ── the engine ────────────────────────────────────────────────────────────────
export const REF = {            // derived points from named joints (toNova output)
  shoulderC: k => mid(k.lShoulder, k.rShoulder),
  hipC:      k => mid(k.lHip, k.rHip),
  head:      k => k.nose,
};
const mid = (a,b) => (a&&b) ? { x:(a.x+b.x)/2, y:(a.y+b.y)/2, vis:Math.min(a.vis,b.vis) } : null;

export class MoverEngine {
  constructor(opts={}){
    this.alpha = opts.alpha ?? 0.4;            // EMA weight of the new frame
    this.visMin = opts.visMin ?? 0.5;
    this.state = {};                           // name → {x,y,vx,vy,t,mag}
    this.cal = null;                           // per-kid calibration
    this.calBuf = {};                          // name → samples during calibration window
    this.calibrating = false;
  }
  // ── calibration (a no-score window: intro/demo) ──
  startCal(){ this.calibrating = true; this.calBuf = {}; }
  finishCal(){
    const cal = { range:{}, base:{} };
    for (const [n, arr] of Object.entries(this.calBuf)){
      const xs = arr.map(p=>p.x).sort((a,b)=>a-b), ys = arr.map(p=>p.y).sort((a,b)=>a-b);
      const p = (s,q) => s[Math.floor(s.length*q)];
      cal.range[n] = { x: Math.max(0.02, p(xs,.9)-p(xs,.1)), y: Math.max(0.02, p(ys,.9)-p(ys,.1)) };
      cal.base[n]  = { x: p(xs,.5), y: p(ys,.5) };
    }
    cal.body = cal.range.shoulderC ? Math.max(cal.range.shoulderC.x, 0.06) : 0.1;   // the kid's own scale
    this.cal = cal; this.calibrating = false; console.log('[CAL]', JSON.stringify(cal)); return cal;
  }
  // ── per frame ──
  update(k, t=performance.now()){
    const pts = { ...k, shoulderC: REF.shoulderC(k), hipC: REF.hipC(k), head: REF.head(k) };
    const out = {};
    for (const [n, p] of Object.entries(pts)){
      if (!p || p.vis < this.visMin) continue;
      const s = this.state[n];
      if (!s){ this.state[n] = { x:p.x, y:p.y, vx:0, vy:0, t }; continue; }
      const dt = Math.max(1, t - s.t) / 1000;
      const x = s.x*(1-this.alpha) + p.x*this.alpha, y = s.y*(1-this.alpha) + p.y*this.alpha;
      const vx = (x - s.x)/dt, vy = (y - s.y)/dt;                 // normalized units / second
      Object.assign(s, { x, y, vx, vy, t });
      if (this.calibrating) (this.calBuf[n] ||= []).push({x,y});
      const dx = this.cal ? (x - this.cal.base[n]?.x) : 0, dy = this.cal ? (y - this.cal.base[n]?.y) : 0;
      const scale = this.cal?.body ?? 0.1;
      out[n] = { x, y, vx, vy,
        dx: dx/scale, dy: dy/scale,                                  // displacement from base, in body-units
        dir: dirOf(vx, vy),                                           // 'L'|'R'|'UP'|'DOWN'|null
        mag: Math.hypot(vx, vy)/scale,                                // speed in body-units/s
        vis: p.vis };
    }
    this.last = out; return out;
  }
  // ── the primitives every rule uses ──
  moved(n, axis, thr=0.35){ const j=this.last?.[n]; if(!j) return null;      // |displacement| beyond thr body-units
    const d = axis==='x' ? j.dx : j.dy; return Math.abs(d) >= thr ? (d>0 ? (axis==='x'?'R':'DOWN') : (axis==='x'?'L':'UP')) : null; }
  still(n, thr=0.12){ const j=this.last?.[n]; return j ? j.mag < thr : null; }
  isolated(mover, refs, thr=0.12){ return refs.every(r => this.still(r, thr)); }
  energy(names){ const js = names.map(n=>this.last?.[n]).filter(Boolean); return js.length ? js.reduce((s,j)=>s+j.mag,0)/js.length : null; }
  dist(a,b){ const A=this.last?.[a], B=this.last?.[b]; return (A&&B) ? Math.hypot(A.x-B.x, A.y-B.y) : null; }
}
function dirOf(vx, vy, min=0.15){ if (Math.hypot(vx,vy) < min) return null; return Math.abs(vx) > Math.abs(vy) ? (vx>0?'R':'L') : (vy>0?'DOWN':'UP'); }
```
(Mirror law: the usercam is scaleX(-1) — engine works in raw camera coords; games map 'L'/'R' to screen-space via one constant `MIRROR=true` at the page level. Verify once on screen with `?pose=1`.)

## 2 · shared/mover-rules.js — the move library (rules on the engine)
```js
import { MoverEngine } from './mover-engine.js';
export const RULES = {
  // ISOLATIONS — mover + must-be-still references. Return {hit:true, side, iso} or null.
  shoulderPop:  E => { const l=E.moved('lShoulder','y',0.3), r=E.moved('rShoulder','y',0.3);
                       const side = l==='UP'&&r==='UP' ? 'BOTH' : l==='UP' ? 'L' : r==='UP' ? 'R' : null;
                       return side ? { hit:true, side, iso:E.isolated('shoulderC',['hipC']) } : null; },
  shoulderSlide:E => { const d=E.moved('shoulderC','x',0.35); return d ? { hit:true, side:d, iso:E.isolated('shoulderC',['hipC','head']) } : null; },
  ribSlide:     E => { const d=E.moved('shoulderC','x',0.35);        // TRUE rib isolation: ribs travel, hips AND head stay
                       return d ? { hit:true, side:d, iso:E.isolated('shoulderC',['hipC','head'], 0.10) } : null; },
  hipSlide:     E => { const d=E.moved('hipC','x',0.35); return d ? { hit:true, side:d, iso:E.isolated('hipC',['shoulderC']) } : null; },
  hipBounce:    E => { const d=E.moved('hipC','y',0.25); return d ? { hit:true, side:d, iso:E.isolated('hipC',['shoulderC']) } : null; },
  headSlide:    E => { const d=E.moved('head','x',0.3);  return d ? { hit:true, side:d, iso:E.isolated('head',['shoulderC']) } : null; },
  headNod:      E => { const d=E.moved('head','y',0.25); return d ? { hit:true, side:d, iso:E.isolated('head',['shoulderC']) } : null; },
  armRaise:     E => { const l=E.moved('lWrist','y',0.6), r=E.moved('rWrist','y',0.6); const s = l==='UP'&&r==='UP'?'BOTH':l==='UP'?'L':r==='UP'?'R':null; return s?{hit:true,side:s}:null; },
  // FREEZE
  freeze:       (E, thr=0.12) => ({ still: E.energy(['shoulderC','hipC','lWrist','rWrist','head']) < thr }),
  // CLAP — wrists converge fast (fuse with audio transient if available: onsetMs within ±120ms → confident)
  clap:         (E, audioOnsetMs=null, t=performance.now()) => { const d=E.dist('lWrist','rWrist'); const fast = (E.last?.lWrist?.mag ?? 0) > 0.8;
                       const visual = d!=null && d < 0.06 && fast; if(!visual) return null;
                       const fused = audioOnsetMs!=null && Math.abs(t-audioOnsetMs) < 120; return { hit:true, confidence: fused ? 1 : 0.6 }; },
  // JUMP — both hips rise fast together
  jump:         E => (E.last?.hipC?.dir==='UP' && E.last.hipC.mag > 1.2) ? { hit:true } : null,
};
// WAVE — traveling peak along the arm chain (order + even spacing = smooth). Stateful: keep a small history.
export class WaveRule {
  constructor(E, arm){ this.E=E; this.chain = arm==='R' ? ['rShoulder','rElbow','rWrist','rIndex'] : ['lShoulder','lElbow','lWrist','lIndex']; this.h={}; this.lastT=0; }
  push(t){ for (const n of this.chain){ const j=this.E.last?.[n]; if(!j) continue; (this.h[n] ||= []).push({t, y:j.y}); this.h[n] = this.h[n].filter(p=>t-p.t<1200); } }
  peakT(n){ const h=this.h[n]; if(!h||h.length<5) return null; for(let i=h.length-3;i>1;i--) if(h[i].y<h[i-1].y && h[i].y<h[i+1].y && (h[i-1].y-h[i].y) > 0.02) return h[i].t; return null; }
  check(t=performance.now()){ this.push(t); if (t-this.lastT < 600) return null;
    const chain = this.chain.filter(n => this.E.last?.[n]);             // rIndex exists only on MediaPipe → chain adapts (3 or 4 links)
    const peaks = chain.map(n=>this.peakT(n)); if (peaks.some(p=>p==null)) return null;
    const gaps = peaks.slice(1).map((p,i)=>p-peaks[i]); if (!gaps.every(g=>g>40 && g<400)) return null;
    const spread = Math.max(...gaps)-Math.min(...gaps); this.lastT = t;
    const other = this.chain[0]==='rShoulder' ? 'lWrist' : 'rWrist';
    return { hit:true, quality: spread<90?'smooth':spread<180?'good':'rough', gaps, iso: this.E.still(other, 0.2) }; }
}
```

## 3 · Windows + graded timing (shared/cue-window.js)
```js
export function grade(t, target, win){ const d=Math.abs(t-target); if (d>win) return null; return d < win*0.33 ? 'PERFECT' : d < win*0.66 ? 'GOOD' : 'OK'; }
// score = base × {PERFECT:1.5, GOOD:1.2, OK:1} × (wrong side ? 0.5 : 1) + (iso ? isoBonus : 0); streaks per game.
```

## 4 · TEST HARNESS + EVIDENCE (this session)
- `test/mover_bench.js`: feeds recorded pose sequences (record 6 short clips with `?pose=1&rec=1`: still · shoulder pops L/R · rib slide with hips still · rib slide with hips moving · a wave · a clap) through the engine → assert: each rule fires ONLY on its clip, `iso` true only on the isolated clip, wave quality reported, clap fuses with a synthetic audio onset.
- Two distances + a small-frame test → [CAL] blocks pasted.
- Report: the bench table (rule × clip = fired/not), [CAL] blocks, engine fps, tag `beta-b0.11`, CHANGELOG. HOLD.
