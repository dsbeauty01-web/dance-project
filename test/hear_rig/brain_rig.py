#!/usr/bin/env python3
"""rig: run the REAL pod/rt_lk.py (paths rewritten to the rig's ws/) on this machine. Outbound goes through the agent proxy,
so aiohttp sessions get trust_env=True. Keys come from /root/.maya/host.env and are never printed."""
import os, sys, runpy, aiohttp
HERE = os.path.dirname(os.path.abspath(__file__)); RIG = os.environ.get("HEAR_RIG_DIR", "/tmp/nova-hear-rig")
for l in open("/root/.maya/host.env"):
    l = l.strip()
    if "=" in l and not l.startswith("#"):
        k, v = l.split("=", 1)
        if k in ("OPENAI_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"): os.environ[k] = v.strip("\"'")
_CS = aiohttp.ClientSession
class CS(_CS):
    def __init__(self, *a, **k): k.setdefault("trust_env", True); super().__init__(*a, **k)
aiohttp.ClientSession = CS
for k in ("NOVA_FACE_SOULX","NOVA_FACE_DUAL","NOVA_TEST_CLIPS","NOVA_KID_EVENTS","NOVA_INTRO_ANSWER"): os.environ.setdefault(k, "1")
os.environ.setdefault("LK_ROOM", "nova-final")
os.environ.setdefault("ENGINE_URL", "http://127.0.0.1:8010"); os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"; os.environ["no_proxy"] = os.environ["NO_PROXY"]
os.chdir(os.path.join(RIG, "ws")); sys.argv = ["rt_lk.py"]
runpy.run_path(os.path.join(RIG, "rt_lk_rig.py"), run_name="__main__")
