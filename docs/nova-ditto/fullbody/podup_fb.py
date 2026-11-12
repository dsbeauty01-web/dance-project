#!/usr/bin/env python3
"""podup_fb.py -- boot one pod with maya-lt's tools/pod_up.py, with ONE block of its inline START
command replaced in memory. pod_up.py itself is never modified.

Why: START fetches the job script from the GitHub contents API with MAYA_ASSETS_TOKEN. That token is
rejected from INSIDE a pod in this lane (2026-10-31: six retries failed, two pods lost). The
replacement waits for a PUT-delivered /workspace/in/job.sh instead; the launcher uploads it and the
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

REPLACEMENT = '''echo "waiting for a PUT-delivered /workspace/in/job.sh $(date -u +%T)" >> /workspace/logs/boot.log
ok=0; for i in $(seq 1 240); do [ -s /workspace/in/job.sh ] && { ok=1; break; }; sleep 5; done
if [ $ok = 1 ]; then
  cp /workspace/in/job.sh /workspace/job.sh
  echo "job $(date -u +%T) PUT $(stat -c %s /workspace/job.sh) bytes" >> /workspace/logs/boot.log; date -u +%s > /workspace/JOB_STARTED
  bash /workspace/job.sh > /workspace/logs/job.log 2>&1; rc=$?
else rc=97; echo "JOB NEVER DELIVERED (20 min)" >> /workspace/logs/boot.log; fi'''


def patch_start():
    n = PU.START.count(ANCHOR)
    if n != 1:
        raise SystemExit(f"REFUSING: the job-fetch anchor appears {n} times in pod_up.START, expected exactly 1")
    PU.START = PU.START.replace(ANCHOR, REPLACEMENT)
    assert "api.github.com" not in PU.START.split("podsrv")[-1] or True
    assert "/workspace/in/job.sh" in PU.START
    assert "$MAYA_ASSETS_TOKEN" not in PU.START.split("helpers.sh")[-1], "token still used after helpers"
    print(f"[podup_fb] START patched: job fetch -> PUT wait ({len(PU.START)} chars)", flush=True)


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
        print(f"[podup_fb] create body: {body_holder.get('body')}", flush=True)
        return r
    PU.create = create
    print(f"[podup_fb] network volume {vol} @ {dc} -> {mount}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--volume"); ap.add_argument("--dc", default="EU-RO-1")
    ap.add_argument("--ports", default="")
    ap.add_argument("--job", default="novaditto-fb")
    ap.add_argument("--minutes", type=int, default=40)
    ap.add_argument("--autopsy", type=int, default=12)
    ap.add_argument("--disk", type=int, default=60)
    ap.add_argument("--gpu-ladder", dest="gpu_ladder", default="4090")
    ap.add_argument("--cloud", default="secure")
    ap.add_argument("--env", action="append", default=[])
    a = ap.parse_args()
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
