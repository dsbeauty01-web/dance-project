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
  var ACTIVE = null;

  /* ── Known pods (history, so a dead id is never silently reused) ───────── */
  var KNOWN = {
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

  var API = {
    ACTIVE: ACTIVE,
    KNOWN: KNOWN,

    /* the live pod id, or null */
    id: function () { return ACTIVE; },

    /* true when a pod id is set AND not marked DEAD */
    isLive: function () {
      if (!ACTIVE) return false;
      var k = KNOWN[ACTIVE];
      return !(k && k.status === 'DEAD');
    },

    /* Each returns a URL for the live pod, or null so the caller falls back. */
    saray: function () { return API.isLive() ? 'https://' + host(ACTIVE, 8765) + '/' : null; },
    engine: function () { return API.isLive() ? 'https://' + host(ACTIVE, 8011) : null; },
    bridge: function () { return API.isLive() ? 'wss://' + host(ACTIVE, 8765) : null; },
    flv: function () { return API.isLive() ? 'https://' + host(ACTIVE, 8080) + '/live/dance_k.flv' : null; }
  };

  window.NOVA_PODS = API;

  try {
    console.log('[POD-REGISTRY] active=' + (ACTIVE || 'none — call sites use legacy fallback'));
  } catch (_) {}
})();
