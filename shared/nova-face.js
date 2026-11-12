// shared/nova-face.js — which engine draws Nova's lips, enforced the same way on every page (2026-11-11, nova-take8c).
//
// THE RULE (Refael, 2026-11-11): Nova talks with DITTO lips everywhere, and before the music and the game start she
// talks WIDE — her full body in her room — never a talking head. "This rule applies to all the games."
//
// HOW A PAGE KNOWS: the pod's bridge (tools/pod/ditto_bridge_patch.py, anchor A8) publishes its LiveKit participant
// metadata as {"face": "ditto"|"musetalk", "ready", "alarm", "w", "h"}. An unpatched bridge sends none.
//   face === 'ditto' and no alarm  -> OK, nothing shown.
//   anything else                  -> the repo's RED BANNER (no silent fallbacks — CLAUDE.md law 4), and
//                                     faceOK() returns false so the page can refuse its talk phase.
// FACE_GRACE_MS after her video arrives is the wait for the metadata ([CLI-FILL] 4000 ms: the bridge sets it right
// after publishing the track, measured on the pod as the line "bridge: face metadata ..."; 4 s covers a reconnect).
//
// WIDE: wide(video) pins the element to the whole figure — object-fit contain, centred — so no CSS default
// (the SARAY 'closeup' mode: cover + object-position 50% 8.6%, beta/freeze.html FRAME MODE) can crop her to a head.
//
// Used by: shared/nova-bridge.js (Nova Says and every game-kit page that attaches her), beta/freeze.html and
// beta/upgroove.html (their one-origin Live objects call watchFace on their own room). No page re-implements this.

export const FACE_REQUIRED = 'ditto';
const FACE_GRACE_MS = 4000;
const AVATAR_ID = 'nova-avatar';

const state = { face: null, ready: false, alarm: null, w: 0, h: 0, seen: false, verdict: 'waiting', why: '' };
const listeners = new Set();

export function faceState() { return { ...state }; }
export function faceOK() { return state.verdict === 'ok'; }
export function onFace(fn) { if (typeof fn === 'function') { listeners.add(fn); fn(faceState()); } return () => listeners.delete(fn); }

export function wide(video) {
  if (!video || !video.style) return;
  video.style.objectFit = 'contain';
  video.style.objectPosition = '50% 50%';
  video.dataset.novaFrame = 'wide';
}

export function redBanner(msg) {
  try {
    let b = document.getElementById('nova-face-banner');
    if (!b) {
      b = document.createElement('div');
      b.id = 'nova-face-banner';
      b.setAttribute('role', 'alert');
      b.style.cssText = 'position:fixed;left:0;right:0;top:0;z-index:2147483647;padding:10px 16px;' +
        'background:#b00020;color:#fff;font:600 15px/1.35 system-ui,sans-serif;text-align:center;box-shadow:0 2px 8px #0008';
      document.body.appendChild(b);
    }
    b.textContent = msg;
    b.hidden = false;
  } catch (_) {}
  try { console.error('[NOVA_FACE] ' + msg); } catch (_) {}
}

function clearBanner() { const b = document.getElementById('nova-face-banner'); if (b) b.hidden = true; }

function judge() {
  let v = 'ok', why = '';
  if (!state.seen) { v = 'waiting'; }
  else if (state.face !== FACE_REQUIRED) { v = 'missing'; why = state.face ? `engine is ${state.face}, not Ditto` : 'the pod did not report a Ditto face'; }
  else if (!state.ready) { v = 'missing'; why = 'Ditto is not ready'; }
  else if (state.alarm) { v = 'alarm'; why = state.alarm; }
  const changed = v !== state.verdict || why !== state.why;
  state.verdict = v; state.why = why;
  if (v === 'missing') redBanner(`⛔ Nova's Ditto face is missing — ${why}. No talking-head fallback.`);
  else if (v === 'alarm') redBanner(`⛔ Nova's Ditto face alarm — ${why}.`);
  else if (v === 'ok') clearBanner();
  if (changed) { const s = faceState(); listeners.forEach(fn => { try { fn(s); } catch (_) {} }); try { window.dispatchEvent(new CustomEvent('nova:face', { detail: s })); } catch (_) {} }
}

function readMeta(p) {
  if (!p || p.identity !== AVATAR_ID) return;
  let m = null;
  try { m = p.metadata ? JSON.parse(p.metadata) : null; } catch (_) { m = null; }
  if (m && typeof m === 'object') {
    state.face = String(m.face || '').toLowerCase() || null;
    state.ready = !!m.ready; state.alarm = m.alarm || null; state.w = m.w | 0; state.h = m.h | 0;
    state.seen = true; judge();
  }
}

// room: a LiveKit Room (livekit-client). LK: the LiveKit namespace (window.LivekitClient). video: her <video>, kept WIDE.
export function watchFace(room, LK, { video } = {}) {
  if (!room || !LK) { state.seen = true; state.face = null; judge(); return; }
  const E = LK.RoomEvent || {};
  if (video) wide(video);
  room.on(E.TrackSubscribed, (track, pub, p) => {
    if (!p || p.identity !== AVATAR_ID || track.kind !== 'video') return;
    if (video) wide(video);
    readMeta(p);
    setTimeout(() => { if (!state.seen) { state.seen = true; state.face = null; } judge(); }, FACE_GRACE_MS);
  });
  if (E.ParticipantMetadataChanged) room.on(E.ParticipantMetadataChanged, (_old, p) => readMeta(p));
  try { (room.remoteParticipants || room.participants || new Map()).forEach(readMeta); } catch (_) {}
}
