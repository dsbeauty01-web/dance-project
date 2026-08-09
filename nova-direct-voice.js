/* LAW-DIRECT-VOICE (founder decision 2026-08-09) — browser ↔ OpenAI Realtime DIRECT.
   The worker never touches audio: it only mints an ephemeral key (/v2/realtime-key).
   The PROVIDER owns every turn, barge-in and echo decision — the local VAD referee
   that beheaded her for 3 months does not exist on this path.
   Activate: ?voiceonly&direct=1 on nova-commercial.html. The old LiveKit path is
   untouched and remains the fallback (drop &direct=1).

   Director-lite runs HERE (the browser already owns every game fact):
   - system items carry facts (light, picks, hits) — same texts as the worker's
   - one response.create per world beat (greet, light, picker, loading, cheer)
   - consent gate: her words can open the picker ONLY if the kid spoke <10s ago
   - transition hard-cut: response.cancel at pick, then the loading beat
   - cheers rate-limited to one per 8s                                            */
(function () {
  'use strict';
  const Q = new URLSearchParams(location.search);
  if (!/[?&]voiceonly/.test(location.search) || Q.get('direct') !== '1') return;

  const API = (window.NOVA_CONFIG && window.NOVA_CONFIG.renderUrl) || 'https://novapython.onrender.com';
  const LOG = (t, m) => { try { console.log('[DIRECT-' + t + ']', m); (window.tapLog || window.LOG || function(){})(t, m); } catch (_) {} };

  const DV = {
    pc: null, dc: null, audioEl: null, ready: false,
    greeted: false, lightDone: false, pickerOpened: false,
    lastKidSpokeAt: 0, lastCheerAt: 0, lastHerLineAt: 0,

    async start() {
      if (this.pc) return;
      LOG('BOOT', 'direct voice starting — provider-owned turns');
      const r = await fetch(API + '/v2/realtime-key', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene: 'intro', voice: Q.get('voice') || undefined }) });
      const js = await r.json();
      if (!js.client_secret) { LOG('ERR', 'no ephemeral key'); return; }

      const pc = new RTCPeerConnection();
      this.pc = pc;
      const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      mic.getTracks().forEach(t => pc.addTrack(t, mic));
      pc.ontrack = (e) => {
        const a = this.audioEl = this.audioEl || document.createElement('audio');
        a.autoplay = true; a.srcObject = e.streams[0]; document.body.appendChild(a);
        const tryPlay = () => a.play().catch(() => {});
        tryPlay(); ['pointerdown', 'keydown'].forEach(ev => document.addEventListener(ev, tryPlay, { passive: true }));
        LOG('AUDIO', 'her voice track attached (direct)');
      };
      const dc = this.dc = pc.createDataChannel('oai-events');
      dc.onmessage = (e) => { try { this.onEvent(JSON.parse(e.data)); } catch (_) {} };
      dc.onopen = () => { LOG('BOOT', 'events channel open'); this.greet(); };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const sdp = await fetch('https://api.openai.com/v1/realtime?model=' + encodeURIComponent(js.model), {
        method: 'POST', body: offer.sdp,
        headers: { 'Authorization': 'Bearer ' + js.client_secret, 'Content-Type': 'application/sdp' } });
      await pc.setRemoteDescription({ type: 'answer', sdp: await sdp.text() });
      this.ready = true;
      LOG('BOOT', 'WebRTC connected to OpenAI Realtime — no middleman');
      setTimeout(() => this.lightBeat(), 22000);          // world event, same 20s law
    },

    send(obj) { try { this.dc && this.dc.readyState === 'open' && this.dc.send(JSON.stringify(obj)); } catch (_) {} },

    sysFact(text) { this.send({ type: 'conversation.item.create', item: {
      type: 'message', role: 'system', content: [{ type: 'input_text', text: text }] } }); },

    beat(instructions) { this.send({ type: 'response.create', response: { instructions: instructions } }); },

    greet() {
      if (this.greeted) return; this.greeted = true;
      this.beat("Greet the kid in ONE short excited line and say exactly: " +
                "Hi! I'm Nova, your magical AI dance teacher! What's your name? Then STOP and wait.");
    },

    lightBeat() {
      if (this.lightDone || this.pickerOpened) return; this.lightDone = true;
      try { window.__introCuePart = 'shoulder'; window.__introCueJoint = 'right_shoulder'; } catch (_) {}
      try { (window.introShoulderChallenge || function(){})(); } catch (_) {}
      this.sysFact("a magic light just appeared on the kid's right shoulder — you can SEE it; " +
                   "discover it out loud with wonder and invite them to MOVE that shoulder, a tiny shrug (never touch)");
      this.beat('React to the newest system note now — one short beat, your own words.');
    },

    /* the page calls this on a detected move (same try_move source as before) */
    moveFact(action) {
      if (!this.ready) return;
      this.sysFact('they just did a ' + action + " — if it's the lit shoulder, celebrate ONCE by name " +
                   '(that move is called an isolation), then lead toward picking a dance game');
      this.beat('React to the newest system note — one short line.');
    },

    /* game beats — same texts + rate limits as the certified worker director */
    gameFact(ev) {
      if (!this.ready) return;
      const t = ev && ev.event;
      if (t === 'picked') {
        this.send({ type: 'response.cancel' });          // TRANSITION HARD-CUT
        this.sysFact("they picked '" + (ev.title || ev.song || 'the game') + "'! it is loading right now — " +
                     'ride the excitement in ONE short line while it loads');
        this.beat('One short excited loading line, then quiet.');
      } else if (t === 'song_start') {
        this.sysFact('the music is STARTING right now');
        this.beat('ONE big go-line, three-six words, then the music leads and you stay mostly quiet.');
      } else if (t === 'hit' || t === 'first_hit' || t === 'freeze_hit') {
        const now = Date.now();
        if (now - this.lastCheerAt > 8000) {             // cheer law: one per 8s
          this.lastCheerAt = now;
          this.sysFact('they nailed a ' + (ev.action || 'move') + (ev.streak ? ' (streak ' + ev.streak + ')' : ''));
          this.beat('One tiny cheer, five words max, name the move.');
        } else { this.sysFact('another hit: ' + (ev.action || 'move')); }
      } else if (t === 'phase' && ev.phase === 'goodbye') {
        this.sysFact('the dance ended — their real highlights are what you saw in the facts above');
        this.beat('Celebrate them BY NAME with one specific real moment, then one warm goodbye line.');
      }
    },

    onEvent(m) {
      const t = m.type || '';
      if (t === 'conversation.item.input_audio_transcription.completed') {
        const txt = (m.transcript || '').trim();
        if (txt) { this.lastKidSpokeAt = Date.now(); LOG('HEARD', txt);
          try { (window.addBubble || function(){})(txt, 'kid'); } catch (_) {} }
      } else if (t === 'response.audio_transcript.done') {
        const txt = (m.transcript || '').trim();
        if (!txt) return;
        this.lastHerLineAt = Date.now(); LOG('NOVA-SAID', txt);
        try { (window.addBubble || function(){})(txt, 'nova'); } catch (_) {}
        /* CONSENT-GATED trigger-out: her words open the picker ONLY on fresh kid input */
        if (!this.pickerOpened && /\b(let'?s|wanna|want to)\s+(dance|play|start)\b/i.test(txt)) {
          if (Date.now() - this.lastKidSpokeAt < 10000) {
            this.pickerOpened = true;
            LOG('TRIGGER', 'picker (consent ok)');
            this.sysFact("the picker is on their screen with exactly three games: 'Hello Hello!', " +
                         "'Up Groove!' and 'Wave!' — help them pick one (never invent other games)");
            try { (window.goToPicker || function(){})(); } catch (_) {}
          } else { LOG('CONSENT', 'blocked self-answer (no kid input 10s)'); }
        }
      } else if (t === 'error') { LOG('ERR', JSON.stringify(m).slice(0, 180)); }
    },
  };

  window.__directVoice = DV;
  document.addEventListener('DOMContentLoaded', () => {
    /* ride the existing orb-tap flow: start on the first user gesture (mic + autoplay legal) */
    const kick = () => { DV.start(); document.removeEventListener('pointerdown', kick); };
    document.addEventListener('pointerdown', kick, { once: true });
    LOG('BOOT', 'armed — first tap starts direct voice');
  });
})();
