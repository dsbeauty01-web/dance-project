// shared/face-panel.js — Nova's live FACE in a side panel (b0.27, first used by beta/freeze4.html).
//
// The face is a live video stream from the face engine (SoulX-FlashHead close-up) handed over by
// shared/nova-bridge.js (attachNova({ onFace })). This module only SHOWS it. It never draws a face itself,
// never plays a recorded one, and has no fallback picture: when the stream is missing the panel says so in red
// (CLAUDE.md law 4: no silent fallbacks — a missing asset = red banner).
//
// What it owns (so no game page re-implements it):
//   · the state badge at the bottom of the tile — Watching / Listening / Talking / Thinking / FREEZE!
//       lexi-ux-patterns Pattern 2 (four states, a small pill at the bottom of Nova's tile, same look at any size)
//       + game-cues-lights "Persistent: state badge (Watching/Listening/Talking/FREEZE!)"
//   · the size — small while she is quiet, bigger while she talks
//       lexi-ux-patterns Pattern 1 ("during dancing Nova is small in the corner (with state badge); when she has
//       something specific to say, she briefly grows") — the page's CSS decides the two widths
//   · the health of the stream — frames must keep arriving, or the red banner shows
//
// API
//   const P = createFacePanel({ root, video, badge, banner, lang, stallMs, onHealth, log })
//   P.attach(stream|null)        the bridge's onFace
//   P.waitLive(ms) → Promise<bool>  true once a real frame has been shown, false after ms
//   P.setBase('watching'|'listening'|'freeze')   what she is doing when she is not talking (the page's phase)
//   P.speaking(true|false)       the bridge's onHerAudio playing / ended
//   P.thinking()                 a line was asked for and her voice has not started yet
//   P.setActive(on)              [NOVA-FINAL] the pod renders this face only in its phase (FACE_RENDERER=dual: the SoulX
//                                face in the game, the Ditto body in intro/ending). While inactive the stall watchdog is
//                                off and no red banner shows; turning it on gives the stream one stall window to arrive.
//   P.state → { live, badge, size, frames, missing, active }

const TXT = {
  en: { watching: 'Watching', listening: 'Listening', talking: 'Talking', thinking: 'Thinking', freeze: 'FREEZE!',
        missing: "Nova's live face is not streaming" },
  he: { watching: 'מסתכלת', listening: 'מקשיבה', talking: 'מדברת', thinking: 'חושבת', freeze: 'קופאים!',
        missing: 'הפנים החיות של נובה לא משודרות' },
};

// lexi-ux-patterns Pattern 2: Thinking "covers latency >500ms" — the badge waits this long before it says so.
const THINK_AFTER_MS = 500;
// The face engine renders in chunks of 24 frames = 0.96 s at 25 fps (maya-lt maya-ops/lt/soulx_shim.py, SHIM_CHUNK),
// so a healthy stream can pause for about one chunk. 3 chunks without a new frame = missing.
// [CLI-FILL] 3000 ms: no spec gives a stall limit for a face stream; 3 x the measured chunk length. QUESTION for the founder.
export const FACE_STALL_MS = 3000;
// A thinking badge that never turns into talk goes back to the base state after this long (so it cannot stick).
// [CLI-FILL] 6000 ms — her measured reply latency is 1.04 s median, 7.0 s worst (docs/TALK-TEST.md, n=6); 6 s covers
// all but that worst case. No spec gives this number. QUESTION for the founder.
const THINK_GIVE_UP_MS = 6000;
// [CLI-FILL] 700 ms — longer than the gaps between her words in the pod recording (≤ 0.5 s), shorter than a pause
// between two lines. QUESTION for the founder.
const TALK_HOLD_MS = 700;

export function createFacePanel({ root, video, badge, banner, lang = 'en', stallMs = FACE_STALL_MS, onHealth = () => {}, log = () => {}, missingText = '', missingTag = 'SoulX' }) {
  const T = { ...(TXT[lang] || TXT.en), ...(missingText ? { missing: missingText } : {}) };
  const S = { live: false, badge: 'watching', size: 'small', frames: 0, missing: true, base: 'watching', talking: false, thinkAt: 0, lastFrameAt: 0, stream: null, active: true };
  let waiters = [];

  video.muted = true; video.playsInline = true; video.autoplay = true;      // her VOICE never comes from this element (bridge owns it)

  function paint() {
    const now = performance.now();
    const thinking = S.thinkAt && now - S.thinkAt > THINK_AFTER_MS && now - S.thinkAt < THINK_GIVE_UP_MS;
    if (S.thinkAt && now - S.thinkAt >= THINK_GIVE_UP_MS) S.thinkAt = 0;
    const b = S.talking ? 'talking' : thinking ? 'thinking' : S.base;
    const size = S.talking ? 'big' : 'small';
    if (b !== S.badge) { S.badge = b; log('badge', b); }
    if (size !== S.size) { S.size = size; log('size', size); }
    badge.textContent = T[b]; badge.dataset.state = b;
    root.dataset.size = size; root.dataset.state = b;
    root.dataset.live = S.live ? '1' : '0';
    banner.textContent = S.missing ? T.missing + (missingTag ? ' (' + missingTag + ')' : '') : '';
    const grace = !S.live && S.activeAt && now - S.activeAt < stallMs;      // just switched on: one stall window to arrive
    banner.hidden = !S.missing || !S.active || grace;
  }

  function setLive(live, why) {
    if (live === S.live) return;
    S.live = live; S.missing = !live; log(live ? 'face-live' : 'face-missing', why || '');
    onHealth(live, why || ''); paint();
    if (live) { waiters.forEach(w => w(true)); waiters = []; }
  }

  function onFrame() { S.frames++; S.lastFrameAt = performance.now(); if (!S.live) setLive(true, 'frame'); }

  // one callback per NEW decoded frame (Chrome/Safari); elsewhere watch currentTime move
  function pump() {
    if (typeof video.requestVideoFrameCallback === 'function') {
      const cb = () => { if (video.srcObject === S.stream && S.stream) { onFrame(); video.requestVideoFrameCallback(cb); } };
      video.requestVideoFrameCallback(cb);
    } else {
      let last = -1; const st = S.stream;
      const tick = () => { if (S.stream !== st || !st) return; if (video.currentTime !== last && video.videoWidth) { last = video.currentTime; onFrame(); } requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }
  }

  // watchdog on a timer, not rAF: a hidden tab stops rAF, and a stream that died must still be noticed when the tab returns
  const dog = setInterval(() => {
    if (S.active && S.live && performance.now() - S.lastFrameAt > stallMs) setLive(false, 'no new frame for ' + stallMs + ' ms');
    paint();
  }, 250);

  paint();
  return {
    attach(stream) {
      S.stream = stream || null; video.srcObject = S.stream;
      if (!stream) { setLive(false, 'track gone'); return; }
      log('face-track', 'attached'); video.play().catch(() => {}); pump();
    },
    waitLive(ms) { if (S.live) return Promise.resolve(true);
      return new Promise(ok => { const w = v => { clearTimeout(t); ok(v); }; const t = setTimeout(() => { waiters = waiters.filter(x => x !== w); ok(false); }, ms); waiters.push(w); }); },
    setBase(b) { if (TXT.en[b] && b !== 'talking' && b !== 'thinking') { S.base = b; paint(); } },
    // her voice level dips between words; without a hold the badge and the panel size flickered Talking↔Listening several
    // times a second (pod run 2026-11-11, recording frames 5.20–6.72 s). Talking ends only after TALK_HOLD_MS of quiet.
    speaking(on) { clearTimeout(S.offT);
      if (on) { S.talking = true; S.thinkAt = 0; paint(); }
      else S.offT = setTimeout(() => { S.talking = false; paint(); }, TALK_HOLD_MS); },
    thinking() { if (!S.talking) { S.thinkAt = performance.now(); } },
    setActive(on) { on = !!on; if (on === S.active) return; S.active = on; log('face-active', on ? 'on' : 'off');
      if (on) { S.lastFrameAt = performance.now(); S.activeAt = performance.now(); } paint(); },
    destroy() { clearInterval(dog); },
    get state() { return { live: S.live, badge: S.badge, size: S.size, frames: S.frames, missing: S.missing, active: S.active }; },
  };
}
