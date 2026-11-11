#!/usr/bin/env python3
"""pod.py -- talk to the nova-take8 pod's own file server through the RunPod HTTP proxy.
  pod.py get PATH [LOCAL]      GET /root/out/PATH (prints it if no LOCAL)
  pod.py put LOCAL [NAME]      PUT to /root/in/NAME (needs the session token)
  pod.py wait PATH SECONDS     poll until PATH exists"""
import os, sys, time, urllib.request, urllib.error
PID = open("/dev/shm/t8/pod_id").read().strip()
BASE = f"https://{PID}-8040.proxy.runpod.net"
TOK = open("/dev/shm/t8/tok").read().strip()
UA = {"User-Agent": "nova-take8/0.1"}


def get(path, local=None, quiet=False):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}", headers=UA), timeout=120)
        b = r.read()
    except Exception as e:
        if not quiet: print(f"GET {path}: {type(e).__name__} {getattr(e, 'code', '')}")
        return None
    if local:
        open(local, "wb").write(b); print(f"got {path} -> {local} ({len(b)} B)")
    elif not quiet:
        sys.stdout.write(b.decode(errors="replace"))
    return b


def put(local, name=None):
    name = name or os.path.basename(local)
    d = open(local, "rb").read()
    rq = urllib.request.Request(f"{BASE}/put/{name}", data=d, method="PUT",
                                headers={**UA, "X-Tok": TOK, "Content-Type": "application/octet-stream"})
    for i in range(4):
        try:
            print(urllib.request.urlopen(rq, timeout=300).read().decode()); return
        except Exception as e:
            print(f"PUT {name} try {i}: {type(e).__name__} {getattr(e, 'code', '')}"); time.sleep(5)
    sys.exit(f"PUT {name} failed")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "get": get(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif c == "put": put(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif c == "wait":
        t0 = time.time()
        while time.time() - t0 < float(sys.argv[3]):
            b = get(sys.argv[2], quiet=True)
            if b is not None:
                print(f"{sys.argv[2]} after {time.time() - t0:.0f}s: {b.decode(errors='replace').strip()[:300]}"); sys.exit(0)
            time.sleep(10)
        print("TIMEOUT waiting for", sys.argv[2]); sys.exit(1)
