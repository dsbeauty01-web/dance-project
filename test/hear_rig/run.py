#!/usr/bin/env python3
"""rig runner: the real page in Chrome against the real brain (OpenAI) + the engine stand-in. No pod.
usage: run.py <outdir> [replay=...] [echo=0.3] [say=shoulder:hi,listen:yes,game:game,end:end] [w=1280 h=720] [extra=&x=1]"""
import base64, json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); RIG = os.environ.get("HEAR_RIG_DIR", "/tmp/nova-hear-rig"); out = sys.argv[1]; os.makedirs(out, exist_ok=True)
A = dict(a.split("=", 1) for a in sys.argv[2:])
replay = A.get("replay", "frozen-body,dance-hype,still-sway"); echo = float(A.get("echo", "0"))
say = dict(x.split(":") for x in A.get("say", "shoulder:hi,listen:yes,game:game,end:end").split(",") if x)
W, H = int(A.get("w", 1280)), int(A.get("h", 720)); extra = A.get("extra", ""); cap = float(A.get("cap", 200))
env = dict(os.environ); env.update({k: v for k, v in A.items() if k.isupper()})
eng = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "engine_stub.py")], stdout=open(os.path.join(out, "engine.log"), "w"), stderr=subprocess.STDOUT)
brain = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "brain_rig.py")], stdout=open(os.path.join(out, "rtlk.log"), "w"), stderr=subprocess.STDOUT, env=env)
time.sleep(4)
b64 = lambda k: base64.b64encode(open(os.path.join(RIG, "kid", k + ".wav"), "rb").read()).decode()
try:
  with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream", "--no-sandbox", "--no-proxy-server", "--mute-audio", f"--window-size={W},{H}"])
    ctx = br.new_context(viewport={"width": W, "height": H}, permissions=["camera", "microphone"])
    ctx.route("**/livekit-client*", lambda r: r.fulfill(status=200, content_type="application/javascript", body=open(os.path.join(HERE, "lk_shim.js")).read()))
    ctx.add_init_script(f"window.__RIG_ECHO = {echo};"); ctx.add_init_script(open(os.path.join(HERE, "kidmic.js")).read())
    pg = ctx.new_page(); logs = []; pg.on("console", lambda m: logs.append(m.text)); pg.on("pageerror", lambda e: logs.append("PAGEERROR " + str(e)))
    pg.goto(f"http://127.0.0.1:8765/beta/freeze4?replay={replay}&rounds=2&checked=1&facewait=40&lang={A.get("lang","en")}{extra}")
    time.sleep(2); pg.screenshot(path=os.path.join(out, "0-start.png")); pg.click("#go"); t0 = time.time(); got = {}; said = {}
    def kid(tag):
        if tag in say and tag not in said:
            said[tag] = round(time.time() - t0, 2); d = pg.evaluate("b => window.__kidSay(b)", b64(say[tag])); print("KID says", say[tag], "at", said[tag], "dur", round(d, 2), flush=True)
    def shot(n):
        if n not in got: got[n] = round(time.time() - t0, 2); pg.screenshot(path=os.path.join(out, n + ".png"))
    while time.time() - t0 < cap:
        s = pg.evaluate("""() => { const L = window.freeze4Log || [], has = (k, d) => L.find(e => e.kind === k && (d === undefined || String(e.detail).startsWith(d)));
          return { gate: document.body.dataset.gate || '', stage: document.getElementById('novaPane').dataset.stage, now: performance.now() / 1000,
            shown: (has('nova-shown') || {}).t, named: (has('v2v', 'greeting said') || {}).t, answered: (has('v2v-answer') || {}).t, chatans: (has('v2v-chat-answer') || {}).t, armed: (has('shoulder', 'armed') || {}).t, listen: (has('intro-listen', 'open') || {}).t, air: (has('voice', 'air') || {}).t,
            lines: L.filter(e => e.kind === 'line').length, herQuiet: (() => { const h = L.filter(e => e.kind === 'her-voice' || e.kind === 'line').slice(-1)[0]; return !h || (h.kind === 'her-voice' && h.detail === 'end' && L[L.length - 1].t - h.t > 3.5); })(), ended: document.getElementById('end').classList.contains('on'), banner: !document.getElementById('banner').classList.contains('hidden'),
            t: L.length ? L[L.length - 1].t : 0, T0: (performance.now() / 1000) - (L.length ? 0 : 0) }; }""")
        # page-log time of "now": freeze4Log t = (performance.now() - T0page)/1000; the page exposes no T0, so use deltas from event times via a probe
        if s["gate"] == "perm": shot("1-gate-perm")
        if s["gate"] == "cam": shot("2-gate-cam")
        if s["gate"] == "nova" and "t_nova" not in got: got["t_nova"] = time.time()
        if s["gate"] == "nova" and time.time() - got.get("t_nova", 1e18) > 2.5: shot("3-gate-nova")
        if s["shown"] is not None:
            if "t_shown" not in got: got["t_shown"] = time.time()
            if time.time() - got["t_shown"] > 1.5: shot("4-intro"); kid("talking")
        if s.get("named") is not None:                     # NOVA-GO5: her name question is over - the child answers it
            if "t_named" not in got: got["t_named"] = time.time()
            if time.time() - got["t_named"] > 0.8: kid("name")
        # NOVA-LIVE2: chat:<wav> = his line after her answer to the name; chat2:<wav> after her answer to that
        if s.get("answered") is not None:
            if "t_ans" not in got: got["t_ans"] = time.time()
            if time.time() - got["t_ans"] > 1.5: kid("chat")
        if s.get("chatans") is not None:
            if "t_chatans" not in got: got["t_chatans"] = time.time()
            # rig fix 2026-11-26: chat2 only after chat was said AND answered (run c1: both wavs played at once)
            if "chat" in said and time.time() - t0 - said["chat"] > 14.0 and time.time() - got["t_chatans"] > 1.5: kid("chat2")
        if s["armed"] is not None:
            if "t_armed" not in got: got["t_armed"] = time.time()
            if time.time() - got["t_armed"] > 1.0: kid("shoulder")
        if s["listen"] is not None: kid("listen")
        if s["air"] is not None:
            if "t_air" not in got: got["t_air"] = time.time()
            if time.time() - got["t_air"] > 0.3: kid("game")
            if time.time() - got["t_air"] > 3.0: shot("5-game")
        if s["ended"]:
            if "t_end" not in got: got["t_end"] = time.time()
            if time.time() - got["t_end"] > 11 and s["herQuiet"]: kid("end"); got.setdefault("t_kidend", time.time())
            if time.time() - got["t_end"] > 14: shot("6-ending")
            if time.time() - got.get("t_kidend", 1e18) > 13 or time.time() - got["t_end"] > 45: break
        if s["banner"]: shot("X-banner"); time.sleep(1); break
        time.sleep(0.1)
    L = pg.evaluate("() => window.freeze4Log || []"); mic = pg.evaluate("() => ({ kid: window.__kidMic, her: (window.__rigHer || []).length })")
    json.dump({"log": L, "said": said, "shots": got, "mic": mic}, open(os.path.join(out, "page.json"), "w"))
    open(os.path.join(out, "console.log"), "w").write("\n".join(logs))
    for e in L:
        if e["kind"] in ("fps", "badge", "size", "her-voice", "wide-face-track", "face-track"): continue
        print("%7.2f %-16s %s" % (e["t"], e["kind"], str(e["detail"])[:150]))
    print("kid said (s after Play):", said, "| shots", {k: v for k, v in got.items() if not k.startswith("t_")}, "| mic", mic)
    br.close()
finally:
    brain.terminate(); eng.terminate()
