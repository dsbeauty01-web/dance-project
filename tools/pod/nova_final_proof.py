#!/usr/bin/env python3
"""tools/pod/nova_final_proof.py — runs ON THE POD (NOVA-FINAL, 2026-11-12): the real run of Refael's approved spec.

  A  beta/freeze4.html in a real Chrome on the virtual screen, the child = a replayed recording (test/clips), recorded with
     sound: INTRO = she talks WIDE (her live Ditto body in her room) -> the music starts -> GAME = her clips + the small SoulX
     face PiP top-left inside her room -> ENDING = WIDE again. Screenshots of each stage. Writes $OUT/nova-final-run.mp4.

Reuses tools/pod/freeze4_proof.py (browser, probes, recorder) unchanged. Never reads or prints a key.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freeze4_proof as F                                               # noqa: E402

BASE, OUT = F.BASE, F.OUT
KID_WAV = os.environ.get("KID_WAV", "/root/kid_line.wav")

# READY GATE proof (2026-11-22). The page now asks for camera + microphone first; Chrome's fake devices answer that
# question for real. The proof's "child" must also be able to SAY something at a chosen moment (Refael's own line, "Hi
# Nova, can you hear me?"), which a looping fake-microphone file cannot do. So for the microphone only, after the real
# getUserMedia has succeeded, the page is handed a stream the proof can play a recording into (window.__kidSay). From
# there on it is the page's real path: bridge mic -> brain -> its recogniser -> the live "You: ..." line -> her answer.
# The recording is also played to the speakers so the proof video has his question in it.
KIDMIC = r"""
(() => {
  const md = navigator.mediaDevices; if (!md || !md.getUserMedia) return;
  const real = md.getUserMedia.bind(md); let ctx = null, dest = null;
  const ensure = () => { if (!ctx) { ctx = new AudioContext(); dest = ctx.createMediaStreamDestination(); } return dest; };
  window.__kidMic = { asked: [], given: 0, said: 0 };
  md.getUserMedia = async (c) => {
    window.__kidMic.asked.push(JSON.stringify(c).slice(0, 80));
    const s = await real(c);                                   // the real permission path (fake devices) still runs
    if (c && c.audio && !c.video) { s.getTracks().forEach(t => t.stop()); window.__kidMic.given++; return ensure().stream; }
    return s;
  };
  window.__kidSay = async (b64) => {
    ensure(); if (ctx.state === 'suspended') await ctx.resume();
    const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    const buf = await ctx.decodeAudioData(u.buffer), n = ctx.createBufferSource();
    n.buffer = buf; n.connect(dest); n.connect(ctx.destination); n.start(); window.__kidMic.said++; return buf.duration;
  };
})();
"""


def run_A(p):
    b = F.browser(p); ctx, pg, logs = F.page_of(b)
    ctx.add_init_script(KIDMIC)
    kid_b64 = None
    if os.path.exists(KID_WAV) and os.path.getsize(KID_WAV) > 2000:
        import base64
        with open(KID_WAV, "rb") as fh: kid_b64 = base64.b64encode(fh.read()).decode()
    print("kid line:", KID_WAV, "bytes", os.path.getsize(KID_WAV) if os.path.exists(KID_WAV) else None, flush=True)
    pg.goto(f"{BASE}/beta/freeze4?replay=frozen-body,dance-hype,still-sway&rounds=2&checked=1&facewait=40&lang=en")
    time.sleep(3)
    rec = F.recorder_start(os.path.join(OUT, "nova-final-run.mp4")); t_rec = time.time()
    time.sleep(1.5)
    pg.click("#go")
    got, marks, under = {}, [], []
    t_end = time.time() + 300
    while time.time() < t_end:
        s = pg.evaluate("""() => ({ stage: document.getElementById('novaPane').dataset.stage, gate: document.body.dataset.gate || '',
            you: (document.getElementById('you') || {}).className || '', youText: (document.getElementById('you') || {}).textContent || '',
            listen: (window.freeze4Log || []).some(e => e.kind === 'intro-listen' && e.detail === 'open'),
            answered: (window.freeze4Log || []).some(e => e.kind === 'intro-answer'),
            wide: window.freeze4Wide ? window.freeze4Wide.state : null, face: window.freeze4Face ? window.freeze4Face.state : null,
            ended: document.getElementById('end').classList.contains('on'),
            started: (window.novaEvents||[]).some(e => e.event === 'round_start'),
            banner: !document.getElementById('banner').classList.contains('hidden') })""")
        t = round(time.time() - t_rec, 2)
        key = (s["gate"] or "open", s["stage"], (s["face"] or {}).get("badge"), s["ended"])
        if not marks or marks[-1][1] != key:
            marks.append([t, key])
            # STUTTER GUARD: the face server's own counters at every stage change, so a late chunk / an underrun (a held
            # frame + 0.16 s of silence) can be placed: at a face switch, or inside her speech
            try:
                import urllib.request
                fs = json.loads(urllib.request.urlopen(F.FACE + "/", timeout=1.5).read())
                under.append([t, key[0] + "/" + str(key[1]) + "/" + str(key[2]), fs.get("underruns"), fs.get("wide_chunks_late"), fs.get("wide_chunks"), fs.get("mode")])
            except Exception as e: under.append([t, "?", str(e)[:40]])
        # the READY GATE, in order: his own picture (Nova not connected) -> Nova live but still hidden -> she appears talking
        if s["gate"] == "cam" and "own" not in got: time.sleep(0.5); got["own"] = F.shot(pg, "A-0a-own-camera-first.png")
        if s["gate"] == "nova" and "hidden" not in got and ((s["wide"] or {}).get("live") or "t_nova" in got and time.time() - got["t_nova"] > 1.5):
            got["hidden"] = F.shot(pg, "A-0b-nova-live-but-hidden.png")
        if s["gate"] == "nova" and "t_nova" not in got: got["t_nova"] = time.time()
        if not s["gate"] and "t_open" not in got and "t_nova" in got:
            got["t_open"] = time.time(); got["shown"] = F.shot(pg, "A-0c-nova-appears.png")
        # the child's line, said once, the moment the page starts listening after her intro
        if s["listen"] and kid_b64 and "kidsaid" not in got:
            got["kidsaid"] = round(pg.evaluate("b => window.__kidSay(b)", kid_b64), 2); print("kid said at", t, "dur", got["kidsaid"], flush=True)
        if "final" in s["you"] and "youtext" not in got: got["youtext"] = F.shot(pg, "A-1b-you-text.png"); print("you text:", s["youText"], flush=True)
        if s["answered"] and "answer" not in got: got["answer"] = F.shot(pg, "A-1c-after-her-answer.png")
        if s["banner"] and "banner" not in got: got["banner"] = F.shot(pg, "A-unexpected-banner.png")
        if s["stage"] == "wide" and (s["wide"] or {}).get("live") and not s["ended"] and "wide" not in got and "t_open" in got and time.time() - got["t_open"] > 1.5:
            got["wide"] = F.shot(pg, "A-1-intro-wide-ditto.png")
        if s["stage"] == "game" and s["started"] and (s["face"] or {}).get("live") and "pip" not in got:
            got["pip"] = F.shot(pg, "A-2-game-pip-face.png")
        if s["stage"] == "game" and (s["face"] or {}).get("badge") == "talking" and "piptalk" not in got:
            got["piptalk"] = F.shot(pg, "A-3-game-pip-talking.png")
        if (s["face"] or {}).get("badge") == "freeze" and "freeze" not in got:
            time.sleep(0.8); got["freeze"] = F.shot(pg, "A-4-freeze-hold.png")
        if s["ended"] and "end" not in got: got["end"] = time.time()
        if s["ended"] and s["stage"] == "wide" and time.time() - got["end"] > 5 and "endwide" not in got:
            got["endwide"] = F.shot(pg, "A-5-ending-wide.png")
        if s["ended"] and time.time() - got["end"] > 18: break
        time.sleep(0.15)
    F.shot(pg, "A-6-after.png")
    F.recorder_stop(rec)
    try: print("kid mic:", json.dumps(pg.evaluate("() => window.__kidMic")), flush=True)
    except Exception as e: print("kid mic: ?", e, flush=True)
    data = F.dump(pg, logs, "A")
    with open(os.path.join(OUT, "A-stages.json"), "w") as fh: json.dump(marks, fh)
    with open(os.path.join(OUT, "A-underruns.json"), "w") as fh: json.dump(under, fh)
    print("underruns [t, gate/stage/badge, underruns, late, chunks, mode]", json.dumps(under)[:3000], flush=True)
    b.close()
    print("A recorded", round(time.time() - t_rec, 1), "s; shots", sorted(k for k in got if k not in ("end", "t_nova", "t_open", "kidsaid")), flush=True)
    print("stages", json.dumps(marks)[:1500], flush=True)
    return data


def browser_cam(p, cam_file):
    """F.browser + the child's camera = a video file (Chrome fake capture), for the MoveNet games (getUserMedia, no ?replay=)"""
    import tempfile
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="nfchrome-"), executable_path=F.CHROME, headless=False,
        no_viewport=True, permissions=["microphone", "camera"], args=[
        "--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
        f"--use-file-for-fake-audio-capture={F.SILENCE}", f"--use-file-for-fake-video-capture={cam_file}",
        f"--window-size={F.W},{F.H}", "--window-position=0,0", "--kiosk",
        "--no-first-run", "--disable-infobars", "--password-store=basic", "--no-sandbox", "--noerrdialogs"])
    return F._B(ctx)


GAMES = {   # game -> (page url, start button, recording cap s)
    "wave": ("/beta/wave?lang=en", "#start", 150), "upperbody": ("/beta/upperbody?lang=en", "#start", 150),
    "novasays": ("/beta/novasays?lang=en&auto=40", "#start", 95), "upgroove": ("/upgroove?lang=en", "#start-btn", 95)}


def run_G(p, game, cam_file, cap_s=None):
    """one short proof per game: start -> she talks WIDE (intro) -> the game with the PiP face -> first between/ending"""
    b = browser_cam(p, cam_file); ctx, pg, logs = F.page_of(b)
    url, btn, cap0 = GAMES[game]; cap_s = cap_s or cap0
    pg.goto(f"{BASE}{url}")
    time.sleep(3)
    rec = F.recorder_start(os.path.join(OUT, f"nova-final-{game}.mp4")); t_rec = time.time()
    time.sleep(1.0); pg.click(btn)
    got, marks, t_end = {}, [], time.time() + cap_s
    while time.time() < t_end:
        s = pg.evaluate("""() => { const L = window.novaLive; const pane = document.querySelector('[data-nova-stage]');
            return { stage: pane ? pane.dataset.novaStage : null, wide: L ? L.wide.state.live : null, face: L ? L.face.state : null,
              card: !!(document.getElementById('card') && !document.getElementById('card').classList.contains('hidden')),
              score: (document.getElementById('scorecard') || {}).style ? document.getElementById('scorecard').style.display === 'flex' : false,
              banner: !!(document.getElementById('banner') && !document.getElementById('banner').classList.contains('hidden')) }; }""")
        t = round(time.time() - t_rec, 2); key = (s["stage"], (s["face"] or {}).get("badge"), s["card"], s["score"])
        if not marks or marks[-1][1] != list(key): marks.append([t, list(key)])
        if s["banner"] and "banner" not in got: got["banner"] = F.shot(pg, f"{game}-unexpected-banner.png")
        if s["stage"] == "wide" and s["wide"] and "wide" not in got and t > 5: got["wide"] = F.shot(pg, f"{game}-1-intro-wide-ditto.png")
        if s["stage"] == "game" and (s["face"] or {}).get("live") and "pip" not in got:
            time.sleep(1.5); got["pip"] = F.shot(pg, f"{game}-2-game-pip-face.png")
        if (s["card"] or s["score"]) and "end" not in got: got["end"] = time.time()
        if "end" in got and time.time() - got["end"] > (20 if game == "upperbody" else 12):
            F.shot(pg, f"{game}-3-after-round.png"); break
        time.sleep(0.2)
    F.recorder_stop(rec)
    data = pg.evaluate("() => ({ live: window.novaLiveLog || [] })")
    with open(os.path.join(OUT, f"{game}-page.json"), "w") as fh: json.dump({"live": data["live"], "stages": marks}, fh)
    with open(os.path.join(OUT, f"{game}-console.log"), "w") as fh: fh.write("\n".join(logs) + "\n")
    b.close()
    print(game, "recorded", round(time.time() - t_rec, 1), "s; shots", sorted(k for k in got if k != "end"), flush=True)
    print("stages", json.dumps(marks)[:1500], flush=True)


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        if sys.argv[1] == "A": run_A(p)
        else: run_G(p, sys.argv[1], sys.argv[2])
