// shared/nova-live.js — Nova's live layer for EVERY game (NOVA-FINAL, 2026-11-12).
//
// Refael (2026-11-12, after watching the Freeze v4 run): "freeze is mostly good — make sure ALL of Nova is like this now".
// The setup beta/freeze4.html proved, as one engine every game page calls (CLAUDE.md law 3: no page re-implements it):
//   · INTRO / BETWEEN / ENDING — she talks WIDE: her live Ditto body in her room (Ditto Gold body, tools/pod/nova_face.py
//     FACE_RENDERER=dual, track `nova-wide-video`) covers the page's own Nova clip in the page's own Nova pane.
//   · GAME — the page's clip is back (its game layout is not touched) and her face is the small SoulX PiP top-left inside
//     her room (shared/face-pip.js). HOLD = hard mute.
//   · she talks less: in the game a line is cut to its first sentence and said only if ≤ 6 words (beta/tiers.js kids
//     maxWordsMidGame 6), one line per gap; intro/ending lines are said whole.
//   · voice routing goes through shared/nova-bridge.js routeVoice() only (phase machine law); the pod switches the face
//     on the same speak-gate (pod/rt_lk.py NOVA_FACE_DUAL).
//   · no silent fallbacks: no pod face within the wait = { ok:false, why } and a red line in her pane; the page decides.
//
//   const nova = createNovaLive({ pane, hide: [els shown only in the game], lang, log, intro: 'page:<game>' })
//   await nova.ready(waitMs) → { ok, dual, why[] }
//   nova.phase('intro'|'between'|'ending'|'game'|'hold')
//   nova.say(text)             → her live voice (staged line), caption in the PiP bubble in the game
//   await nova.waitLine(capMs) → resolves after her line has been said (her voice started, then 1.2 s quiet)
import { attachNova, routeVoice, note, onHerAudio, bridgeState } from './nova-bridge.js';
import { createFacePanel } from './face-panel.js';
import { mountFacePip } from './face-pip.js';

const CSS = `
.nova-live-wide{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;z-index:5;visibility:hidden;background:transparent}
[data-nova-stage=wide] > .nova-live-wide[data-live="1"]{visibility:visible}
[data-nova-stage=wide] > .nova-live-hide{visibility:hidden!important}
.nova-live-banner{position:absolute;left:8%;right:8%;top:40%;z-index:9;padding:12px;border-radius:14px;text-align:center;
  background:#3a0d0d;color:#ffb3b3;font:800 clamp(12px,1.5vw,17px)/1.25 Nunito,system-ui}
.nova-live-banner[hidden]{display:none}
`;
const MAX_GAME_WORDS = 6;                 // beta/tiers.js kids maxWordsMidGame; freeze4.html "she talks less"

export function shortLine(text, max = MAX_GAME_WORDS){
  const words = s => s.split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
  const first = (text.match(/^.*?[.!?](?=\s|$)/) || [text])[0].trim();
  if (words(first) <= max) return first;
  const clause = first.split(/\s+—\s+/)[0].trim();
  return clause !== first && words(clause) <= max ? clause.replace(/[,;:]$/, '') + '!' : null;
}

export function createNovaLive({ pane, hide = [], lang = 'en', log = () => {}, intro = 'page' } = {}){
  if (!document.getElementById('nova-live-css')){ const st = document.createElement('style'); st.id = 'nova-live-css'; st.textContent = CSS; document.head.appendChild(st); }
  if (getComputedStyle(pane).position === 'static') pane.style.position = 'relative';
  hide.forEach(el => el && el.classList.add('nova-live-hide'));
  const wv = document.createElement('video'); wv.className = 'nova-live-wide'; wv.playsInline = true; wv.muted = true; wv.autoplay = true; wv.dataset.live = '0';
  const wb = document.createElement('div'); wb.className = 'nova-live-banner'; wb.hidden = true;
  const wbadge = document.createElement('div'); wbadge.style.display = 'none';
  pane.append(wv, wb, wbadge);
  const pip = mountFacePip(pane, { lang, log });
  pip.root.style.zIndex = 12;
  const face = pip.panel;
  const wide = createFacePanel({ root: wv, video: wv, badge: wbadge, banner: wb, lang, log: (k, d) => log('wide-' + k, d), missingTag: 'Ditto',
    missingText: lang === 'he' ? 'הגוף החי של נובה (דיטו) לא משודר' : "Nova's live talking body is not streaming",
    onHealth: live => { wv.dataset.live = live ? '1' : '0'; } });
  wide.setActive(false); face.setActive(false);   // nothing to watch until ready() attaches (pod run #6: red 'not streaming' line from page load on Nova Says)
  const S = { dual: false, phase: '', mode: '', gapLine: false, herOn: false, startedAt: 0, endedAt: 0 };
  onHerAudio({ playing: () => { S.herOn = true; S.startedAt = performance.now(); face.speaking(true); log('her-voice', 'start'); },
               ended: () => { S.herOn = false; S.endedAt = performance.now(); face.speaking(false); log('her-voice', 'end'); } });

  function stage(st){
    if (!S.dual){ pip.show(true); pane.dataset.novaStage = 'game'; return; }
    pane.dataset.novaStage = st; pip.show(st === 'game'); face.setActive(st === 'game'); wide.setActive(st === 'wide'); log('stage', st);
  }
  function route(mode){ if (mode === S.mode) return; S.mode = mode; routeVoice(mode); log('voice', mode); stage(mode === 'engine' ? 'wide' : 'game'); }

  const api = {
    get dual(){ return S.dual; }, face, wide, pip,
    async ready(waitMs = 30000){
      log('attach', 'start'); pane.dataset.novaStage = 'wide';
      face.setActive(false); wide.setActive(false); wide.setActive(true);   // one stall window of grace while the tracks arrive (no red flash at attach)
      if (!(window.LivekitClient || window.LiveKitClient)) await new Promise(res => {      // same client line as beta/freeze4.html
        const sc = document.createElement('script'); sc.src = 'https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js';
        sc.onload = res; sc.onerror = () => { log('attach-error', 'livekit-client failed to load'); res(); }; document.head.appendChild(sc); });
      try { await attachNova({ intro, onFace: s => face.attach(s), onWide: s => { S.dual = S.dual || !!s; wide.attach(s); } }); }
      catch (e){ log('attach-error', String(e?.message || e)); }
      const t0 = performance.now(); let faceOk = false;
      while (performance.now() - t0 < waitMs){
        if (wide.state.live){ S.dual = true; faceOk = true; break; }
        if (face.state.live && !bridgeState().wide){ faceOk = true; break; }
        await new Promise(r => setTimeout(r, 200));
      }
      if (S.dual){ face.setActive(false); stage('wide'); } else { wide.setActive(false); stage('game'); }
      let st = bridgeState();
      while (!(st.ws && st.voice) && performance.now() - t0 < waitMs){ await new Promise(r => setTimeout(r, 200)); st = bridgeState(); }
      const why = [];
      if (!faceOk) why.push(lang === 'he' ? 'הפנים החיות של נובה לא משודרות' : "Nova's live face is not streaming");
      if (!st.ws || !st.voice) why.push(lang === 'he' ? 'הקול החי של נובה לא מחובר' : "Nova's live voice is not connected");
      log('attach', JSON.stringify({ face: faceOk, dual: S.dual, ...st }));
      if (why.length){ wb.textContent = '⛔ ' + why.join(' · '); wb.hidden = false; }
      return { ok: !why.length, dual: S.dual, why };
    },
    phase(p){
      S.phase = p; log('phase', p);
      if (p === 'intro' || p === 'between' || p === 'ending') route('engine');
      else if (p === 'hold'){ route('mute'); face.setBase('freeze'); }
      else { route('air'); S.gapLine = false; face.setBase('watching'); }
    },
    say(text){
      if (!text) return false;
      if (S.mode === 'mute'){ log('line-held-back', 'hold: ' + text); return false; }
      if (S.mode === 'air'){
        const s = shortLine(text); if (!s){ log('line-held-back', 'over ' + MAX_GAME_WORDS + ' words: ' + text); return false; }
        if (S.gapLine){ log('line-held-back', 'one per gap: ' + s); return false; }
        S.gapLine = true; text = s;
      }
      note(`say exactly: "${text}"`); face.thinking(); log('line', text); pip.say(text); return true;
    },
    gap(){ S.gapLine = false; },
    async waitLine(capMs = 20000){
      const t0 = performance.now();
      while (performance.now() - t0 < capMs){
        if (S.startedAt > t0 && !S.herOn && performance.now() - S.endedAt > 1200) return true;
        await new Promise(r => setTimeout(r, 100));
      }
      return false;
    },
  };
  window.novaLive = api;
  return api;
}
