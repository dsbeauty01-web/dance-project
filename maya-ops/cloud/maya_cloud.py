#!/usr/bin/env python3
"""
maya_cloud.py — drive Maya from a Claude Code CLOUD session (phone, laptop closed). REST only, no SSH.

  python maya_cloud.py check                 # deploy check-mode pod -> wait -> read /health -> STOP IT -> print report
  python maya_cloud.py up    --name maya-check --mode check
  python maya_cloud.py report --id <podId>
  python maya_cloud.py down  --id <podId>    # stop by explicit id only

Why this exists (and why it is not spawn_stream.py):
  • The RunPod account has ZERO templates, so templateId deploys cannot work. This deploys by imageName +
    containerRegistryAuthId instead.
  • spawn_stream.py defaults to volume 1ditrne6cb / EU-RO-1 — that is NOVA's volume. Maya's volume is
    maya-persist = 8gu2r2r0hr in US-TX-3. Wrong volume = wrong project's data.
  • There is deliberately NO "stop all" here. Rule 1: one agent touches the account at a time, stop by id,
    never sweep — other projects share this account.

ENV (names only; values come from the cloud session's environment settings):
  RUNPOD_API_KEY                required
  RUNPOD_IMAGE                  default ghcr.io/dsbeauty01-web/maya-lt:latest
  RUNPOD_REGISTRY_AUTH_ID       default cmuba1ii5003nrtix7j8yyr43   (ghcr-maya-lt)
  RUNPOD_VOLUME_ID              default 8gu2r2r0hr                  (maya-persist)
  RUNPOD_DC                     default US-TX-3                     (must match the volume's region)
  RUNPOD_GPU_LADDER             default "NVIDIA GeForce RTX 4090,NVIDIA RTX A5000,NVIDIA L4"
  RUNPOD_PORTS                  default "8010/http,8787/http,8794/http,8889/http"
  RUNPOD_DISK_GB                default 40
  OPENAI_API_KEY                passed to the pod — the voice is openaitts/coral, forced by /start.sh
  MAYA_ASSETS_TOKEN             GitHub token that can read dsbeauty01-web/maya-lt (PRIVATE).
                                Only needed when the pod has no network volume: /start.sh then pulls
                                the face bake, gestures and weights from release assets-v1.
  MAYA_MINUTES                  default 15 — how long an autostarted run lasts
Docs: https://rest.runpod.io/v1  (POST /pods · GET /pods/{id} · POST /pods/{id}/stop)
"""
import argparse, json, os, sys, time

import requests

E = os.environ.get
API = "https://rest.runpod.io/v1"
HEALTH_PORT = 8787

IMAGE = E("RUNPOD_IMAGE", "ghcr.io/dsbeauty01-web/maya-lt:latest")
REGISTRY_AUTH = E("RUNPOD_REGISTRY_AUTH_ID", "cmuba1ii5003nrtix7j8yyr43")  # ghcr-maya-lt
VOLUME = E("RUNPOD_VOLUME_ID", "8gu2r2r0hr")                              # maya-persist
DC = E("RUNPOD_DC", "US-TX-3")                                           # maya-persist lives here


def H():
    key = E("RUNPOD_API_KEY", "")
    if not key:
        sys.exit("RUNPOD_API_KEY is not set — add it in the cloud session's environment settings.")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def req(method, path, **kw):
    r = requests.request(method, API + path, headers=H(), timeout=60, **kw)
    if r.status_code >= 300:
        raise RuntimeError(f"runpod {method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def proxy(pod_id: str, port: int) -> str:
    return f"https://{pod_id}-{port}.proxy.runpod.net"


def up(name: str, mode: str) -> str:
    """Create a pod from the image (no template exists) and return its id."""
    # The image's /start.sh autostarts `lt_run.sh $MAYA_MODE $MAYA_MINUTES` — MAYA_MODE is the switch,
    # lt_run.sh is the entry point. (lt_boot.sh is the older hand-run path; it expects the pre-image
    # layout where LiveTalking lived on the volume, so the cloud check must not call it.)
    # Voice: /start.sh exports LT_TTS=openaitts / LT_REF_FILE=coral and deliberately overrides
    # anything host.env says, so no ElevenLabs key is needed or wanted here.
    env = {"MAYA_AUTOSTART": "1", "MAYA_MODE": mode, "MAYA_MINUTES": str(E("MAYA_MINUTES", "15"))}
    for k in ("OPENAI_API_KEY", "MAYA_ASSETS_TOKEN", "MAYA_ASSETS_REPO", "MAYA_ASSETS_TAG",
              "GUARD_CAP_MIN", "GUARD_STALE_MIN", "AVATAR"):
        if E(k):
            env[k] = E(k)
    if mode != "check":  # check mode must never reach Facebook/YouTube
        for k in ("FB_PAGE_ID", "FB_PAGE_TOKEN", "BUY_URL", "YT_STREAM_KEY"):
            if E(k):
                env[k] = E(k)

    body = {
        "name": name,
        "imageName": IMAGE,
        "containerRegistryAuthId": REGISTRY_AUTH,
        "cloudType": E("RUNPOD_CLOUD", "SECURE"),
        "networkVolumeId": VOLUME,
        "dataCenterIds": [DC],
        "ports": [p.strip() for p in E("RUNPOD_PORTS", "8010/http,8787/http,8794/http,8889/http").split(",")],
        "env": env,
        "containerDiskInGb": int(E("RUNPOD_DISK_GB", "40")),
    }

    last = None
    for gpu in [g.strip() for g in E("RUNPOD_GPU_LADDER", "NVIDIA GeForce RTX 4090,NVIDIA RTX A5000,NVIDIA L4").split(",")]:
        try:
            pod = req("POST", "/pods", json={**body, "gpuTypeIds": [gpu]})
            print(f"pod created on {gpu}: {pod['id']}  (volume {VOLUME} @ {DC}, mode={mode})")
            return pod["id"]
        except RuntimeError as e:
            last = str(e)
            print(f"no capacity on {gpu} -> next rung")
    sys.exit(f"no GPU available on any rung. last error: {last}")


def wait_running(pod_id: str, timeout_s: int = 600) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        p = req("GET", f"/pods/{pod_id}")
        if p.get("desiredStatus") == "RUNNING" and p.get("publicIp"):
            return p
        time.sleep(5)
    raise TimeoutError(f"pod {pod_id} never reached RUNNING within {timeout_s}s")


def health(pod_id: str, timeout_s: int = 900) -> dict:
    """Poll the pod's /health through RunPod's HTTPS proxy. No SSH, no open inbound port needed."""
    url = proxy(pod_id, HEALTH_PORT) + "/health"
    deadline, last = time.time() + timeout_s, "no response yet"
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code < 300:
                return r.json()
            last = f"{r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(10)
    raise TimeoutError(f"{url} never answered within {timeout_s}s. last: {last}")


def summarize(snap: dict) -> dict:
    """Pull the numbers Refael asks for out of whatever /health returns."""
    flat, out = {}, {}

    def walk(d, prefix=""):
        for k, v in (d or {}).items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                walk(v, key + ".")
            else:
                flat[key] = v

    walk(snap)
    for key, val in flat.items():
        low = key.lower()
        if "fps" in low:
            out.setdefault("fps", val)
        if "dbfs" in low or "lufs" in low or "loud" in low:
            out.setdefault("audio_level", val)
    out["killed"] = snap.get("killed")
    out["ok"] = snap.get("ok")
    return out


def down(pod_id: str):
    """Stop ONE pod, by id. There is no --all here on purpose."""
    req("POST", f"/pods/{pod_id}/stop")
    print(f"stopped {pod_id}")


def cmd_check(args):
    pod_id = up(args.name, "check")
    try:
        p = wait_running(pod_id)
        print(f"RUNNING on {(p.get('machine') or {}).get('gpuTypeId')} — health: {proxy(pod_id, HEALTH_PORT)}/health")
        snap = health(pod_id)
        print("\n=== MAYA CHECK REPORT ===")
        print(json.dumps(summarize(snap), indent=2, ensure_ascii=False))
        print("\n--- full /health ---")
        print(json.dumps(snap, indent=2, ensure_ascii=False)[:4000])
    finally:
        down(pod_id)  # always stop, even if the check failed — a forgotten pod bills by the minute


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="deploy check-mode pod, report, stop it")
    c.add_argument("--name", default="maya-check")
    c.set_defaults(func=cmd_check)

    u = sub.add_parser("up", help="deploy a pod and leave it running")
    u.add_argument("--name", default="maya-check")
    u.add_argument("--mode", default="check", choices=["check", "live"])
    u.set_defaults(func=lambda a: print(up(a.name, a.mode)))

    r = sub.add_parser("report", help="read /health of a running pod")
    r.add_argument("--id", required=True)
    r.set_defaults(func=lambda a: print(json.dumps(summarize(health(a.id)), indent=2, ensure_ascii=False)))

    d = sub.add_parser("down", help="stop one pod by id")
    d.add_argument("--id", required=True)
    d.set_defaults(func=lambda a: down(a.id))

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
