#!/usr/bin/env python3
"""tools/pod/freeze4_proof.py — runs ON THE POD: beta/freeze4.html in a real (headed) Chrome on a virtual screen, the
child = a replayed recording (test/clips), recorded with sound by ffmpeg (x11grab + PulseAudio), plus two probes in the
page sampled on every animation frame:
  · her voice level  = the bridge's analyser on the audio that is actually playing (window.__novaVoiceAnalyser)
  · her mouth motion = mean frame-to-frame change of the mouth area of the face video element (#face)
From those: how long after her voice starts the face's mouth starts moving, and a cross-correlation lag.

  python freeze4_proof.py B   → no face server yet: the red banner (screenshot)
  python freeze4_proof.py A   → the full game, recorded (the deliverable mp4), screenshots small / big / freeze / end
  python freeze4_proof.py C   → the face stream stops mid-game (face server /pause): the panel turns red
Writes to $OUT (default /root/out). Never reads or prints a key.
"""
import json, os, subprocess, sys, time, base64, signal

BASE = os.environ.get("BASE", "http://127.0.0.1:8765")
FACE = os.environ.get("FACE_URL", "http://127.0.0.1:8010")
OUT = os.environ.get("OUT", "/root/out")
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
SILENCE = os.environ.get("SILENCE_WAV", "/root/silence.wav")
W, H = 1280, 720
os.makedirs(OUT, exist_ok=True)

PROBE = r"""
(() => {
  const P = window.__probe = { t: [], v: [], m: [], badge: [], size: [] };
  let cv = null, cx = null, prev = null;
  const step = () => {
    try {
      const t = performance.now();
      let v = 0; const an = window.__novaVoiceAnalyser;
      if (an) { const b = new Float32Array(an.fftSize); an.getFloatTimeDomainData(b); let s = 0; for (let i = 0; i < b.length; i++) s += b[i] * b[i]; v = Math.sqrt(s / b.length); }
      let m = 0; const f = document.getElementById('face');
      if (f && f.videoWidth) {
        if (!cv) { cv = document.createElement('canvas'); cv.width = 96; cv.height = 96; cx = cv.getContext('2d', { willReadFrequently: true }); }
        cx.drawImage(f, 0, 0, 96, 96);
        const d = cx.getImageData(29, 53, 38, 29).data;          // mouth box: x 30-70 %, y 55-85 % of the face tile
        if (prev) { let s = 0; for (let i = 0; i < d.length; i += 4) s += Math.abs(d[i] - prev[i]) + Math.abs(d[i + 1] - prev[i + 1]) + Math.abs(d[i + 2] - prev[i + 2]); m = s / (d.length / 4 * 3); }
        prev = d.slice();
      }
      if (P.t.length < 60 * 60 * 8) { P.t.push(+t.toFixed(1)); P.v.push(+v.toFixed(4)); P.m.push(+m.toFixed(3));
        const st = window.freeze4Face && window.freeze4Face.state; P.badge.push(st ? st.badge : ''); P.size.push(st ? st.size : ''); }
    } catch (e) {}
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
})();
"""


def browser(p):
    return p.chromium.launch(executable_path=CHROME, headless=False, args=[
        "--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
        f"--use-file-for-fake-audio-capture={SILENCE}", f"--window-size={W},{H}", "--window-position=0,0", "--kiosk",
        "--no-first-run", "--disable-infobars", "--password-store=basic", "--no-sandbox"])


def page_of(b):
    ctx = b.new_context(viewport={"width": W, "height": H}, no_viewport=False, permissions=["microphone", "camera"])
    pg = ctx.new_page(); logs = []
    pg.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
    pg.on("pageerror", lambda e: logs.append(f"[pageerror] {e}"))
    pg.add_init_script(PROBE)
    return ctx, pg, logs


def shot(pg, name):
    p = os.path.join(OUT, name); pg.screenshot(path=p); print("shot", p, flush=True); return p


def face_png(pg, name):
    """the face video's own frame at its native size, as the browser received it (for the sharpness comparison)"""
    url = pg.evaluate("""() => { const f = document.getElementById('face'); if (!f || !f.videoWidth) return null;
      const c = document.createElement('canvas'); c.width = f.videoWidth; c.height = f.videoHeight; c.getContext('2d').drawImage(f, 0, 0); return c.toDataURL('image/png'); }""")
    if url:
        with open(os.path.join(OUT, name), "wb") as fh: fh.write(base64.b64decode(url.split(",", 1)[1]))
    return bool(url)


def dump(pg, logs, tag):
    data = pg.evaluate("() => ({ log: window.freeze4Log || [], brain: window.novaBrainLog || [], events: window.novaEvents || [], probe: window.__probe || null })")
    with open(os.path.join(OUT, f"{tag}-page.json"), "w") as fh: json.dump(data, fh)
    with open(os.path.join(OUT, f"{tag}-console.log"), "w") as fh: fh.write("\n".join(logs) + "\n")
    return data


def recorder_start(path):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", f"{W}x{H}", "-framerate", "25", "-i", os.environ.get("DISPLAY", ":99"),
           "-f", "pulse", "-i", os.environ.get("PULSE_MONITOR", "rec.monitor"),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def recorder_stop(p):
    try: p.stdin.write(b"q"); p.stdin.flush(); p.wait(30)
    except Exception: p.send_signal(signal.SIGINT); p.wait(30)


def run_B(p):
    b = browser(p); ctx, pg, logs = page_of(b)
    pg.goto(f"{BASE}/beta/freeze4?replay=frozen-body&rounds=2&checked=1&autostart=1&facewait=8&lang=en")
    pg.wait_for_function("() => !document.getElementById('banner').classList.contains('hidden')", timeout=40000)
    time.sleep(1); shot(pg, "B-red-banner-no-face.png")
    txt = pg.evaluate("() => document.getElementById('banner').innerText")
    ev = pg.evaluate("() => (window.novaEvents || []).length")
    dump(pg, logs, "B"); b.close()
    res = {"banner": txt, "game_events": ev}
    print("B", json.dumps(res), flush=True); return res


def run_A(p):
    b = browser(p); ctx, pg, logs = page_of(b)
    pg.goto(f"{BASE}/beta/freeze4?replay=frozen-body,dance-hype,still-sway&rounds=3&checked=1&lang=en")
    time.sleep(3)
    rec = recorder_start(os.path.join(OUT, "freeze4-live-soulx.mp4")); t_rec = time.time()
    time.sleep(1.5)
    pg.click("#go")
    got = {}
    def poll(until_s):
        t_end = time.time() + until_s
        while time.time() < t_end:
            st = pg.evaluate("() => window.freeze4Face ? window.freeze4Face.state : null") or {}
            ended = pg.evaluate("() => document.getElementById('end').classList.contains('on')")
            banner = pg.evaluate("() => !document.getElementById('banner').classList.contains('hidden')")
            if banner and "banner" not in got: got["banner"] = shot(pg, "A-unexpected-banner.png")
            if st.get("badge") == "talking" and "big" not in got:
                time.sleep(0.7); got["big"] = shot(pg, "A-1-talking-panel-big.png"); face_png(pg, "A-face-received-1.png")
            if st.get("badge") == "talking" and "big" in got and "big2" not in got and time.time() - got.setdefault("_tb", time.time()) > 20:
                got["big2"] = shot(pg, "A-4-talking-in-game.png"); face_png(pg, "A-face-received-2.png")
            if st.get("badge") == "watching" and st.get("size") == "small" and "small" not in got and pg.evaluate("() => (window.novaEvents||[]).some(e => e.event === 'round_start')"):
                time.sleep(0.7); got["small"] = shot(pg, "A-2-dance-panel-small.png")
            if st.get("badge") == "freeze" and "freeze" not in got:
                time.sleep(0.8); got["freeze"] = shot(pg, "A-3-freeze-hold.png")
            if ended and "end" not in got: got["end_t"] = time.time(); got["end"] = True
            if got.get("end") and time.time() - got["end_t"] > 13:
                break
            time.sleep(0.15)
    poll(240)
    shot(pg, "A-5-ending.png"); face_png(pg, "A-face-received-3.png")
    recorder_stop(rec)
    data = dump(pg, logs, "A"); b.close()
    print("A recorded", round(time.time() - t_rec, 1), "s; shots", sorted(k for k in got if not k.startswith("_")), flush=True)
    return data


def run_C(p):
    import urllib.request
    b = browser(p); ctx, pg, logs = page_of(b)
    pg.goto(f"{BASE}/beta/freeze4?replay=frozen-body,dance-hype&rounds=2&checked=1&autostart=1&fast=1&lang=en")
    pg.wait_for_function("() => (window.novaEvents||[]).some(e => e.event === 'round_start')", timeout=90000)
    t0 = time.time()
    urllib.request.urlopen(urllib.request.Request(FACE + "/pause?s=7", method="POST"), timeout=5).read()
    pg.wait_for_function("() => !document.getElementById('faceBanner').hidden", timeout=15000, polling=50)
    took = round((time.time() - t0) * 1000); shot(pg, "C-face-stream-lost.png")
    pg.wait_for_function("() => document.getElementById('faceBanner').hidden", timeout=20000, polling=50)
    back = round((time.time() - t0) * 1000)
    dump(pg, logs, "C"); b.close()
    res = {"red_after_ms": took, "cleared_after_ms": back}
    print("C", json.dumps(res), flush=True); return res


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    which = sys.argv[1]
    with sync_playwright() as p:
        r = {"A": run_A, "B": run_B, "C": run_C}[which](p)
    if which != "A":
        with open(os.path.join(OUT, f"{which}-result.json"), "w") as fh: json.dump(r, fh)
