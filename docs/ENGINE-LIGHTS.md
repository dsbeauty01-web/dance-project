# ENGINE-LIGHTS — the shared LIGHT engine (one canvas engine for every game · driven by the mover-engine · full code · CLI deploys)

Read `.claude/skills/game-cues-lights/SKILL.md` first. Builds `shared/light-engine.js`. Lights are positioned from LIVE joints and timed from the CUE table + the detection's own events — so they're accurate by construction. Tag `beta-b0.12`. No game page edits this session except a demo page `beta/lights-demo.html`.

## THE LAW
Gold is the only thing that glows. Every cue = **WHEN** (the orb appears one beat early + a beat-pulse), **WINDOW** (the ring closes to the orb), **WHERE** (ribbon = direction / comet = a path). Every hit = flare + fly-up + tick. Isolation = mover gold + a faint "stay still" ring on the reference. Never red.

## 1 · shared/light-engine.js (complete)
```js
export class LightEngine {
  constructor(canvas, opts={}){
    this.cv=canvas; this.cx=canvas.getContext('2d'); this.mirror = opts.mirror ?? true;
    this.tier = opts.tier ?? 'kids';                                  // 'kids' full juice · 'adult' cool
    this.col = this.tier==='kids' ? { main:'#ffc23e', hot:'#ffdf7e', ice:'#aee8ff', warm:'#ffb27d' } : { main:'#e6a93a', hot:'#f2c66d', ice:'#aee8ff', warm:'#e0a57a' };
    this.joints={}; this.cues=[]; this.parts=[]; this.rings=[]; this.comets=[]; this.stills=[]; this.fire=false;
    this.fit(); addEventListener('resize', ()=>this.fit()); this.audio = new LightAudio();
    requestAnimationFrame(()=>this.draw());
  }
  fit(){ this.cv.width=this.cv.clientWidth*devicePixelRatio; this.cv.height=this.cv.clientHeight*devicePixelRatio; }
  // ── joint feed: call every pose frame with the mover-engine output (normalized 0..1 coords) ──
  setJoints(out){ for (const [n,j] of Object.entries(out)){ if(!j) continue;
    this.joints[n] = { x: (this.mirror ? 1-j.x : j.x)*this.cv.width, y: j.y*this.cv.height, dir:j.dir }; } }
  P(n){ return this.joints[n]; }
  // ── CUES (from the cue table, one beat early) ──
  cue({ joint, dir=null, windowMs=900, leadMs=1000, still=[] }){
    this.cues = this.cues.filter(c=>c.joint!==joint);
    this.cues.push({ joint, dir, born:performance.now(), windowMs, leadMs, still });
    this.audio.chime(); }
  clearCue(joint){ this.cues = this.cues.filter(c=>c.joint!==joint); }
  // ── EVENTS (from detection) ──
  hit(joint, quality='good', pts=null){ const p=this.P(joint); if(!p) return;
    const col = quality==='iso' ? this.col.hot : quality==='wrong' ? '#cbb7e8' : this.col.main;
    const n = this.tier==='kids' ? 16 : 7;
    for(let i=0;i<n;i++) this.parts.push({x:p.x,y:p.y,vx:(Math.random()-.5)*7,vy:(Math.random()-.8)*7,r:3+Math.random()*3,a:1,col});
    this.rings.push({x:p.x,y:p.y,r:8,a:1,col,grow:4}); this.clearCue(joint); this.audio.tick(this.streak||0);
    if(pts!=null) this.flyUp(p, `+${pts}`); }
  isoShimmer(){ for (const n of ['lHip','rHip']){ const p=this.P(n); if(!p) continue;
    for(let i=0;i<(this.tier==='kids'?10:4);i++) this.parts.push({x:p.x,y:p.y,vx:(Math.random()-.5)*3,vy:-Math.random()*2,r:2.5,a:1,col:this.col.hot}); } }
  warm(joint='hipC'){ const p=this.P(joint); if(p) this.rings.push({x:p.x,y:p.y,r:26,a:.5,col:this.col.warm,grow:1.2,soft:true}); }
  ice(){ const c=this.P('shoulderC'); if(c) this.rings.push({x:c.x,y:c.y,r:40,a:.9,col:this.col.ice,grow:9,soft:true}); }
  setFire(on){ this.fire = on && this.tier==='kids'; }
  comet(chain, quality='good'){                                        // the WAVE light: a head + tail riding the chain, timed by the detected peaks
    const pts = chain.map(n=>this.P(n)).filter(Boolean); if(pts.length<3) return;
    this.comets.push({ pts, t0:performance.now(), dur: quality==='smooth'?550:quality==='good'?700:900, col: quality==='smooth'?this.col.hot:this.col.main }); }
  flyUp(p, text){ this.parts.push({x:p.x,y:p.y-10,vx:0,vy:-1.6,r:0,a:1,text,col:this.col.hot}); }
  // ── DRAW ──
  draw(){
    const cx=this.cx, now=performance.now(); cx.clearRect(0,0,this.cv.width,this.cv.height);
    for (const c of this.cues){ const p=this.P(c.joint); if(!p) continue;
      const age=(now-c.born), pulse=8+Math.sin(age/160)*3, R=(this.fire?26:20)+pulse;
      const g=cx.createRadialGradient(p.x,p.y,2,p.x,p.y,R*2.4); g.addColorStop(0,this.fire?this.col.hot:this.col.main); g.addColorStop(1,'rgba(255,194,62,0)');
      cx.fillStyle=g; cx.beginPath(); cx.arc(p.x,p.y,R*2.4,0,7); cx.fill();
      const total=c.leadMs+c.windowMs, frac=Math.max(0, 1 - age/total);                    // ring closes across lead+window
      cx.strokeStyle='rgba(255,223,126,.9)'; cx.lineWidth=3; cx.beginPath(); cx.arc(p.x,p.y,R*2.4*frac+R,0,7); cx.stroke();
      if (c.dir==='L'||c.dir==='R'){ const s=(c.dir==='R')^this.mirror ? -1 : 1;             // ribbon in SCREEN space
        cx.strokeStyle='rgba(255,194,62,.8)'; cx.lineWidth=6; cx.lineCap='round'; cx.beginPath(); cx.moveTo(p.x,p.y); cx.quadraticCurveTo(p.x+s*46,p.y-8,p.x+s*82,p.y-2); cx.stroke(); }
      if (c.dir==='UP'||c.dir==='DOWN'){ const s=c.dir==='UP'?-1:1; cx.strokeStyle='rgba(255,194,62,.8)'; cx.lineWidth=6; cx.beginPath(); cx.moveTo(p.x,p.y); cx.quadraticCurveTo(p.x+8,p.y+s*46,p.x+2,p.y+s*82); cx.stroke(); }
      for (const sn of c.still){ const q=this.P(sn); if(!q) continue;                        // the ISOLATION pair: faint "stay still" ring
        cx.strokeStyle='rgba(255,255,255,.35)'; cx.setLineDash([6,6]); cx.lineWidth=2; cx.beginPath(); cx.arc(q.x,q.y,22,0,7); cx.stroke(); cx.setLineDash([]); }
    }
    for (const m of this.comets){ const u=Math.min(1,(now-m.t0)/m.dur); const head=pathPoint(m.pts,u);
      for (let k=0;k<12;k++){ const uu=Math.max(0,u-k*0.035); const q=pathPoint(m.pts,uu); cx.globalAlpha=(1-k/12)*.9; cx.fillStyle=m.col; cx.beginPath(); cx.arc(q.x,q.y,10-k*0.6,0,7); cx.fill(); }
      cx.globalAlpha=1; if(u>=1) m.done=true; }
    this.comets=this.comets.filter(m=>!m.done);
    for (const q of this.parts){ q.x+=q.vx; q.y+=q.vy; if(!q.text) q.vy+=.12; q.a-=q.text?.018:.03; cx.globalAlpha=Math.max(q.a,0);
      if (q.text){ cx.fillStyle=q.col; cx.font='800 26px "Baloo 2",system-ui'; cx.fillText(q.text,q.x,q.y); } else { cx.fillStyle=q.col; cx.beginPath(); cx.arc(q.x,q.y,q.r,0,7); cx.fill(); } }
    this.parts=this.parts.filter(q=>q.a>0); cx.globalAlpha=1;
    for (const r of this.rings){ r.r+=r.grow; r.a-=r.soft?.015:.05; cx.strokeStyle=r.col; cx.globalAlpha=Math.max(r.a,0); cx.lineWidth=r.soft?8:3; cx.beginPath(); cx.arc(r.x,r.y,r.r,0,7); cx.stroke(); }
    this.rings=this.rings.filter(r=>r.a>0); cx.globalAlpha=1;
    requestAnimationFrame(()=>this.draw());
  }
}
function pathPoint(pts,u){ const n=pts.length-1, i=Math.min(n-1,Math.floor(u*n)), f=u*n-i; const a=pts[i], b=pts[i+1]; return { x:a.x+(b.x-a.x)*f, y:a.y+(b.y-a.y)*f }; }
class LightAudio { constructor(){ this.ctx=null; } ensure(){ this.ctx ||= new (window.AudioContext||window.webkitAudioContext)(); return this.ctx; }
  blip(freq,ms=80,gain=.12){ const c=this.ensure(), o=c.createOscillator(), g=c.createGain(); o.frequency.value=freq; o.type='sine'; g.gain.value=gain; o.connect(g).connect(c.destination); o.start(); g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+ms/1000); o.stop(c.currentTime+ms/1000); }
  tick(streak){ this.blip(Math.min(1100, 660+streak*40), 70); }  chime(){ this.blip(880,120,.05); }  ding(){ this.blip(1320,160,.14); } }
```

## 2 · How a game uses both engines (the contract — 10 lines)
```js
const E = new MoverEngine(); const L = new LightEngine(fxCanvas, { tier:'kids', mirror:true });
onPoseFrame(k => { const out = E.update(k); L.setJoints(out); if (game.calibrating) return;
  const target = cues.current();                                                         // {joint, dir, at, windowMs, rule, still}
  if (target && L.cues.length===0 && clock() >= target.at - target.lead) L.cue({ joint:target.joint, dir:target.dir, windowMs:target.windowMs, leadMs:target.lead, still:target.still });
  const r = RULES[target?.rule]?.(E); if (r?.hit && grade(clock(), target.at, target.windowMs)){ score.hit(target, r, grade(...)); L.hit(target.joint, r.iso?'iso':r.side&&r.side!==target.dir?'wrong':'good', pts); if(r.iso) L.isoShimmer(); }
  if (target && !E.isolated(target.joint, target.still)) L.warm(target.still[0]);
});
```

## 3 · DEMO + EVIDENCE (this session)
`beta/lights-demo.html`: usercam + both engines + a 30s scripted cue table (shoulder L/R pops, a rib slide with the isolation pair, a wave comet on each arm, a clap sparkle, a freeze ice). Screenshots of each effect on a real body + a 30s screen recording → Downloads **lights-demo-video** + 3 beeps 🔔🔔🔔. Tag `beta-b0.12`. HOLD — the founder judges the LOOK.
