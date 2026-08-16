/* ═══════════════════════════════════════════════════════════════════════════
   game-core.js — GAMES-PERFECT shared core (2026-08-16)
   Pages live on GitHub Pages; the pod serves ONLY the avatar stream + brain (CORS).
   This module is the ONLY shared code: LiveKit-direct avatar attach, brain socket,
   mic capture, camera + MoveNet, music ducking, PULSE. Game LOGIC is never here —
   each game page owns its cue table, scoring, layout, and lines.

   Copied precisely from the pod's first-party avatar page (rt_lk.py PAGE) so the
   media wiring is identical; only the base URL changes (cross-origin + CORS) and
   parent.postMessage is replaced by direct callbacks.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const LK = global.LivekitClient || global.LiveKitClient;

  // ── pod base URL: ?saray= / ?pod= override → registry → hard fail (no hardcoded pod) ──
  function podBase() {
    const q = new URLSearchParams(location.search);
    let b = q.get('saray') || q.get('pod') ||
            (global.NOVA_PODS && global.NOVA_PODS.saray && global.NOVA_PODS.saray()) || null;
    if (!b) return null;
    return b.replace(/\/+$/, ''); // no trailing slash
  }

  const Core = {
    pod: null, room: null, ws: null, ctx: null,
    micOn: false, micGated: false, wsConns: 0,
    videoEl: null, music: null, cbNote: null, cbStatus: null, cbKidSaid: null,
    MUSIC_VOL: 0.6, DUCK_VOL: 0.35,

    /* ── connect: attach avatar (LiveKit-direct) + open brain socket ── */
    async connect(opts) {
      this.pod = podBase();
      if (!this.pod) throw new Error('no pod base (set ?pod= or registry)');
      this.videoEl = opts.videoEl;
      this.cbNote = opts.onNote || function () {};
      this.cbStatus = opts.onStatus || function () {};
      this.cbKidSaid = opts.onKidSaid || function () {};
      this._persona = opts.persona || null;
      this._intro = opts.intro || null;      // e.g. 'joined' — game context for the brain
      await this._joinRoom();
      this._connectWS();
    },

    async _joinRoom() {
      const r = await (await fetch(this.pod + '/token')).json();
      this.room = new LK.Room({ adaptiveStream: false, dynacast: false });
      this.room.on(LK.RoomEvent.TrackSubscribed, (track, pub, p) => {
        if (p.identity !== 'nova-avatar') return;
        if (track.kind === 'video') { track.attach(this.videoEl); this._onVideo && this._onVideo(); }
        if (track.kind === 'audio') {
          const a = track.attach(); a.autoplay = true; a.muted = false; a.playsInline = true;
          a.id = 'nova-audio-el'; document.body.appendChild(a);
          this._novaAudio = a;
          let ok = false;
          const tryPlay = () => a.play().then(() => { ok = true; const b = document.getElementById('unmute-btn'); if (b) b.remove(); })
            .catch(e => console.warn('[AUDIO] blocked', e.name));
          tryPlay();
          ['pointerdown', 'touchstart', 'keydown'].forEach(ev => document.addEventListener(ev, tryPlay, { passive: true }));
          // music ducking wired to HER real audio element events (E4)
          a.addEventListener('playing', () => this._duck(true));
          a.addEventListener('ended', () => this._duck(false));
          a.addEventListener('pause', () => this._duck(false));
          setTimeout(() => {
            if (ok || document.getElementById('unmute-btn')) return;
            const b = document.createElement('button'); b.id = 'unmute-btn';
            b.textContent = '🔊  TAP TO HEAR NOVA';
            b.style.cssText = 'position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:99999;font:700 22px system-ui;color:#1a1013;background:#ffd24a;border:0;padding:20px 34px;border-radius:999px;box-shadow:0 10px 40px rgba(0,0,0,.5);cursor:pointer';
            b.onclick = () => { a.muted = false; a.volume = 1; tryPlay(); setTimeout(() => { if (b.parentNode) b.remove(); }, 400); };
            document.body.appendChild(b);
          }, 1500);
        }
      });
      this.room.on(LK.RoomEvent.Disconnected, () => this._reconnect());
      await this.room.connect(r.url, r.token);
    },
    async _reconnect() { try { const r = await (await fetch(this.pod + '/token')).json(); await this.room.connect(r.url, r.token); } catch (e) { setTimeout(() => this._reconnect(), 2500); } },

    _connectWS() {
      const qs = new URLSearchParams();
      if (this._intro) qs.set('intro', this._intro);
      if (this.wsConns++) qs.set('rc', '1');
      const q = qs.toString();
      const url = this.pod.replace(/^http/, 'ws') + '/rt' + (q ? '?' + q : '');
      this.ws = new WebSocket(url);
      this.ws.onopen = () => {
        // inject the game persona the moment the socket is open (not before)
        if (this._persona) this.persona(this._persona);
        if (this._intro) this.send({ type: 'nova-pick', game: this._intro });
      };
      this.ws.onclose = () => setTimeout(() => this._connectWS(), 1800);
      this.ws.onmessage = (ev) => {
        let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
        if (m.type === 'you_text') this.cbKidSaid(m.text || '');
        else if (m.type === 'nova_done') this.cbNote({ kind: 'nova_said', text: m.text || '' });
        else if (m.type === 'status') {
          if (m.speaking === true) this.micGated = true;
          else if (m.speaking === false) this.micGated = false;
          this.cbStatus({ state: m.state || '', speaking: m.speaking });
        }
      };
    },

    send(o) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(o)); },
    persona(text) { this.send({ type: 'persona', text: text }); },
    say(text) { this.send({ type: 'nova-say', text: text }); },
    cue(intent, ctx) { this.send({ type: 'nova-cue', intent: intent, ctx: ctx || '' }); },
    fact(move) { this.send({ type: 'nova-fact', move: move }); },
    hold(on) { this.send({ type: 'hold', on: !!on }); },
    gameStart() { this.send({ type: 'game-start' }); },
    setAvatar(id) { fetch(this.pod + '/set_avatar?id=' + encodeURIComponent(id)).catch(() => {}); },

    /* ── mic (ONE-MIC): capture → 24k PCM → brain socket ── */
    async startMic() {
      if (this.micOn) return;
      const stream = this._stream || await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      this.ctx = this.ctx || new (global.AudioContext || global.webkitAudioContext)();
      if (this.ctx.state === 'suspended') await this.ctx.resume();
      const src = this.ctx.createMediaStreamSource(stream);
      const proc = this.ctx.createScriptProcessor(4096, 1, 1);
      const ratio = this.ctx.sampleRate / 24000;
      proc.onaudioprocess = (e) => {
        if (this.micGated) return;
        const ch = e.inputBuffer.getChannelData(0);
        const n = Math.floor(ch.length / ratio), b = new Int16Array(n);
        for (let i = 0; i < n; i++) { let s = ch[Math.floor(i * ratio)]; if (s > 1) s = 1; if (s < -1) s = -1; b[i] = s * 0x7fff; }
        const u = new Uint8Array(b.buffer); let x = ''; for (let i = 0; i < u.length; i++) x += String.fromCharCode(u[i]);
        this.send({ type: 'audio', data: btoa(x) });
      };
      src.connect(proc); proc.connect(this.ctx.destination); this.micOn = true;
    },

    /* ── camera + MoveNet (E1): ONE getUserMedia, two consumers (usercam + detector) ── */
    async startCamera(usercamEl, onPose) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 }, audio: false });
        usercamEl.srcObject = s; usercamEl.muted = true; usercamEl.playsInline = true; await usercamEl.play().catch(() => {});
        this._camOK = true;
        if (!global.poseDetection) return;
        const det = await global.poseDetection.createDetector(global.poseDetection.SupportedModels.MoveNet,
          { modelType: global.poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING });
        const loop = async () => {
          if (usercamEl.readyState >= 2) {
            try { const poses = await det.estimatePoses(usercamEl); if (poses && poses[0]) onPose(poses[0].keypoints); } catch (e) {}
          }
          this._camRAF = requestAnimationFrame(loop);
        };
        loop();
      } catch (e) { this._camOK = false; if (this._onCamFail) this._onCamFail(); }
    },
    camOK() { return !!this._camOK; },

    /* ── music: 0.6 + duck to 0.35 on her voice (E4) ── */
    attachMusic(el) { this.music = el; el.volume = this.MUSIC_VOL; },
    _duck(on) {
      if (!this.music) return;
      const to = on ? this.DUCK_VOL : this.MUSIC_VOL, ms = on ? 150 : 300, from = this.music.volume, t0 = performance.now();
      const step = () => { const k = Math.min(1, (performance.now() - t0) / ms); this.music.volume = from + (to - from) * k; if (k < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    },

    /* ── PULSE: end-of-session beacon (Part 4) ── */
    pulse(payload) {
      try {
        const body = JSON.stringify(Object.assign({ ts: Date.now() }, payload));
        if (navigator.sendBeacon && global.NOVA_PULSE_URL) navigator.sendBeacon(global.NOVA_PULSE_URL, body);
        else if (global.NOVA_PULSE_URL) fetch(global.NOVA_PULSE_URL, { method: 'POST', body: body, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(() => {});
        else console.log('[PULSE]', body);
      } catch (e) {}
    },

    onVideo(cb) { this._onVideo = cb; },
    onCamFail(cb) { this._onCamFail = cb; },
  };

  global.NovaCore = Core;
})(window);
