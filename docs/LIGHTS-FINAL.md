# LIGHTS-FINAL — the approved light language (founder-approved effect by effect · final code · apply to Wave + Upper Body · record)

Replace the corresponding parts of `shared/light-engine.js`. Everything else in the engine stays (bloom(), sw(), P(), parts/rings loop, tiers). Tag `beta-b0.17`. Then wire into `beta/wave.html` + `beta/upperbody.html`, record both, beeps, hold.

## THE LANGUAGE (decided)
- **Move cue (shoulder pop / arm raise / head):** the bloomed orb on the joint + closing ring with the PERFECT band + direction ribbon — as in v3 but body-scaled + bloomed (already done in b0.16). Unchanged.
- **WAVE:** the COMET — glowing head + fading tail + sparks riding the arm chain; a dim slow comet = the cue, a bright fast one = the hit. No orb, no ring.
- **RIBS / TORSO / HIPS:** the HOOP — a perspective ring around the ribs (gold, moves: slides for side, front-arc swells for forward, back-arc lights for backward) + a dashed white hip hoop that never moves.
- **FREEZE:** just the ICE GLOW on the body silhouette — faint → deep through the hold — no orb, no ring, no specks.
- **CLAP:** the SNAP — small hand glows + a thin line between them; contact = a sharp 4-point star + one thin ring, 250ms. No puff.

═══════════════════════════════════════════
## CODE — light-engine.js additions/replacements
═══════════════════════════════════════════
```js
// ── shared helpers (keep bloom(x,y,r,col,a,spread) and sw() from b0.16) ──
roundBand(x,y,hw,h,col,a,blur){ const c=this.cx; c.save(); c.globalAlpha=a; c.fillStyle=col; c.shadowBlur=blur; c.shadowColor=col; c.beginPath(); c.roundRect(x-hw,y-h,hw*2,h*2,h); c.fill(); c.restore(); }

// ── A · COMET (wave) ──
comet(chain, quality='good', asCue=false){
  const pts=chain.map(n=>this.P(n)).filter(Boolean); if(pts.length<3) return; const sw=this.sw();
  this.comets.push({ pts, t0:performance.now(), dur: asCue?1400:(quality==='smooth'?550:quality==='good'?700:900),
    headR:(asCue?0.14:0.22)*sw, tail:asCue?14:22, alpha:asCue?0.55:1, col:(quality==='smooth'||asCue)?this.col.hot:this.col.main, sparks:!asCue }); }
cometCue(chain){ this.comet(chain,'good',true); }
drawComets(now){ const cx=this.cx;
  for (const m of this.comets){ const u=Math.min(1,(now-m.t0)/m.dur), head=pathPoint(m.pts,u);
    for (let k=0;k<40;k++){ const q=pathPoint(m.pts,k/39); cx.globalAlpha=(k/39>u?0.28:0.10)*m.alpha; cx.fillStyle=this.col.main; cx.beginPath(); cx.arc(q.x,q.y,3,0,7); cx.fill(); }
    cx.globalCompositeOperation='lighter';
    for (let k=0;k<m.tail;k++){ const q=pathPoint(m.pts,Math.max(0,u-k*0.03)), a=(1-k/m.tail)*m.alpha;
      this.bloom(q.x,q.y,m.headR*0.8,m.col,a*0.35,4); this.bloom(q.x,q.y,m.headR*0.5,m.col,a*0.6,2); this.bloom(q.x,q.y,m.headR*0.28,this.col.hot,a,1); }
    this.bloom(head.x,head.y,m.headR,this.col.hot,m.alpha,2.5); this.bloom(head.x,head.y,m.headR*0.42,'#ffffff',m.alpha,1);
    if (m.sparks && Math.random()<0.6){ const q=pathPoint(m.pts,Math.random()*u), sw=this.sw(); this.parts.push({x:q.x+(Math.random()-.5)*sw*.15,y:q.y+(Math.random()-.5)*sw*.18,vx:(Math.random()-.5)*1.5,vy:-Math.random()*1.5,r:2.5,a:1,col:this.col.hot}); }
    cx.globalCompositeOperation='source-over'; cx.globalAlpha=1; if(u>=1) m.done=true; }
  this.comets=this.comets.filter(m=>!m.done); }

// ── B · HOOP (ribs / torso / hips) ──
hoopCue({ mover='ribs', dir, windowMs, leadMs }){ this.cues=this.cues.filter(c=>c.id!=='hoop'); this.cues.push({ id:'hoop', type:'hoop', mover, dir, born:performance.now(), windowMs, leadMs }); this.audio.chime(); }
hoopArc(cx0,cy0,rx,ry,col,aBack,aFront,w){ const c=this.cx; c.lineWidth=w; c.strokeStyle=col; c.shadowColor=col; c.shadowBlur=14;
  c.globalAlpha=aBack; c.beginPath(); c.ellipse(cx0,cy0,rx,ry,0,Math.PI,2*Math.PI); c.stroke();
  c.globalAlpha=aFront; c.lineWidth=w*1.4; c.beginPath(); c.ellipse(cx0,cy0,rx,ry,0,0,Math.PI); c.stroke(); c.shadowBlur=0; }
drawHoopCue(c, now){
  const cx=this.cx, sw=this.sw(), l=this.P('lShoulder'), r=this.P('rShoulder'), hc=this.P('hipC'); if(!(l&&r&&hc)) return;
  const ribsY=(l.y+r.y)/2+sw*0.36, mover = c.mover==='hips' ? {x:hc.x,y:hc.y,rx:sw*0.5,ry:sw*0.15} : {x:(l.x+r.x)/2,y:ribsY,rx:sw*0.58,ry:sw*0.17};
  const anchor = c.mover==='hips' ? {x:(l.x+r.x)/2,y:ribsY,rx:sw*0.58,ry:sw*0.17} : {x:hc.x,y:hc.y,rx:sw*0.45,ry:sw*0.13};
  const age=now-c.born, u=Math.min(1,age/c.leadMs), s=(c.dir==='R')^this.mirror?-1:1;
  cx.globalCompositeOperation='lighter';
  if (c.dir==='L'||c.dir==='R'){ const travel=sw*0.48;
    for (let k=3;k>=0;k--){ const g=Math.max(0,u-k*0.22); this.hoopArc(mover.x+s*g*travel,mover.y,mover.rx,mover.ry,k===0?this.col.hot:this.col.main,(0.1+0.12*(3-k))*0.6,0.15+0.2*(3-k),sw*0.03); }
    for (let i=0;i<3;i++){ const ax=mover.x+s*(mover.rx+sw*0.1+i*sw*0.09); cx.globalAlpha=0.9-i*0.25; cx.fillStyle=this.col.main; cx.beginPath(); cx.moveTo(ax,mover.y-sw*.06); cx.lineTo(ax+s*sw*.07,mover.y); cx.lineTo(ax,mover.y+sw*.06); cx.closePath(); cx.fill(); } }
  else if (c.dir==='F'){ for (let k=0;k<4;k++){ const g=Math.max(0,u-(3-k)*0.22), sc=1+0.4*g; this.hoopArc(mover.x,mover.y+g*sw*0.2,mover.rx*sc,mover.ry*sc,k===3?this.col.hot:this.col.main,0.08,0.25+0.2*k,sw*0.03*sc); } }
  else if (c.dir==='B'){ for (let k=0;k<4;k++){ const g=Math.max(0,u-(3-k)*0.22), sc=1-0.25*g; this.hoopArc(mover.x,mover.y-g*sw*0.15,mover.rx*sc,mover.ry*sc,k===3?'#e1d2ff':'#c8b4ff',0.35+0.2*k,0.08,sw*0.03*sc); } }
  cx.globalCompositeOperation='source-over';
  cx.globalAlpha=0.85; cx.setLineDash([sw*.06,sw*.05]); cx.strokeStyle='#fff'; cx.lineWidth=3; cx.beginPath(); cx.ellipse(anchor.x,anchor.y,anchor.rx,anchor.ry,0,0,7); cx.stroke(); cx.setLineDash([]);
  const tx=mover.x+((c.dir==='L'||c.dir==='R')?s*sw*0.48:0), total=c.leadMs+c.windowMs, frac=Math.max(0,1-age/total);
  cx.globalAlpha=0.9; cx.strokeStyle=this.col.hot; cx.lineWidth=sw*0.035; cx.shadowBlur=14; cx.shadowColor=this.col.main; cx.beginPath(); cx.arc(tx,mover.y,sw*0.55*frac+sw*0.2,0,7); cx.stroke(); cx.shadowBlur=0;
  cx.globalAlpha=0.2; cx.fillStyle=this.col.hot; cx.beginPath(); cx.arc(tx,mover.y,sw*0.25,0,7); cx.fill(); cx.globalAlpha=1; }
hoopHit(){ const l=this.P('lShoulder'), r=this.P('rShoulder'); if(l&&r){ const sw=this.sw(); this.rings.push({x:(l.x+r.x)/2,y:(l.y+r.y)/2+sw*0.36,r:sw*0.5,a:1,col:this.col.hot,grow:sw*0.03,ellipse:sw*0.17/(sw*0.58)}); } this.cues=this.cues.filter(c=>c.id!=='hoop'); }

// ── C · FREEZE (ice glow only) ──
freezeStart(holdMs){ this.freeze={ t0:performance.now(), holdMs, broke:false }; }
freezeBreak(){ if(this.freeze&&!this.freeze.broke){ this.freeze.broke=true; this.freeze.tBreak=performance.now(); } }
freezeEnd(held){ if(!this.freeze) return; held ? (this.freeze.done=performance.now(), this.audio.ding()) : this.freezeBreak(); }
drawFreeze(now){ const f=this.freeze, M=this.maskCanvas; if(!f||!M) return; const cx=this.cx, u=Math.min(1,(now-f.t0)/f.holdMs);
  const g = f.broke ? Math.max(0,0.55-(now-f.tBreak)/600) : 0.3+0.5*u;
  cx.save(); cx.globalAlpha=0.28*g; cx.drawImage(this.tint(M,'#aee8ff'),0,0);
  cx.globalCompositeOperation='lighter'; cx.globalAlpha=0.24*g; cx.filter='blur(16px)'; cx.drawImage(this.tint(M,'#e8f8ff'),0,0); cx.restore();
  if ((f.done&&now-f.done>800)||(f.broke&&g<=0)) this.freeze=null; }
// requires pose-engine to pass the segmentation mask on freeze pages: L.setMask(maskImage) each frame → this.maskCanvas; tint() caches per frame.

// ── D · CLAP (snap) ──
clapCue({ windowMs, leadMs }){ this.cues=this.cues.filter(c=>c.id!=='clap'); this.cues.push({ id:'clap', type:'clap', born:performance.now(), windowMs, leadMs }); }
drawClapCue(c, now){ const cx=this.cx, sw=this.sw(), l=this.P('lWrist'), r=this.P('rWrist'); if(!(l&&r)) return;
  const d=Math.hypot(r.x-l.x,r.y-l.y), close=Math.max(0,1-d/(sw*1.6));
  cx.globalCompositeOperation='lighter';
  for (const p of [l,r]){ this.bloom(p.x,p.y,sw*0.09+sw*0.03*close,this.col.main,0.8,2); this.bloom(p.x,p.y,sw*0.04,this.col.hot,1,1); }
  cx.globalAlpha=0.45+0.4*close; cx.strokeStyle=close>0.5?this.col.hot:this.col.main; cx.lineWidth=2+2*close; cx.beginPath(); cx.moveTo(l.x,l.y); cx.lineTo(r.x,r.y); cx.stroke();
  cx.globalCompositeOperation='source-over'; cx.globalAlpha=1; if (now-c.born>c.leadMs+c.windowMs) this.cues=this.cues.filter(x=>x!==c); }
clapHit(){ const l=this.P('lWrist'), r=this.P('rWrist'); if(!(l&&r)) return; const m={x:(l.x+r.x)/2,y:(l.y+r.y)/2}, sw=this.sw();
  this.cues=this.cues.filter(c=>c.id!=='clap'); this.snaps.push({x:m.x,y:m.y,t0:performance.now(),len:sw*0.36});
  this.rings.push({x:m.x,y:m.y,r:sw*0.12,a:1,col:this.col.hot,grow:sw*0.05,thin:true}); this.audio.clap(); }
drawSnaps(now){ const cx=this.cx; for (const s of this.snaps){ const a=Math.max(0,1-(now-s.t0)/250); cx.globalAlpha=a; cx.strokeStyle='#fff'; cx.lineWidth=3; cx.shadowBlur=8; cx.shadowColor='#fff';
    for (const [ang,f] of [[0,1],[90,1],[45,.5],[135,.5]]){ const rad=ang*Math.PI/180, dx=Math.cos(rad)*s.len*f*(0.6+0.4*a), dy=Math.sin(rad)*s.len*f*(0.6+0.4*a); cx.beginPath(); cx.moveTo(s.x-dx,s.y-dy); cx.lineTo(s.x+dx,s.y+dy); cx.stroke(); }
    cx.shadowBlur=0; } this.snaps=this.snaps.filter(s=>now-s.t0<250); cx.globalAlpha=1; }
// draw loop order: cues (orb/hoop/clap by type) → comets → freeze → parts → rings (thin rings lineWidth 2, 300ms) → snaps
```

═══════════════════════════════════════════
## APPLY TO THE GAMES
═══════════════════════════════════════════
**Wave (beta/wave.html):** cue = `L.cometCue(chain)` at lead; hit = `L.comet(chain, quality)`; hold at 26s = `L.freezeStart(1500)` / `freezeBreak` / `freezeEnd(held)` (enable the mask on this page). Remove any orb/ring cue on wrists.
**Upper Body (beta/upperbody.html, after UPPERBODY-SMART):** side targets = `L.hoopCue({mover:'ribs', dir, windowMs, leadMs})`; hit = `L.hoopHit()` + `L.hit('shoulderC', iso?'iso':'good', pts)`; the finish freeze = the ice glow. Flow beats = `hoopCue` with dir 'F' or 'B' (shown, unscored).
**Freeze game (beta/freeze.html):** replace the ice-flash/ring with `freezeStart/End` (ice glow); the warning orb stays.

## RECORD + HOLD
Real-body recordings: **beta-b0.17-wave** (comet cue → comet hit → hold ice) and **beta-b0.17-upperbody** (hoop slides, hoop hit, finish ice) → Downloads + 3 beeps 🔔🔔🔔. Frame-verify each effect before encoding. Hold for the founder.
