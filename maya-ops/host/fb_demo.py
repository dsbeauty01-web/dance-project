#!/usr/bin/env python3
"""
fb_demo.py — the WITNESSED Facebook demo, fully scripted. Run on the pod.

  1. validates FB_PAGE_TOKEN (or exchanges a user token to long-lived page token)
  2. creates a LIVE video on the Page → RTMP url + permalink
  3. starts the video push:  ENGINE mode (MuseTalk live avatar → RTMP)  or  LOOP mode (ffmpeg loop file)
  4. starts maya_host.py --platform facebook   (read comments → answer → "@Name —" top-level reply [+ voice])
  5. records a PROOF timeline: every comment → reply, with latency; saves proof.json + prints it
  6. after DEMO_MINUTES: ends the live, stops everything

ENV (in ~/.maya/host.env)
  FB_PAGE_ID  FB_PAGE_TOKEN  FB_APP_ID  FB_APP_SECRET  (FB_USER_TOKEN optional → auto long-lived exchange)
  DEMO_MINUTES=0 (0 = run until `touch KILL`)   DEMO_TITLE="Vitamin C Serum — LIVE | Maya (AI Host)"
  PUSH_MODE=engine|loop     LOOP_FILE=/workspace/maya-ops/bake/src/serum_present_src.mp4
  ENGINE_START_CMD="..."    # shell template; {rtmp_url} is substituted. e.g. python app.py --transport rtmp --push_url {rtmp_url} ...
  MAYA_HOST_PY=/workspace/maya-ops/host/maya_host.py
"""
import json, os, signal, subprocess, sys, time, shlex
import requests

E = os.environ.get
G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"
PAGE = E("FB_PAGE_ID", "")
TOKEN = E("FB_PAGE_TOKEN", "")
PROOF = {"started": time.time(), "events": []}


def say(msg):
    print(f"[fb_demo {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def die(msg):
    say("FATAL: " + msg); sys.exit(2)


# ---------- 1. token ----------
def token_ok(tok: str) -> bool:
    r = requests.get(f"{G}/{PAGE}", params={"fields": "id,name", "access_token": tok}, timeout=10).json()
    return "id" in r


def long_lived_page_token(user_token: str) -> str:
    r = requests.get(f"{G}/oauth/access_token", params={"grant_type": "fb_exchange_token", "client_id": E("FB_APP_ID"),
                     "client_secret": E("FB_APP_SECRET"), "fb_exchange_token": user_token}, timeout=10).json()
    if "access_token" not in r:
        die(f"long-lived exchange failed: {r}")
    acc = requests.get(f"{G}/me/accounts", params={"access_token": r["access_token"]}, timeout=10).json()
    for p in acc.get("data", []):
        if p["id"] == PAGE:
            return p["access_token"]
    die("page not in /me/accounts for this user token")


def ensure_token():
    global TOKEN
    if TOKEN and token_ok(TOKEN):
        say("page token OK"); return
    ut = E("FB_USER_TOKEN", "")
    if ut:
        TOKEN = long_lived_page_token(ut)
        with open(os.path.expanduser("~/.maya/host.env"), "a") as f:
            f.write(f"\nFB_PAGE_TOKEN={TOKEN}\n")
        say("long-lived page token minted + saved"); return
    die("no valid FB token. Get a user token via Graph Explorer (config 'rafa', MythicMingle, all toggles ON) → FB_USER_TOKEN=... in ~/.maya/host.env → rerun.")


# ---------- 2. live ----------
def create_live() -> dict:
    r = requests.post(f"{G}/{PAGE}/live_videos", data={"status": "LIVE_NOW", "title": E("DEMO_TITLE", "Maya — LIVE (AI Host)"),
                      "description": "AI host Maya. Vitamin C serum, 20%, one drop every morning. Live price 149 ILS. Link below.",
                      "access_token": TOKEN}, timeout=15).json()
    if "id" not in r:
        die(f"create live failed: {r}")
    info = requests.get(f"{G}/{r['id']}", params={"fields": "id,permalink_url,secure_stream_url,stream_url", "access_token": TOKEN}, timeout=10).json()
    vid = requests.get(f"{G}/{r['id']}", params={"fields": "video{id}", "access_token": TOKEN}, timeout=10).json()
    live = {"id": r["id"], "video_id": (vid.get("video") or {}).get("id") or r["id"],
            "rtmp": info.get("secure_stream_url") or info.get("stream_url") or r.get("secure_stream_url") or r.get("stream_url"),
            "permalink": "https://www.facebook.com" + info.get("permalink_url", "")}
    say(f"LIVE created: {live['id']}  watch: {live['permalink']}")
    PROOF["live"] = {k: v for k, v in live.items() if k != "rtmp"}
    return live


def end_live(live_id: str):
    requests.post(f"{G}/{live_id}", data={"end_live_video": "true", "access_token": TOKEN}, timeout=10)
    say("live ended")


# ---------- 3. push ----------
def start_push(rtmp: str) -> subprocess.Popen:
    if E("PUSH_MODE", "loop") == "engine" and E("ENGINE_START_CMD"):
        cmd = E("ENGINE_START_CMD").format(rtmp_url=shlex.quote(rtmp))
        say("push: ENGINE mode (live avatar)")
        return subprocess.Popen(cmd, shell=True)
    loop = E("LOOP_FILE", "")
    if not loop or not os.path.exists(loop):
        die("LOOP_FILE missing and no ENGINE_START_CMD")
    say("push: LOOP mode (text-only demo; voice needs ENGINE mode)")
    cmd = ["ffmpeg", "-re", "-stream_loop", "-1", "-i", loop, "-c:v", "libx264", "-preset", "veryfast", "-b:v", "4500k",
           "-maxrate", "4500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p", "-g", "50", "-keyint_min", "50", "-r", "25",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-f", "flv", rtmp]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------- 4. host ----------
def start_host(live_id: str) -> subprocess.Popen:
    env = dict(os.environ, FB_PAGE_TOKEN=TOKEN, FB_LIVE_VIDEO_ID=live_id)
    cmd = [sys.executable, E("MAYA_HOST_PY", "maya_host.py"), "--platform", "facebook", "--fb-live-id", live_id]
    say("maya_host starting: " + " ".join(cmd[1:]))
    return subprocess.Popen(cmd, env=env)


# ---------- 5. proof timeline ----------
def proof_loop(live_id: str, minutes: int):
    """minutes=0 → run until a KILL file appears (no auto-end)."""
    seen = {}
    end = time.time() + minutes * 60 if minutes > 0 else float("inf")
    while time.time() < end and not os.path.exists("KILL"):
        r = requests.get(f"{G}/{live_id}/comments", params={"fields": "id,from{name,id},message,created_time", "order": "chronological",
                         "filter": "stream", "limit": 100, "access_token": TOKEN}, timeout=10).json()
        for c in r.get("data", []):
            if c["id"] in seen:
                continue
            seen[c["id"]] = c
            frm = (c.get("from") or {})
            is_page = str(frm.get("id")) == str(PAGE)
            ev = {"ts": c.get("created_time"), "who": "MAYA" if is_page else frm.get("name"), "text": c.get("message", "")}
            PROOF["events"].append(ev)
            say(("  ↳ MAYA: " if is_page else "COMMENT ") + f"{ev['who']}: {ev['text'][:90]}")
        time.sleep(4)


def latency_table():
    from datetime import datetime
    def ts(s):
        try:
            return datetime.fromisoformat(s.replace("+0000", "+00:00").replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
    rows, pending = [], []
    for e in PROOF["events"]:
        if e["who"] != "MAYA":
            pending.append(e)
        else:
            name = e["text"].split("—")[0].lstrip("@").strip()
            for p in list(pending):
                if p["who"] and p["who"].split()[0] == name.split()[0]:
                    rows.append({"comment": p["text"][:60], "reply": e["text"][:80], "latency_s": round(ts(e["ts"]) - ts(p["ts"]), 1)})
                    pending.remove(p); break
    return rows


# ---------- main ----------
def main():
    if not PAGE:
        die("FB_PAGE_ID missing")
    ensure_token()
    live = create_live()
    push = start_push(live["rtmp"])
    time.sleep(8)
    host = start_host(live["id"])
    say(f"DEMO RUNNING {E('DEMO_MINUTES', '12')} min. Comment here now: {live['permalink']}")
    try:
        proof_loop(live["video_id"], int(E("DEMO_MINUTES", "0")))
    finally:
        for p in (host, push):
            try:
                p.send_signal(signal.SIGINT); p.wait(timeout=10)
            except Exception:
                p.kill()
        end_live(live["id"])
        PROOF["latency_table"] = latency_table()
        PROOF["ended"] = time.time()
        with open("proof.json", "w", encoding="utf-8") as f:
            json.dump(PROOF, f, ensure_ascii=False, indent=2)
        say("PROOF:\n" + json.dumps(PROOF["latency_table"], ensure_ascii=False, indent=2))
        say("permalink (replay keeps the comments+replies visible): " + live["permalink"])


if __name__ == "__main__":
    main()
