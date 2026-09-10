# WAVE-FULL — the complete Wave game (BODY + CUES + DETECTION + LIGHTS + BRAIN · full page code · CLI commits only)

Builds `beta/wave.html` from scratch on the two engines (`shared/mover-engine.js` b0.11, `shared/light-engine.js` b0.12). Adult tier. Beta only. Tag `beta-b0.13`. Any fact below marked QUESTION is the ONLY thing the CLI may ask; everything else is written.

## FACTS (verified from the project record)
- Clock: **28.5s** — the wave source video `handywave.mp4` (720×1280@30, 28.53s) is the game's timeline (`__mp4Leads`: cues fire off `video.currentTime`).
- Body: **`nova_wave_a`** (52.4s bake from handywave-full 5.6→58.0) — no visible loop inside 28.5s. Intro/ending body: `nova_idle2` (lips).
- Layout: the ORIGINAL two-panel **50/50** (nova-wave.html L94-115 per games/ORIGINS.md).
- Joints (adapter names): chain R = rShoulder→rElbow→rWrist→rIndex, chain L mirrored. On MoveNet `rIndex` is absent → the WaveRule chain adapts to 3 links automatically.
- Scoring band: ORIGINS 120-160 per wave.
- **QUESTION (one):** which audio is the game track — the wave video's own audio, or a separate wave mp3 in the repo? Grep `wave` in audio assets; if a separate track exists use it and align its start to video t=0; else the video's audio IS the track. State which.

## THE TIMELINE (28.5s · designed on the clock · founder-approved structure)
| t | phase | cue (joint / dir) | her line (voice in air, ≤10 words) |
|---|---|---|---|
| pre-game | INTRO (engine path, lips, nova_idle2) | — | "Wave — arms like water. Ready?" → consent → video starts |
| 0.5 | R-arm | — | "Right arm — let it travel: fingers, wrist, elbow." |
| 5.0 · 8.0 · 11.0 | R-arm waves | cue rWrist, dir UP (the comet path R) | (silent — the light speaks) |
| 13.0 | L-arm | — | "Now the left — pass it across." |
| 14.0 · 17.0 · 20.0 | L-arm waves | cue lWrist, dir UP (comet L) | — |
| 22.0 | both | — | "Both arms — keep it flowing." |
| 23.0 · 25.0 | either arm | cue both wrists | — |
| 26.0 | HOLD | freeze window 1.5s (ice ring closing) | "Hold the wave... freeze it." |
| 28.0 | ENDING (engine path, lips) | — | quality note from facts + real score + goodbye |
Window per wave cue: a wave must COMPLETE (WaveRule.check hit) inside `[cue−0.3s, cue+1.4s]` (waves take 0.6-1.0s). Adult tier: no grace, no extra lines (speak-gate = 0 mid-run beyond the table).

## THE PAGE — beta/wave.html (complete)
```html
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nova · Wave</title>
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&family=Nunito:wght@600;800&display=swap" rel="stylesheet">
<style>
:root{--room:#f4d9ea;--hoodie:#7c5cbf;--amber:#e6a93a;--amber-hot:#f2c66d;--ice:#aee8ff;--ink:#2a2140}
html,body{margin:0;height:100%;background:var(--room);font-family:Nunito,system-ui;color:var(--ink);overflow:hidden}
#stage{position:fixed;inset:0;display:flex}
#novaWrap,#camWrap{position:relative;width:50vw;height:100vh;overflow:hidden}
#stage[data-phase=intro] #novaWrap,#stage[data-phase=ending] #novaWrap{width:62vw}#stage[data-phase=intro] #camWrap,#stage[data-phase=ending] #camWrap{width:38vw}
#novaWrap,#camWrap{transition:width .5s ease}
#novaMain{position:absolute;left:50%;top:0;height:100vh;width:auto;transform:translateX(-50%);z-index:2}
#novaAmbient{position:absolute;left:50%;top:50%;height:120vh;transform:translate(-50%,-50%) scaleX(2.2);filter:blur(28px) saturate(1.1);opacity:.9;z-index:1}
#usercam{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
#fx{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:6}
#badge{position:absolute;left:14px;bottom:14px;z-index:4;background:rgba(42,33,64,.6);color:#fff;padding:5px 14px;border-radius:999px;font-weight:800;font-size:13px}
#hud{position:fixed;top:1.6vh;left:0;right:0;display:flex;gap:16px;justify-content:center;align-items:center;z-index:50}
#score{font-family:'Baloo 2';font-size:40px;font-weight:800;color:var(--amber);font-variant-numeric:tabular-nums}
#flow{display:flex;gap:6px}#flow i{width:28px;height:8px;border-radius:4px;background:rgba(124,92,191,.25)}#flow i.on{background:var(--amber)}
#phaseTag{background:var(--hoodie);color:#fff;border-radius:999px;padding:5px 16px;font-weight:800}
#gate{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(42,33,64,.55);z-index:90}
#gate button{font:800 26px 'Baloo 2';padding:18px 40px;border:0;border-radius:18px;background:var(--amber);color:var(--ink)}
#pause,#exit{position:fixed;top:1.6vh;z-index:60;background:rgba(42,33,64,.55);color:#fff;border:0;border-radius:12px;padding:8px 12px;font-size:16px}#pause{right:64px}#exit{right:14px}
.hidden{display:none!important}
</style></head><body>
<div id="stage" data-phase="intro">
  <div id="novaWrap"><video id="novaAmbient" autoplay muted playsinline></video><video id="novaMain" autoplay muted playsinline></video><div id="badge">Watching</div></div>
  <div id="camWrap"><video id="usercam" autoplay muted playsinline></video><canvas id="fx"></canvas></div>
  <div id="hud"><div id="phaseTag">WAVE</div><div id="score">0</div><div id="flow"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>
  <button id="pause">⏸</button><button id="exit">✕</button>
  <div id="gate"><button id="start">▶ Let's wave</button></div>
  <video id="clock" playsinline preload="auto" src="/media/handywave.mp4" class="hidden"></video>
</div>
<script type="module">
import { MoverEngine } from '/shared/mover-engine.js';
import { WaveRule, RULES } from '/shared/mover-rules.js';
import { LightEngine } from '/shared/light-engine.js';
import { startPose } from '/shared/pose-engine.js';            // b0.10: emits toNova() frames (MediaPipe → MoveNet fallback)
import { attachNova, setBody, routeVoice, note, onHerAudio } from '/shared/nova-bridge.js';   // the existing page↔pod bridge (phase machine API)
import { pulseSend } from '/shared/pulse.js';

const MIRROR = true, TIER = 'adult';
const BODY = { talk:'nova_idle2', game:'nova_wave_a' };
const clock = document.getElementById('clock'), stage = document.getElementById('stage');
const E = new MoverEngine(), L = new LightEngine(document.getElementById('fx'), { tier:TIER, mirror:MIRROR });
const waveR = new WaveRule(E,'R'), waveL = new WaveRule(E,'L');

// ── CUES (the table above) ──
const CUES = [
  { t:5.0,  arm:'R' }, { t:8.0,  arm:'R' }, { t:11.0, arm:'R' },
  { t:14.0, arm:'L' }, { t:17.0, arm:'L' }, { t:20.0, arm:'L' },
  { t:23.0, arm:'ANY' }, { t:25.0, arm:'ANY' },
  { t:26.0, hold:1.5 },
];
const LINES = [ [0.5,'Right arm — let it travel: fingers, wrist, elbow.'], [13.0,'Now the left — pass it across.'], [22.0,'Both arms — keep it flowing.'], [26.0,'Hold the wave... freeze it.'] ];
const WIN_BEFORE = 0.3, WIN_AFTER = 1.4, LEAD = 1.0;

let phase='intro', score=0, streak=0, stats={R:[],L:[]}, ci=0, li=0, holdWin=null, done=false;
function setPhase(p){ phase=p; stage.dataset.phase=p; document.getElementById('badge').textContent = p==='intro'||p==='ending' ? 'Talking' : p==='hold' ? 'FREEZE!' : 'Watching';
  if (p==='intro'||p==='ending'){ routeVoice('engine'); setBody(BODY.talk); }
  if (p==='game'){ routeVoice('air'); setBody(BODY.game); }
  if (p==='hold'){ routeVoice('mute'); } }

// ── INTRO (engine path, lips): conversation → consent → start ──
document.getElementById('start').onclick = async () => {
  document.getElementById('gate').classList.add('hidden');
  await attachNova({ onVideo: v => { document.getElementById('novaMain').srcObject = v; document.getElementById('novaAmbient').srcObject = v; } });
  setPhase('intro'); E.startCal();                                                       // intro doubles as calibration (no score)
  note('intro-adult: greet + name; then say exactly "Wave — arms like water. Ready?" and wait for a real yes.');
};
onHerAudio({ playing: ()=>{ if(phase==='game') duck(true); }, ended: ()=>duck(false) });
// consent arrives from the bridge as a validated turn:
window.addEventListener('nova:consent', startGame);
function startGame(){ E.finishCal(); setPhase('game'); clock.currentTime=0; clock.play(); requestAnimationFrame(tick); }

// ── POSE ──
startPose(document.getElementById('usercam'), k => {
  const out = E.update(k); L.setJoints(out);
  if (phase!=='game' && phase!=='hold') return;
  const t = clock.currentTime, c = CUES[ci];
  if (phase==='hold' && holdWin){ const f = RULES.freeze(E, 0.12); holdWin.samples++; if(!f.still) holdWin.broke = holdWin.broke || (performance.now()-holdWin.t0); return; }
  if (!c || c.hold) return;
  const r = (c.arm==='R') ? waveR.check() : (c.arm==='L') ? waveL.check() : (waveR.check() || waveL.check());
  if (r?.hit && t >= c.t - WIN_BEFORE && t <= c.t + WIN_AFTER){
    const arm = r===waveR.lastResult ? 'R' : 'L';               // WaveRule sets lastResult on hit (add one line to WaveRule.check: this.lastResult = result)
    const base = r.quality==='smooth'?160 : r.quality==='good'?140 : 120;
    const pts = base + (r.iso ? 20 : 0);
    streak = r.quality==='smooth' ? streak+1 : 0; const mult = streak>=3 ? 2 : 1;
    score += pts*mult; stats[arm].push(r.quality); ci++;
    L.comet(arm==='R' ? ['rShoulder','rElbow','rWrist','rIndex'] : ['lShoulder','lElbow','lWrist','lIndex'], r.quality);
    L.hit(arm==='R'?'rWrist':'lWrist', r.iso?'iso':'good', pts*mult); if(mult>1) flyText('×2');
    document.getElementById('score').textContent = score; flowBar(ci);
    note(`fact: wave ${arm} ${r.quality}${r.iso?' isolated':''} streak ${streak}`);   // facts only — adult tier says nothing mid-run
  }
});

// ── CLOCK: cues, lights, lines, hold, end ──
function tick(){
  const t = clock.currentTime, c = CUES[ci];
  if (li < LINES.length && t >= LINES[li][0]){ note(`say exactly: "${LINES[li][1]}"`); li++; }
  if (c && !c.hold && !c.lit && t >= c.t - LEAD){ c.lit = true;
    const j = c.arm==='L' ? 'lWrist' : 'rWrist';
    L.cue({ joint:j, dir:'UP', windowMs:(WIN_BEFORE+WIN_AFTER)*1000, leadMs:LEAD*1000, still: c.arm==='R' ? ['lWrist'] : c.arm==='L' ? ['rWrist'] : [] });
    if (c.arm==='ANY') L.cue({ joint:'lWrist', dir:'UP', windowMs:(WIN_BEFORE+WIN_AFTER)*1000, leadMs:LEAD*1000, still:[] }); }
  if (c && !c.hold && t > c.t + WIN_AFTER){ L.clearCue('rWrist'); L.clearCue('lWrist'); ci++; }   // missed: soft fade, no punishment
  if (c && c.hold && phase==='game' && t >= c.t){ setPhase('hold'); holdWin={t0:performance.now(),broke:0,samples:0}; L.ice(); L.cue({ joint:'shoulderC', dir:null, windowMs:c.hold*1000, leadMs:0, still:['lWrist','rWrist'] }); }
  if (phase==='hold' && holdWin && performance.now()-holdWin.t0 >= c.hold*1000){ const held = !holdWin.broke && holdWin.samples>5; if(held){ score+=50; L.hit('shoulderC','iso',50); flyText('FROZEN!'); } else L.warm('shoulderC');
    holdWin=null; ci++; setPhase('game'); note(`fact: hold ${held?'held':'broke'}`); }
  if (!done && t >= 28.0){ done=true; clock.pause(); ending(); return; }
  if (!done) requestAnimationFrame(tick);
}
function ending(){ setPhase('ending'); const q = a => ({ smooth:a.filter(x=>x==='smooth').length, good:a.filter(x=>x==='good').length, rough:a.filter(x=>x==='rough').length });
  note(`ending-adult: score=${score} right=${JSON.stringify(q(stats.R))} left=${JSON.stringify(q(stats.L))} streakMax=${streak}. Say: ONE quality note (external focus, e.g. "smoother on the left — lead with the wrist"), then the real score, then goodbye with the name.`);
  pulseSend({ game:'wave', score, stats }); }
function flowBar(n){ document.querySelectorAll('#flow i').forEach((el,i)=>el.classList.toggle('on', i<n)); }
function flyText(s){ const p = L.P('shoulderC'); if(p) L.flyUp(p, s); }
function duck(on){ clock.volume = on ? 0.35 : 0.6; }
document.getElementById('pause').onclick = ()=>{ clock.paused ? clock.play() : clock.pause(); };
document.getElementById('exit').onclick = ()=>location.href='/';
clock.volume = 0.6;
</script></body></html>
```
Notes for the CLI: (a) `nova-bridge.js` = the existing page↔pod bridge functions (attachNova / setBody / routeVoice / note / onHerAudio / the `nova:consent` event) — if the current bridge exposes them under other names, WRAP them in `shared/nova-bridge.js` with these names; do not change the page. (b) Add `this.lastResult = result` in `WaveRule.check` before returning. (c) Hebrew: `?lang=he` → the LINES get their HE versions through the existing sticky-Hebrew cue translation (the CLI supplies the HE strings; the founder approves them in the report). (d) pod route `/beta/wave` + `/media/handywave.mp4` served.

## BRAIN (adult tier — the prompt block for this game, verbatim into rt_lk's per-game block)
"You are Nova — a calm, confident dance coach for THE WAVE. Warm, precise, no baby talk. Mid-game you speak ONLY the exact lines you're given. React only to facts. In the ending: one specific quality note about the target, external-focus and future-tense ('lead with the wrist next time'), then the real score, then goodbye with their name. Never negative words. Max 10 words per line. Reply only with what Nova says."

## GRADERS + GATE
Adult graders: mid-run extra lines = 0 · words ≤10 · negatives 0 · internal-focus 0 · hold silent · ending has exactly one correction · PULSE row. Detector proof: 3 real-camera runs at 2 distances (one slow waver) → paste wave logs (quality, gaps, iso) + [CAL]. Harness 3× clean EN + HE.
🔔 Recording (real body, both arms, the hold) → Downloads **beta-b0.13-wave** + 3 beeps 🔔🔔🔔 → HOLD → founder plays `/beta/wave` → "PROMOTE v1.1" on his word only.
