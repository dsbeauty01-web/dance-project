#!/usr/bin/env python3
"""live_intro_driver.py -- uploaded OVER /root/in/live_intro_harness.py so the running job's
stage D3 executes this instead, with the real harness alongside as real_harness.py.

Why: stage D1 of novafix_job2.sh had already decided the face engine and started boot.sh
before two facts were known.

  1. The bridge probe returned rc=2 and the job fell back to MuseTalk -- but the file it
     probed is md5 e9be0f4fa9560bff522e95687b093cde, which is exactly what attempt 1's
     --apply PRODUCED (1c4448b4... -> e9be0f4f...). A3 counts 0 because the patch already
     consumed that line; A1/A2/A4 still count 1 because the patch inserts AROUND them.
     The bridge is correctly patched, so NOVA_FACE=ditto is available and honest here.
  2. More sourceless packages were missing than stage R's target list reached (edge_tts,
     and the volume's own vendored pip), so :8765 never came up.

So this driver, in order: finish the repair, restart the stack with NOVA_FACE=ditto only if
the bridge really is the patched file, prove what the page serves, then hand off to the
untouched harness with the same arguments. It records nothing itself.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

IN = "/root/in"
OUT = "/root/novafix_out"
DP = "/workspace/_sys/pylibs311_good/dist-packages"
PATCHED_MD5 = "e9be0f4fa9560bff522e95687b093cde"   # what attempt 1's --apply produced
T0 = time.time()


def say(s):
    line = f"[driver {time.strftime('%H:%M:%S', time.gmtime())}] {s}"
    print(line, flush=True)
    with open(os.path.join(OUT, "DRIVER"), "a") as f:
        f.write(line + "\n")


def http(path, port=8765, timeout=8):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            return r.status, r.read()
    except Exception as e:
        return None, str(e).encode()


def md5(p):
    r = subprocess.run(["md5sum", p], capture_output=True, text=True)
    return r.stdout.split()[0] if r.returncode == 0 else "-"


# ---------------------------------------------------------------- 1. finish the repair
def repair():
    targets = ("flask,livekit.api,livekit.rtc,aiohttp,requests,numpy,edge_tts,"
               "pip,websockets,soundfile,av")
    say(f"repair round 2, targets: {targets}")
    r = subprocess.run([sys.executable, "-I", os.path.join(IN, "repair_pylibs.py"),
                        "--dist-packages", DP, "--repair", "--targets", targets,
                        "--rounds", "20", "--report", os.path.join(OUT, "pylibs_repair2.json")],
                       capture_output=True, text=True, timeout=1500)
    with open(os.path.join(OUT, "pylibs_repair2.txt"), "w") as f:
        f.write(r.stdout + r.stderr)
    for ln in (r.stdout or "").splitlines():
        say("  " + ln)
    # independent proof, with the REAL PYTHONPATH the stack uses
    env = dict(os.environ)
    env["PYTHONPATH"] = DP
    proof = {}
    for m in ("flask", "livekit.api", "livekit.rtc", "aiohttp", "edge_tts", "numpy"):
        p = subprocess.run([sys.executable, "-c", f"import {m};print('OK')"],
                           capture_output=True, text=True, env=env, timeout=180)
        proof[m] = "OK" if p.returncode == 0 else (p.stderr or "").strip().splitlines()[-1:]
        say(f"  import {m}: {proof[m]}")
    json.dump(proof, open(os.path.join(OUT, "imports_after_repair2.json"), "w"), indent=1)
    return proof


# ---------------------------------------------------------------- 2. restart the stack
def restart_stack():
    face = "musetalk"
    cur = md5("/workspace/lk_bridge.py")
    if cur == PATCHED_MD5:
        face = "ditto"
        say(f"lk_bridge.py md5 {cur} == attempt 1's applied patch -> NOVA_FACE=ditto")
    else:
        say(f"lk_bridge.py md5 {cur} is NOT the patched file -> staying on MuseTalk")
    s, _ = http("/health", 8031)
    if face == "ditto" and s != 200:
        face = "musetalk"
        say("Ditto on :8031 does not answer -> MuseTalk (no silent fallbacks: this is stated)")
    with open(os.path.join(OUT, "FACE"), "w") as f:
        f.write(face)

    # LAW-PODS-8-BRACKET: every pattern is bracketed so it cannot match this script itself
    for pat in ("[r]t_lk.py", "[l]k_bridge.py", "[b]oot.sh"):
        subprocess.run(f"pkill -f '{pat}'", shell=True, capture_output=True)
    time.sleep(3)

    env = dict(os.environ)
    env["NOVA_DEPLOY_BRANCH"] = "nova-ditto"
    env["NOVA_DITTO_DELAY_SITE"] = "bridge"
    if face == "ditto":
        env["NOVA_FACE"] = "ditto"
    else:
        env.pop("NOVA_FACE", None)
    env.pop("PYTHONPATH", None)          # boot.sh sets its own
    say(f"boot.sh restarting with NOVA_FACE={env.get('NOVA_FACE', '(unset)')}")
    with open(os.path.join(OUT, "bootwrap2.log"), "wb") as lg:
        subprocess.Popen(["setsid", "bash", "/workspace/boot.sh"], stdout=lg, stderr=lg,
                         stdin=subprocess.DEVNULL, env=env, start_new_session=True)
    for i in range(96):                  # 8 min
        s, _ = http("/")
        if s == 200:
            say(f"BRAIN_UP after {i * 5}s")
            return face, True
        if i and i % 12 == 0:
            miss = subprocess.run(
                "grep -hoE \"No module named '[^']+'\" /root/boot.log /root/bridge.log "
                "/root/rtlk.log /root/app.log 2>/dev/null | sort -u | head -6",
                shell=True, capture_output=True, text=True).stdout.strip()
            say(f"  {i * 5}s... still missing: {miss or '(nothing)'}")
        time.sleep(5)
    say("BRAIN NEVER CAME UP in 8 min")
    return face, False


def page_proof():
    rows = []
    for p in ("/beta/freeze?intro=freeze", "/freeze?intro=freeze", "/", "/health"):
        s, b = http(p, timeout=15)
        jt = b.count(b"JUDGE-TRUTH") if isinstance(b, bytes) else 0
        rows.append(f"{p:<28} http={s}  {len(b)} bytes  JUDGE-TRUTH={jt}")
        say("  " + rows[-1])
        if p.startswith("/beta/freeze") and s == 200 and b:
            with open(os.path.join(OUT, "freeze.served.html"), "wb") as f:
                f.write(b)
    with open(os.path.join(OUT, "page_probe2.txt"), "w") as f:
        f.write("\n".join(rows) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    say("start")
    s, _ = http("/")
    if s == 200:
        say("the brain is already serving -- skipping repair and restart")
        face = open(os.path.join(OUT, "FACE")).read().strip() if os.path.exists(os.path.join(OUT, "FACE")) else "?"
        up = True
    else:
        repair()
        face, up = restart_stack()
    page_proof()
    if not up:
        say("no stack -> nothing to record. Not pretending otherwise.")
        return 7
    real = os.path.join(IN, "real_harness.py")
    if not os.path.exists(real):
        say("real_harness.py missing -- cannot record")
        return 8
    say(f"handing off to the real harness (engine={face}): " + " ".join(sys.argv[1:]))
    r = subprocess.run([sys.executable, real] + sys.argv[1:])
    say(f"harness rc={r.returncode}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
