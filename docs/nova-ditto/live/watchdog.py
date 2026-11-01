#!/usr/bin/env python3
"""watchdog.py -- hard REST terminate of ONE pod id at a deadline, from this container.
Independent of the pod's own self-stop. Writes a proof file the caller reads back.

  python3 -I watchdog.py <podid> <minutes> <keyfile> <prooffile>
"""
import json, os, sys, time, urllib.request

pid, minutes, keyfile, proof = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
key = open(keyfile).read().strip()
deadline = time.time() + minutes * 60
json.dump({"pod": pid, "armed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "fires_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(deadline)),
           "minutes": minutes, "pid": os.getpid(), "state": "ARMED"}, open(proof, "w"), indent=1)
while time.time() < deadline:
    time.sleep(10)
    try:
        r = urllib.request.Request(f"https://rest.runpod.io/v1/pods/{pid}",
                                   headers={"Authorization": f"Bearer {key}", "User-Agent": "maya-launch/0.1"})
        with urllib.request.urlopen(r, timeout=20) as x:
            x.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:                      # already terminated: stand down
            d = json.load(open(proof)); d["state"] = "STOOD_DOWN (pod already gone)"
            d["at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            json.dump(d, open(proof, "w"), indent=1); sys.exit(0)
    except Exception:
        pass
for attempt in range(5):
    try:
        r = urllib.request.Request(f"https://rest.runpod.io/v1/pods/{pid}", method="DELETE",
                                   headers={"Authorization": f"Bearer {key}", "User-Agent": "maya-launch/0.1"})
        with urllib.request.urlopen(r, timeout=30) as x:
            x.read()
        break
    except urllib.error.HTTPError as e:
        if e.code == 404:
            break
    except Exception:
        time.sleep(5)
d = json.load(open(proof)); d["state"] = "FIRED"; d["at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(d, open(proof, "w"), indent=1)
