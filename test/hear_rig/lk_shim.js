/* rig: stands in for livekit-client in the page. Same events the bridge listens to; her wide body = the calm clip, her
   voice = what the engine stub streams (already delayed like the real face server). */
(() => {
  const RoomEvent = { TrackSubscribed: 'trackSubscribed', TrackUnsubscribed: 'trackUnsubscribed', Disconnected: 'disconnected' };
  class Room {
    constructor(){ this.h = {}; }
    on(e, f){ (this.h[e] ||= []).push(f); return this; }
    emit(e, ...a){ (this.h[e] || []).forEach(f => f(...a)); }
    async connect(){
      const p = { identity: 'nova-face' }, mk = (kind, t) => ({ kind, mediaStreamTrack: t, attach(){ const a = document.createElement(kind); a.srcObject = new MediaStream([t]); return a; } });
      const v = document.createElement('video'); v.src = '/media/nova_talk_calm.mp4'; v.loop = true; v.muted = true; v.playsInline = true; await v.play();
      const wt = v.captureStream().getVideoTracks()[0];
      const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); let k = 0;
      setInterval(() => { g.fillStyle = '#f2c9a8'; g.fillRect(0, 0, 256, 256); g.fillStyle = '#402'; g.beginPath(); g.ellipse(128, 180, 30, 6 + (window.__rigLvl || 0) * 60 + (k++ % 2), 0, 0, 7); g.fill();
        g.fillRect(80, 90, 20, 20); g.fillRect(156, 90, 20, 20); }, 40);
      const ft = c.captureStream(25).getVideoTracks()[0];
      const ac = window.__rigAC || (window.__rigAC = new AudioContext()); if (ac.state === 'suspended') await ac.resume();
      const dest = ac.createMediaStreamDestination(), an = ac.createAnalyser(); an.fftSize = 256; const ab = new Float32Array(256);
      setInterval(() => { an.getFloatTimeDomainData(ab); let s = 0; for (const x of ab) s += x * x; window.__rigLvl = Math.sqrt(s / 256); }, 40);
      this.emit(RoomEvent.TrackSubscribed, mk('video', wt), { trackName: 'nova-wide-video' }, p);
      this.emit(RoomEvent.TrackSubscribed, mk('video', ft), { trackName: 'nova-face-video' }, p);
      this.emit(RoomEvent.TrackSubscribed, mk('audio', dest.stream.getAudioTracks()[0]), { trackName: 'nova-face-voice' }, p);
      const sock = new WebSocket('ws://127.0.0.1:8010/rigaudio'); sock.binaryType = 'arraybuffer'; window.__rigHer = [];
      sock.onmessage = ev => { if (typeof ev.data === 'string') return;
        const due = new Float64Array(ev.data.slice(0, 8))[0], i16 = new Int16Array(ev.data.slice(8));
        const b = ac.createBuffer(1, i16.length, 16000), ch = b.getChannelData(0); for (let i = 0; i < i16.length; i++) ch[i] = i16[i] / 32768;
        const s = ac.createBufferSource(); s.buffer = b; s.connect(dest); s.connect(an);
        if (window.__rigEcho) s.connect(window.__rigEcho);            // the rig's "phone speaker into the microphone"
        const at = Math.max(ac.currentTime, ac.currentTime + due - Date.now() / 1000); s.start(at);
        window.__rigHer.push([+(performance.now() / 1000 + (at - ac.currentTime)).toFixed(2), +(i16.length / 16000).toFixed(2)]); };
    }
  }
  window.LivekitClient = { Room, RoomEvent };
})();
