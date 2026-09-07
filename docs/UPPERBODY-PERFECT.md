# UPPERBODY-PERFECT — the definitive fix (design system · the golden-light language · smart detection · full code · measured cues embedded)

CLI MANDATE: deploy this as written. Where a real gap exists that this file missed, you MAY think and fill it — but only in the spirit of the laws below, logged as `[CLI-FILL] <what & why>` in the report. Never contradict a written value. Founder gates stay.

THE LAWS: INPUT-LOCK untouched · her mid-round voice = live in the air only (engine/lips ONLY intro, between-rounds, ending on nova_idle2) · never red, never punishing · the golden light is the ONLY action color · all cues on the routine's video clock · FREEZE-pattern first-party page (no iframes) · PULSE fires at end.

═══════════════════════════════════════════════════════
## 0 · DESIGN TOKENS (from HER world — the bake's own colors)
═══════════════════════════════════════════════════════
```css
:root{
  --room-pink:#f4d9ea; --room-lilac:#cbb7e8;      /* her room's walls */
  --hoodie:#7c5cbf;                                /* deep purple — structure/HUD chrome */
  --gold:#ffc23e; --gold-hot:#ffdf7e;              /* THE action color — cues, score, celebration */
  --ice:#aee8ff;                                   /* freeze/hold only */
  --ink:#2a2140;                                   /* text on light */
  --ok-green:#7ddba3;                               /* quality sparkle tier only, never fills */
}
/* Type: display 'Baloo 2' 700-800 · body 'Nunito' 600 · numbers tabular-nums */
```
Rule of restraint: gold is the ONLY thing that glows. Purple frames, pink breathes, ice appears only at freezes. Nothing else animates without a reason.

═══════════════════════════════════════════════════════
## 1 · LAYOUT + HTML (adaptive per phase — Lexi law + the 60/40)
═══════════════════════════════════════════════════════
```html
<div id="stage" data-phase="intro">
  <div id="novaWrap">
    <video id="routine"   playsinline preload="auto" src="/media/rapa_src.mp4"></video>
    <video id="novaMain"    autoplay muted playsinline></video>
    <video id="novaAmbient" autoplay muted playsinline></video>
    <div id="stateBadge">Watching</div>
  </div>
  <div id="camWrap">
    <video id="usercam" autoplay muted playsinline></video>
    <canvas id="fx"></canvas>
    <div id="scorePop"></div>
  </div>
  <div id="hud">
    <div id="roundDots"><i class="on"></i><i></i><i></i><i></i></div>
    <div id="score">0</div><div id="fire" class="hidden">🔥×2</div>
    <div id="roundTag">ROUND 1 · SLOW</div>
  </div>
  <div id="countdown" class="hidden"></div>
  <div id="verdictCard" class="hidden"></div>
  <div id="scorecard" class="hidden"></div>
  <button id="pauseBtn">⏸</button><button id="exitBtn">✕</button>
</div>
```
```css
#stage{position:fixed;inset:0;display:flex;background:var(--room-pink);font-family:'Nunito',system-ui}
#novaWrap{position:relative;height:100vh;overflow:hidden;transition:width .5s ease;width:60vw}
#camWrap{position:relative;height:100vh;overflow:hidden;transition:width .5s ease;width:40vw}
/* ADAPTIVE (Lexi law): talking phases Nova breathes bigger; rounds keep 60/40 but the kid's side runs hot */
#stage[data-phase="intro"] #novaWrap, #stage[data-phase="between"] #novaWrap, #stage[data-phase="ending"] #novaWrap{width:66vw}
#stage[data-phase="intro"] #camWrap,  #stage[data-phase="between"] #camWrap,  #stage[data-phase="ending"] #camWrap{width:34vw}
#routine,#novaMain{position:absolute;left:50%;top:0;height:100vh;width:auto;transform:translateX(-50%);z-index:2}
#novaAmbient{position:absolute;left:50%;top:50%;height:120vh;transform:translate(-50%,-50%) scaleX(2.2);filter:blur(28px) saturate(1.12);opacity:.9;z-index:1}
#usercam{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
#fx{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:6}
#stateBadge{position:absolute;left:14px;bottom:14px;z-index:4;background:rgba(42,33,64,.6);color:#fff;padding:5px 14px;border-radius:999px;font-weight:700;font-size:13px}
#hud{position:fixed;top:1.6vh;left:0;right:0;display:flex;gap:16px;justify-content:center;align-items:center;z-index:50}
#score{font-family:'Baloo 2';font-size:44px;font-weight:800;color:var(--gold);text-shadow:0 2px 10px rgba(124,92,191,.35);font-variant-numeric:tabular-nums}
#fire{font-family:'Baloo 2';font-size:26px;color:var(--gold-hot);animation:firePulse .5s infinite alternate}
@keyframes firePulse{to{transform:scale(1.12);filter:brightness(1.2)}}
#roundTag{background:var(--hoodie);color:#fff;border-radius:999px;padding:5px 16px;font-weight:800}
#roundDots i{display:inline-block;width:10px;height:10px;border-radius:50%;background:rgba(124,92,191,.3);margin:0 3px}
#roundDots i.on{background:var(--gold)}
#countdown{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Baloo 2';font-size:20vw;color:var(--gold);text-shadow:0 6px 40px rgba(255,194,62,.5);z-index:70}
#verdictCard{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(42,33,64,.55);z-index:75;color:#fff;font-family:'Baloo 2'}
#scorecard{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(42,33,64,.85);z-index:80;color:#fff}
#pauseBtn,#exitBtn{position:fixed;top:1.6vh;z-index:60;background:rgba(42,33,64,.55);color:#fff;border:0;border-radius:12px;padding:8px 12px;font-size:16px}
#pauseBtn{right:64px}#exitBtn{right:14px}
.hidden{display:none!important}
```

═══════════════════════════════════════════════════════
## 2 · THE MEASURED CUE MAP (frame-verified — DO NOT REMEASURE)
═══════════════════════════════════════════════════════
```js
const DEMO_END = 13.5;
const TARGETS = [                      // video-time, screen-space dirs (kid mirrored — verified on screen once)
  {t:16.10,dir:'R'},{t:17.37,dir:'L'},{t:19.55,dir:'B'},{t:21.20,dir:'F'},
  {t:23.00,dir:'R'},{t:24.30,dir:'L'},{t:25.55,dir:'B'},{t:26.80,dir:'F'},
  {t:28.07,dir:'R'},{t:29.37,dir:'L'},
  {t:31.90,dir:'R'},{t:32.50,dir:'L'},{t:33.27,dir:'R'},{t:34.33,dir:'L'},   // the fast burst
  {t:35.20,dir:'FREEZE',hold:1.0},
];
const ROUNDS=[
  {n:1,rate:1.00,label:'ROUND 1 · SLOW',win:1.0,lead:1.2},
  {n:2,rate:1.00,label:'ROUND 2 · SLOW',win:0.9,lead:1.1},
  {n:3,rate:1.25,label:'ROUND 3 · FAST',win:0.75,lead:0.9},
  {n:4,rate:1.25,label:'ROUND 4 · FAST',win:0.65,lead:0.8},
];
// Round 1 plays from 0 (demo = calibration). Rounds 2-4 start at DEMO_END. Target times scale by 1/rate at runtime.
```

═══════════════════════════════════════════════════════
## 3 · THE GOLDEN-LIGHT ENGINE (the signature — full canvas code)
═══════════════════════════════════════════════════════
```js
const cv=document.getElementById('fx'),cx=cv.getContext('2d');
function fitCanvas(){cv.width=cv.clientWidth*devicePixelRatio;cv.height=cv.clientHeight*devicePixelRatio}
addEventListener('resize',fitCanvas);fitCanvas();
const J={rs:6,ls:5,chest:'chest',rh:12,lh:11};              // MoveNet ids (screen-space post-mirror)
let joints={};                                               // updated per pose frame: {name:{x,y}} in canvas px
function jpos(name){ if(name==='chest'){const a=joints.ls,b=joints.rs;return a&&b?{x:(a.x+b.x)/2,y:(a.y+b.y)/2+18}:null}
  return joints[name] }
let cue=null, parts=[], fire=false;
function setCue(dir,windowMs){ cue={dir,born:performance.now(),windowMs,joint:dir==='R'?'rs':dir==='L'?'ls':'chest'} }
function clearCue(){cue=null}
function flare(dir,quality){ const p=jpos(dir==='R'?'rs':dir==='L'?'ls':'chest'); if(!p)return;
  const col=quality==='iso'?'#ffdf7e':quality==='wrong'?'#cbb7e8':'#ffc23e';
  for(let i=0;i<16;i++)parts.push({x:p.x,y:p.y,vx:(Math.random()-0.5)*7,vy:(Math.random()-0.8)*7,r:3+Math.random()*3,a:1,col});
  ring(p, col) }
let rings=[]; function ring(p,col){rings.push({...p,r:8,a:1,col})}
function hipShimmer(){ const l=jpos('lh'),r=jpos('rh'); if(!l||!r)return;
  for(const p of [l,r]) for(let i=0;i<10;i++)parts.push({x:p.x,y:p.y,vx:(Math.random()-.5)*3,vy:-Math.random()*2,r:2.5,a:1,col:'#ffdf7e',gold:true}) }
function hipWarm(){ const l=jpos('lh'),r=jpos('rh'); if(l&&r) rings.push({x:(l.x+r.x)/2,y:(l.y+r.y)/2,r:26,a:.5,col:'#ffb27d',soft:true}) }
function draw(){
  cx.clearRect(0,0,cv.width,cv.height);
  if(cue){ const p=jpos(cue.joint); if(p){
    const age=(performance.now()-cue.born)/1000, pulse=8+Math.sin(age*6)*3, R=(fire?26:20)+pulse;
    // the orb
    const g=cx.createRadialGradient(p.x,p.y,2,p.x,p.y,R*2.4);
    g.addColorStop(0,fire?'#ffdf7e':'#ffc23e');g.addColorStop(1,'rgba(255,194,62,0)');
    cx.fillStyle=g;cx.beginPath();cx.arc(p.x,p.y,R*2.4,0,7);cx.fill();
    // the timing ring (window countdown — closes toward the orb)
    const frac=Math.max(0,1-(age*1000)/cue.windowMs);
    cx.strokeStyle='rgba(255,223,126,.9)';cx.lineWidth=3;
    cx.beginPath();cx.arc(p.x,p.y,R*2.4*frac+R,0,7);cx.stroke();
    // the lean ribbon (direction)
    if(cue.dir==='R'||cue.dir==='L'){ const s=cue.dir==='R'?1:-1;
      cx.strokeStyle='rgba(255,194,62,.8)';cx.lineWidth=6;cx.lineCap='round';
      cx.beginPath();cx.moveTo(p.x,p.y);cx.quadraticCurveTo(p.x+s*46,p.y-8,p.x+s*82,p.y-2);cx.stroke(); }
    if(cue.dir==='F'||cue.dir==='B'){ const s=cue.dir==='F'?1:-1;      // F = grow toward camera: expanding arcs
      for(let i=1;i<=2;i++){cx.strokeStyle=`rgba(255,194,62,${.7/i})`;cx.lineWidth=4;
        cx.beginPath();cx.arc(p.x,p.y,R+10*i*s* (s>0?1:1),0,7);cx.stroke();} }
  }}
  for(const q of parts){q.x+=q.vx;q.y+=q.vy;q.vy+=.12;q.a-=.03;
    cx.globalAlpha=Math.max(q.a,0);cx.fillStyle=q.col;cx.beginPath();cx.arc(q.x,q.y,q.r,0,7);cx.fill()}
  parts=parts.filter(q=>q.a>0);cx.globalAlpha=1;
  for(const r of rings){r.r+=r.soft?1.2:4;r.a-=r.soft?.015:.05;
    cx.strokeStyle=r.col;cx.globalAlpha=Math.max(r.a,0);cx.lineWidth=r.soft?8:3;
    cx.beginPath();cx.arc(r.x,r.y,r.r,0,7);cx.stroke()}
  rings=rings.filter(r=>r.a>0);cx.globalAlpha=1;
  requestAnimationFrame(draw)
} draw();
// SOUND: tick on hit (WebAudio osc blip, base 660Hz, +40Hz per streak step, cap 1100) · soft chime on cue-born · no miss sound.
```
Score fly-up: `#scorePop` spawns "+15" at the hit joint's screen pos, floats up 700ms, gold, Baloo.

═══════════════════════════════════════════════════════
## 4 · SMART DETECTION (calibrated · smoothed · kind)
═══════════════════════════════════════════════════════
```js
// CALIBRATION — during round-1 demo (0→13.5s): learn THIS kid.
const cal={sx:[],sw:[],hx:[]};
function onPoseDemo(k){const L=5,R=6,HL=11,HR=12;if(k[L].score<.35||k[R].score<.35)return;
  cal.sx.push((k[L].x+k[R].x)/2);cal.sw.push(Math.abs(k[L].x-k[R].x));cal.hx.push((k[HL].x+k[HR].x)/2)}
function pct(a,p){const s=[...a].sort((x,y)=>x-y);return s[Math.floor(s.length*p)]}
let CAL=null;
function finishCal(){const spread=pct(cal.sx,.9)-pct(cal.sx,.1);
  CAL={sx0:pct(cal.sx,.5),hx0:pct(cal.hx,.5),sw0:pct(cal.sw,.5),
    slide:Math.max(.05,spread*.35),hip:Math.max(.03,spread*.18),front:1.07,back:.93};
  log('[CAL]',CAL)}                                   // evidence: paste from 2 runs at different distances
// LIVE — EMA + velocity assist + grace
let ema={},lastDev=0,graceUsed=false;
function onPoseGame(k){const L=5,R=6,HL=11,HR=12;if(k[L].score<.35||k[R].score<.35)return;
  const raw={sx:(k[L].x+k[R].x)/2,sw:Math.abs(k[L].x-k[R].x),hx:(k[HL].x+k[HR].x)/2};
  for(const key in raw)ema[key]=ema[key]==null?raw[key]:ema[key]*.6+raw[key]*.4;
  updateJointsCanvasPositions(k);                      // feeds the light engine (mirrored px)
  const dev=ema.sx-CAL.sx0,wr=ema.sw/CAL.sw0,hip=Math.abs(ema.hx-CAL.hx0),vel=dev-lastDev;lastDev=dev;
  const nxt=targets[ti];if(!nxt||nxt.hit)return trackWobble(hip);
  const t=routine.currentTime,w=curWin();
  if(t<nxt.t-w)return; if(t>nxt.t+w){ if(!graceUsed&&!nxt.missed){graceUsed=true;nxt.grace=true} nxt.missed=true;ti++;clearCue();return }
  let got=null;
  if(nxt.dir==='R'&&(dev> CAL.slide||(dev> CAL.slide*.6&&vel> .004)))got='R';
  if(nxt.dir==='L'&&(dev<-CAL.slide||(dev<-CAL.slide*.6&&vel<-.004)))got='L';
  if(nxt.dir==='F'&&wr>CAL.front)got='F';
  if(nxt.dir==='B'&&wr<CAL.back)got='B';
  if(nxt.dir==='FREEZE')return checkHold(k,nxt);
  if(got){hit(nxt,hip<CAL.hip,false)}
  else{const any=dev>CAL.slide?'R':dev<-CAL.slide?'L':null;
    if(any&&Math.abs(t-nxt.t)<w*.5)hit(nxt,hip<CAL.hip,true)}     // wrong side = half, still flows
}
let wob=0;function trackWobble(h){wob=h>CAL.hip*1.6?wob+16:0;if(wob>400){hipWarm();wob=0}}
```
Live-tune overrides stay: `?slide= ?hip= ?front= ?back=`.

═══════════════════════════════════════════════════════
## 5 · SCORING + FIRE MODE + VERDICTS
═══════════════════════════════════════════════════════
```js
let score=0,streak=0,roundHits=0,roundIso=0,sideStats={R:0,L:0,B:0,F:0};
function hit(tg,iso,wrong){tg.hit=true;ti++;clearCue();
  const R=ROUNDS[round];let pts=R.rate===1?15:10;
  if(wrong)pts=Math.round(pts/2);
  if(iso&&R.rate===1){pts+=10;hipShimmer();roundIso++}
  if(R.rate>1){streak++;fire=streak>=3;ui.fire(fire);if(fire)pts*=2}else{streak=0;fire=false}
  if(round===3)pts+=5;
  score+=pts;roundHits++;if(!wrong)sideStats[tg.dir]++;
  flare(tg.dir,iso?'iso':wrong?'wrong':'good');tick(streak);popScore(pts,tg.dir);hud.score(score);
  emitFact({fact:'ub_hit',dir:tg.dir,iso,wrong,round:round+1,streak})}
function endRound(){const hits=roundHits,v=hits>=10?'NAILED':hits>=6?'GOOD':'TRIED';
  if(v==='NAILED')score+=30;
  showVerdictCard(v,hits,roundIso);                              // 2.2s card: big word + stars + iso count
  emitFact({fact:'ub_round',n:round+1,verdict:v,hits,iso:roundIso});
  roundHits=0;roundIso=0;graceUsed=false;
  round<3?betweenRounds(v):finale()}
function checkHold(k,tg){/* stillness 1.0s vs CAL-scaled energy thr → +50, all-joints flare + confetti; emitFact ub_freeze */}
function finale(){ if(allFourNailed())score+=100; showScorecard(); setPhase('ending'); /* her trio + PULSE */ }
```
Countdown 3·2·1 (gold, huge) before round 1's targets begin (after the demo) and before each next round.

═══════════════════════════════════════════════════════
## 6 · PHASES + HER VOICE
═══════════════════════════════════════════════════════
intro/between/ending → engine path, lips on **nova_idle2**, adaptive layout widens her. Rounds → routine video is the body, her voice live in the air, speak-gate: ONE line max mid-round, fact-fed. Between rounds she coaches from sideStats + iso count ("right side champion — round «n», we wake the LEFT!") then invites; tap or verbal yes starts the countdown. Ending trio: real numbers → "did you have fun? tell me anything!" (feedback_text+emoji) → named goodbye → PULSE row (paste in evidence).

═══════════════════════════════════════════════════════
## GATE + EVIDENCE
═══════════════════════════════════════════════════════
Self-run all 4 rounds via claude-in-chrome (synthetic pose feed OK for logic; visual pass screenshots of: orb+ring+ribbon, flare, hip shimmer, fire mode, verdict card, scorecard). 🔔 Recording → Downloads **upperbody-perfect-video** + 3 beeps 🔔🔔🔔 → HOLD for the founder's live 4-round playthrough → merge on his word only.
Evidence: [CAL] from 2 distances · a round's full hit log · [CLI-FILL] list · sideStats→her coach line match · PULSE row · screenshots per effect.
