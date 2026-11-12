// shared/face-pip.js — Nova's small live FACE as picture-in-picture, TOP-LEFT INSIDE her room (NOVA-FINAL, 2026-11-12).
//
// Refael's approved spec (2026-11-12, item 3): "In-game: her singing/talking face is a small SoulX face as picture-in-
// picture, TOP-LEFT INSIDE her room; do not change her game layout. Applies to all games (freeze, wave, etc.)."
// So this module only ADDS a tile inside the pane that already shows her body clips. The pane keeps its size, the child's
// pane and the lights canvas never move. Every game page calls the same function — no page re-implements the tile.
//
// The tile is shared/face-panel.js (state badge, stall watchdog, red banner — no silent fallbacks) mounted in a PiP box.
//
//   const pip = mountFacePip(pane, { lang, log, onHealth })
//   pip.panel        → the createFacePanel() API (attach / waitLive / setBase / speaking / thinking / setActive / state)
//   pip.show(on)     → tile visible (game) or hidden (intro / ending: she talks WIDE on her body, no head on top of it)
//   pip.say(text)    → her line in a bubble under the tile (never over her body)
//
// Sizes [CLI-FILL — no spec gives them]: small = 24 % of the pane width, 32 % while she talks (lexi-ux-patterns Pattern 1
// "during dancing Nova is small in the corner; when she has something specific to say, she briefly grows"), capped at
// 30 % / 40 % of the pane height so a wide pane (phone landscape) never gets a huge head. Her body clips are centred
// portrait figures (1076x1924, measured): on a 16:9 screen her half is 0.89 x her clip height wide and her figure fills
// the middle 56 %, so a 24 % tile at the left edge sits on the wall of her room, not on her. QUESTION for the founder:
// the two sizes.
import { createFacePanel } from './face-panel.js';

const CSS = `
.nova-pip{position:absolute;left:12px;top:56px;z-index:6;width:min(24%,30vh);display:flex;flex-direction:column;gap:6px;
  transition:width .5s ease,opacity .35s ease;pointer-events:none}
.nova-pip[data-size=big]{width:min(32%,40vh)}
.nova-pip[data-show="0"]{opacity:0;visibility:hidden}
.nova-pip .pip-tile{position:relative;width:100%;aspect-ratio:1/1;border-radius:18px;overflow:hidden;background:#2a1a4a;
  outline:3px solid rgba(255,255,255,.18);box-shadow:0 6px 22px rgba(0,0,0,.35);transition:outline-color .25s,box-shadow .25s}
.nova-pip[data-state=talking] .pip-tile{outline-color:var(--gold,#ffd65a);box-shadow:0 0 26px rgba(255,214,90,.45)}
.nova-pip[data-state=freeze] .pip-tile{outline-color:#aee8ff}
.nova-pip video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#2a1a4a}
.nova-pip[data-live="0"] video{visibility:hidden}
.nova-pip .pip-badge{position:absolute;left:50%;bottom:6px;transform:translateX(-50%);z-index:3;white-space:nowrap;
  font:800 clamp(10px,1.1vw,14px)/1 'Baloo 2',Nunito,system-ui;padding:5px 10px;border-radius:999px;background:rgba(0,0,0,.72);color:#fff}
.nova-pip .pip-badge[data-state=talking]{background:#1f7a4a}
.nova-pip .pip-badge[data-state=freeze]{background:#aee8ff;color:#12324a}
.nova-pip .pip-badge[data-state=thinking]::after{content:' …'}
.nova-pip .pip-banner{position:absolute;inset:0;z-index:2;display:flex;align-items:center;justify-content:center;text-align:center;padding:8px;
  background:#3a0d0d;color:#ffb3b3;font:800 clamp(10px,1.2vw,14px)/1.25 Nunito,system-ui}
.nova-pip .pip-banner[hidden]{display:none}
.nova-pip .pip-say{width:max(100%,160px);background:rgba(255,255,255,.93);color:#2a1a4a;border-radius:12px;padding:5px 8px;
  font:800 clamp(11px,1.2vw,15px)/1.2 'Baloo 2',Nunito,system-ui;text-align:center;opacity:0;transform:translateY(6px);transition:opacity .25s,transform .25s}
.nova-pip .pip-say.on{opacity:1;transform:none}
`;

export function mountFacePip(pane, { lang = 'en', log = () => {}, onHealth = () => {} } = {}) {
  if (!document.getElementById('nova-pip-css')) {
    const st = document.createElement('style'); st.id = 'nova-pip-css'; st.textContent = CSS; document.head.appendChild(st);
  }
  const root = document.createElement('div'); root.className = 'nova-pip'; root.dataset.show = '0'; root.dataset.size = 'small';
  root.setAttribute('aria-label', 'Nova');
  root.innerHTML = '<div class="pip-tile"><video playsinline muted autoplay></video><div class="pip-banner" hidden></div><div class="pip-badge"></div></div><div class="pip-say"></div>';
  pane.appendChild(root);
  const video = root.querySelector('video'), badge = root.querySelector('.pip-badge'), banner = root.querySelector('.pip-banner'), sayEl = root.querySelector('.pip-say');
  if (lang === 'he') sayEl.dir = 'rtl';
  const panel = createFacePanel({ root, video, badge, banner, lang, log, onHealth });
  let sayT = null;
  return {
    panel, root, video,
    show(on) { root.dataset.show = on ? '1' : '0'; },
    say(text) { sayEl.textContent = text; sayEl.classList.add('on'); clearTimeout(sayT); sayT = setTimeout(() => sayEl.classList.remove('on'), Math.max(2600, 120 * text.length)); },
  };
}
