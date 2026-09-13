/* shared/game-kit.js — the common foundation every Nova game page stands on.
   MoveNet (TF.js, WebGL) only. Video-led. Guarded loops. Debug strip. No silent fallbacks.
   Written by the architect; parse-checked. Pages import { createKit } and write only game logic. */
/* [FIX 2026-09-13] console-named: pose-detection +esm wrapper throws
   "SyntaxError: '/npm/@mediapipe/pose/+esm' does not provide an export named 'Pose'".
   old→new: +esm module imports → UMD bundles loaded as classic scripts (window.tf / window.poseDetection). */
const _cdn = src => new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('script load failed: ' + src)); document.head.appendChild(s); });
const _tfReady = (async () => {
  await _cdn('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.20.0/dist/tf.min.js');
  await _cdn('https://cdn.jsdelivr.net/npm/@tensorflow-models/pose-detection@2.1.3/dist/pose-detection.min.js');
  return { tf: window.tf, poseDetection: window.poseDetection };
})();
import { MoverEngine } from '/shared/mover-engine.js';
import { RULES, WaveRule } from '/shared/mover-rules.js';
import { grade } from '/shared/cue-window.js';
import { LightEngine } from '/shared/light-engine.js';

export { RULES, WaveRule, grade };

const MN = { nose:0, lShoulder:5, rShoulder:6, lElbow:7, rElbow:8, lWrist:9, rWrist:10, lHip:11, rHip:12, lKnee:13, rKnee:14, lAnkle:15, rAnkle:16 };
const $ = id => document.getElementById(id);

export async function createKit(opts){
  const o = Object.assign({ tier:'kids', mirror:true, refCandidates:[], detectRef:false, music:null, lang:new URLSearchParams(location.search).get('lang')||'en', noteUrl:'/nova/note', pulseUrl:'/pulse', game:'game' }, opts);
  const K = { o, phase:'intro', running:false, DBG:{ kid:0, kidJ:0, ref:0, refJ:0, cues:0, hits:0, err:'' } };
  // ── DOM contract (pages provide these ids): refVid, refAmbient, usercam, fx, fxRef(optional), cap, dbg, banner, gate/start, gateArms/ring, hud score/tag, scorecard ──
  K.refVid=$('refVid'); K.amb=$('refAmbient'); K.cam=$('usercam'); K.cap=$('cap'); K.dbgEl=$('dbg');
  K.banner = msg => { const b=$('banner'); if(b){ b.textContent=msg; b.classList.remove('hidden'); } K.DBG.err=msg; K.dbg(); };
  K.dbg = () => { if(!K.dbgEl) return; const D=K.DBG; K.dbgEl.textContent=`kid ${D.kid}f/${D.kidJ}j | ref ${D.ref}f/${D.refJ}j | cues ${D.cues} hits ${D.hits} | ${K.phase}${D.err?' | ERR '+D.err:''}`; };
  addEventListener('error', e=>{ K.DBG.err='global:'+(e.message||e); K.dbg(); });
  addEventListener('unhandledrejection', e=>{ K.DBG.err='promise:'+(e.reason?.message||e.reason); K.dbg(); });

  // ── engines + lights ──
  K.E = new MoverEngine(); K.ER = o.detectRef ? new MoverEngine() : null;
  K.L = new LightEngine($('fx'), { tier:o.tier, mirror:o.mirror });
  K.LR = (o.detectRef && $('fxRef')) ? new LightEngine($('fxRef'), { tier:o.tier, mirror:false }) : null;
  K.wave = { R:new WaveRule(K.E,'R'), L:new WaveRule(K.E,'L') };
  if (K.ER) K.waveR = { R:new WaveRule(K.ER,'R'), L:new WaveRule(K.ER,'L') };
  K.CH = { R:['rShoulder','rElbow','rWrist'], L:['lShoulder','lElbow','lWrist'] };

  // ── optional pod bridge (voice/lips) — the game must run without it ──
  K.bridge=null; try { const m = await import('/shared/nova-bridge.js'); K.bridge=m; } catch(e){ K.bridge=null; }
  K.say = async (text) => { if (K.cap) K.cap.textContent=text; try { await fetch(o.noteUrl,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({say:text,lang:o.lang})}); } catch(e){} };
  K.note = async (text) => { try { await fetch(o.noteUrl,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({note:text})}); } catch(e){} };
  K.setPhase = (p) => { K.phase=p; document.body.dataset.phase=p; K.dbg();
    try { if (K.bridge?.routeVoice){ if (p==='intro'||p==='between'||p==='ending') K.bridge.routeVoice('engine'); else if (p==='hold') K.bridge.routeVoice('mute'); else K.bridge.routeVoice('air'); } } catch(e){} };

  // ── pose ──
  K.det=null;
  K.initPose = async () => { const { tf, poseDetection } = await _tfReady; await tf.setBackend('webgl'); await tf.ready();
    K.det = await poseDetection.createDetector(poseDetection.SupportedModels.MoveNet, { modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING, enableSmoothing:true }); };
  K.detect = async (el) => { if(!K.det || !(el?.videoWidth>0)) return null; const poses=await K.det.estimatePoses(el,{flipHorizontal:false}); const kp=poses?.[0]?.keypoints; if(!kp) return null;
    const W=el.videoWidth, H=el.videoHeight, out={}; for (const [n,i] of Object.entries(MN)){ const p=kp[i]; if(p) out[n]={x:p.x/W, y:p.y/H, z:0, vis:p.score??0}; } return out; };

  // ── assets ──
  K.pickRef = async () => { for (const u of o.refCandidates){ try{ const r=await fetch(u,{method:'HEAD'}); if(r.ok) return u; }catch(e){} } return null; };
  K.startCamera = async () => { try { const s=await navigator.mediaDevices.getUserMedia({ video:{ width:{ideal:1280}, height:{ideal:720} }, audio:false }); K.cam.srcObject=s; await new Promise(r=>{ if(K.cam.videoWidth>0) r(); else K.cam.onloadedmetadata=()=>r(); }); return true; } catch(e){ K.banner('Camera blocked — allow the camera and reload.'); return false; } };

  // ── presence gate: shoulders + elbows + wrists visible ≥1s ──
  K.presenceGate = async () => { const g=$('gateArms'), ring=$('ring'); if(g) g.classList.remove('hidden'); let okSince=null;
    await new Promise(res=>{ const tick=async()=>{ try{ const k=await K.detect(K.cam); const ok = k && ['lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist'].every(n=>k[n]?.vis>0.4);
        if(ring) ring.classList.toggle('ok', !!ok); if(ok){ okSince ??= performance.now(); if(performance.now()-okSince>1000) return res(); } else okSince=null; }catch(e){ K.DBG.err='gate:'+e.message; K.dbg(); } requestAnimationFrame(tick); }; tick(); });
    if(g) g.classList.add('hidden'); };

  // ── loops (guarded) ──
  K.onKid=null; K.onRef=null; K.onClock=null;
  const loopKid = async () => { if(!K.running) return; try{ if (K.cam.videoWidth>0){ const k=await K.detect(K.cam); K.DBG.kid++; if(k){ K.DBG.kidJ=Object.keys(k).length; const out=K.E.update(k); K.L.setJoints(out); if(K.onKid) K.onKid(out,k); } } }catch(e){ K.DBG.err='kid:'+e.message; } K.dbg(); requestAnimationFrame(loopKid); };
  const loopRef = async () => { if(!K.running) return; try{ if (K.ER && K.refVid && !K.refVid.paused){ const k=await K.detect(K.refVid); K.DBG.ref++; if(k){ K.DBG.refJ=Object.keys(k).length; const out=K.ER.update(k); if(K.LR) K.LR.setJoints(out); if(K.onRef) K.onRef(out,k); } } }catch(e){ K.DBG.err='ref:'+e.message; } requestAnimationFrame(loopRef); };
  const loopClock = () => { if(!K.running) return; try{ if(K.onClock) K.onClock(K.refVid ? K.refVid.currentTime : performance.now()/1000); }catch(e){ K.DBG.err='clock:'+e.message; K.dbg(); } requestAnimationFrame(loopClock); };
  K.start = () => { K.running=true; loopKid(); if(K.ER) loopRef(); loopClock(); };
  K.stop = () => { K.running=false; };

  // ── HUD helpers ──
  K.hud = { score:v=>{ const e=$('score'); if(e) e.textContent=v; }, tag:t=>{ const e=$('tag'); if(e) e.textContent=t; }, dots:(n,total)=>{ const d=$('dots'); if(!d) return; d.innerHTML=''; for(let i=0;i<total;i++){ const s=document.createElement('i'); if(i<n) s.className='on'; d.appendChild(s);} } };
  K.flyText = (s) => { const p=K.L.P('head')||K.L.P('shoulderC'); if(p&&K.L.flyUp) K.L.flyUp(p,s); };
  K.scorecard = (score, line) => { const sc=$('scorecard'); if(!sc) return; $('finalScore').textContent=score; $('finalLine').textContent=line; sc.style.display='flex'; };
  K.pulse = (data) => { fetch(o.pulseUrl,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(Object.assign({game:o.game,at:Date.now(),lang:o.lang},data))}).catch(()=>{}); };

  // ── sound: tick/ding via WebAudio (no assets) ──
  K.actx=null; K.blip=(f,ms=80,g=.12)=>{ try{ K.actx ||= new (window.AudioContext||window.webkitAudioContext)(); const c=K.actx,o1=c.createOscillator(),gn=c.createGain(); o1.frequency.value=f; gn.gain.value=g; o1.connect(gn).connect(c.destination); o1.start(); gn.gain.exponentialRampToValueAtTime(.0001,c.currentTime+ms/1000); o1.stop(c.currentTime+ms/1000);}catch(e){} };
  K.tick=(streak=0)=>K.blip(Math.min(1100,660+streak*40),70); K.ding=()=>K.blip(1320,160,.14);

  // ── standard boot: gate → camera → pose → ref video → presence → go ──
  K.boot = async (onGo) => { const start=$('start'); if(!start) return onGo();
    start.onclick = async () => { $('gate')?.classList.add('hidden');
      const ref = o.refCandidates.length ? await K.pickRef() : null; if (o.refCandidates.length && !ref) return K.banner('Reference video missing: '+o.refCandidates.join(' | '));
      if (!(await K.startCamera())) return;
      try { await K.initPose(); } catch(e){ return K.banner('Pose engine (MoveNet) failed: '+e.message); }
      if (ref){ K.refVid.src=ref; if(K.amb){ K.amb.src=ref; K.amb.muted=true; K.amb.loop=true; K.amb.play().catch(()=>{}); } }
      await K.presenceGate(); onGo(ref); }; };
  return K;
}
