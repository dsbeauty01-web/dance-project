/* rig + proof: the child's microphone = a stream the test can speak into (window.__kidSay), with a real microphone's
   noise floor, and optionally her own voice leaking back in (window.__RIG_ECHO = 0..1, a phone with weak echo cancelling). */
(() => {
  const md = navigator.mediaDevices; if (!md || !md.getUserMedia) return;
  const real = md.getUserMedia.bind(md); let ctx = null, dest = null;
  const ensure = () => { if (!ctx) { ctx = window.__rigAC || (window.__rigAC = new AudioContext()); dest = ctx.createMediaStreamDestination();
      const n = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = n.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * 0.002;
      const ns = ctx.createBufferSource(); ns.buffer = n; ns.loop = true; ns.connect(dest); ns.start();
      const e = ctx.createGain(); e.gain.value = +(window.__RIG_ECHO || 0); const dl = ctx.createDelay(1); dl.delayTime.value = 0.06; e.connect(dl); dl.connect(dest); window.__rigEcho = e; }
    return dest; };
  window.__kidMic = { asked: [], given: 0, said: 0 };
  md.getUserMedia = async (c) => {
    window.__kidMic.asked.push(JSON.stringify(c).slice(0, 120));
    const s = await real(c);
    if (c && c.audio) { s.getAudioTracks().forEach(t => { t.stop(); s.removeTrack(t); }); window.__kidMic.given++;
      const t = ensure().stream.getAudioTracks()[0].clone(); if (!c.video) return new MediaStream([t]); s.addTrack(t); }
    return s;
  };
  window.__kidSay = async (b64) => {
    ensure(); if (ctx.state === 'suspended') await ctx.resume();
    const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    const buf = await ctx.decodeAudioData(u.buffer), n = ctx.createBufferSource();
    n.buffer = buf; n.connect(dest); n.connect(ctx.destination); n.start(); window.__kidMic.said++; return buf.duration;
  };
})();
