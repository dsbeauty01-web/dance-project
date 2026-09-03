/* ═══ NOVA POD REGISTRY (2026-08-02) ════════════════════════════════════════════
   ONE source of truth for RunPod hostnames.

   WHY: pod ids were hardcoded in four files (nova-commercial.html,
   animal-freeze.html, nova-app.html, nova-joined.html). Every pod swap meant
   hunting literals across the codebase, and stale ids kept the app pointing at
   dead pods ("she didn't reply" / the dead-FLV-pod bug noted inline in
   nova-commercial.html). A pod is ephemeral infrastructure; it does not belong
   baked into a flagship HTML file.

   HOW TO POINT THE APP AT A LIVE POD — set ACTIVE below to the pod id, commit.
   That is the whole change. Nothing else in the codebase needs editing.

   Resolution order (unchanged for callers, override always wins):
     1. URL query param   (?saray= / ?engine= / ?bridge= / ?flv=)
     2. ACTIVE in this file
     3. the caller's own legacy literal fallback

   Because of (3) this file can never break a page: if it fails to load, or
   ACTIVE is null, every call site falls back to exactly the behaviour it had
   before the registry existed.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── SET THIS ─────────────────────────────────────────────────────────────
     The pod id of the CURRENTLY RUNNING pod. null = no known-live pod, so
     call sites use their legacy fallback. */
  var ACTIVE = 'ahpn3b9rl1tqrl';

  /* ── LIVE-POD AUTO-DETECTION (2026-08-29, founder: "yes build it") ────────
     THE PROBLEM THIS KILLS: pods die (suicide timers, founder closes them) and
     ACTIVE keeps pointing at the corpse until someone repoints it in a PR — so
     the PUBLIC page regularly serves a dead pod ("voice napping" for everyone).
     THE FIX: at load, this file probes /health on ACTIVE + the recent-pod list
     + the pod this browser last saw alive (localStorage). First healthy pod
     WINS and silently replaces ACTIVE for every later API call (call sites use
     the API functions lazily, so they inherit the live id with zero changes).
     If NOTHING answers, behaviour is exactly as before (ACTIVE + legacy
     fallbacks) — this feature can only ever improve the outcome.
     NOTE: /health must send CORS (Access-Control-Allow-Origin:*) for a probe
     to read it; pods running an older rt_lk just look dead to the probe, which
     is no worse than today. Sessions should append fresh pod ids here. */
  var CANDIDATES = [
    ACTIVE,
    'ahpn3b9rl1tqrl',   // nova-tester — persistent tester pod (2026-09-03), locked URL target
    'gtdmu76ocpjjmu',   // nova-certify-2      (2026-08-30, MACHINE-CERTIFY)
    'qfe21r86dqilms',   // nova-freeze-fresh3  (2026-08-29)
    'fh9v6w92vlcdhl',   // nova-freeze-final2  (2026-08-29)
    'q0xetjpgafc926',   // nova-freeze-onetap  (2026-08-28)
    'ze6l99yiw0t9gg',   // nova-freeze-ready2  (2026-08-28)
    'juy2dwly735jok'    // nova-freeze-final   (2026-08-28)
  ];
  var LIVE = null;            // set by detection; wins over ACTIVE when present
  var DETECTION_DONE = false; // true once every probe settled

  /* ── Known pods (history, so a dead id is never silently reused) ───────── */
  var KNOWN = {
    '1l8zzrqk2c3fs6': {
      role: 'LIVE — saray/brain 8765, engine 8010, bridge -> LiveKit room nova-live',
      note: 'SECURE RTX 4090, EU-RO-1, volume 1ditrne6cb, name nova-live-2026-08-17. Created ' +
            '2026-08-17 to smoke-test the MuseTalk game fixes (up-groove nova-pick=upgroove; ' +
            'wave nova-pick=wave + nova_idle fallback since wave is unbakeable). Booted from ' +
            '/workspace/boot.sh in tmux(novaboot); VOICE_BACKEND=hume.',
      lastSeenLive: '2026-08-17',
      status: 'BOOTING — MuseTalk cold load per LAW-PODS-9'
    },
    '2bhlam3hm43qnz': {
      role: 'BAKE POD (not a live target) — Maya gesture set, volume 1ditrne6cb',
      note: 'SECURE 4090 EU-RO-1, name nova-bake-maya. Created 2026-08-04 to bake the 6 Maya ' +
            'clips + repair the dead nova_hype. NOTE: POD LAW prefers a COMMUNITY pod for bakes, ' +
            'but EU-RO-1 had zero Community capacity across 7 GPU types, and the volume is pinned ' +
            'to that datacenter. A dedicated pod was used so the live pod was never touched. ' +
            'Runs /workspace/bake-batch.sh in tmux(bake) and SELF-STOPS when done.',
      lastSeenLive: '2026-08-04',
      status: 'BAKING — never point the app here; results land on the shared volume'
    },
    '7v5jwbbewo1gf5': {
      role: 'LIVE — saray/brain 8765, engine 8010, bridge -> LiveKit room nova-live',
      note: 'SECURE RTX 4090, EU-RO-1, volume 1ditrne6cb, name nova-live-fixtest. ' +
            'Created 2026-08-03 04:2x UTC to test the FREEZE FIX PACK. Booted from the ' +
            'volume copy /workspace/boot.sh (which carries its own env exports).',
      lastSeenLive: '2026-08-03',
      status: 'BOOTING — created + boot.sh launched in tmux(novaboot); cold load per LAW-PODS-9'
    },
    'ubu8krpcf0k62v': {
      role: 'saray/brain 8765, engine 8010, bridge -> LiveKit room nova-live',
      note: 'SECURE RTX 4090, EU-RO-1, volume 1ditrne6cb. Booted 2026-08-02 11:18 UTC. ' +
            'STOPPED by founder 2026-08-02 14:21 UTC; resume now fails — the host has no ' +
            'free GPUs, so this id cannot be revived. Kept for history.',
      lastSeenLive: '2026-08-02',
      status: 'EXITED — was verified live (nova-video 1076x1924 in room nova-live, voice probe ' +
              'answered OAI session.created + nova_text); cannot restart, host GPUs taken'
    },
    'b9b6v8cljo578h': {
      role: 'saray / musetalk live avatar (8765)',
      note: 'nova-engine-2, RTX PRO 4500 on volume 1ditrne6cb, nova_idle CALM intro + gesture bank',
      lastSeenLive: '2026-07-27',
      status: 'UNVERIFIED — was live at the 2026-07-27 release; not probed since'
    },
    'k9o3iexgqif9il': {
      role: 'legacy flv 8080 / bridge 8765 / engine 8011',
      note: 'nova-home pod swap 2026-07-20; the inline comment in nova-commercial.html already calls this "the dead FLV pod"',
      lastSeenLive: '2026-07-20',
      status: 'DEAD'
    }
  };

  function host(id, port) { return id + '-' + port + '.proxy.runpod.net'; }

  /* the id every API call should use: a detected-live pod beats the static ACTIVE */
  function cur() { return LIVE || ACTIVE; }

  var API = {
    ACTIVE: ACTIVE,
    KNOWN: KNOWN,

    /* the live pod id, or null */
    id: function () { return cur(); },

    /* true when a pod id is set AND not marked DEAD. After detection completes
       with a confirmed-live pod, always true; detection never flips this false
       (a probe miss must not break legacy behaviour). */
    isLive: function () {
      if (LIVE) return true;
      if (!ACTIVE) return false;
      var k = KNOWN[ACTIVE];
      return !(k && k.status === 'DEAD');
    },

    /* Each returns a URL for the live pod, or null so the caller falls back. */
    saray: function () { return API.isLive() ? 'https://' + host(cur(), 8765) + '/' : null; },
    /* Engine port is 8010 on the current stack (boot.sh: app.py --listenport 8010,
       ENGINE_URL=http://127.0.0.1:8010). The older k9o3iexgqif9il generation used
       8011; on pod ubu8krpcf0k62v port 8011 answers 502. Verified 2026-08-02. */
    engine: function () { return API.isLive() ? 'https://' + host(cur(), 8010) : null; },
    bridge: function () { return API.isLive() ? 'wss://' + host(cur(), 8765) : null; },
    flv: function () { return API.isLive() ? 'https://' + host(cur(), 8080) + '/live/dance_k.flv' : null; },

    /* detection status for pages that want to wait/react:
       NOVA_PODS.detected(cb) — cb(idOrNull) immediately if done, else on completion */
    _cbs: [],
    detected: function (cb) {
      if (DETECTION_DONE) { try { cb(LIVE); } catch (_) {} }
      else API._cbs.push(cb);
    }
  };

  /* ── the detection sweep ── */
  function probe(id, timeoutMs, cb) {
    var done = false;
    var ctl = ('AbortController' in window) ? new AbortController() : null;
    var t = setTimeout(function () { if (ctl) try { ctl.abort(); } catch (_) {} }, timeoutMs || 5000);
    fetch('https://' + host(id, 8765) + '/health',
          { cache: 'no-store', signal: ctl ? ctl.signal : undefined })
      .then(function (r) { return r.json(); })
      .then(function (j) { clearTimeout(t); if (!done) { done = true; cb(!!(j && j.ok)); } })
      .catch(function () { clearTimeout(t); if (!done) { done = true; cb(false); } });
  }

  function detect() {
    var ids = [];
    try { var mem = localStorage.getItem('nova-live-pod'); if (mem) ids.push(mem); } catch (_) {}
    for (var i = 0; i < CANDIDATES.length; i++) {
      if (CANDIDATES[i] && ids.indexOf(CANDIDATES[i]) < 0) ids.push(CANDIDATES[i]);
    }
    if (!ids.length) { DETECTION_DONE = true; return; }
    var pending = ids.length;
    ids.forEach(function (id) {
      probe(id, 5000, function (ok) {
        pending--;
        if (ok && !LIVE) {
          LIVE = id;
          API.ACTIVE = id;
          try { localStorage.setItem('nova-live-pod', id); } catch (_) {}
          try { console.log('[POD-REGISTRY] LIVE pod detected: ' + id +
                            (id !== ACTIVE ? ' (auto-corrected from stale ACTIVE=' + ACTIVE + ')' : '')); } catch (_) {}
          try { window.dispatchEvent(new CustomEvent('nova-pod-live', { detail: { id: id } })); } catch (_) {}
        }
        if (pending <= 0) {
          DETECTION_DONE = true;
          if (!LIVE) try { console.warn('[POD-REGISTRY] no live pod answered — legacy ACTIVE behaviour'); } catch (_) {}
          var cbs = API._cbs.splice(0);
          for (var c = 0; c < cbs.length; c++) { try { cbs[c](LIVE); } catch (_) {} }
        }
      });
    });
  }
  try { detect(); } catch (_) { DETECTION_DONE = true; }

  window.NOVA_PODS = API;

  try {
    console.log('[POD-REGISTRY] active=' + (ACTIVE || 'none — call sites use legacy fallback') +
                ' — probing ' + CANDIDATES.length + ' candidates for a live pod…');
  } catch (_) {}
})();
