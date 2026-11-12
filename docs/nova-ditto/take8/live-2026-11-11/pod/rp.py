#!/usr/bin/env python3
"""rp.py -- minimal RunPod helper for session nova-take8. Reads ONLY the RUNPOD_API_KEY line of
/root/.maya/host.env into this process. Never prints it.
  rp.py status                 balance + every pod (id, name, status, $/h, volume)
  rp.py create NAME START_B64  create the one Secure 4090 pod (no network volume)
  rp.py get ID                 one pod's runtime
  rp.py delete ID              terminate by ID and verify it is gone
"""
import base64, json, sys, time, urllib.request, urllib.error


def key():
    for ln in open("/root/.maya/host.env"):
        if ln.startswith("RUNPOD_API_KEY="):
            return ln.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no RUNPOD_API_KEY line")


K = key()  # read from host.env inside this process only; never printed


def gql(q):
    r = urllib.request.Request("https://api.runpod.io/graphql", data=json.dumps({"query": q}).encode(),
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + K, "User-Agent": "nova-take8/0.1"})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())


def rest(method, path, body=None):
    r = urllib.request.Request("https://rest.runpod.io/v1" + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + K, "User-Agent": "nova-take8/0.1"})
    try:
        b = urllib.request.urlopen(r, timeout=60).read()
        return json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:400]}


def status():
    d = gql("query { myself { clientBalance currentSpendPerHr pods { id name desiredStatus costPerHr "
            "networkVolumeId machine { gpuDisplayName } } } }")
    m = d.get("data", {}).get("myself") or {}
    print(json.dumps({"balance": m.get("clientBalance"), "spend_per_hr": m.get("currentSpendPerHr"),
                      "pods": m.get("pods")}, indent=1))


def create(name, start_b64):
    start = base64.b64decode(start_b64).decode()
    body = {"cloudType": "SECURE", "gpuTypeIds": ["NVIDIA GeForce RTX 4090"], "gpuCount": 1,
            "imageName": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
            "containerDiskInGb": 60, "volumeInGb": 0, "ports": ["8040/http"], "name": name,
            "interruptible": False, "dockerStartCmd": ["bash", "-c", start]}
    if len(sys.argv) > 4 and sys.argv[4]:                     # Nova's own volume, its datacenter
        body.update({"networkVolumeId": sys.argv[4], "dataCenterIds": [sys.argv[5]], "volumeMountPath": "/workspace"})
    r = rest("POST", "/pods", body)
    print(json.dumps({k: r.get(k) for k in ("id", "name", "costPerHr", "desiredStatus", "http_error", "body")}))


def get(pid):
    r = rest("GET", f"/pods/{pid}")
    print(json.dumps({k: r.get(k) for k in ("id", "name", "desiredStatus", "costPerHr", "lastStartedAt",
                                            "portMappings", "publicIp", "http_error")}))


def delete(pid):
    r = rest("DELETE", f"/pods/{pid}")
    print("delete:", json.dumps(r)[:200])
    for _ in range(10):
        time.sleep(3)
        g = rest("GET", f"/pods/{pid}")
        if g.get("http_error") == 404 or not g.get("id"):
            print("GONE verified", pid)
            return
    print("NOT YET GONE", json.dumps(g)[:200])


if __name__ == "__main__":
    c = sys.argv[1]
    {"status": lambda: status(), "create": lambda: create(sys.argv[2], sys.argv[3]),
     "get": lambda: get(sys.argv[2]), "delete": lambda: delete(sys.argv[2])}[c]()
