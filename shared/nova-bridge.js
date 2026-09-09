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
//
// POD-VERIFY (needs a live pod to confirm against rt_lk): the exact ws message vocabulary.
// This sends {type:'nova-say'|'nova-cue'|'speak_gate'|'audio'} — the same types beta/freeze.html
// posts today. `note()` splits on the "say exactly"/"fact" prefix; if rt_lk expects a different
// tag for staged lines, adjust HERE only (the pages never change).

const BASE = location.origin + '/';
const WSBASE = BASE.replace(/^http/, 'ws');

let ws = null, room = null, voiceGain = null, audioEl = null, ctx = null;
let speakGated = false, micGated = false, wsConns = 0, wsDelay = 1500;
const herAudio = { playing: () => {}, ended: () => {} };

// ── public API ──────────────────────────────────────────────────────────────
export async function attachNova({ onVideo, intro = '' } = {}) {
  await joinLiveKit(onVideo);
  connectWS(intro);
  try { await startMic(); } catch (e) { console.warn('[BRIDGE] mic blocked', e && e.message); }
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

export function onHerAudio({ playing, ended } = {}) {
  if (playing) herAudio.playing = playing;
  if (ended) herAudio.ended = ended;
}

// ── internals (faithful to beta/freeze.html Live) ────────────────────────────
async function joinLiveKit(onVideo) {
  try {
    const LK = window.LivekitClient || window.LiveKitClient;
    if (!LK) { console.warn('[BRIDGE] LiveKit client not loaded'); return; }
    const r = await (await fetch(BASE + 'token')).json();
    room = new LK.Room({ adaptiveStream: false, dynacast: false });
    room.on(LK.RoomEvent.TrackSubscribed, (track, pub, p) => {
      if (p.identity !== 'nova-avatar') return;
      if (track.kind === 'video' && onVideo) onVideo(new MediaStream([track.mediaStreamTrack]));
      if (track.kind === 'audio') routeHerAudio(track);
    });
    let rc = 2000;
    const resub = async () => {
      try { const r2 = await (await fetch(BASE + 'token')).json(); await room.connect(r2.url, r2.token); rc = 2000; }
      catch (_) { rc = Math.min(30000, Math.round(rc * 1.8)); setTimeout(resub, rc); }
    };
    room.on(LK.RoomEvent.Disconnected, () => setTimeout(resub, rc));
    await room.connect(r.url, r.token);
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
  ws.onopen = () => { wsDelay = 1500; };
  ws.onclose = () => { wsDelay = Math.min(30000, Math.round((wsDelay || 1500) * 1.8)); setTimeout(() => connectWS(intro), wsDelay); };
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
