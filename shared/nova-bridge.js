// shared/nova-bridge.js — the page↔pod live bridge as a reusable module (b0.13).
// Extracted from the proven one-origin `Live` object in beta/freeze.html so every game
// drives Nova's live voice/avatar the same way. Exposes the names the game pages import:
//   attachNova({onVideo})  — join LiveKit, pipe her video out, open the /rt brain socket, start mic
//   setBody(id)            — GET /set_avatar?id=<id>   (swap the baked avatar)
//   routeVoice(mode)       — 'engine' (she speaks normally) | 'air' (page-credited, ≤1/gap) | 'mute'
//   note(text)             — a director note to the brain: "say exactly: …" = a spoken line;
//                            "fact: …" = silent context (mirrors the freeze staged-line contract)
//   onHerAudio({playing,ended}) — fires around her live-voice turns (for music ducking)
//   window 'nova:consent'  — dispatched when a validated kid "yes" arrives at the name/ready beat
//   attachNova({onFace})   — [b0.27 freeze4] OPTIONAL: the live FACE stream (SoulX-FlashHead close-up), published as a
//                            second LiveKit participant `nova-face`. onFace(MediaStream) when it arrives,
//                            onFace(null) when it goes away. Pages that pass no onFace behave exactly as before.
//   bridgeState()          — [b0.27 freeze4] { room, ws, face, voice } booleans, so a page can show the red banner
//                            (no silent fallbacks) instead of guessing what is missing.
//
// POD-VERIFY (needs a live pod to confirm against rt_lk): the exact ws message vocabulary.
// This sends {type:'nova-say'|'nova-cue'|'speak_gate'|'audio'} — the same types beta/freeze.html
// posts today. `note()` splits on the "say exactly"/"fact" prefix; if rt_lk expects a different
// tag for staged lines, adjust HERE only (the pages never change).
//
// FACE: tools/pod/nova_face.py publishes `nova-face` (SoulX face video + her voice audio) when the pod runs with
// NOVA_FACE_SOULX=1 (docs/FREEZE4-SOULX-FACE.md). Change FACE_ID HERE only if that identity ever changes.

// FACE (2026-11-11, nova-take8c): Ditto draws her lips everywhere. shared/nova-face.js reads which engine the pod's
// bridge reports and raises the red banner when it is not Ditto. Under Ditto the live track is ALWAYS her talking
// body (the Ditto source, her room, full figure): a non-talk body asked through setBody() is NOT drawn by the pod,
// so it is said out loud (red banner) instead of silently showing the talk body.
import { watchFace, faceState, faceOK, onFace, redBanner } from './nova-face.js';
export { faceState, faceOK, onFace };
const TALK_BODIES = new Set(['nova_idle2', 'nova_idle']);   // beta/freeze.html TALK_BODY + the Ditto pack's idle

const BASE = location.origin + '/';
const WSBASE = BASE.replace(/^http/, 'ws');

let ws = null, room = null, voiceGain = null, audioEl = null, ctx = null;
let speakGated = false, micGated = false, wsConns = 0, wsDelay = 1500;
const herAudio = { playing: () => {}, ended: () => {} };
const FACE_ID = 'nova-face';                         // = FACE_IDENTITY in tools/pod/nova_face.py
const state = { room: false, ws: false, face: false, voice: false };
export function bridgeState() { return { ...state }; }

// ── public API ──────────────────────────────────────────────────────────────
export async function attachNova({ onVideo, onFace, intro = '' } = {}) {
  await joinLiveKit(onVideo, onFace);
  connectWS(intro);
  try { await startMic(); } catch (e) { console.warn('[BRIDGE] mic blocked', e && e.message); }
}

export function setBody(id) {
  if (!id) return;
  if (faceState().face === 'ditto' && !TALK_BODIES.has(id)) {
    // QUESTION (founder): under Ditto the pod shows only the talking body; game bodies must come from the page
    // (clips) or the in-game face engine. Until that exists for this page, say so — never a silent stand-in.
    redBanner(`⛔ body "${id}" is not drawn under Ditto — this page still asks the pod for it.`);
  }
  fetch(BASE + 'set_avatar?id=' + encodeURIComponent(id), { mode: 'no-cors', cache: 'no-store' }).catch(() => {});
}

export function routeVoice(mode) {
  // 'engine' → she may speak through the engine (intro/ending). 'air' → one page-credited
  // line per gap, streamed as voice_air. 'mute' → no generations at all (freeze hold).
  speakGated = mode !== 'engine';
  if (voiceGain) voiceGain.gain.value = (mode === 'engine' || mode === 'air') ? 1 : 0;
  send({ type: 'speak_gate', on: speakGated, mode: mode === 'air' ? 'air' : 'hard' });
}

export function note(text) {
  if (!text) return;
  const say = /^\s*say\s+exactly\s*:/i.test(text);
  if (say) send({ type: 'nova-say', text: text.replace(/^\s*say\s+exactly\s*:\s*/i, '').replace(/^["']|["']$/g, '') });
  else send({ type: 'nova-cue', intent: 'note', ctx: text });   // facts / staging = silent context
}

export function onHerAudio({ playing, ended } = {}) {
  if (playing) herAudio.playing = playing;
  if (ended) herAudio.ended = ended;
}

// ── internals (faithful to beta/freeze.html Live) ────────────────────────────
async function joinLiveKit(onVideo, onFace) {
  try {
    const LK = window.LivekitClient || window.LiveKitClient;
    if (!LK) { console.warn('[BRIDGE] LiveKit client not loaded'); return; }
    const r = await (await fetch(BASE + 'token')).json();
    room = new LK.Room({ adaptiveStream: false, dynacast: false });
    watchFace(room, LK);
    room.on(LK.RoomEvent.TrackSubscribed, (track, pub, p) => {
      if (p.identity === FACE_ID) {                  // the live face (SoulX): its video is her face, its audio is her voice —
        // tools/pod/nova_face.py renders the face FROM those very samples, so voice and face leave the pod together.
        // Only pages that pass onFace take her voice from here (a freeze4 pod has no nova-avatar participant).
        if (track.kind === 'video' && onFace) { state.face = true; onFace(new MediaStream([track.mediaStreamTrack])); }
        if (track.kind === 'audio' && onFace) { state.voice = true; routeHerAudio(track); }
        return;
      }
      if (p.identity !== 'nova-avatar') return;
      if (track.kind === 'video' && onVideo) onVideo(new MediaStream([track.mediaStreamTrack]));
      if (track.kind === 'audio') { state.voice = true; routeHerAudio(track); }
    });
    if (LK.RoomEvent.TrackUnsubscribed) room.on(LK.RoomEvent.TrackUnsubscribed, (track, pub, p) => {
      if (p.identity === FACE_ID && track.kind === 'video') { state.face = false; if (onFace) onFace(null); }
    });
    let rc = 2000;
    const resub = async () => {
      try { const r2 = await (await fetch(BASE + 'token')).json(); await room.connect(r2.url, r2.token); rc = 2000; state.room = true; }
      catch (_) { rc = Math.min(30000, Math.round(rc * 1.8)); setTimeout(resub, rc); }
    };
    room.on(LK.RoomEvent.Disconnected, () => { state.room = false; setTimeout(resub, rc); });
    await room.connect(r.url, r.token); state.room = true;
    console.log('[BRIDGE] LiveKit joined', r.room);
  } catch (e) { console.warn('[BRIDGE] room err', e && e.message); }
}

function routeHerAudio(track) {
  // route through a shared AudioContext so a single user-gesture unlock covers it (one-tap),
  // with a muted media element kept alive (Chrome only pumps WebRTC audio into WebAudio while
  // a media element also consumes the track).
  try {
    ctx ||= new (window.AudioContext || window.webkitAudioContext)();
    const ms = new MediaStream([track.mediaStreamTrack]);
    const src = ctx.createMediaStreamSource(ms);
    voiceGain = ctx.createGain(); voiceGain.gain.value = speakGated ? 0 : 1;
    src.connect(voiceGain); voiceGain.connect(ctx.destination);
    const a = track.attach(); a.muted = true; a.autoplay = true; a.playsInline = true; document.body.appendChild(a); audioEl = a;
    // level meter → herAudio.playing/ended for music ducking
    const an = ctx.createAnalyser(); an.fftSize = 512; voiceGain.connect(an);
    window.__novaVoiceAnalyser = an;                 // read-only probe for proof runs (voice-to-face delay); changes nothing
    const buf = new Float32Array(an.fftSize); let on = false;
    setInterval(() => {
      an.getFloatTimeDomainData(buf); let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      const rms = Math.sqrt(s / buf.length);
      if (rms > 0.01 && !on) { on = true; herAudio.playing(); }
      else if (rms <= 0.008 && on) { on = false; herAudio.ended(); }
    }, 100);
    console.log('[BRIDGE] her voice routed through shared AudioContext, state=' + ctx.state);
  } catch (e) {
    console.warn('[BRIDGE] webaudio route failed, bare element:', e && e.message);
    const a = track.attach(); a.autoplay = true; a.muted = !!speakGated; a.playsInline = true; document.body.appendChild(a); audioEl = a; a.play().catch(() => {});
  }
}

function connectWS(intro) {
  const qs = new URLSearchParams(location.search);
  if (intro) qs.set('intro', intro);
  if (wsConns++) qs.set('rc', '1');                 // seamless reconnect: no re-greet
  ws = new WebSocket(WSBASE + 'rt?' + qs.toString());
  ws.onopen = () => { wsDelay = 1500; state.ws = true; };
  ws.onclose = () => { state.ws = false; wsDelay = Math.min(30000, Math.round((wsDelay || 1500) * 1.8)); setTimeout(() => connectWS(intro), wsDelay); };
  ws.onmessage = (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch (_) { return; }
    if (m.type === 'voice_air') { herAudio.playing(); return; }
    if (m.type === 'nova_done') { herAudio.ended(); window.dispatchEvent(new CustomEvent('nova:said', { detail: m.text || '' })); return; }
    if (m.type === 'you_text') {
      const txt = (m.text || '').toLowerCase();
      window.dispatchEvent(new CustomEvent('nova:kid', { detail: m.text || '' }));
      // consent = a validated kid affirmation at the name/ready beat (EN + HE singles)
      if (/\b(yes|yeah|yep|ready|ok(ay)?|sure|let'?s go)\b/.test(txt) || /(כן|מוכן|מוכנה|אוקיי|סבבה|יאללה)/.test(txt))
        window.dispatchEvent(new Event('nova:consent'));
      return;
    }
    if (m.type === 'status') { if (m.speaking === true) micGated = true; else if (m.speaking === false) micGated = false; }
  };
}

async function startMic() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  const mctx = new (window.AudioContext || window.webkitAudioContext)(); if (mctx.state === 'suspended') await mctx.resume();
  const src = mctx.createMediaStreamSource(stream);
  const proc = mctx.createScriptProcessor(4096, 1, 1);
  const ratio = mctx.sampleRate / 24000;
  proc.onaudioprocess = (e) => {
    if (micGated) return;                            // anti-echo: drop mic while she speaks
    const ch = e.inputBuffer.getChannelData(0);
    const n = Math.floor(ch.length / ratio), b = new Int16Array(n);
    for (let i = 0; i < n; i++) { let s = ch[Math.floor(i * ratio)]; if (s > 1) s = 1; if (s < -1) s = -1; b[i] = s * 0x7fff; }
    const u = new Uint8Array(b.buffer); let x = ''; for (let i = 0; i < u.length; i++) x += String.fromCharCode(u[i]);
    send({ type: 'audio', data: btoa(x) });
  };
  src.connect(proc); proc.connect(mctx.destination);
}

function send(obj) { try { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); } catch (_) {} }
