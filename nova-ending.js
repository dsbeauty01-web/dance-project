/*
 * nova-ending.js — Build 2: the one Smart Ending, shared by every game.
 *
 * The same component for all 5 commercial games + animal-freeze, personalized
 * per game. The arc (right after the last beat):
 *   1. HER MOMENT   — praise built from THIS session's real data, by name.
 *   2. FEEDBACK ASK — "how was it for YOU?" -> 😍 🙂 😕 (one tap, 8s skip),
 *                     then "Tell me one thing!" (mic already live, 5s skip).
 *   3. THE HOOK     — per-game "see you next time" that plants tomorrow.
 *   4. Exactly two buttons: 🔁 Play again  /  👋 Bye Nova.
 *
 * HARD RULES:
 *   - NEVER a zero, "0 pts", or an empty star row. Celebration data only.
 *     Raw numbers go to the session record (NovaRec.end), never the kid's screen.
 *   - Works in live voice / voice-only / silent — text always carries her lines.
 *   - Character law: warm, hyped big-sister; specific praise; never wrong/no/fail.
 *
 * Voice is injected by the host page via opts.speak(text) so each file keeps
 * its own pipeline (commercial = /v2/tts mp3; animal-freeze = SARAY live say).
 */
(function () {
  var HOOKS = {
    en: {
      joined: 'Tomorrow — the SPIN!',
      hello: 'Tomorrow we meet a SECRET friend!',
      wave: 'Tomorrow — the GIANT wave!',
      wavemagic: 'Tomorrow, magic with BOTH hands!',
      freeze: 'Tomorrow, freeze on ONE leg!',
      bounce: 'Tomorrow — the DOUBLE bounce!',
      _default: 'Tomorrow — a brand new move!',
    },
    he: {
      joined: 'מחר — הסיבוב!',
      hello: 'מחר נכיר חבר סודי!',
      wave: 'מחר — הגל הענק!',
      wavemagic: 'מחר, קסם בשתי ידיים!',
      freeze: 'מחר, קופאים על רגל אחת!',
      bounce: 'מחר — הקפיצה הכפולה!',
      _default: 'מחר — תנועה חדשה לגמרי!',
    },
  };

  var FACE_REACT = {
    en: { love: 'YESSS! Best dance ever!', ok: 'We were GOOD today!', meh: "I'll be even better next time, promise!" },
    he: { love: 'יסססס! הריקוד הכי טוב!', ok: 'היינו טובים היום!', meh: 'אני אהיה עוד יותר טובה מחר, מבטיחה!' },
  };

  var STR = {
    en: {
      ask: 'So… how was it for YOU?',
      tellOne: 'Tell me one thing!',
      again: '🔁 Play again',
      bye: '👋 Bye Nova',
      byeName: function (n) { return 'See you next time' + (n ? ', ' + n : '') + '!'; },
      presence: function (n) { return (n ? n + ' — you' : 'You') + ' SHOWED UP and danced with me. That\'s my favorite part!'; },
    },
    he: {
      ask: 'אז… איך היה לך?',
      tellOne: 'ספרו לי דבר אחד!',
      again: '🔁 עוד פעם',
      bye: '👋 ביי נובה',
      byeName: function (n) { return 'נתראה בפעם הבאה' + (n ? ', ' + n : '') + '!'; },
      presence: function (n) { return (n ? n + ' — ' : '') + 'באת ורקדת איתי, וזה החלק הכי אהוב עליי!'; },
    },
  };

  var FACES = [
    { key: 'love', emoji: '😍' },
    { key: 'ok', emoji: '🙂' },
    { key: 'meh', emoji: '😕' },
  ];

  function injectCSS() {
    if (document.getElementById('nova-ending-css')) return;
    var s = document.createElement('style');
    s.id = 'nova-ending-css';
    s.textContent = [
      '#nova-ending{position:fixed;inset:0;z-index:99999;display:flex;flex-direction:column;',
      'align-items:center;justify-content:center;gap:min(3vh,26px);padding:6vw;box-sizing:border-box;',
      'background:radial-gradient(120% 120% at 50% 0%,#3a1d6e 0%,#1a0b33 60%,#0b0618 100%);',
      'color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;text-align:center;',
      'opacity:0;transition:opacity .5s ease;overflow:hidden}',
      '#nova-ending.show{opacity:1}',
      '#nova-ending .ne-moment{font-size:clamp(22px,5.2vw,40px);font-weight:800;line-height:1.15;',
      'max-width:16em;text-shadow:0 2px 18px rgba(0,0,0,.4);opacity:0;transform:translateY(12px);',
      'transition:opacity .5s ease,transform .5s ease}',
      '#nova-ending .ne-moment.in{opacity:1;transform:none}',
      '#nova-ending .ne-ask{font-size:clamp(18px,4vw,28px);font-weight:700;opacity:0;transition:opacity .4s}',
      '#nova-ending .ne-ask.in{opacity:1}',
      '#nova-ending .ne-faces{display:flex;gap:min(4vw,22px);width:100%;max-width:560px;opacity:0;',
      'transform:translateY(10px);transition:opacity .4s,transform .4s}',
      '#nova-ending .ne-faces.in{opacity:1;transform:none}',
      '#nova-ending .ne-face{flex:1;aspect-ratio:1/1;border:none;border-radius:24px;',
      'background:rgba(255,255,255,.10);font-size:clamp(40px,11vw,72px);cursor:pointer;',
      'transition:transform .12s,background .2s;-webkit-tap-highlight-color:transparent}',
      '#nova-ending .ne-face:active{transform:scale(.9)}',
      '#nova-ending .ne-face.pick{background:rgba(255,255,255,.28);transform:scale(1.06)}',
      '#nova-ending .ne-hook{font-size:clamp(20px,4.6vw,34px);font-weight:800;color:#ffe27a;',
      'text-shadow:0 2px 16px rgba(255,180,0,.3);opacity:0;transform:scale(.9);',
      'transition:opacity .5s,transform .5s}',
      '#nova-ending .ne-hook.in{opacity:1;transform:none}',
      '#nova-ending .ne-btns{display:flex;gap:min(4vw,20px);opacity:0;transition:opacity .4s}',
      '#nova-ending .ne-btns.in{opacity:1}',
      '#nova-ending .ne-btn{border:none;border-radius:999px;padding:16px 26px;font-size:clamp(16px,4vw,22px);',
      'font-weight:800;cursor:pointer;-webkit-tap-highlight-color:transparent;transition:transform .12s}',
      '#nova-ending .ne-btn:active{transform:scale(.94)}',
      '#nova-ending .ne-again{background:#ffd23f;color:#2a1152}',
      '#nova-ending .ne-bye{background:rgba(255,255,255,.16);color:#fff}',
      '#nova-ending[dir="rtl"]{direction:rtl}',
    ].join('');
    document.head.appendChild(s);
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  function show(opts) {
    opts = opts || {};
    injectCSS();
    var lang = (opts.lang === 'he') ? 'he' : 'en';
    var s = STR[lang];
    var name = opts.name || null;
    var speak = (typeof opts.speak === 'function') ? opts.speak : function () {};
    var done = false;

    // 1) HER MOMENT — real data if given, else celebrate presence (never a number).
    var moment = (opts.bestMoment && String(opts.bestMoment).trim()) || s.presence(name);
    if (name && opts.bestMoment && moment.indexOf(name) === -1) moment = name + ' — ' + moment;

    var hook = opts.hookLine || (HOOKS[lang][opts.game] || HOOKS[lang]._default);
    var goodbye = s.byeName(name);

    // remove any prior instance
    var old = document.getElementById('nova-ending');
    if (old) old.remove();

    var root = el('div'); root.id = 'nova-ending';
    if (lang === 'he') root.setAttribute('dir', 'rtl');
    var mMoment = el('div', 'ne-moment', moment);
    var mAsk = el('div', 'ne-ask', s.ask);
    var mFaces = el('div', 'ne-faces');
    var mHook = el('div', 'ne-hook');
    var mBtns = el('div', 'ne-btns');
    root.appendChild(mMoment); root.appendChild(mAsk); root.appendChild(mFaces);
    root.appendChild(mHook); root.appendChild(mBtns);
    (opts.mount || document.body).appendChild(root);
    requestAnimationFrame(function () { root.classList.add('show'); });

    var picked = null, fbSent = { hook_shown: false };
    function sendFeedback(patch) {
      try { if (window.NovaRec) NovaRec.feedback(patch); } catch (e) {}
    }

    // buttons (exactly two, present from the start but revealed at the hook)
    var bAgain = el('button', 'ne-btn ne-again', s.again);
    var bBye = el('button', 'ne-btn ne-bye', s.bye);
    mBtns.appendChild(bAgain); mBtns.appendChild(bBye);
    bAgain.onclick = function () { finish('again'); };
    bBye.onclick = function () { finish('bye'); };

    function finish(which) {
      if (done) return; done = true;
      try { if (window.NovaRec) NovaRec.end(opts.stats || {}); } catch (e) {}
      root.classList.remove('show');
      setTimeout(function () {
        try { root.remove(); } catch (e) {}
        if (which === 'again' && typeof opts.onAgain === 'function') opts.onAgain();
        else if (typeof opts.onBye === 'function') opts.onBye();
      }, 450);
    }

    // ── sequence ───────────────────────────────────────────────
    // beat 1: her moment (spoken)
    setTimeout(function () { mMoment.classList.add('in'); speak(moment); }, 250);

    // beat 2: the feedback ask + faces (after she lands the praise)
    setTimeout(function () {
      mAsk.classList.add('in');
      speak(s.ask);
      FACES.forEach(function (f) {
        var b = el('button', 'ne-face', f.emoji);
        b.setAttribute('aria-label', f.key);
        b.onclick = function () { choose(f.key, b); };
        mFaces.appendChild(b);
      });
      mFaces.classList.add('in');
    }, 2600);

    // 8s no tap -> skip silently to the "tell me one thing" beat
    var skipFaces = setTimeout(function () { choose(null, null); }, 2600 + 8000);

    var chose = false;
    function choose(faceKey, btn) {
      if (chose) return; chose = true;
      clearTimeout(skipFaces);
      if (faceKey) {
        picked = faceKey;
        if (btn) btn.classList.add('pick');
        sendFeedback({ face: faceKey });
        // her warm reaction to the face
        var react = FACE_REACT[lang][faceKey];
        setTimeout(function () { speak(react); }, 250);
      }
      // "tell me one thing!" — mic is already live; next kid line -> feedback.said
      setTimeout(function () {
        mAsk.textContent = STR[lang].tellOne;
        speak(STR[lang].tellOne);
        try { if (window.NovaRec) NovaRec.markFeedbackWindow(5000); } catch (e) {}
      }, faceKey ? 1100 : 0);

      // 5s silence (or right away if skipped) -> the hook + goodbye
      setTimeout(revealHook, faceKey ? (1100 + 5000) : 400);
    }

    function revealHook() {
      mAsk.style.opacity = '0';
      mFaces.style.opacity = '0';
      mHook.textContent = hook;
      mHook.classList.add('in');
      fbSent.hook_shown = true;
      sendFeedback({ hook_shown: true, face: picked || null });
      // ending arc complete -> record /end now (idempotent; button also calls it),
      // so an abandoned-at-goodbye visit is still saved with its stats.
      try { if (window.NovaRec) NovaRec.end(opts.stats || {}); } catch (e) {}
      speak(hook);
      setTimeout(function () { speak(goodbye); mBtns.classList.add('in'); }, 1400);
    }

    return { finish: finish };
  }

  window.NovaEnding = { show: show };
})();
