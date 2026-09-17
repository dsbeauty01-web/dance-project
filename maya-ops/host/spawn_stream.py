#!/usr/bin/env python3
"""
spawn_stream.py — one pod per client stream (or per 2-3 concurrent sessions), via the RunPod REST API.

  python spawn_stream.py up   --name maya-sela --targets fb,amazon        # start pod from template, wait, print endpoints
  python spawn_stream.py list
  python spawn_stream.py down --id <podId>
  python spawn_stream.py down --all-maya                                 # stop every pod whose name starts with maya-

ENV: RUNPOD_API_KEY · RUNPOD_TEMPLATE_ID (the golden image: engine + mediamtx + host stack, boot script reads
     STREAM_TARGETS/CLIENT env) · RUNPOD_VOLUME_ID=1ditrne6cb · RUNPOD_GPU_LADDER="NVIDIA GeForce RTX 4090,NVIDIA RTX A5000,NVIDIA L4"
     RUNPOD_DC=EU-RO-1 (volume region) · RUNPOD_PORTS="22/tcp,8010/http,8787/http,8794/http,8889/http"
Docs: https://rest.runpod.io/v1  (POST /pods · GET /pods · POST /pods/{id}/stop · DELETE /pods/{id})
"""
import argparse, json, os, sys, time
import requests

E = os.environ.get
API = "https://rest.runpod.io/v1"
H = {"Authorization": f"Bearer {E('RUNPOD_API_KEY', '')}", "Content-Type": "application/json"}


def req(method, path, **kw):
    r = requests.request(method, API + path, headers=H, timeout=60, **kw)
    if r.status_code >= 300:
        sys.exit(f"runpod {method} {path} → {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def up(name: str, targets: str, client: str):
    ladder = [g.strip() for g in E("RUNPOD_GPU_LADDER", "NVIDIA GeForce RTX 4090,NVIDIA RTX A5000,NVIDIA L4").split(",")]
    body_base = {
        "name": name, "templateId": E("RUNPOD_TEMPLATE_ID", ""), "cloudType": E("RUNPOD_CLOUD", "SECURE"),
        "networkVolumeId": E("RUNPOD_VOLUME_ID", "1ditrne6cb"), "dataCenterIds": [E("RUNPOD_DC", "EU-RO-1")],
        "ports": [p.strip() for p in E("RUNPOD_PORTS", "22/tcp,8010/http,8787/http,8794/http,8889/http").split(",")],
        "env": {"STREAM_TARGETS": targets, "CLIENT": client, "MAYA_AUTOSTART": "1"},
        "containerDiskInGb": int(E("RUNPOD_DISK_GB", "40")),
    }
    last = None
    for gpu in ladder:  # capacity ladder: first GPU type with cards wins
        try:
            pod = req("POST", "/pods", json={**body_base, "gpuTypeIds": [gpu]})
            print(f"pod created on {gpu}: {pod.get('id')}"); break
        except SystemExit as e:
            last = str(e); print(f"no capacity on {gpu} → next"); pod = None
    if not pod:
        sys.exit(f"no GPU available on any rung: {last}")
    pid = pod["id"]
    for _ in range(60):  # wait for RUNNING + ports
        p = req("GET", f"/pods/{pid}")
        if p.get("desiredStatus") == "RUNNING" and p.get("publicIp"):
            break
        time.sleep(5)
    p = req("GET", f"/pods/{pid}")
    base = f"https://{pid}-{{port}}.proxy.runpod.net"
    out = {"id": pid, "gpu": p.get("machine", {}).get("gpuTypeId"), "ip": p.get("publicIp"),
           "health": base.format(port=8787) + "/health", "rt_speak": base.format(port=8794) + "/health",
           "engine": base.format(port=8010), "ssh": f"ssh root@{p.get('publicIp')} -p {next((m.get('publicPort') for m in p.get('portMappings', []) if m.get('privatePort') == 22), '?')}"}
    print(json.dumps(out, indent=2))
    with open(os.path.expanduser(f"~/.maya/pods/{name}.json"), "w") if os.path.isdir(os.path.expanduser("~/.maya/pods")) else open(f"{name}.pod.json", "w") as f:
        json.dump(out, f, indent=2)
    return out


def list_pods():
    for p in req("GET", "/pods").get("pods", req("GET", "/pods")) if isinstance(req("GET", "/pods"), dict) else req("GET", "/pods"):
        print(p.get("id"), p.get("name"), p.get("desiredStatus"), p.get("costPerHr"))


def down(pid: str = "", all_maya: bool = False):
    if all_maya:
        pods = req("GET", "/pods")
        pods = pods.get("pods", pods) if isinstance(pods, dict) else pods
        for p in pods:
            if str(p.get("name", "")).startswith("maya-") and p.get("desiredStatus") == "RUNNING":
                req("POST", f"/pods/{p['id']}/stop"); print("stopped", p["id"], p["name"])
        return
    req("POST", f"/pods/{pid}/stop"); print("stopped", pid)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up"); u.add_argument("--name", required=True); u.add_argument("--targets", default="fb"); u.add_argument("--client", default="")
    sub.add_parser("list")
    d = sub.add_parser("down"); d.add_argument("--id", default=""); d.add_argument("--all-maya", action="store_true")
    a = ap.parse_args()
    if a.cmd == "up": up(a.name, a.targets, a.client)
    elif a.cmd == "list": list_pods()
    else: down(a.id, a.all_maya)
