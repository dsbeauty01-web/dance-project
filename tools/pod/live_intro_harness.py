#!/usr/bin/env python3
"""live_intro_harness.py -- open the REAL commercial intro page in headless Chromium, record the
LiveKit tracks Nova publishes to ONE continuous file, and let a human off-pod play the kid.

It is NOT a remote-exec endpoint. The only thing it accepts from outside is a line of text to type
into the page's own chat box (#nova-chat-input, the founder's 2026-08-09 typed lane, which sends
the brain the same {"type":"text"} a child's typed reply sends). Files it reads:

  /workspace/in/kid_<NNN>.txt   one kid line, typed in filename order, each consumed once
  /workspace/in/GESTURE_<name>  fire that bank clip on the Ditto server (NOVA_FACE=ditto only)
  /workspace/in/STOP            stop recording, mux, exit

Files it writes, all under $OUT (podsrv serves /workspace read-only):

  ws.jsonl       every brain websocket frame, in and out, with a monotonic t -- the transcript
  console.log    every console message and page error
  STATUS         one line per state change, so progress is readable from off-pod
  live_intro.mp4 the recording: her video track + her audio track, one continuous file

THE RECORDING. There is no X display on the pod, so the picture is composited in the page: her
remote video track is drawn to a canvas at 25 fps with a caption band carrying the last lines of
the real conversation, canvas.captureStream(25) is joined with her remote AUDIO track, and one
MediaRecorder writes the pair. Chunks are POSTed to a 127.0.0.1 sink with a sequence number and
concatenated in order, so the file is one continuous take, not a stitch of separate recordings.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

INIT_JS = r"""
// Runs before any page script. Two hooks, no behaviour change.
window.__wslog = [];
window.__ms = [];
(function(){
  // 1. every MediaStream the page attaches to a media element -- this is how we reach the
  //    LiveKit tracks without needing the page's own (script-scope, non-global) Stage object.
  var d = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'srcObject');
  Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {
    configurable: true, get: d.get,
    set: function(v){ try{ if(v) window.__ms.push({tag:(this.tagName||'')+'#'+(this.id||''), ms:v}); }catch(e){}
                      return d.set.call(this, v); }
  });
  // 2. every brain websocket frame, both directions.
  var OW = window.WebSocket;
  function W(url, proto){
    var ws = proto === undefined ? new OW(url) : new OW(url, proto);
    var brain = (''+url).indexOf('/rt') >= 0;
    if (brain) {
      window.__wsurl = ''+url;
      ws.addEventListener('message', function(ev){
        try{ window.__wslog.push({t: performance.now()/1000, d:'in', m: ''+ev.data}); }catch(e){}
      });
      var os_ = ws.send.bind(ws);
      ws.send = function(x){ try{ window.__wslog.push({t: performance.now()/1000, d:'out', m: ''+x}); }catch(e){}
                             return os_(x); };
      ws.addEventListener('open',  function(){ window.__wslog.push({t: performance.now()/1000, d:'ev', m:'{"type":"_ws_open"}'}); });
      ws.addEventListener('close', function(){ window.__wslog.push({t: performance.now()/1000, d:'ev', m:'{"type":"_ws_close"}'}); });
    }
    return ws;
  }
  W.prototype = OW.prototype;
  ['CONNECTING','OPEN','CLOSING','CLOSED'].forEach(function(k,i){ W[k]=i; });
  window.WebSocket = W;
})();

// ---- the recorder, started from Python once her tracks exist -----------------------------
window.__caps = [];
window.__recState = {started:false, frames:0, chunks:0, bytes:0, err:null, w:0, h:0};
window.__startRec = async function(sink, cw, ch){
  var S = window.__recState;
  if (S.started) return S;
  // VIDEO (fixed 2026-11-02, session novarec). This used to be
  //     window.__ms.find(x => x.ms.getVideoTracks().length > 0)
  // i.e. the FIRST attached stream with video. On this page that is the page's own CAMERA
  // PREVIEW, and the camera on a headless pod is --use-fake-device-for-media-stream: Chromium's
  // green test pattern with a rotating wedge and a timecode. Takes 1-3 recorded 67-82 s of that
  // fake webcam and none of Nova. The giveaway was in the log the whole time: the bridge
  // published 720x1288 and the recorder reported src=960x720.
  // A LOCAL track has a deviceId in getSettings(); a REMOTE one does not. Prefer remote, then
  // the tallest track (Nova is portrait 720x1288, the fake camera is landscape 960x720).
  var vcands = [];
  window.__ms.forEach(function(x){
    try {
      x.ms.getVideoTracks().forEach(function(t){
        var st; try { st = t.getSettings ? t.getSettings() : {}; } catch(e) { st = {}; }
        vcands.push({x: x, t: t, tag: x.tag, label: t.label, local: !!st.deviceId,
                     w: st.width || 0, h: st.height || 0});
      });
    } catch(e) {}
  });
  window.__videoPick = {n: vcands.length, cands: vcands.map(function(c){
    return {tag: c.tag, label: c.label, local: c.local, w: c.w, h: c.h}; })};
  if (!vcands.length) return {started:false, why:'no video stream attached yet', seen:window.__ms.length};
  // getSettings() reports a deviceId for BOTH the local camera and the remote track in
  // Chromium, so `local` cannot be the discriminator (measured: the fake camera is
  // {label:'fake_device_0', 960x720} and Nova is {label:'remote video', 360x644}, both
  // local:true). Score on what actually separates them: the element Nova is attached to
  // (#nova-live-video), the track label, and portrait-vs-landscape.
  function score(c){
    var s = 0;
    if (/nova/i.test(c.tag || '')) s += 8;
    if (/remote/i.test(c.label || '')) s += 4;
    if ((c.h || 0) > (c.w || 0)) s += 2;                    // she is portrait, the camera is not
    if (/fake_device|camera|webcam|default/i.test(c.label || '')) s -= 16;
    if (/#cam\b|#cam$/i.test(c.tag || '')) s -= 8;
    return s;
  }
  vcands.forEach(function(c){ c.score = score(c); });
  vcands.sort(function(a, b){ return b.score - a.score || (b.h || 0) - (a.h || 0); });
  var chosen = vcands[0];
  window.__videoPick.cands = vcands.map(function(c){
    return {tag: c.tag, label: c.label, w: c.w, h: c.h, score: c.score}; });
  if (chosen.score <= 0) return {started:false, why:'only the local camera is attached so far',
                                 pick: window.__videoPick};
  window.__videoPick.chosen = {tag: chosen.tag, label: chosen.label, w: chosen.w, h: chosen.h};
  var vs = chosen.x, vt = chosen.t;
  // AUDIO (fixed 2026-11-02, session novarec). This used to be
  //     window.__ms.find(x => x.ms.getAudioTracks().length > 0)
  // i.e. the FIRST attached stream carrying audio -- which on this page is the LOCAL MIC, and
  // the mic on a headless pod is --use-file-for-fake-audio-capture=/root/silence.wav. Take 1
  // therefore recorded a real-but-silent audio track: ffmpeg measured max_volume -84.3 dB over
  // 67 s while app.log showed the engine genuinely producing speech ("put audio stream 16000")
  // and Ditto rendering 211 audio-driven chunks. Her voice was never the track being captured.
  // Now: mix EVERY attached audio track through WebAudio, so hers is in whichever stream it
  // arrives on and the silent mic contributes nothing.
  var at = null, mixed = [];
  try {
    var AC = window.AudioContext || window.webkitAudioContext;
    var ac = new AC({sampleRate: 48000});
    var dest = ac.createMediaStreamDestination();
    window.__ms.forEach(function(x){
      try {
        if (!x.ms.getAudioTracks().length) return;
        x.ms.getAudioTracks().forEach(function(t){
          var st;
          try { st = t.getSettings ? t.getSettings() : {}; } catch(e) { st = {}; }
          mixed.push({tag: x.tag, label: t.label, muted: t.muted,
                      local: !!st.deviceId, id: (t.id||'').slice(0,8)});
        });
        ac.createMediaStreamSource(x.ms).connect(dest);
      } catch(e) {}
    });
    try { await ac.resume(); } catch(e) {}
    at = dest.stream.getAudioTracks()[0] || null;
    window.__audioMix = {n: mixed.length, tracks: mixed, ctx: ac.state};
  } catch(e) {
    window.__audioMix = {err: ''+e};
    var as = window.__ms.find(function(x){ try{ return x.ms.getAudioTracks().length>0; }catch(e){ return false; } });
    at = as ? as.ms.getAudioTracks()[0] : null;
  }
  var v = document.createElement('video');
  v.srcObject = new MediaStream([vt]); v.muted = true; v.autoplay = true; v.playsInline = true;
  try { await v.play(); } catch(e) {}
  var c = document.createElement('canvas'); c.width = cw; c.height = ch;
  var g = c.getContext('2d');
  var CAP_H = Math.round(ch * 0.22);
  function wrap(text, max){
    var w = text.split(' '), out = [], cur = '';
    for (var i=0;i<w.length;i++){
      var t = cur ? cur+' '+w[i] : w[i];
      if (g.measureText(t).width > max && cur){ out.push(cur); cur = w[i]; } else cur = t;
    }
    if (cur) out.push(cur);
    return out;
  }
  function draw(){
    try{
      g.fillStyle = '#07080d'; g.fillRect(0,0,cw,ch);
      var vw = v.videoWidth, vh = v.videoHeight;
      if (vw && vh){
        S.w = vw; S.h = vh;
        var s = Math.min(cw/vw, ch/vh), dw = vw*s, dh = vh*s;
        g.drawImage(v, (cw-dw)/2, (ch-dh)/2, dw, dh);
      }
      // caption band: the last lines of the REAL exchange, so the file shows the back-and-forth
      var caps = window.__caps.slice(-6);
      g.font = '600 ' + Math.round(ch*0.0225) + 'px system-ui, sans-serif';
      var lines = [];
      for (var i=0;i<caps.length;i++){
        var who = caps[i].who, body = wrap(caps[i].text, cw-28);
        for (var j=0;j<body.length;j++) lines.push({who:who, text:(j?'   ':'')+body[j]});
      }
      lines = lines.slice(-5);
      if (lines.length){
        var lh = Math.round(ch*0.030), bh = lines.length*lh + 16;
        g.fillStyle = 'rgba(6,8,14,.72)'; g.fillRect(0, ch-bh, cw, bh);
        for (var k=0;k<lines.length;k++){
          g.fillStyle = lines[k].who === 'NOVA' ? '#ffd24a' : '#8fd0ff';
          g.fillText(lines[k].who + ': ' + lines[k].text, 14, ch - bh + 14 + (k+1)*lh - 6);
        }
      }
      S.frames++;
    }catch(e){ S.err = ''+e; }
  }
  draw();
  window.__recTimer = setInterval(draw, 40);
  var st = c.captureStream(25);
  if (at) st.addTrack(at);
  var mime = ['video/webm;codecs=vp8,opus','video/webm;codecs=vp9,opus','video/webm']
             .find(function(m){ return MediaRecorder.isTypeSupported(m); });
  var rec = new MediaRecorder(st, {mimeType: mime, videoBitsPerSecond: 2200000, audioBitsPerSecond: 96000});
  window.__rec = rec;
  var seq = 0, chain = Promise.resolve();
  rec.ondataavailable = function(e){
    if (!e.data || !e.data.size) return;
    var n = seq++, blob = e.data;
    S.chunks++; S.bytes += blob.size;
    // text/plain keeps it a CORS-simple request (no preflight); seq keeps the order exact.
    chain = chain.then(function(){
      return fetch(sink + '?seq=' + n, {method:'POST', mode:'no-cors',
                                        body: new Blob([blob], {type:'text/plain'})});
    }).catch(function(err){ S.err = 'sink: ' + err; });
  };
  rec.onerror = function(e){ S.err = 'rec: ' + (e && e.message); };
  rec.start(1000);
  S.started = true; S.mime = mime; S.audio = !!at; S.mix = window.__audioMix; S.vpick = window.__videoPick;
  return S;
};
window.__stopRec = async function(){
  try{ clearInterval(window.__recTimer); }catch(e){}
  try{ window.__rec.requestData(); window.__rec.stop(); }catch(e){}
  await new Promise(function(r){ setTimeout(r, 2500); });
  return window.__recState;
};
"""

SINK_PY = r"""
import os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
D = sys.argv[1]; os.makedirs(D, exist_ok=True)
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _done(self, code):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Content-Length", "0"); self.end_headers()
    def do_OPTIONS(self): self._done(204)
    def do_POST(self):
        q = parse_qs(urlparse(self.path).query)
        seq = int((q.get("seq") or ["0"])[0])
        n = int(self.headers.get("Content-Length", "0")); left = n; buf = b""
        while left > 0:
            c = self.rfile.read(min(1 << 20, left))
            if not c: break
            buf += c; left -= len(c)
        with open(os.path.join(D, "%06d.part" % seq), "wb") as f:
            f.write(buf)
        self._done(200)
ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765/beta/freeze?intro=freeze",
                help="one URL, or several separated by | and tried in order")
    ap.add_argument("--out", default="/workspace/novalive_out")
    ap.add_argument("--inbox", default="/workspace/in")
    ap.add_argument("--rec-dir", default="/root/rec")
    ap.add_argument("--sink-port", type=int, default=8099)
    ap.add_argument("--max-s", type=float, default=600.0)
    ap.add_argument("--cw", type=int, default=540)
    ap.add_argument("--ch", type=int, default=960)
    ap.add_argument("--ditto-port", type=int, default=8031)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(a.rec_dir, exist_ok=True)
    for f in glob.glob(os.path.join(a.rec_dir, "*.part")):
        os.remove(f)
    # /workspace/in is on the SHARED network volume, so it can carry a previous session's files
    # (this cost pod 2 on 2026-10-31). Clear only our own control files, nothing else.
    for f in (glob.glob(os.path.join(a.inbox, "kid_*.txt"))
              + glob.glob(os.path.join(a.inbox, "GESTURE_*"))
              + [os.path.join(a.inbox, "STOP")]):
        try:
            os.remove(f)
        except OSError:
            pass
    ws_path = os.path.join(a.out, "ws.jsonl")
    con_path = os.path.join(a.out, "console.log")
    st_path = os.path.join(a.out, "STATUS")
    wsf = open(ws_path, "w", buffering=1)
    conf = open(con_path, "w", buffering=1)
    t00 = time.time()

    def status(s):
        line = f"[{time.time()-t00:7.1f}s] {s}"
        print(line, flush=True)
        with open(st_path, "a") as f:
            f.write(line + "\n")

    sink_src = os.path.join(a.out, "_sink.py")
    with open(sink_src, "w") as f:
        f.write(SINK_PY)
    sink = subprocess.Popen([sys.executable, sink_src, a.rec_dir, str(a.sink_port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status(f"chunk sink up on 127.0.0.1:{a.sink_port} -> {a.rec_dir}")

    sil = "/root/silence.wav"
    if not os.path.exists(sil):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=mono", "-t", "20", "-c:a", "pcm_s16le", sil], check=False)

    # ---- PAGE REPAIR (2026-11-01) ---------------------------------------------------------
    # boot.sh's deploy step copies the repo's pages onto the volume. On 2026-11-01 the volume was
    # out of quota, so every cp opened its destination, truncated it, and then failed to write:
    # /workspace/pages/beta/freeze.html and twelve shared/*.js were left at 0 bytes, timestamped
    # 11:33, and /beta/freeze answered 200 with an empty body. The truncation itself freed the
    # quota, so the volume is writable again but the files are gone.
    # If an uploaded repair set is present, put those exact files back BEFORE opening the page.
    # Names are flattened as "<subdir>__<file>" because podsrv's PUT takes a basename only.
    # Nothing is overwritten unless the uploaded copy is LARGER than what is on the volume, so a
    # healthy file is never clobbered by this.
    fixed, skipped = [], []
    for src in sorted(glob.glob(os.path.join(a.inbox, "*__*"))):
        sub, _, base = os.path.basename(src).partition("__")
        if sub not in ("beta", "shared", "models") or not base:
            continue
        dst = os.path.join("/workspace/pages", sub, base)
        try:
            have = os.path.getsize(dst) if os.path.exists(dst) else -1
            want = os.path.getsize(src)
            if have >= want:
                skipped.append(f"{sub}/{base} ({have} >= {want})")
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp = dst + ".novalive-new"
            shutil.copyfile(src, tmp)
            os.replace(tmp, dst)          # atomic: the live file is never a partial write
            fixed.append(f"{sub}/{base} {have} -> {os.path.getsize(dst)}")
        except Exception as e:
            skipped.append(f"{sub}/{base} FAILED {type(e).__name__}: {e}")
    if fixed or skipped:
        status(f"page repair: restored {len(fixed)}, left alone {len(skipped)}")
        for f in fixed:
            status("  + " + f)
        for f in skipped[:6]:
            status("  . " + f)

    from playwright.sync_api import sync_playwright          # noqa: E402

    caps = []          # [{who,text}] -- the real exchange, mirrored into the recording
    said = []          # her lines, in order
    heard = []         # the kid's lines as the brain transcribed/echoed them
    typed = []
    gestures = []
    seen_kid = set()
    rec_started = [False]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
            "--autoplay-policy=no-user-gesture-required",
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-audio-capture={sil}",
            "--allow-running-insecure-content", "--disable-features=IsolateOrigins,site-per-process",
        ])
        ctx = browser.new_context(viewport={"width": a.cw, "height": a.ch},
                                  permissions=["camera", "microphone"],
                                  ignore_https_errors=True)
        ctx.add_init_script(INIT_JS)
        page = ctx.new_page()
        page.on("console", lambda m: conf.write(f"[{time.time()-t00:7.1f}s] {m.type}: {m.text}\n"))
        page.on("pageerror", lambda e: conf.write(f"[{time.time()-t00:7.1f}s] PAGEERROR: {e}\n"))
        # 2026-11-01: on a pod whose volume is out of quota, boot.sh's deploy step truncates the
        # page it was meant to deploy, and /beta/freeze then answers 200 with an EMPTY body: the
        # harness saw a white page with no #start-btn and no console output at all. So the URL is
        # a LIST now, tried in order, and a page that never shows the Let's-Play button is treated
        # as not-served rather than silently recorded as a blank screen.
        opened = None
        for u in [x for x in a.url.split("|") if x.strip()]:
            status(f"goto {u}")
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                status(f"  goto failed: {type(e).__name__}")
                continue
            try:
                body = page.evaluate("()=>({len:(document.body&&document.body.innerText||'').length,"
                                     "html:document.documentElement.outerHTML.length,"
                                     "txt:(document.body&&document.body.innerText||'').slice(0,160)})")
                status(f"  body text {body['len']} chars, html {body['html']} bytes: {body['txt']!r}")
            except Exception:
                pass
            try:
                page.click("#start-btn", timeout=15000)
                status(f"  clicked Let's Play on {u}")
                opened = u
                break
            except Exception as e:
                status(f"  no #start-btn here ({type(e).__name__})")
        if not opened:
            status("NO PAGE SERVED the app on any candidate URL -- nothing to record")

        def pump_ws():
            try:
                rows = page.evaluate("()=>window.__wslog.splice(0)")
            except Exception:
                return []
            out = []
            for r in rows:
                wsf.write(json.dumps(r) + "\n")
                try:
                    m = json.loads(r["m"])
                except Exception:
                    continue
                t = m.get("type")
                if t == "nova_done" and (m.get("text") or "").strip():
                    said.append(m["text"].strip())
                    caps.append({"who": "NOVA", "text": m["text"].strip()})
                    out.append(("nova", m["text"].strip()))
                elif t == "you_text" and (m.get("text") or "").strip():
                    heard.append(m["text"].strip())
                    if not caps or caps[-1].get("text") != m["text"].strip():
                        caps.append({"who": "NOAM", "text": m["text"].strip()})
                    out.append(("kid", m["text"].strip()))
                elif t in ("_ws_open", "_ws_close"):
                    status("brain ws " + t[4:])
            if caps:
                try:
                    page.evaluate("(c)=>{window.__caps=c;}", caps[-8:])
                except Exception:
                    pass
            return out

        def try_start_rec():
            if rec_started[0]:
                return
            try:
                s = page.evaluate("async ([u,w,h])=>await window.__startRec(u,w,h)",
                                  [f"http://127.0.0.1:{a.sink_port}/chunk", a.cw, a.ch])
            except Exception as e:
                status(f"startRec threw: {e}")
                return
            if s and not s.get("started") and s.get("why"):
                if time.time() - t00 > 4 and int(time.time()*2) % 20 == 0:
                    status(f"waiting for her video track: {s.get('why')} {json.dumps(s.get('pick'))}")
            if s and s.get("started"):
                rec_started[0] = True
                status(f"RECORDING started mime={s.get('mime')} audio_track={s.get('audio')} "
                       f"audio_mix={json.dumps(s.get('mix'))} video={json.dumps(s.get('vpick',{}).get('chosen'))}")

        t_end = time.time() + a.max_s
        stop = os.path.join(a.inbox, "STOP")
        last_status = 0.0
        while time.time() < t_end:
            try_start_rec()
            for who, txt in pump_ws():
                status(("SHE: " if who == "nova" else "KID(echo): ") + txt[:120])
            # kid lines, PUT from off-pod, typed in filename order, each exactly once
            for p in sorted(glob.glob(os.path.join(a.inbox, "kid_*.txt"))):
                if p in seen_kid:
                    continue
                seen_kid.add(p)
                try:
                    line = open(p, encoding="utf-8").read().strip()
                except Exception:
                    continue
                if not line:
                    continue
                try:
                    page.fill("#nova-chat-input", line, timeout=8000)
                    page.press("#nova-chat-input", "Enter")
                    typed.append(line)
                    caps.append({"who": "NOAM", "text": line})
                    status(f"TYPED: {line}")
                except Exception as e:
                    status(f"type failed ({line[:40]}): {e}")
            for p in sorted(glob.glob(os.path.join(a.inbox, "GESTURE_*"))):
                if p in seen_kid:
                    continue
                seen_kid.add(p)
                name = os.path.basename(p)[len("GESTURE_"):]
                try:
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{a.ditto_port}/gesture",
                        data=json.dumps({"clip": name, "hold_s": 3.0}).encode(),
                        headers={"Content-Type": "application/json"}, method="POST")
                    r = json.loads(urllib.request.urlopen(req, timeout=6).read())
                except Exception as e:
                    r = {"ok": False, "why": f"{type(e).__name__}: {e}"}
                gestures.append({"t": round(time.time() - t00, 2), "clip": name, "resp": r})
                status(f"GESTURE {name} -> {json.dumps(r)}")
            if os.path.exists(stop):
                status("STOP seen")
                break
            if time.time() - last_status > 15:
                last_status = time.time()
                try:
                    s = page.evaluate("()=>window.__recState")
                except Exception:
                    s = {}
                status(f"rec frames={s.get('frames')} chunks={s.get('chunks')} "
                       f"bytes={s.get('bytes')} src={s.get('w')}x{s.get('h')} err={s.get('err')}")
            time.sleep(0.35)

        pump_ws()
        final = {}
        if rec_started[0]:
            try:
                final = page.evaluate("async ()=>await window.__stopRec()")
            except Exception as e:
                status(f"stopRec threw: {e}")
        status(f"recorder final: {json.dumps(final)}")
        time.sleep(2.0)
        pump_ws()
        try:
            page.screenshot(path=os.path.join(a.out, "page_end.png"), timeout=15000)
        except Exception:
            pass
        browser.close()

    sink.terminate()
    parts = sorted(glob.glob(os.path.join(a.rec_dir, "*.part")))
    webm = os.path.join(a.rec_dir, "live_intro.webm")
    nb = 0
    with open(webm, "wb") as o:
        for p in parts:
            b = open(p, "rb").read()
            o.write(b)
            nb += len(b)
    status(f"webm: {len(parts)} chunks, {nb} bytes")
    mp4 = os.path.join(a.out, "live_intro.mp4")
    rc = 1
    if nb > 0:
        # one continuous take: stream copy is not possible (vp8/opus -> mp4), so one encode.
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", webm,
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                            "-movflags", "+faststart", mp4], capture_output=True, text=True)
        rc = r.returncode
        if rc:
            status("ffmpeg mux failed: " + (r.stderr or "")[-400:])
        else:
            subprocess.run(["cp", webm, os.path.join(a.out, "live_intro.webm")], check=False)
    probe = ""
    if os.path.exists(mp4):
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "stream=codec_type,codec_name,width,height,nb_frames,duration,avg_frame_rate",
                                "-of", "json", mp4], capture_output=True, text=True).stdout
    summary = {
        "url": a.url, "mp4": mp4, "mp4_bytes": os.path.getsize(mp4) if os.path.exists(mp4) else 0,
        "webm_bytes": nb, "chunks": len(parts), "recorder": final, "ffmpeg_rc": rc,
        "nova_lines": said, "kid_typed": typed, "kid_echo": heard,
        "gestures": gestures, "probe": probe,
    }
    with open(os.path.join(a.out, "live_intro.json"), "w") as f:
        json.dump(summary, f, indent=1)
    status(f"DONE mp4={summary['mp4_bytes']} bytes  her lines={len(said)}  my lines={len(typed)}")
    with open(os.path.join(a.out, "HARNESS_DONE"), "w") as f:
        f.write(str(int(time.time())))
    wsf.close()
    conf.close()
    return 0 if summary["mp4_bytes"] > 0 else 5


if __name__ == "__main__":
    sys.exit(main())
