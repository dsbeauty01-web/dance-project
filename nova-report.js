/* ============================================================================
 * nova-report.js — NOVA FULL AUTO-REPORT (shared diagnostics for every page)
 * Add `<script src="nova-report.js"></script>` to a game, then open with ?report
 * to run a live end-to-end health check of EVERY subsystem and show a copyable panel:
 *
 *   FRONTEND   — JS errors, CDN kits (tfjs / pose-detection / livekit), light engine, cues
 *   CAMERA+DET — secure context, mediaDevices, MoveNet model load + a real estimatePoses
 *   BACKEND    — Render /health, POST /v2/create-session (LiveKit creds)
 *   REALTIME   — LiveKit room connect + data channel
 *   RUNWAY     — avatar VIDEO track arrival (this is where the 400 shows up)
 *   VOICE      — Hume/EVI AUDIO track arrival
 *   API        — /v2/vision-observe, /filler reachability
 *
 * Safe: only runs when ?report is present. Uses its OWN session, then disconnects.
 * Pair with ?nonova so the game's own Nova connect doesn't compete:  ?report&nonova
 * ========================================================================== */
(function () {
  'use strict';
  if (!/[?&]report/.test(location.search)) return;

  var RENDER = (window.NOVA && window.NOVA.RENDER_URL) || (window.CFG && window.CFG.RENDER_URL) || 'https://novapython.onrender.com';
  var jsErrors = [];
  window.addEventListener('error', function (e) { jsErrors.push((e.message || 'error') + (e.filename ? ' @' + e.filename.split('/').pop() + ':' + e.lineno : '')); });
  window.addEventListener('unhandledrejection', function (e) { jsErrors.push('promise: ' + (e.reason && e.reason.message || e.reason)); });

  var rows = [];   // {group,name,status,detail}
  function row(group, name) { var r = { group: group, name: name, status: 'run', detail: '…' }; rows.push(r); render(); return r; }
  function set(r, status, detail) { r.status = status; r.detail = detail == null ? '' : String(detail); render(); }

  // ---------- UI ----------
  var panel, body, started = false;
  function ui() {
    panel = document.createElement('div');
    panel.id = 'nova-report';
    panel.innerHTML =
      '<style>' +
      '#nova-report{position:fixed;inset:0;z-index:99999;background:#0a0612f2;color:#e7ecf5;font:13px/1.5 ui-monospace,Menlo,Consolas,monospace;overflow:auto;padding:14px 14px 80px}' +
      '#nova-report h1{font:700 16px system-ui;margin:0 0 2px;color:#ffd27a}' +
      '#nova-report .sub{color:#9fb0cc;font:12px system-ui;margin-bottom:10px}' +
      '#nova-report .grp{margin:12px 0 4px;color:#9fd0ff;font:700 12px system-ui;letter-spacing:.5px;text-transform:uppercase;border-bottom:1px solid #243049;padding-bottom:3px}' +
      '#nova-report .r{display:flex;gap:8px;padding:3px 0;align-items:flex-start}' +
      '#nova-report .ic{flex:0 0 18px;text-align:center}' +
      '#nova-report .nm{flex:0 0 150px;color:#cfe}' +
      '#nova-report .dt{flex:1;color:#aeb9cd;word-break:break-word}' +
      '#nova-report .ok{color:#7CFFB0}#nova-report .bad{color:#ff7a6b}#nova-report .warn{color:#ffd27a}' +
      '#nova-report .bar{position:fixed;left:0;right:0;bottom:0;background:#0d1320;border-top:1px solid #243049;padding:10px 14px;display:flex;gap:10px;align-items:center}' +
      '#nova-report button{background:#1c2740;color:#fff;border:1px solid #34507e;border-radius:8px;padding:9px 14px;font:600 13px system-ui;cursor:pointer}' +
      '#nova-report button:active{transform:scale(.97)}' +
      '#nova-report .summ{font:700 13px system-ui}' +
      '</style>' +
      '<h1>NOVA · full auto-report</h1>' +
      '<div class="sub">backend: ' + RENDER + ' · page: ' + location.pathname.split('/').pop() + '</div>' +
      '<div id="nr-body"></div>' +
      '<div class="bar"><span class="summ" id="nr-summ">running…</span>' +
      '<button id="nr-copy">📋 Copy report</button>' +
      '<button id="nr-detect">▶ Test detection</button>' +
      '<button id="nr-close">✕ Close</button></div>';
    document.body.appendChild(panel);
    body = panel.querySelector('#nr-body');
    panel.querySelector('#nr-close').onclick = function () { panel.remove(); };
    panel.querySelector('#nr-copy').onclick = function () {
      var txt = report(); try { navigator.clipboard.writeText(txt); } catch (e) {}
      var b = panel.querySelector('#nr-copy'); b.textContent = '✓ Copied'; setTimeout(function () { b.textContent = '📋 Copy report'; }, 1500);
    };
    panel.querySelector('#nr-detect').onclick = function () { this.disabled = true; this.textContent = 'testing…'; testDetection(); };
  }
  var ICON = { run: ['⏳', ''], ok: ['✅', 'ok'], bad: ['❌', 'bad'], warn: ['⚠️', 'warn'] };
  function render() {
    if (!body) return;
    var groups = {}; rows.forEach(function (r) { (groups[r.group] = groups[r.group] || []).push(r); });
    var html = '';
    Object.keys(groups).forEach(function (g) {
      html += '<div class="grp">' + g + '</div>';
      groups[g].forEach(function (r) { var ic = ICON[r.status] || ICON.run;
        html += '<div class="r"><span class="ic ' + ic[1] + '">' + ic[0] + '</span><span class="nm">' + r.name + '</span><span class="dt ' + ic[1] + '">' + esc(r.detail) + '</span></div>'; });
    });
    body.innerHTML = html;
    var done = rows.filter(function (r) { return r.status !== 'run'; }).length;
    var bad = rows.filter(function (r) { return r.status === 'bad'; }).length;
    var ok = rows.filter(function (r) { return r.status === 'ok'; }).length;
    var s = panel.querySelector('#nr-summ'); if (s) s.innerHTML = ok + ' ok · ' + bad + ' fail · ' + done + '/' + rows.length + ' done' + (bad ? ' <span class="bad">— see ❌</span>' : (done === rows.length ? ' <span class="ok">— all good</span>' : ''));
  }
  function esc(s) { return String(s).replace(/[<>&]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]; }); }
  function report() { return 'NOVA AUTO-REPORT  ' + location.href + '\nbackend: ' + RENDER + '\n\n' +
    rows.map(function (r) { return (ICON[r.status] || ICON.run)[0] + ' [' + r.group + '] ' + r.name + ' — ' + r.detail; }).join('\n') +
    '\n\nJS errors: ' + (jsErrors.length ? jsErrors.join(' | ') : 'none'); }

  function withTimeout(p, ms) { return Promise.race([p, new Promise(function (_, rej) { setTimeout(function () { rej(new Error('timeout ' + ms + 'ms')); }, ms); })]); }

  // ---------- CHECKS ----------
  async function run() {
    if (started) return; started = true; ui();

    // FRONTEND
    setTimeout(function () { var r = row('frontend', 'JS errors'); jsErrors.length ? set(r, 'bad', jsErrors.slice(0, 4).join(' | ')) : set(r, 'ok', 'none'); }, 1200);
    (function () {
      var r = row('frontend', 'tfjs kit'); set(r, window.tf ? 'ok' : 'bad', window.tf ? ('v' + (tf.version && tf.version.tfjs || '?')) : 'window.tf missing');
      var r2 = row('frontend', 'pose-detection kit'); set(r2, window.poseDetection ? 'ok' : 'bad', window.poseDetection ? 'loaded (MoveNet)' : 'missing');
      var r3 = row('frontend', 'livekit-client kit'); set(r3, window.LivekitClient ? 'ok' : 'warn', window.LivekitClient ? 'loaded' : 'not on this page');
      var r4 = row('frontend', 'magic-light engine'); set(r4, window.NovaLight ? 'ok' : 'bad', window.NovaLight ? ('NovaLight + ' + Object.keys(window.NovaLight.PRESETS || {}).length + ' presets') : 'nova-light.js missing');
      var r5 = row('frontend', 'cues table');
      var n = (window.CUES && window.CUES.length) || (window.TIMELINE_HELLO_RAW && window.TIMELINE_HELLO_RAW.length) || 0;
      set(r5, n ? 'ok' : 'warn', n ? (n + ' cues loaded') : 'no CUES global exposed on this page');
    })();

    // CAMERA
    (function () {
      var r = row('camera+detection', 'secure context'); set(r, window.isSecureContext ? 'ok' : 'bad', window.isSecureContext ? 'https/localhost ✓ (camera allowed)' : 'NOT secure — camera blocked');
      var r2 = row('camera+detection', 'getUserMedia API'); set(r2, (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ? 'ok' : 'bad', (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ? 'available' : 'unavailable');
      row('camera+detection', 'MoveNet model').detail = 'tap ▶ Test detection (loads the model)';
    })();

    // BACKEND + REALTIME + RUNWAY + VOICE (the live chain)
    await backendChain();
    render();
  }

  async function backendChain() {
    // health
    var rh = row('backend', 'Render /health');
    try { var t0 = performance.now(); var res = await withTimeout(fetch(RENDER + '/health', { cache: 'no-store' }), 60000);
      set(rh, res.ok ? 'ok' : 'bad', 'HTTP ' + res.status + ' · ' + Math.round(performance.now() - t0) + 'ms' + (res.status === 200 ? ' (worker awake)' : ''));
    } catch (e) { set(rh, 'bad', 'unreachable: ' + e.message); }

    // create-session
    var rs = row('backend', 'POST /v2/create-session'); var creds = null;
    try { var t1 = performance.now(); var r = await withTimeout(fetch(RENDER + '/v2/create-session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kidId: 'report-' + Date.now() }) }), 70000);
      if (!r.ok) { set(rs, 'bad', 'HTTP ' + r.status + ' — ' + (await r.text().catch(function(){return '';})).slice(0, 80)); }
      else { creds = await r.json(); var okc = creds && creds.serverUrl && creds.token;
        set(rs, okc ? 'ok' : 'bad', okc ? ('creds ok · ' + Math.round(performance.now() - t1) + 'ms · room ' + (creds.roomName || creds.sessionId || '?')) : 'missing serverUrl/token'); }
    } catch (e) { set(rs, 'bad', 'failed: ' + e.message); }

    // LiveKit connect + track arrivals (Runway video + Hume audio)
    var rc = row('realtime', 'LiveKit connect');
    var rv = row('runway', 'avatar VIDEO track');
    var ra = row('voice', 'Hume/EVI AUDIO track');
    if (!creds || !window.LivekitClient) {
      set(rc, 'bad', creds ? 'livekit-client not loaded on this page' : 'no creds (create-session failed)');
      set(rv, 'bad', 'skipped — no connection'); set(ra, 'bad', 'skipped — no connection'); return;
    }
    try {
      var room = new LivekitClient.Room({ adaptiveStream: false, dynacast: false });
      var gotV = false, gotA = false;
      room.on(LivekitClient.RoomEvent.TrackSubscribed, function (t) {
        if (t.kind === 'video' && !gotV) { gotV = true; set(rv, 'ok', 'Runway avatar video arrived ✓'); }
        if (t.kind === 'audio' && !gotA) { gotA = true; set(ra, 'ok', 'Hume/EVI voice audio arrived ✓'); }
      });
      var tc = performance.now();
      await withTimeout(room.connect(creds.serverUrl, creds.token), 25000);
      set(rc, 'ok', 'connected · ' + Math.round(performance.now() - tc) + 'ms · room ' + room.name);
      try { await room.localParticipant.setMicrophoneEnabled(true); } catch (e) {}
      // wait up to 90s for Nova's agent to publish (cold start + Runway + EVI)
      var wdl = performance.now() + 90000;
      while (performance.now() < wdl && !(gotV && gotA)) { await new Promise(function (r) { setTimeout(r, 1000); }); }
      if (!gotV) set(rv, 'bad', 'no video in 90s — Runway avatar failed (check agent.py runway_avatar.start / Runway API)');
      if (!gotA) set(ra, 'bad', 'no audio in 90s — Hume/EVI voice not publishing (worker agent may have crashed)');
      try { room.disconnect(); } catch (e) {}
    } catch (e) { set(rc, 'bad', 'connect failed: ' + e.message); set(rv, 'bad', 'skipped'); set(ra, 'bad', 'skipped'); }

    // extra endpoints
    pingEndpoint('api', 'GET /v2/vision-observe', RENDER + '/v2/vision-observe', 'POST', { sessionId: 'report', text: 'ping' });
    pingEndpoint('api', 'GET /filler', RENDER + '/filler?t=' + Date.now(), 'GET');
  }

  async function pingEndpoint(group, name, url, method, bodyObj) {
    var r = row(group, name);
    try { var opt = { method: method, cache: 'no-store' };
      if (method === 'POST') { opt.headers = { 'Content-Type': 'application/json' }; opt.body = JSON.stringify(bodyObj || {}); }
      var res = await withTimeout(fetch(url, opt), 30000);
      set(res.status < 500 ? r : r, res.status < 500 ? 'ok' : 'warn', 'HTTP ' + res.status + (res.status === 404 ? ' (endpoint not on worker)' : ''));
    } catch (e) { set(r, 'warn', 'unreachable: ' + e.message); }
  }

  async function testDetection() {
    var r = row('camera+detection', 'MoveNet model');
    try {
      if (!window.tf || !window.poseDetection) { set(r, 'bad', 'kits not loaded'); return; }
      var t0 = performance.now();
      try { await tf.setBackend('webgl'); } catch (e) { try { await tf.setBackend('cpu'); } catch (_) {} }
      await tf.ready();
      var det = await withTimeout(poseDetection.createDetector(poseDetection.SupportedModels.MoveNet, { modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING }), 30000);
      var c = document.createElement('canvas'); c.width = 256; c.height = 256;
      var poses = await det.estimatePoses(c, { flipHorizontal: false });
      set(r, 'ok', 'loaded + ran on ' + tf.getBackend() + ' · ' + Math.round(performance.now() - t0) + 'ms (0 poses on blank = correct)');
      var rb = panel.querySelector('#nr-detect'); if (rb) rb.textContent = '✓ detection ok';
    } catch (e) { set(r, 'bad', 'failed: ' + e.message); }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(run, 400); });
  else setTimeout(run, 400);
})();
