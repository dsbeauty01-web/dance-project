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
//   attachNova({onWide})   — [NOVA-FINAL 2026-11-12] OPTIONAL: her WIDE talking body (Ditto lips on her body in her
//                            room), a second video track `nova-wide-video` of the same `nova-face` participant
//                            (tools/pod/nova_face.py FACE_RENDERER=dual). onWide(MediaStream) / onWide(null).
//   bridgeState()          — [b0.27 freeze4] { room, ws, face, voice } booleans, so a page can show the red banner
//                            (no silent fallbacks) instead of guessing what is missing.
//
//   window 'nova:hearing' / 'nova:kid-delta' / 'nova:kid' / 'nova:kid-drop' — [2026-11-22] what the PLAYER says, live:
//                            the brain heard a voice start (status.hearing) · words as they are recognised (you_delta) ·
//                            the accepted turn (you_text, as before) · a turn it did not accept (you_drop; only sent by
//                            a pod started with NOVA_KID_EVENTS=1). Pages that do not listen behave exactly as before.
//   attachNova({echoGuard:true}) — [2026-11-22] OPTIONAL: also drop the mic while her voice is AUDIBLE in this browser.
//                            The brain reopens the mic 0.6 s after ITS last audio chunk, but with the Ditto body her
//                            voice is played DITTO_PRIME (1.4 s) later, so her last words could come back in as a
//                            "kid turn". Off unless a page asks for it.
//
//   [NOVA-GO4 2026-11-23, docs/NOVA-FIX-2026-11-23b.md — the player must be HEARD; all optional, off unless a page asks]
//   primeAudio()           — call it INSIDE the Play tap: her voice's AudioContext and the microphone's are created and
//                            resumed in the user gesture (the commercial page's one-tap audio unlock), and any later tap
//                            resumes them again if the browser suspended them.
//   attachNova({micStream}) — use THIS microphone stream (the one the permission question returned) instead of opening
//                            a second one. One capture, never stopped behind the bridge's back.
//   attachNova({micMeter:true}) — window 'nova:mic' every 250 ms: { level 0..1, open, dead } where dead names why the
//                            microphone gives nothing ('ended' | 'muted' | 'suspended' | 'stalled' | 'silent' | '').
//   micState() / restartMic() — the same numbers on demand / open the microphone again (after a 'dead').
//   pageLog(kind, detail)  — a line of the page's own log to the brain (printed as [PAGE] when the pod runs NOVA_HEAR=1).
//
// POD-VERIFY (needs a live pod to confirm against rt_lk): the exact ws message vocabulary.
// This sends {type:'nova-say'|'nova-cue'|'speak_gate'|'audio'} — the same types beta/freeze.html
// posts today. `note()` splits on the "say exactly"/"fact" prefix; if rt_lk expects a different
// tag for staged lines, adjust HERE only (the pages never change).
//
// FACE: tools/pod/nova_face.py publishes `nova-face` (SoulX face video + her voice audio) when the pod runs with
// NOVA_FACE_SOULX=1 (docs/FREEZE4-SOULX-FACE.md). Change FACE_ID HERE only if that identity ever changes.

const BASE = location.origin + '/';
const WSBASE = BASE.replace(/^http/, 'ws');

let ws = null, room = null, voiceGain = null, audioEl = null, ctx = null;
// NOVA-GO4: the microphone, watched. chunks = audio callbacks, sent = chunks that went to the brain.
let mctxPrimed = null, micMeter = false, micTimer = null;
const mic = { stream: null, track: null, ctx: null, proc: null, src: null, chunks: 0, sent: 0, heldBrain: 0, heldEcho: 0, peak: 0, peakHold: 0, lastCbAt: 0, lastSoundAt: 0, startedAt: 0, mutedAt: 0, dead: '', error: '' };
// [CLI-FILL] no spec gives these: a callback gap of 2 s = stalled; 5 s of EXACT digital zero = a dead capture (a real
// microphone always has a noise floor); a track muted for 2 s = muted.
const MIC_STALL_MS = 2000, MIC_SILENT_MS = 5000, MIC_MUTED_MS = 2000;
// NOVA-GO4 echoLook (with micMeter): the echo guard, made tight. Rig run go4echo (her voice leaking into the microphone at
// half volume, no echo cancelling = the worst phone): the guard looked at her level every 100 ms on a 10 ms window, so the
// first ~100 ms of every phrase after a pause went to the brain; the pieces added up to "kid turns" ("Hi", "No") and she
// answered herself. Now her level is read for every microphone buffer over a full buffer's window, and a buffer is only
// sent after she has stayed quiet for the next ECHO_LOOK buffers (~0.18 s later): an onset can no longer slip through.
// The child's own words are never cut by this - they only arrive ~0.18 s later. [CLI-FILL] 2 buffers; peak 0.01.
let herWide = null, herWideBuf = null, herLoudAt = 0; const ECHO_LOOK = 2, micFifo = [];
function herLoudNow() {
  if (!herWide) return herOn;
  herWide.getFloatTimeDomainData(herWideBuf); let pk = 0;
  for (let i = 0; i < herWideBuf.length; i += 4) { const a = herWideBuf[i] < 0 ? -herWideBuf[i] : herWideBuf[i]; if (a > pk) pk = a; }
  return pk > 0.01;
}
let speakGated = false, micGated = false, wsConns = 0, wsDelay = 1500;
// echoGuard: [CLI-FILL] 300 ms tail after her voice goes quiet (room echo; the level meter below already needs
// <= 100 ms to notice the quiet). No spec gives it. QUESTION.
let echoGuard = false, herOn = false, herOffAt = 0; const ECHO_TAIL_MS = 300;
// [NOVA-GO5 react 2026-11-24] holdMicFor(ms): the page plays a short sound of hers locally (her listening hum) — the mic
// is held for that long so the hum never reaches the brain as the child's words.
let localHoldUntil = 0;
export function holdMicFor(ms) { localHoldUntil = Math.max(localHoldUntil, performance.now() + ms); }
// NOVA-FINAL: several listeners (a page's music ducking AND shared/nova-live.js's "her line is said" both need it;
// a second onHerAudio() used to silently replace the first).
const _herL = { playing: [], ended: [] };
const herAudio = { playing: () => _herL.playing.forEach(f => { try { f(); } catch (_) {} }), ended: () => _herL.ended.forEach(f => { try { f(); } catch (_) {} }) };
const FACE_ID = 'nova-face';                         // = FACE_IDENTITY in tools/pod/nova_face.py
const state = { room: false, ws: false, face: false, voice: false, wide: false };
export function bridgeState() { return { ...state }; }

// ── public API ──────────────────────────────────────────────────────────────
export async function attachNova({ onVideo, onFace, onWide, intro = '', echoGuard: eg = false, micStream = null, micMeter: mm = false } = {}) {
  echoGuard = !!eg; micMeter = !!mm;
  await joinLiveKit(onVideo, onFace, onWide);
  connectWS(intro);
  try { await startMic(micStream); } catch (e) { mic.error = String(e && e.message || e); console.warn('[BRIDGE] mic blocked', e && e.message); }
  if (micMeter && !micTimer) micTimer = setInterval(micTick, 250);
}

// NOVA-GO4 — inside the Play tap (a user gesture): both audio contexts exist and run before anything is awaited.
export function primeAudio() {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    ctx ||= new AC(); mctxPrimed ||= new AC();
    const wake = () => { for (const c of [ctx, mctxPrimed, mic.ctx]) { try { if (c && c.state === 'suspended') c.resume(); } catch (_) {} } };
    wake();
    if (!primeAudio.on) { primeAudio.on = true; for (const ev of ['pointerdown', 'touchend', 'keydown']) window.addEventListener(ev, wake, { passive: true }); }
    return { voice: ctx.state, mic: mctxPrimed.state };
  } catch (e) { return { error: String(e && e.message || e) }; }
}
export function micState() {
  const t = mic.track;
  return { chunks: mic.chunks, sent: mic.sent, heldBrain: mic.heldBrain, heldEcho: mic.heldEcho, peak: +mic.peakHold.toFixed(4), dead: mic.dead, error: mic.error,
           track: t ? t.readyState + (t.muted ? '/muted' : '') + (t.enabled ? '' : '/disabled') : 'none', label: t ? (t.label || '').slice(0, 40) : '',
           ctx: mic.ctx ? mic.ctx.state : 'none', rate: mic.ctx ? mic.ctx.sampleRate : 0, voiceCtx: ctx ? ctx.state : 'none', ws: !!(ws && ws.readyState === 1), open: micOpen() };
}
export function pageLog(kind, detail) { send({ type: 'page_log', t: +(performance.now() / 1000).toFixed(2), kind, detail: typeof detail === 'string' ? detail : JSON.stringify(detail) }); }
export async function restartMic() {
  try { if (mic.proc) mic.proc.disconnect(); if (mic.src) mic.src.disconnect(); if (mic.stream) mic.stream.getTracks().forEach(t => t.stop()); } catch (_) {}
  mic.stream = mic.track = mic.proc = mic.src = null; mic.dead = ''; mic.error = '';
  try { await startMic(null); return true; } catch (e) { mic.error = String(e && e.message || e); return false; }
}
function micOpen() { return !micGated && !(echoGuard && (herOn || performance.now() - herOffAt < ECHO_TAIL_MS)); }
function micTick() {
  const now = performance.now(), t = mic.track; let dead = '';
  if (!t || mic.error) dead = 'ended';
  else if (t.readyState === 'ended') dead = 'ended';
  else if (t.muted && mic.mutedAt && now - mic.mutedAt > MIC_MUTED_MS) dead = 'muted';
  else if (mic.ctx && mic.ctx.state !== 'running') dead = 'suspended';
  else if (mic.startedAt && now - Math.max(mic.lastCbAt, mic.startedAt) > MIC_STALL_MS) dead = 'stalled';
  else if (mic.startedAt && now - Math.max(mic.lastSoundAt, mic.startedAt) > MIC_SILENT_MS) dead = 'silent';
  if (dead !== mic.dead) { mic.dead = dead; console.log('[BRIDGE] mic ' + (dead ? 'DEAD: ' + dead : 'alive'), JSON.stringify(micState())); }
  window.dispatchEvent(new CustomEvent('nova:mic', { detail: { level: Math.min(1, mic.peak * 3), open: micOpen(), dead } }));
  mic.peakHold = Math.max(mic.peak, mic.peakHold * 0.9); mic.peak = 0;
}

export function setBody(id) {
  if (!id) return;
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

// [NOVA-GO5 2026-11-24] the approved live intro (pod/rt_lk.py NOVA_V2V_INTRO=1, page flag `v2vintro`):
//   liveIntro('greet')        — ask the brain for her greeting + name question, said INSIDE the conversation.
//                               window 'nova:v2v' { detail: true|false } = the brain's answer (false / no event = a brain
//                               without the flag: the page falls back to its staged greeting).
//   liveIntro('armed', why)   — the page has the name (or its safety ran out) and takes the shoulder-light beat.
export function liveIntro(what, why = '') { send({ type: what === 'greet' ? 'v2v-greet' : 'v2v-armed', why }); }

export function onHerAudio({ playing, ended } = {}) {
  if (playing) _herL.playing.push(playing);
  if (ended) _herL.ended.push(ended);
}

// ── internals (faithful to beta/freeze.html Live) ────────────────────────────
async function joinLiveKit(onVideo, onFace, onWide) {
  try {
    const LK = window.LivekitClient || window.LiveKitClient;
    if (!LK) { console.warn('[BRIDGE] LiveKit client not loaded'); return; }
    const r = await (await fetch(BASE + 'token')).json();
    room = new LK.Room({ adaptiveStream: false, dynacast: false });
    room.on(LK.RoomEvent.TrackSubscribed, (track, pub, p) => {
      if (p.identity === FACE_ID) {                  // the live face (SoulX): its video is her face, its audio is her voice —
        // tools/pod/nova_face.py renders the face FROM those very samples, so voice and face leave the pod together.
        // Only pages that pass onFace take her voice from here (a freeze4 pod has no nova-avatar participant).
        const wideTrack = pub && pub.trackName === 'nova-wide-video';   // NOVA-FINAL: her Ditto body, not the SoulX face
        if (track.kind === 'video' && wideTrack) { if (onWide) { state.wide = true; onWide(new MediaStream([track.mediaStreamTrack])); } return; }
        if (track.kind === 'video' && onFace) { state.face = true; onFace(new MediaStream([track.mediaStreamTrack])); }
        if (track.kind === 'audio' && onFace) { state.voice = true; routeHerAudio(track); }
        return;
      }
      if (p.identity !== 'nova-avatar') return;
      if (track.kind === 'video' && onVideo) onVideo(new MediaStream([track.mediaStreamTrack]));
      if (track.kind === 'audio') { state.voice = true; routeHerAudio(track); }
    });
    if (LK.RoomEvent.TrackUnsubscribed) room.on(LK.RoomEvent.TrackUnsubscribed, (track, pub, p) => {
      if (p.identity === FACE_ID && track.kind === 'video') {
        if (pub && pub.trackName === 'nova-wide-video') { state.wide = false; if (onWide) onWide(null); }
        else { state.face = false; if (onFace) onFace(null); }
      }
    });
    let rc = 2000;
    const resub = async () => {
      try { const r2 = await (await fetch(BASE + 'token')).json(); await room.connect(r2.url, r2.token); rc = 2000; state.room = true; }
      catch (_) { rc = Math.min(30000, Math.round(rc * 1.8)); setTimeout(resub, rc); }
    };
    room.on(LK.RoomEvent.Disconnected, () => { state.room = false; setTimeout(resub, rc); });
    await room.connect(r.url, r.token); state.room = true;
    // NOVA-TRACE (2026-11-25, read-only): the player's network to the media server, every 5 s — measured, not guessed.
    try {
      pageLog('net', { region: (room.serverInfo && room.serverInfo.region) || null, edge: (room.serverInfo && room.serverInfo.nodeId) || null });
      setInterval(async () => {
        try {
          const pc = room.engine && room.engine.pcManager && (room.engine.pcManager.subscriber || room.engine.pcManager.publisher);
          const st = pc && pc.getStats ? await pc.getStats() : null; let rtt = null, jit = null, lost = null;
          if (st) st.forEach(x => {
            if (x.type === 'candidate-pair' && x.nominated && x.currentRoundTripTime != null) rtt = Math.round(x.currentRoundTripTime * 1000);
            if (x.type === 'inbound-rtp' && x.kind === 'audio') { jit = Math.round((x.jitter || 0) * 1000); lost = x.packetsLost; }
          });
          pageLog('net', { rtt_ms: rtt, jitter_ms: jit, lost });
        } catch (e) {}
      }, 5000);
    } catch (e) {}
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
    herWide = ctx.createAnalyser(); herWide.fftSize = 4096; herWideBuf = new Float32Array(4096); voiceGain.connect(herWide);   // NOVA-GO4 echoLook
    const buf = new Float32Array(an.fftSize); let on = false;
    setInterval(() => {
      an.getFloatTimeDomainData(buf); let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      const rms = Math.sqrt(s / buf.length);
      if (rms > 0.01 && !on) { on = true; herOn = true; herAudio.playing(); }
      else if (rms <= 0.008 && on) { on = false; herOn = false; herOffAt = performance.now(); herAudio.ended(); }
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
  ws.onopen = () => { wsDelay = 1500; state.ws = true; if (micMeter) micGated = false; };   // NOVA-GO4 (with micMeter): a NEW brain session has not said "speaking" - a gate left closed by the old one would never reopen
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
    if (m.type === 'ack' && m.of === 'v2v-greet') { window.dispatchEvent(new CustomEvent('nova:v2v', { detail: !!m.on })); return; }
    if (m.type === 'you_delta') { window.dispatchEvent(new CustomEvent('nova:kid-delta', { detail: m.delta || '' })); return; }
    if (m.type === 'you_drop') { window.dispatchEvent(new CustomEvent('nova:kid-drop', { detail: { text: m.text || '', why: m.why || '' } })); return; }
    if (m.type === 'status') { if (m.speaking === true) micGated = true; else if (m.speaking === false) micGated = false;
      if (m.hearing === true) window.dispatchEvent(new Event('nova:hearing'));
      // NOVA-LIVE2: the child just stopped talking (the brain's voice detector), with how long he talked, in seconds
      if (typeof m.kid_stopped === 'number') window.dispatchEvent(new CustomEvent('nova:kid-stopped', { detail: m.kid_stopped })); }
  };
}

async function startMic(given) {
  const live = given && given.getAudioTracks().some(t => t.readyState === 'live');
  const stream = live ? given : await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  const mctx = mctxPrimed || new (window.AudioContext || window.webkitAudioContext)();
  // a resume() outside a user gesture can stay pending for ever on some browsers; with a primed context never wait on it
  if (mctx.state === 'suspended') { if (mctxPrimed) mctx.resume().catch(() => {}); else await mctx.resume(); }
  const src = mctx.createMediaStreamSource(stream);
  const proc = mctx.createScriptProcessor(4096, 1, 1);
  const ratio = mctx.sampleRate / 24000;
  const tr = stream.getAudioTracks()[0];
  Object.assign(mic, { stream, track: tr, ctx: mctx, proc, src, startedAt: performance.now(), lastCbAt: 0, lastSoundAt: 0, mutedAt: tr && tr.muted ? performance.now() : 0, dead: '' });
  if (tr) { tr.addEventListener('mute', () => { mic.mutedAt = performance.now(); }); tr.addEventListener('unmute', () => { mic.mutedAt = 0; });
    tr.addEventListener('ended', () => { console.warn('[BRIDGE] mic track ended'); }); }
  proc.onaudioprocess = (e) => {
    const ch = e.inputBuffer.getChannelData(0);
    if (micMeter) {                                  // the level is measured on EVERY buffer, sent or held back
      let pk = 0; for (let i = 0; i < ch.length; i += 8) { const a = ch[i] < 0 ? -ch[i] : ch[i]; if (a > pk) pk = a; }
      const now = performance.now(); mic.chunks++; mic.lastCbAt = now; if (pk > 0) mic.lastSoundAt = now; if (pk > mic.peak) mic.peak = pk;
    }
    if (performance.now() < localHoldUntil) { mic.heldEcho++; micFifo.length = 0; return; }   // NOVA-GO5 react: her local hum
    const look = echoGuard && micMeter;              // NOVA-GO4 echoLook
    if (look) { const now = performance.now(); if (herLoudNow()) herLoudAt = now;
      if (micGated) { mic.heldBrain++; micFifo.length = 0; return; }
      if (herOn || now - herOffAt < ECHO_TAIL_MS || now - herLoudAt < ECHO_TAIL_MS) { mic.heldEcho += 1 + micFifo.length; micFifo.length = 0; return; } }
    else {
    if (micGated) { mic.heldBrain++; return; }       // anti-echo: drop mic while she speaks
    if (echoGuard && (herOn || performance.now() - herOffAt < ECHO_TAIL_MS)) { mic.heldEcho++; return; }   // …and while she is still AUDIBLE here
    }
    const n = Math.floor(ch.length / ratio), b = new Int16Array(n);
    for (let i = 0; i < n; i++) { let s = ch[Math.floor(i * ratio)]; if (s > 1) s = 1; if (s < -1) s = -1; b[i] = s * 0x7fff; }
    const u = new Uint8Array(b.buffer); let x = ''; for (let i = 0; i < u.length; i++) x += String.fromCharCode(u[i]);
    if (look) { micFifo.push(btoa(x)); while (micFifo.length > ECHO_LOOK) { mic.sent++; send({ type: 'audio', data: micFifo.shift() }); } return; }
    mic.sent++;
    send({ type: 'audio', data: btoa(x) });
  };
  src.connect(proc); proc.connect(mctx.destination);
}

function send(obj) { try { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); } catch (_) {} }
