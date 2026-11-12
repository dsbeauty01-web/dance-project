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


def run_A(p):
    b = F.browser(p); ctx, pg, logs = F.page_of(b)
    pg.goto(f"{BASE}/beta/freeze4?replay=frozen-body,dance-hype,still-sway&rounds=2&checked=1&facewait=40&lang=en")
    time.sleep(3)
    rec = F.recorder_start(os.path.join(OUT, "nova-final-run.mp4")); t_rec = time.time()
    time.sleep(1.5)
    pg.click("#go")
    got, marks = {}, []
    t_end = time.time() + 300
    while time.time() < t_end:
        s = pg.evaluate("""() => ({ stage: document.getElementById('novaPane').dataset.stage,
            wide: window.freeze4Wide ? window.freeze4Wide.state : null, face: window.freeze4Face ? window.freeze4Face.state : null,
            ended: document.getElementById('end').classList.contains('on'),
            started: (window.novaEvents||[]).some(e => e.event === 'round_start'),
            banner: !document.getElementById('banner').classList.contains('hidden') })""")
        t = round(time.time() - t_rec, 2)
        key = (s["stage"], (s["face"] or {}).get("badge"), s["ended"])
        if not marks or marks[-1][1] != key: marks.append([t, key])
        if s["banner"] and "banner" not in got: got["banner"] = F.shot(pg, "A-unexpected-banner.png")
        if s["stage"] == "wide" and (s["wide"] or {}).get("live") and not s["ended"] and "wide" not in got and t > 6:
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
    data = F.dump(pg, logs, "A")
    with open(os.path.join(OUT, "A-stages.json"), "w") as fh: json.dump(marks, fh)
    b.close()
    print("A recorded", round(time.time() - t_rec, 1), "s; shots", sorted(k for k in got if k != "end"), flush=True)
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
