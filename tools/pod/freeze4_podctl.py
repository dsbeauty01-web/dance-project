#!/usr/bin/env python3
"""tools/pod/freeze4_podctl.py — run from the operator's machine: the FREEZE v4 proof pod, start to finish.

  balance                      RunPod balance + spend rate (refuses nothing; just prints)
  create <commit>              ONE Secure RTX 4090 pod named nova-freeze4 on Maya's SoulX image; refuses under $5 balance
                               or if a pod named nova-freeze4 already exists. Prints the pod id only.
  status <id>                  desiredStatus / runtime / cost rate, and the pod's STAGES file
  pull <id> <dir> [files…]     download result files from the pod's :8099 results server
  terminate <id>               DELETE by id, then confirm the id is gone from the pod list
  watchdog <id> <minutes>      local backstop: terminate <id> after <minutes> whatever happens
Keys are read from $FREEZE4_ENV (default /root/.maya/host.env) inside this process only and never printed.
The pod gets OPENAI_API_KEY + LIVEKIT_URL/API_KEY/API_SECRET (the brain and the face need them) — nothing else.
"""
import json, os, sys, time, urllib.request, urllib.error

ENVF = os.environ.get("FREEZE4_ENV", "/root/.maya/host.env")
IMAGE = os.environ.get("FREEZE4_IMAGE", "ghcr.io/dsbeauty01-web/maya-lt:soulx-wide-v2")
NAME = "nova-freeze4"
FLOOR = 5.0
REST = "https://rest.runpod.io/v1"


def keys():
    out = {}
    for line in open(ENVF, encoding="utf8"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1); out[k.strip()] = v.strip().strip('"').strip("'")
    return out


K = keys()
AUTH = {"Authorization": "Bearer " + K["RUNPOD_API_KEY"], "Content-Type": "application/json", "User-Agent": "nova-freeze4/1.0"}


def req(method, url, body=None, timeout=30):
    r = urllib.request.Request(url, method=method, headers=AUTH, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            t = f.read().decode() or "null"; return f.status, json.loads(t) if t.strip()[:1] in "[{" else t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def balance():
    s, d = req("POST", "https://api.runpod.io/graphql", {"query": "query { myself { clientBalance currentSpendPerHr } }"})
    m = (d or {}).get("data", {}).get("myself", {}) if isinstance(d, dict) else {}
    return m.get("clientBalance"), m.get("currentSpendPerHr")


def pods():
    s, d = req("GET", REST + "/pods")
    return d if isinstance(d, list) else []


def registry_auth_id():
    s, d = req("GET", REST + "/containerregistryauth")
    for a in d if isinstance(d, list) else []:
        if a.get("name") == "ghcr-maya-lt": return a["id"]
    raise SystemExit("registry credential ghcr-maya-lt not found (names: %s)" % [a.get("name") for a in (d if isinstance(d, list) else [])])


def create(commit):
    bal, rate = balance()
    print("balance", bal, "spend/h now", rate)
    if bal is None or float(bal) < FLOOR: raise SystemExit(f"REFUSED: balance {bal} < ${FLOOR}")
    if any(p.get("name") == NAME for p in pods()): raise SystemExit("REFUSED: a pod named nova-freeze4 already exists")
    url = f"https://raw.githubusercontent.com/dsbeauty01-web/dance-project/{commit}/tools/pod/freeze4_pod.sh"
    body = {
        "name": NAME, "imageName": IMAGE, "gpuTypeIds": ["NVIDIA GeForce RTX 4090"], "gpuCount": 1,
        "cloudType": "SECURE", "interruptible": False, "containerDiskInGb": 60, "volumeInGb": 0,
        "ports": ["8099/http", "8765/http"], "containerRegistryAuthId": registry_auth_id(),
        "dockerEntrypoint": ["/bin/bash", "-c"],
        "dockerStartCmd": [f"mkdir -p /root/out; curl -fsSL {url} -o /root/f4.sh >> /root/out/fetch.log 2>&1; "
                           f"FREEZE4_BRANCH=nova-freeze-v4 bash /root/f4.sh; sleep infinity"],
        "env": {k: K[k] for k in ("OPENAI_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")} | {"FREEZE4_WATCH_MIN": "50"},
    }
    s, d = req("POST", REST + "/pods", body, timeout=60)
    if not isinstance(d, dict) or "id" not in d: raise SystemExit(f"CREATE FAILED {s}: {str(d)[:300]}")
    print("pod", d["id"], "costPerHr", d.get("costPerHr"), "created", time.strftime("%H:%M:%S", time.gmtime()), "UTC")


def status(pid):
    s, d = req("GET", f"{REST}/pods/{pid}")
    if isinstance(d, dict):
        print({k: d.get(k) for k in ("name", "desiredStatus", "costPerHr", "lastStatusChange", "image", "machineId")})
    else: print(s, d)
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://{pid}-8099.proxy.runpod.net/STAGES", headers={"User-Agent": "nova-freeze4/1.0"}), timeout=20) as f:
            print(f.read().decode()[-2500:])
    except Exception as e: print("results server:", str(e)[:120])


def pull(pid, d, files):
    os.makedirs(d, exist_ok=True)
    for f in files:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{pid}-8099.proxy.runpod.net/{f}", headers={"User-Agent": "nova-freeze4/1.0"}), timeout=180) as r:
                b = r.read()
            os.makedirs(os.path.dirname(os.path.join(d, f)) or d, exist_ok=True)
            open(os.path.join(d, f), "wb").write(b); print("got", f, len(b))
        except Exception as e: print("MISS", f, str(e)[:100])


def terminate(pid):
    s, d = req("DELETE", f"{REST}/pods/{pid}")
    print("DELETE", pid, "->", s)
    for _ in range(12):
        if not any(p.get("id") == pid for p in pods()): print("CONFIRMED GONE", pid); return True
        time.sleep(5)
    print("STILL LISTED", pid); return False


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    if c == "balance": print("balance", *balance())
    elif c == "mine": print([(p.get("id"), p.get("desiredStatus")) for p in pods() if p.get("name") == NAME])
    elif c == "create": create(a[0])
    elif c == "status": status(a[0])
    elif c == "pull": pull(a[0], a[1], a[2:])
    elif c == "terminate": terminate(a[0])
    elif c == "watchdog":
        time.sleep(float(a[1]) * 60); print("LOCAL WATCHDOG fired"); terminate(a[0])
