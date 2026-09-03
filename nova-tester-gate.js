/* ═══ NOVA TESTER GATE (2026-09-03) ════════════════════════════════════════════
   Two friendly, self-contained gates for the tester package. Loaded as ONE
   <script> after pod-registry.js so the 8000-line flagship page is untouched.

   1) WAKING STATE — while no pod answers /health, show "Nova's waking up"
      instead of a broken page. Hooks pod-registry (window.NOVA_PODS). Auto-retries.
   2) CONSENT GATE — the camera can NEVER open before a parent consents, because
      we wrap navigator.mediaDevices.getUserMedia: the first call awaits the
      consent screen. Works for every camera code-path with zero edits to them.

   Bilingual (reads window.NOVA_LANG: 'he' | 'en'). No external assets. Inert and
   safe: if pod-registry is missing, the waking splash times out and hands over.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  var HE = (window.NOVA_LANG === 'he');
  var T = {
    wake:   HE ? 'נובה מתעוררת…' : "Nova's waking up…",
    wakeSub:HE ? 'עוד רגע קטן, כבר מתחילים לרקוד' : 'One little moment — the dancing is about to start',
    cTitle: HE ? 'רגע לפני שמתחילים' : 'One moment before we start',
    cBody:  HE
      ? 'נובה רואה בשידור חי דרך המצלמה כדי לראות את הריקוד. שום דבר לא מוקלט ולא נשמר — רק תוצאת המשחק והשם הפרטי של הילד/ה.'
      : 'Nova watches live through the camera to see the dance. Nothing is recorded or stored — only the game score and your child’s first name.',
    cCheck: HE ? 'אני ההורה ומאשר/ת' : "I’m the parent and I agree",
    cBtn:   HE ? 'הקישו כדי להתחיל' : 'Tap to start'
  };

  /* ── consent promise: getUserMedia awaits this ───────────────────────────── */
  var consentResolve, consentGranted = false;
  var consentP = new Promise(function (res) { consentResolve = res; });

  /* wrap getUserMedia BEFORE any page code can call it */
  try {
    var md = navigator.mediaDevices;
    if (md && md.getUserMedia) {
      var orig = md.getUserMedia.bind(md);
      md.getUserMedia = function (constraints) {
        if (consentGranted) return orig(constraints);
        try { showConsent(); } catch (_) {}
        return consentP.then(function () { return orig(constraints); });
      };
    }
  } catch (_) {}

  /* ── styles ───────────────────────────────────────────────────────────────── */
  function css() {
    if (document.getElementById('ntg-css')) return;
    var s = document.createElement('style'); s.id = 'ntg-css';
    s.textContent = [
      '.ntg{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;',
      'align-items:center;justify-content:center;gap:18px;padding:7vw;box-sizing:border-box;text-align:center;',
      'font-family:Fredoka,"Baloo 2","Varela Round",system-ui,sans-serif;color:#fff;',
      'background:radial-gradient(130% 130% at 50% 0%,#5b3aa6 0%,#2a1560 55%,#140a33 100%)}',
      '.ntg[hidden]{display:none}',
      '.ntg h2{font-size:clamp(26px,6vw,44px);margin:0;font-weight:800;text-wrap:balance}',
      '.ntg p{font-size:clamp(16px,3.4vw,22px);margin:0;max-width:22em;line-height:1.5;color:#e7ddff}',
      '.ntg-dots{display:flex;gap:12px;margin-top:6px}',
      '.ntg-dots i{width:14px;height:14px;border-radius:50%;background:#c9b6ff;display:block;',
      'animation:ntgb 1.1s ease-in-out infinite}',
      '.ntg-dots i:nth-child(2){animation-delay:.18s}.ntg-dots i:nth-child(3){animation-delay:.36s}',
      '@keyframes ntgb{0%,80%,100%{transform:translateY(0);opacity:.5}40%{transform:translateY(-14px);opacity:1}}',
      '.ntg-card{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);',
      'border-radius:22px;padding:clamp(22px,5vw,38px);max-width:30em;display:flex;flex-direction:column;gap:18px}',
      '.ntg-check{display:flex;align-items:center;gap:12px;justify-content:center;font-size:clamp(15px,3.2vw,19px);cursor:pointer}',
      '.ntg-check input{width:26px;height:26px;accent-color:#ffd23f;flex:none}',
      '.ntg-btn{border:none;border-radius:999px;padding:16px 30px;font:800 clamp(18px,4vw,24px)/1 inherit;',
      'background:#ffd23f;color:#2a1152;cursor:pointer;transition:transform .12s,opacity .2s}',
      '.ntg-btn:disabled{opacity:.4;cursor:not-allowed}.ntg-btn:not(:disabled):active{transform:scale(.95)}',
      '.ntg-lock{font-size:13px;color:#c9b6ff;opacity:.85}'
    ].join('');
    (document.head || document.documentElement).appendChild(s);
  }

  /* ── waking overlay ──────────────────────────────────────────────────────── */
  var wakeEl, retryTimer;
  function showWaking() {
    css();
    if (wakeEl) { wakeEl.hidden = false; return; }
    wakeEl = document.createElement('div'); wakeEl.className = 'ntg'; wakeEl.id = 'ntg-wake';
    if (HE) wakeEl.dir = 'rtl';
    wakeEl.innerHTML =
      '<div class="ntg-dots"><i></i><i></i><i></i></div>' +
      '<h2></h2><p></p>';
    wakeEl.querySelector('h2').textContent = T.wake;
    wakeEl.querySelector('p').textContent = T.wakeSub;
    document.body.appendChild(wakeEl);
  }
  function hideWaking() { if (wakeEl) wakeEl.hidden = true; if (retryTimer) clearInterval(retryTimer); }

  /* ── consent overlay ─────────────────────────────────────────────────────── */
  var consentEl;
  function showConsent() {
    css();
    if (consentGranted) return;
    if (consentEl) { consentEl.hidden = false; return; }
    consentEl = document.createElement('div'); consentEl.className = 'ntg'; consentEl.id = 'ntg-consent';
    if (HE) consentEl.dir = 'rtl';
    consentEl.innerHTML =
      '<div class="ntg-card">' +
      '<h2></h2><p></p>' +
      '<label class="ntg-check"><input type="checkbox" id="ntg-cb"><span></span></label>' +
      '<button class="ntg-btn" id="ntg-go" disabled></button>' +
      '<div class="ntg-lock">🔒 <span id="ntg-lk"></span></div>' +
      '</div>';
    consentEl.querySelector('h2').textContent = T.cTitle;
    consentEl.querySelector('p').textContent = T.cBody;
    consentEl.querySelector('.ntg-check span').textContent = T.cCheck;
    var btn = consentEl.querySelector('#ntg-go'); btn.textContent = T.cBtn;
    consentEl.querySelector('#ntg-lk').textContent = HE ? 'ללא הקלטה · ללא אחסון' : 'no recording · no storage';
    var cb = consentEl.querySelector('#ntg-cb');
    cb.addEventListener('change', function () { btn.disabled = !cb.checked; });
    btn.addEventListener('click', function () {
      if (!cb.checked) return;
      consentGranted = true;
      consentEl.hidden = true;
      try { consentResolve(); } catch (_) {}
    });
    document.body.appendChild(consentEl);
  }

  /* ── boot: waking until a pod is live ────────────────────────────────────── */
  function boot() {
    showWaking();
    var pods = window.NOVA_PODS;
    if (!pods || typeof pods.detected !== 'function') {
      // registry absent — don't trap the tester; hand over after a short splash
      setTimeout(hideWaking, 2500);
      return;
    }
    pods.detected(function (liveId) {
      if (liveId) { hideWaking(); return; }
      // no pod yet: keep the friendly splash and re-check by reloading every 25s
      retryTimer = setInterval(function () {
        if (window.NOVA_PODS && window.NOVA_PODS.isLive && window.NOVA_PODS.isLive()) {
          hideWaking(); return;
        }
        location.reload();
      }, 25000);
    });
    // a pod that goes live after load still fires this event
    window.addEventListener('nova-pod-live', hideWaking);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  // expose for the screenshot harness / tests
  window.NOVA_GATE = { showConsent: showConsent, showWaking: showWaking, hideWaking: hideWaking };
})();
