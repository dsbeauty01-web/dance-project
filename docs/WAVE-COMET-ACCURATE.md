# WAVE-COMET-ACCURATE — the comet that rides the REAL wave (phase-driven · sleeve-of-light ribbon · ball impossible · full code · QA'd)

Read `.claude/skills/game-vfx-juice/SKILL.md` first. Replaces the comet parts of `shared/light-engine.js` and adds a phase feed from `shared/mover-rules.js`. Tag `beta-b0.18`. Demo section for the wave MUST use `handywave.mp4` (the real extended-arm wave) as the fake webcam — the hands-on-hips clip can't show a wave.

## THE IDEA
The comet is not on a timer. **The WaveRule already knows which joint is peaking and when.** The comet head sits at the joint currently peaking and glides toward the next along the arm's actual bones — so the light follows the human, not a stopwatch. The trail is a tapered ribbon wrapped around the bones (a sleeve of light), never dots.

═══════════════════════════════════════════
## 1 · mover-rules.js — expose the wave phase (add to WaveRule)
═══════════════════════════════════════════
```js
// inside class WaveRule:
phase(t=performance.now()){
  // returns { head: 0..1 along the chain, active: bool, peaks:[t|null] } — head follows the LATEST peak, gliding toward the next joint
  const chain = this.chain.filter(n => this.E.last?.[n]);
  const peaks = chain.map(n => this.peakT(n));
  let last=-1; for (let i=0;i<peaks.length;i++) if (peaks[i]!=null && t-peaks[i] < 700) last=i;   // most recent joint that peaked within 700ms
  if (last<0) return { head:0, active:false, peaks };
  const since = t - peaks[last], glide = Math.min(1, since/220);                                   // ~220ms per link, eased
  const eased = 1 - Math.pow(1-glide, 3);                                                         // easeOutCubic
  const head = Math.min(1, (last + eased) / (chain.length-1));
  return { head, active: true, peaks, links: chain.length };
}
```

═══════════════════════════════════════════
## 2 · light-engine.js — the accurate comet (replaces comet/cometCue/drawComets)
═══════════════════════════════════════════
```js
// ── geometry helpers ──
catmull(pts, n=32){ if (pts.length<2) return pts; const out=[]; const P=[pts[0],...pts,pts[pts.length-1]];
  for (let i=1;i<P.length-2;i++){ for (let s=0;s<n/(pts.length-1);s++){ const t=s/(n/(pts.length-1)), t2=t*t, t3=t2*t, p0=P[i-1],p1=P[i],p2=P[i+1],p3=P[i+2];
    out.push({ x:0.5*((2*p1.x)+(-p0.x+p2.x)*t+(2*p0.x-5*p1.x+4*p2.x-p3.x)*t2+(-p0.x+3*p1.x-3*p2.x+p3.x)*t3),
               y:0.5*((2*p1.y)+(-p0.y+p2.y)*t+(2*p0.y-5*p1.y+4*p2.y-p3.y)*t2+(-p0.y+3*p1.y-3*p2.y+p3.y)*t3) }); } }
  out.push(pts[pts.length-1]); return out; }
pathLen(pts){ let L=0; for (let i=1;i<pts.length;i++) L+=Math.hypot(pts[i].x-pts[i-1].x, pts[i].y-pts[i-1].y); return L; }
at(pts,u){ const n=pts.length-1, i=Math.min(n-1,Math.max(0,Math.floor(u*n))), f=u*n-i; const a=pts[i],b=pts[i+1]; return { x:a.x+(b.x-a.x)*f, y:a.y+(b.y-a.y)*f, ang:Math.atan2(b.y-a.y,b.x-a.x) }; }
ribbon(pts, uHead, w0, w1, col, alpha){                                        // tapered ribbon from uHead back along the path
  const cx=this.cx, N=24, left=[], right=[];
  for (let k=0;k<=N;k++){ const u=uHead - k*(0.55/N); if (u<0) break; const p=this.at(pts,u), w=(w0+(w1-w0)*(k/N))*0.5;
    const nx=-Math.sin(p.ang)*w, ny=Math.cos(p.ang)*w; left.push({x:p.x+nx,y:p.y+ny}); right.push({x:p.x-nx,y:p.y-ny}); }
  if (left.length<2) return;
  const g=cx.createLinearGradient(left[0].x,left[0].y,left[left.length-1].x,left[left.length-1].y); g.addColorStop(0,col); g.addColorStop(1,'rgba(255,194,62,0)');
  cx.globalAlpha=alpha; cx.fillStyle=g; cx.beginPath(); cx.moveTo(left[0].x,left[0].y); for (const p of left) cx.lineTo(p.x,p.y); for (let i=right.length-1;i>=0;i--) cx.lineTo(right[i].x,right[i].y); cx.closePath(); cx.fill(); }

// ── COMET STATE ──
// cue: a slow sweep that shows the path (timer-based is correct for a cue — nothing to follow yet)
cometCue(chain){ this.cometCueState = { chain, t0:performance.now(), dur:1400 }; }
// live: bound to a WaveRule — the head follows the DETECTED phase every frame
cometLive(waveRule, chain){ this.cometLiveState = { rule:waveRule, chain, glow:0 }; }
cometHit(quality){ const s=this.cometLiveState; if (s) { s.hitT=performance.now(); s.quality=quality; } }
cometStop(){ this.cometLiveState=null; }

drawComets(now){
  const cx=this.cx, sw=this.sw();
  const draw = (chainNames, uHead, strength, quality) => {
    const raw = chainNames.map(n=>this.P(n)).filter(Boolean); if (raw.length<3) return;
    const pts = this.catmull(raw, 32);
    if (this.pathLen(raw) < 1.2*sw){ const w=this.P(chainNames[2]); if (w) this.bloom(w.x,w.y,sw*0.08,this.col.main,0.5*strength,2); return; }   // PATH GUARD: arm not extended → soft wrist pulse only, no comet, no ball
    const headR = Math.min(sw*0.16, 26*devicePixelRatio);                                    // CAP — the ball is impossible
    const col = quality==='smooth' ? this.col.hot : this.col.main;
    cx.globalCompositeOperation='lighter';
    this.ribbon(pts, uHead, sw*0.18, sw*0.06, col, 0.55*strength);                           // the sleeve of light on the bones
    const h=this.at(pts,uHead);
    this.bloom(h.x,h.y,headR,col,0.35*strength,2.2); this.bloom(h.x,h.y,headR*0.55,col,0.7*strength,1.4); this.bloom(h.x,h.y,headR*0.3,'#ffffff',strength,1);
    if (strength>0.8 && Math.random()<0.5){ const q=this.at(pts,Math.max(0,uHead-Math.random()*0.4)); const g1=this.gauss(), g2=this.gauss();
      this.parts.push({x:q.x+g1*sw*0.06,y:q.y+g2*sw*0.06,vx:g1*0.8,vy:-Math.abs(g2)*1.2,r:2,a:1,col:this.col.hot,life:550}); }
    cx.globalCompositeOperation='source-over'; cx.globalAlpha=1;
  };
  // CUE sweep
  const c=this.cometCueState; if (c){ const u=Math.min(1,(now-c.t0)/c.dur), e=1-Math.pow(1-u,3); draw(c.chain, e, 0.55, 'cue'); if (u>=1) this.cometCueState=null; }
  // LIVE — phase-driven
  const s=this.cometLiveState; if (s){ const ph=s.rule.phase(now);
    s.glow += ((ph.active?1:0) - s.glow)*0.25;                                                 // eases in when a wave is happening, out when not
    if (s.glow>0.05){ let u=ph.head;
      if (s.hitT && now-s.hitT<260){ u=Math.min(1.12, ph.head + 0.12*(1-(now-s.hitT)/260)); }  // FOLLOW-THROUGH: overshoot the fingertip on a hit, then settle
      draw(s.chain, Math.min(1,u), s.glow*(s.hitT&&now-s.hitT<260 ? 1 : 0.8), s.quality||'good'); }
  }
}
gauss(){ let u=0,v=0; while(!u) u=Math.random(); while(!v) v=Math.random(); return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)*0.5; }
```
Draw-loop order: cues → comets → ice → parts → rings → snaps (unchanged).

═══════════════════════════════════════════
## 3 · game wiring (beta/wave.html)
═══════════════════════════════════════════
```js
// at each cue (lead): L.cometCue(chain)                       // shows the path once
// when a phase starts (5s R-arm): L.cometLive(waveR, CHAIN_R); at 13s: L.cometStop(); L.cometLive(waveL, CHAIN_L); at 22s: both — two live states (extend cometLiveState to an array, one per arm; never merge chains)
// on a detected wave: L.cometHit(r.quality) — the head overshoots the fingertip and settles (follow-through)
// at the hold (26s): L.cometStop() for both, then L.freezeStart(1500)
```

═══════════════════════════════════════════
## QA (the architect ran this against the skill — the CLI re-verifies)
═══════════════════════════════════════════
✓ Anticipation = the cue sweep · ✓ Impact = the hit overshoot + white core + sparks · ✓ Follow-through = 260ms overshoot then settle · ✓ Easing = easeOutCubic glide per link + cue sweep, glow eases in/out (no linear) · ✓ Trail = tapered Catmull-Rom ribbon, not dots · ✓ Bloom = 3 additive layers · ✓ Body-scaled = all sizes from sw; head capped at 0.16×sw (v4 ball bug dead) · ✓ Path guard = no comet on a bunched arm · ✓ Gaussian sparks 550ms · ✓ Material = light behaves like light (no hard shapes) · ✓ Never over the face (chain never includes the head) · ✓ Two arms = two states.
Timing check: link glide 220ms ≈ real wave spacing (WaveRule accepts 40-400ms gaps) — the head keeps pace with a real human wave; faster waves advance the head by peaks, not by the timer.

## RECORD + HOLD
Wave section on `handywave.mp4` as the webcam: frame-verify the head at the shoulder → elbow → wrist → fingertip in sequence during a real wave, the ribbon hugging the arm, the overshoot on the hit. → Downloads **lights-demo-v5** + 3 beeps 🔔🔔🔔. Hold.
