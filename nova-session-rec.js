/*
 * nova-session-rec.js — Build 1.3: the memory of every visit.
 *
 * Fire-and-forget session recorder shared by nova-commercial.html and
 * animal-freeze.html. Talks ONLY to the worker (never Supabase directly).
 *
 * HARD LAW: absence of network = ZERO difference to the kid. Every call is
 * wrapped; nothing here throws, blocks the game loop, or shows an error.
 * If the worker is dead, the kid never knows.
 *
 * Usage:
 *   NovaRec.start({ lang:'en', device:'mobile', appVersion:'commercial-v1', game:'joined' });
 *   NovaRec.event('cue', {move:'wave'});         // structured gameplay event
 *   NovaRec.transcript('kid', 'look at me!');    // who = 'kid' | 'nova'
 *   NovaRec.tapLogBuffer(window.__LOG_BUFFER, {HEARD:'kid','NOVA-SAID':'nova'});
 *   NovaRec.setGame('mixed');
 *   NovaRec.markFeedbackWindow(6000);            // next kid line -> feedback.said
 *   NovaRec.feedback({face:'love'});
 *   NovaRec.end({score:420, hits:7});
 */
(function () {
  var BASE = (window.NOVA_REC_BASE || 'https://novapython.onrender.com') + '/api/v1';

  function uuid() {
    try { if (window.crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (e) {}
    // RFC4122-ish fallback
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0, v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  var sid = uuid();
  var T0 = (window.performance && performance.now) ? performance.now() : Date.now();
  var started = false, ended = false;
  var evBuf = [], txBuf = [];     // pending deltas since last flush
  var logRef = null, logMap = null, logIdx = 0;   // optional LOG_BUFFER tap
  var game = null;
  var fbWindowUntil = 0;          // ms timestamp: kid speech before this -> feedback.said
  var timer = null;

  function nowT() {
    var t = ((window.performance && performance.now) ? performance.now() : Date.now()) - T0;
    return Math.round(t) / 1000;   // seconds since rec start
  }

  // One best-effort POST. keepalive:true so it survives page unload. Never throws.
  function post(path, body) {
    try {
      fetch(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        keepalive: true,
        mode: 'cors',
        credentials: 'omit',
      }).catch(function () {});
    } catch (e) { /* swallow — a dead worker must not affect the kid */ }
  }

  function drainLog() {
    if (!logRef || !Array.isArray(logRef)) return;
    for (; logIdx < logRef.length; logIdx++) {
      var ln = logRef[logIdx];
      if (!ln) continue;
      // ship the raw log line as an event
      evBuf.push({ t: parseFloat(ln.t) || nowT(), type: ln.tag || 'log', msg: ln.msg || null, data: ln.data || null });
      // derive transcript from mapped tags
      if (logMap && logMap[ln.tag]) {
        var who = logMap[ln.tag];
        var text = (ln.data && (ln.data.text || ln.data.msg)) || ln.msg || '';
        if (text) pushTranscript(who, String(text));
      }
    }
  }

  function pushTranscript(who, text) {
    var entry = { t: nowT(), who: who, text: text };
    if (who === 'kid' && Date.now() < fbWindowUntil) {
      entry.feedback_said = true;
      // also surface the spoken feedback line into the feedback jsonb
      post('/session/feedback', { session_id: sid, feedback: { said: text } });
      fbWindowUntil = 0;
    }
    txBuf.push(entry);
  }

  function flush() {
    if (!started) return;
    drainLog();
    if (!evBuf.length && !txBuf.length) return;
    var events = evBuf, transcript = txBuf;
    evBuf = []; txBuf = [];
    post('/session/events', { session_id: sid, events: events, transcript: transcript });
  }

  var API = {
    get id() { return sid; },

    start: function (opts) {
      if (started) return sid;
      started = true;
      opts = opts || {};
      game = opts.game || null;
      post('/session/start', {
        session_id: sid,
        lang: opts.lang || null,
        device: opts.device || null,
        app_version: opts.appVersion || opts.app_version || null,
        game: game,
      });
      timer = setInterval(flush, 30000);
      // flush on tab hide / unload — the last chance to save the visit
      try {
        window.addEventListener('visibilitychange', function () {
          if (document.visibilityState === 'hidden') flush();
        });
        window.addEventListener('pagehide', flush);
        window.addEventListener('beforeunload', flush);
      } catch (e) {}
      return sid;
    },

    event: function (type, data) {
      if (!started) return;
      evBuf.push({ t: nowT(), type: type, data: data || null });
    },

    transcript: function (who, text) {
      if (!started || !text) return;
      pushTranscript(who === 'nova' ? 'nova' : 'kid', String(text));
    },

    // Tap an existing in-page log array (nova-commercial's window.__LOG_BUFFER).
    // tagMap maps a log tag -> 'kid'|'nova' to derive transcript lines.
    tapLogBuffer: function (arr, tagMap) {
      logRef = arr || null; logMap = tagMap || null; logIdx = 0;
    },

    setGame: function (g) { game = g; if (started) post('/session/events', { session_id: sid, events: [{ t: nowT(), type: 'set-game', data: { game: g } }], transcript: [] }); },

    // Open a window during the ending: the next kid line becomes feedback.said.
    markFeedbackWindow: function (ms) { fbWindowUntil = Date.now() + (ms || 6000); },

    feedback: function (obj) {
      if (!started || !obj) return;
      post('/session/feedback', { session_id: sid, feedback: obj });
    },

    flush: flush,

    end: function (stats) {
      if (!started || ended) return;
      ended = true;
      flush();
      if (timer) clearInterval(timer);
      post('/session/end', { session_id: sid, stats: stats || {}, game: game });
    },
  };

  window.NovaRec = API;
})();
