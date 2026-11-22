#!/usr/bin/env python3
"""nova_play.py -- bring up the NOVA-FINAL pod for a HUMAN to play (2026-11-21, Refael: "get me Nova").
nova_final_ctl.py unchanged, except its RunPod calls go through maya-lt's runpod_api (REST v1 was retired 2026-11-15),
and the proof steps are skipped (NF_SKIP_W/A, no extra games): brain + dual face server stay up, the page is served by
the pod on :8765  ->  https://<pod>-8765.proxy.runpod.net/beta/freeze4?lang=en
  nova_play.py create | status <id> | terminate <id> | mine
"""
import importlib.util, os, sys
# Default = the FULL on-pod proof (W + A): the pod's own Chrome plays the game and saves A-1..A-6 screenshots and
# nova-final-run.mp4 on :8099. Only that proves her picture reaches a browser. NF_SKIP_W=1 NF_SKIP_A=1 = play-only (faster).
os.environ.setdefault("NF_GAMES", "none")
os.environ.setdefault("FREEZE4_REGISTRY", "ghcr-2026-11-21")   # the older saved ghcr passwords are rejected: pods exit in 2 s
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv, ARGV = [sys.argv[0], "noop"], sys.argv[1:]
import nova_final_ctl as C
spec = importlib.util.spec_from_file_location("runpod_api", os.environ.get("RUNPOD_API_PY", "/home/claude/mt-wt/maya_launch/maya_launch/runpod_api.py"))
RA = importlib.util.module_from_spec(spec); spec.loader.exec_module(RA)
_req = C.req
def req(method, url, body=None, timeout=30):
    if url.startswith(C.REST):
        path = url[len(C.REST):]
        try:
            if method == "POST" and path == "/pods":
                # 2026-11-22: her voice came out chopped (20 gaps of 40-340 ms inside her own sentences, measured on the
                # pod's OWN recording, so not the network) on a host with 13.6 cores; the renderer also took 259 s to warm
                # up against 150 s on a 26-core host. Ask for a real machine, as the widget and the co-host launcher do.
                v = int(os.environ.get("NF_MIN_VCPU", "24"))
                if v > 0: body = dict(body, minVCPUPerGPU=v)
            d = RA.create_pod(body, C.K["RUNPOD_API_KEY"]) if (method == "POST" and path == "/pods") else RA.call(method, path, body, C.K["RUNPOD_API_KEY"])
            return 200, d
        except RA.RunPodError as e:
            return (e.code or 0), str(e)[:400]
    return _req(method, url, body, timeout)
C.req = req
def _reg():
    d = RA.gql("query { myself { containerRegistryCreds { id name } } }", key=C.K["RUNPOD_API_KEY"])
    d = d.get("data", d)
    for c in d["myself"]["containerRegistryCreds"]:
        if c["name"] == C.REG: return c["id"]
    raise SystemExit("registry credential %s not found" % C.REG)
C.registry_auth_id = _reg
if __name__ == "__main__":
    c, *a = ARGV
    if c == "create":
        if not a: raise SystemExit("usage: nova_play.py create <full 40-char commit of dance-project to serve>")
        C.create(a[0])
    elif c == "status": C.status(a[0])
    elif c == "terminate": C.terminate(a[0])
    elif c == "mine": print([(p.get("id"), p.get("name"), p.get("desiredStatus")) for p in C.pods() if (p.get("name") or "").startswith("nova")])
    elif c == "reg": print(C.registry_auth_id()[:6] + "…")
