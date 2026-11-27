#!/usr/bin/env python3
"""rig runner: the real page in Chrome against the real brain (OpenAI) + the engine stand-in. No pod.
usage: run.py <outdir> [replay=...] [echo=0.3] [say=shoulder:hi,listen:yes,game:game,end:end] [w=1280 h=720] [extra=&x=1]"""
import base64, json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); RIG = os.environ.get("HEAR_RIG_DIR", "/tmp/nova-hear-rig"); out = sys.argv[1]; os.makedirs(out, exist_ok=True)
A = dict(a.split("=", 1) for a in sys.argv[2:])
replay = A.get("replay", "frozen-body,dance-hype,still-sway"); echo = float(A.get("echo", "0"))
say = dict(x.split(":") for x in A.get("say", "" if ("ev" in A or "until" in A) else "shoulder:hi,listen:yes,game:game,end:end").split(",") if x)
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
    # NOVA-LEAD v2 scenario rig (2026-11-26): ev=STEP:mode:after[:wav];... - events fire in order, each when the page is in STEP.
    #   open = the child speaks <after> s into open microphone (her voice off) · over = he talks OVER her, <after> s after her
    #   voice starts · hit = a real shoulder lift <after> s after the check is armed. until=game stops when the game starts.
    EV = [dict(zip(("step", "mode", "after", "wav"), x.split(":") + [None])) for x in A.get("ev", "").split(";") if x]; evs = {"i": 0, "step": "", "t_step": 0, "her": False, "t_her": 0, "n": 0, "t_arm": None, "t_prev": 0, "n_prev": -1, "d_prev": 0}
    def scenario():
        q = pg.evaluate("""() => { const hv = (window.freeze4Log || []).filter(e => e.kind === 'her-voice'); return { step: (window.freeze4Lead || {}).step || '',
            her: !!hv.length && hv[hv.length - 1].detail === 'start', n: hv.filter(e => e.detail === 'start').length, arm: !!(window.freeze4Shoulder && window.freeze4Shoulder.on) }; }""")
        now = time.time()
        if q["step"] != evs["step"]: evs["step"] = q["step"]; evs["t_step"] = now; evs["n_ref"] = q["n"]; evs["t_talk"] = None
        if evs.get("t_talk") is None and q["n"] > evs.get("n_ref", 0): evs["t_talk"] = now      # her next line became audible
        if q["her"] != evs["her"]: evs["her"] = q["her"]; evs["t_her"] = now
        evs["n"] = q["n"]
        if q["arm"] and evs["t_arm"] is None: evs["t_arm"] = now
        if evs["i"] >= len(EV): return
        e = EV[evs["i"]]; aft = float(e["after"] or 0)
        if e["step"] != q["step"]: return
        if e["step"] == "" and now - t0 < aft: return          # 2026-11-27: a sound BEHIND THE CURTAIN, <after> s after the Play tap
        fire = False
        if e["mode"] == "hit": fire = q["arm"] and now - evs["t_arm"] > aft
        elif e["mode"] == "over": fire = evs.get("t_talk") is not None and now - evs["t_talk"] > aft and (q["her"] or now - evs["t_her"] < 0.5) and now - evs["t_prev"] > evs["d_prev"] + 0.5
        else:   # open: her voice off, his previous clip over, and she has answered it (or 7 s passed)
            fire = (not q["her"] and now - evs["t_her"] > aft and now - evs["t_step"] > aft and now - evs["t_prev"] > evs["d_prev"] + 0.3
                    and (evs["n"] > evs["n_prev"] or now - evs["t_prev"] > evs["d_prev"] + 7))
        if not fire: return
        evs["i"] += 1
        if e["mode"] == "hit":
            pg.evaluate("() => { window.freeze4Log.push({ t: +((performance.now() - window.freeze4T0) / 1000).toFixed(2), kind: 'rig-kid', detail: '(lifts the shoulder)' }); window.freeze4Shoulder.on && window.freeze4Shoulder.end('win'); }")
            print("KID lifts the shoulder at", round(now - t0, 2), flush=True); return
        d = pg.evaluate("([b, w]) => { window.freeze4Log.push({ t: +((performance.now() - window.freeze4T0) / 1000).toFixed(2), kind: 'rig-kid', detail: w }); return window.__kidSay(b); }", [b64(e["wav"]), e["wav"] + (" (over her)" if e["mode"] == "over" else "")])
        evs["n_ref"] = q["n"]; evs["t_talk"] = None
        evs["t_prev"] = now; evs["d_prev"] = d; evs["n_prev"] = q["n"] + (0 if e["mode"] == "over" else 0)
        print("KID says", e["wav"], "at", round(now - t0, 2), "dur", round(d, 2), "(" + e["mode"] + ", step " + e["step"] + ")", flush=True)
    def shot(n):
        if n not in got: got[n] = round(time.time() - t0, 2); pg.screenshot(path=os.path.join(out, n + ".png"))
    while time.time() - t0 < cap:
        s = pg.evaluate("""() => { const L = window.freeze4Log || [], has = (k, d) => L.find(e => e.kind === k && (d === undefined || String(e.detail).startsWith(d)));
          return { gate: document.body.dataset.gate || '', stage: document.getElementById('novaPane').dataset.stage, now: performance.now() / 1000,
            shown: (has('nova-shown') || {}).t, named: (has('v2v', 'greeting said') || {}).t, answered: (has('v2v-answer') || {}).t, chatans: (has('v2v-chat-answer') || {}).t, armed: (has('shoulder', 'armed') || {}).t, lname: (has('lead', 'step NAME') || {}).t, llight: (has('lead', 'step LIGHT') || {}).t, lgame: (has('lead', 'step GAME') || {}).t, lplayed: (L.find(e => e.kind === 'lead' && /^played out.*lift that shoulder/.test(String(e.detail))) || {}).t, listen: (has('intro-listen', 'open') || {}).t, air: (has('voice', 'air') || {}).t,
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
        # NOVA_BARGE rig: over:<wav> = the child talks OVER her answer to `chat` (0.9 s after her voice starts)
        if "over" in say and "chat" in said and "over" not in said:
            nst = pg.evaluate("() => (window.freeze4Log || []).filter(e => e.kind === 'her-voice' && e.detail === 'start').length")
            if "n_her0" not in got: got["n_her0"] = nst
            elif nst > got["n_her0"]:
                if "t_her_over" not in got: got["t_her_over"] = time.time()
                if time.time() - got["t_her_over"] > 0.9: kid("over")
        # NOVA-LEAD rig (2026-11-26): name:<wav> = his answer in NAME (omit = a silent child) · nameq:<wav> = his own question in NAME
        #   first (then name: after her answer) · light:<wav> = his question 2 s into LIGHT · hit=<s> = a real lift <s> after the
        #   LIGHT step (omit, with extra=&shrug=off = he never lifts)
        if EV or A.get("until") == "game":
            scenario()
            if s.get("lgame") is not None:
                if "t_lgame" not in got: got["t_lgame"] = time.time()
                if time.time() - got["t_lgame"] > 2.5: break
        elif s.get("lname") is not None:
            if "t_lname" not in got: got["t_lname"] = time.time()
            if "nameq" in say:
                if time.time() - got["t_lname"] > 0.5: kid("nameq")
                if "nameq" in said and time.time() - t0 - said["nameq"] > float(A.get("nameq_gap", 6.5)): kid("name")
            elif time.time() - got["t_lname"] > 0.5: kid("name")
        if s.get("llight") is not None:
            if "t_llight" not in got: got["t_llight"] = time.time()
            if "light_at" in A and time.time() - got["t_llight"] > float(A["light_at"]): kid("light")
            if "light_at" not in A and s.get("lplayed") is not None: kid("light")          # right after her light line played out (the microphone is open)
            if "hit" in A and "hit" not in got and time.time() - got["t_llight"] > float(A["hit"]):
                got["hit"] = round(time.time() - t0, 2); pg.evaluate("() => window.freeze4Shoulder.on && window.freeze4Shoulder.end('win')"); print("KID lifts the shoulder at", got["hit"], flush=True)
        if s["armed"] is not None and s.get("lname") is None:
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
    try: json.dump(pg.evaluate("() => window.__bargeDbg || []"), open(os.path.join(out, "barge.json"), "w"))
    except Exception: pass
    json.dump({"log": L, "said": said, "shots": got, "mic": mic}, open(os.path.join(out, "page.json"), "w"))
    open(os.path.join(out, "console.log"), "w").write("\n".join(logs))
    for e in L:
        if e["kind"] in ("fps", "badge", "size", "her-voice", "wide-face-track", "face-track"): continue
        print("%7.2f %-16s %s" % (e["t"], e["kind"], str(e["detail"])[:150]))
    if EV or A.get("until") == "game":
        # THE TRANSCRIPT: who said what, in page seconds (t = 0 at page load); then time to game + the backups used
        g = next((e for e in L if e["kind"] == "lead" and str(e["detail"]).startswith("step GAME")), None); gr = next((e for e in L if e["kind"] == "line"), None)
        print("\n=== TRANSCRIPT " + A.get("name", "") + " ===")
        who = {"rig-kid": "CHILD  (audio)", "lead-kid": "CHILD  (heard)", "lead-her": "NOVA   (said) ", "line": "NOVA   (asked)", "shoulder": "LIGHT         "}
        for e in L:
            d = str(e["detail"])
            if e["kind"] in who: print("%6.1f  %s  %s" % (e["t"], who[e["kind"]], d[:170]))
            elif e["kind"] == "lead" and d.startswith(("step ", "backup", "done", "light armed", "she heard", "reveal")): print("%6.1f  PAGE            %s" % (e["t"], d[:170]))
        bk = [str(e["detail"])[8:] for e in L if e["kind"] == "lead" and str(e["detail"]).startswith("backup: ")]
        print("TIME TO GAME: %s s after the greeting was asked | backups used (%d): %s\n" % (("%.1f" % (g["t"] - gr["t"])) if g and gr else "NOT REACHED", len(bk), " · ".join(bk) or "none"))
    print("kid said (s after Play):", said, "| shots", {k: v for k, v in got.items() if not k.startswith("t_")}, "| mic", mic)
    br.close()
finally:
    brain.terminate(); eng.terminate()
