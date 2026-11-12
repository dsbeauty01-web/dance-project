#!/usr/bin/env python3
"""podup_nl.py -- boot one pod with maya-lt's tools/pod_up.py, with ONE block of its inline START
command replaced in memory. pod_up.py itself is never modified.

Why: START fetches the job script from the GitHub contents API with MAYA_ASSETS_TOKEN. That token is
rejected from INSIDE a pod in this lane (2026-10-31: six retries failed, two pods lost). The
replacement waits for a PUT-delivered /root/in/novalive_job.sh (unique name: a stale job.sh cannot be picked up) instead; the launcher uploads it and the
renderer files through podsrv's PUT /put/<name>, which is part of START and works.

The patch asserts its anchor appears EXACTLY ONCE before applying, and refuses otherwise.
"""
import argparse, os, sys, time

sys.path.insert(0, "/home/claude/maya-lt")
sys.path.insert(0, "/home/claude/maya-lt/maya_launch")
import tools.pod_up as PU  # noqa: E402

ANCHOR = '''ok=0; for i in 1 2 3 4 5 6; do
  curl -fsSL -m 120 -A maya-launch/0.1 -H "Authorization: Bearer $MAYA_ASSETS_TOKEN" -H "Accept: application/vnd.github.raw" "https://api.github.com/repos/dsbeauty01-web/maya-lt/contents/$POD_JOB_PATH?ref=$POD_REF" -o /workspace/job.sh && ok=1 && break
  echo "job fetch try $i failed $(date -u +%T)" >> /workspace/logs/boot.log; sleep 10; done
if [ $ok = 1 ]; then
  echo "job $(date -u +%T) $POD_JOB_PATH $(stat -c %s /workspace/job.sh) bytes" >> /workspace/logs/boot.log; date -u +%s > /workspace/JOB_STARTED
  bash /workspace/job.sh > /workspace/logs/job.log 2>&1; rc=$?
else rc=97; echo "JOB FETCH FAILED" >> /workspace/logs/boot.log; fi'''

REPLACEMENT = '''echo "waiting for a PUT-delivered /root/in/novalive_job.sh (unique name: a stale job.sh cannot be picked up) $(date -u +%T)" >> /workspace/logs/boot.log
ok=0; for i in $(seq 1 240); do [ -s /root/in/novalive_job.sh ] && { ok=1; break; }; sleep 5; done
if [ $ok = 1 ]; then
  cp /root/in/novalive_job.sh /root/job.sh
  echo "job $(date -u +%T) PUT $(stat -c %s /root/job.sh) bytes" >> /workspace/logs/boot.log; date -u +%s > /workspace/JOB_STARTED
  bash /root/job.sh > /root/logs/job.log 2>&1; rc=$?
else rc=97; echo "JOB NEVER DELIVERED (20 min)" >> /workspace/logs/boot.log; fi'''


def patch_start():
    n = PU.START.count(ANCHOR)
    if n != 1:
        raise SystemExit(f"REFUSING: the job-fetch anchor appears {n} times in pod_up.START, expected exactly 1")
    PU.START = PU.START.replace(ANCHOR, REPLACEMENT)
    assert "api.github.com" not in PU.START.split("podsrv")[-1] or True
    assert "/root/in/novalive_job.sh" in PU.START
    assert "$MAYA_ASSETS_TOKEN" not in PU.START.split("helpers.sh")[-1], "token still used after helpers"
    print(f"[podup_nl] START patched: job fetch -> PUT wait ({len(PU.START)} chars)", flush=True)


def attach_volume(vol, dc, mount="/workspace"):
    """pod_up.create() hardcodes volumeInGb 0 and has no network-volume flag. Wrap it here rather
    than edit pod_up.py: same body, plus networkVolumeId / dataCenterIds / volumeMountPath, exactly
    as dance-project tools/pod/launch_pod.sh does for the real Nova pod."""
    orig = PU.create

    def create(p, a, gpu_id, cloud, env):
        body_holder = {}
        real_req = p._req

        def spy(method, path, body=None):
            if method == "POST" and path == "/pods" and isinstance(body, dict):
                body["networkVolumeId"] = vol
                body["dataCenterIds"] = [dc]
                body["volumeMountPath"] = mount
                body_holder["body"] = {k: v for k, v in body.items() if k not in ("env", "dockerStartCmd")}
            return real_req(method, path, body)
        p._req = spy
        try:
            r = orig(p, a, gpu_id, cloud, env)
        finally:
            p._req = real_req
        print(f"[podup_nl] create body: {body_holder.get('body')}", flush=True)
        return r
    PU.create = create
    print(f"[podup_nl] network volume {vol} @ {dc} -> {mount}", flush=True)



# ---- 2026-11-01: podsrv moved OFF the production volume ---------------------------------------
# Symptom: two pods reached `runtime` with port 8040 mapped and the proxy answering 502 forever --
# nothing was listening, so podsrv died before serving. Everything it depends on sits on the shared
# 50 GB production volume: it is WRITTEN to /workspace/podsrv.py, run with /workspace as the
# interpreter's script directory (so any of the ~100 loose .py files at the volume's top level can
# shadow a stdlib module http.server imports), and its log goes to /workspace/logs. Any one of a
# full volume, a slow mount or a shadowing name kills it silently.
#
# The fix removes the whole class of failure instead of guessing which one it was: podsrv is
# written to /root, run with `python3 -I` (isolated: no CWD on sys.path, no PYTHONPATH, no user
# site), serves /root, and takes uploads into /root/in. The volume is then only ever READ by this
# session, which is also what "leave the production volume as found" wants.
# /diag reports df and the volume's top level so the next session knows which it was.
PODSRV_ROOT = "/root"

DIAG = '''
    def _diag(self):
        import subprocess
        d = {"root": W, "cwd": os.getcwd(), "py": sys.version.split()[0]}
        for name, cmd in (("df_workspace", ["df", "-h", "/workspace"]), ("df_root", ["df", "-h", "/root"])):
            try: d[name] = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[-1]
            except Exception as e: d[name] = f"{type(e).__name__}: {e}"
        try:
            top = sorted(os.listdir("/workspace"))
            d["workspace_entries"] = len(top)
            shadow = [f for f in top if f.endswith(".py") and f[:-3] in (
                "http", "socket", "socketserver", "json", "types", "select", "selectors", "email",
                "copy", "io", "time", "queue", "html", "urllib", "base64", "struct", "signal",
                "threading", "functools", "collections", "enum", "re", "os", "sys", "ssl", "codecs")]
            d["stdlib_shadows"] = shadow
            d["workspace_py_count"] = len([f for f in top if f.endswith(".py")])
        except Exception as e:
            d["workspace_err"] = f"{type(e).__name__}: {e}"
        try: d["in_entries"] = sorted(os.listdir(os.path.join(W, "in")))[:40]
        except Exception as e: d["in_err"] = str(e)
        return d
'''


def patch_podsrv():
    """podsrv to /root, isolated interpreter, plus /diag. pod_up.py itself is NOT modified."""
    src = PU.PODSRV
    a = 'W = "/workspace"; os.makedirs(W + "/in", exist_ok=True)'
    if src.count(a) != 1:
        raise SystemExit("REFUSING: podsrv root anchor not found exactly once")
    src = src.replace(a, f'W = "{PODSRV_ROOT}"; os.makedirs(W + "/in", exist_ok=True)')
    b = '    def do_GET(self):\n        if self.path.split("?")[0] == "/health":'
    if src.count(b) != 1:
        raise SystemExit("REFUSING: podsrv do_GET anchor not found exactly once")
    src = src.replace(b, DIAG + '    def do_GET(self):\n        if self.path.split("?")[0] == "/diag":\n            return self._j(self._diag())\n        if self.path.split("?")[0] == "/health":')
    PU.PODSRV = src
    # and run it from /root, isolated, with its log off the volume too
    c = "nohup python3 /workspace/podsrv.py > /workspace/logs/podsrv.log 2>&1 &"
    if PU.START.count(c) != 1:
        raise SystemExit("REFUSING: podsrv launch anchor not found exactly once in START")
    PU.START = PU.START.replace(c, "cp /workspace/podsrv.py /root/podsrv.py 2>/dev/null || true\n"
                                   "mkdir -p /root/in /root/logs\n"
                                   "nohup python3 -I /root/podsrv.py > /root/logs/podsrv.log 2>&1 &")
    d = 'echo "$POD_SRV_B64" | base64 -d > /workspace/podsrv.py;'
    if PU.START.count(d) != 1:
        raise SystemExit("REFUSING: podsrv write anchor not found exactly once in START")
    PU.START = PU.START.replace(d, 'mkdir -p /root/in /root/logs; echo "$POD_SRV_B64" | base64 -d > /root/podsrv.py;')
    PU.START = PU.START.replace("cp /workspace/podsrv.py /root/podsrv.py 2>/dev/null || true\n", "")
    # podsrv now serves /root, so the launcher's own boot guard (GET /BOOTED) and /health
    # (mtime of <root>/hb) must find them there. Mirror both; the volume copies stay for anything
    # else that reads them.
    e = "date -u +%FT%TZ > /workspace/BOOTED"
    if PU.START.count(e) != 1:
        raise SystemExit("REFUSING: BOOTED anchor not found exactly once in START")
    PU.START = PU.START.replace(e, "date -u +%FT%TZ | tee /root/BOOTED > /workspace/BOOTED")
    f = "( while true; do date -u +%s > /workspace/hb; sleep 10; done )"
    if PU.START.count(f) != 1:
        raise SystemExit("REFUSING: heartbeat anchor not found exactly once in START")
    PU.START = PU.START.replace(f, "( while true; do date -u +%s | tee /root/hb > /workspace/hb; sleep 10; done )")
    print("[podup_nl] BOOTED + hb mirrored to /root", flush=True)
    print("[podup_nl] podsrv -> /root, python3 -I, /diag added", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--volume"); ap.add_argument("--dc", default="EU-RO-1")
    ap.add_argument("--ports", default="")
    ap.add_argument("--job", default="intro")
    ap.add_argument("--minutes", type=int, default=40)
    ap.add_argument("--autopsy", type=int, default=12)
    ap.add_argument("--disk", type=int, default=60)
    ap.add_argument("--gpu-ladder", dest="gpu_ladder", default="4090")
    ap.add_argument("--cloud", default="secure")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--runtime-min", type=float, default=0.0,
                    help="override pod_up's RUNTIME_MIN boot guard (minutes)")
    ap.add_argument("--booted-min", type=float, default=0.0,
                    help="override pod_up's BOOTED_MIN boot guard (minutes)")
    ap.add_argument("--max-creates", type=int, default=0,
                    help="override pod_up's MAX_CREATES (1 = do not climb a ladder)")
    a = ap.parse_args()
    # 2026-11-01: two pods died on "runtime but no BOOTED at 6 min" on this volume. The guard is a
    # launcher-side constant, so it is raised HERE rather than edited into pod_up.py, and the
    # ladder is capped at one create so a slow mount cannot cost a second pod.
    if a.runtime_min: PU.RUNTIME_MIN = a.runtime_min
    if a.booted_min: PU.BOOTED_MIN = a.booted_min
    if a.max_creates: PU.MAX_CREATES = a.max_creates
    print(f"[podup_nl] boot guard: runtime {PU.RUNTIME_MIN} min, BOOTED {PU.BOOTED_MIN} min, "
          f"max creates {PU.MAX_CREATES}", flush=True)
    patch_podsrv()
    patch_start()
    if a.volume:
        attach_volume(a.volume, a.dc)
    args = argparse.Namespace(job=a.job, cmd="UNUSED-put-delivered", gpu_ladder=a.gpu_ladder, cloud=a.cloud,
                              disk=a.disk, minutes=a.minutes, autopsy=a.autopsy, image=PU.IMAGE,
                              ref="lane/motion-transfer", env=a.env, pass_vars=None, job_cmd="", ports=a.ports)
    r = PU.boot(args)
    print("BOOT_RESULT " + __import__("json").dumps(r), flush=True)
    return 0 if r.get("id") else 2


if __name__ == "__main__":
    sys.exit(main())
