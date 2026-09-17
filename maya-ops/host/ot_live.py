#!/usr/bin/env python3
"""
ot_live.py — put Maya live on Facebook through OpenTalking's BUILT-IN streaming output (no aiortc fights).

OpenTalking API (from its docs/api/sessions + docs/api/streaming):
  POST /sessions {"avatar_id","model","tts_provider","stt_provider"} → {"session_id"}
  POST /sessions/{sid}/start                          → ready
  POST /sessions/{sid}/outputs  (Bearer OPENTALKING_STREAMING_CONTROL_TOKEN, Idempotency-Key)
       {"type":"rtmps","name":..,"auto_connect":true,"transport":{"endpoint":"rtmps://host:443/rtmp/","stream_key":"..."}}
  GET  /sessions/{sid}/outputs                        → status snapshots (no secrets)
  POST /sessions/{sid}/speak {"text","mode":"replace|append","command_id","tts_provider"}
  POST /sessions/{sid}/interrupt

USAGE
  python ot_live.py up   --avatar maya --model quicktalk --tts openai      # creates FB live (fb_tool), session, RTMPS output
  python ot_live.py up   --avatar anchor --model mock --tts edge --no-fb   # CPU smoke: session only, no Facebook
  python ot_live.py say  "Refael — it's 149 shekels live right now."       # speak on the running session
  python ot_live.py status | down

ENV (~/.maya/host.env): OT_BASE=http://127.0.0.1:8210  OPENTALKING_STREAMING_CONTROL_TOKEN=<token you set in OpenTalking .env>
     FB_* (for fb_tool)  OT_STATE=~/.maya/ot_session.json
Facebook RTMPS: secure_stream_url = rtmps://live-api-s.facebook.com:443/rtmp/<KEY> → endpoint + stream_key split here.
"""
import argparse, json, os, subprocess, sys, time, uuid
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
for p in (os.path.expanduser("~/.maya/host.env"),):
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
E = os.environ.get
BASE = E("OT_BASE", "http://127.0.0.1:8210").rstrip("/")
TOKEN = E("OPENTALKING_STREAMING_CONTROL_TOKEN", "")
STATE = os.path.expanduser(E("OT_STATE", "~/.maya/ot_session.json"))
AUTH = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def say_(m):
    print(f"[ot_live {time.strftime('%H:%M:%S')}] {m}", flush=True)


def req(method, path, ok=(200, 201, 202, 204), **kw):
    r = requests.request(method, BASE + path, timeout=kw.pop("timeout", 30), **kw)
    if r.status_code not in ok:
        sys.exit(f"{method} {path} → {r.status_code}: {r.text[:300]}")
    return r.json() if r.text and r.headers.get("content-type", "").startswith("application/json") else {}


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w"), indent=2)


# ---------- session ----------
def create_session(avatar, model, tts, stt):
    j = req("POST", "/sessions", headers={"Content-Type": "application/json"},
            json={"avatar_id": avatar, "model": model, "tts_provider": tts, "stt_provider": stt})
    sid = j["session_id"]
    say_(f"session {sid} (avatar={avatar} model={model} tts={tts})")
    req("POST", f"/sessions/{sid}/start", timeout=180)
    for _ in range(60):  # wait ready
        st = requests.get(f"{BASE}/sessions/{sid}", timeout=10)
        if st.status_code == 200 and str(st.json().get("state", st.json().get("status", ""))).lower() in ("ready", "running", "started", "active"):
            break
        time.sleep(2)
    say_("session ready")
    return sid


# ---------- facebook ----------
def fb_create_live():
    out = subprocess.run([sys.executable, os.path.join(HERE, "fb_tool.py"), "live", "create"], capture_output=True, text=True)
    print(out.stdout)
    if out.returncode != 0:
        sys.exit("fb_tool live create failed: " + out.stderr[-400:])
    rtmp = next((l.split("rtmp:", 1)[1].strip() for l in out.stdout.splitlines() if l.startswith("rtmp:")), "")
    perma = next((l.split("permalink:", 1)[1].strip() for l in out.stdout.splitlines() if l.startswith("permalink:")), "")
    if not rtmp:
        sys.exit("no rtmp url from fb_tool")
    endpoint, key = rtmp.rsplit("/", 1)
    return endpoint + "/", key, perma


def attach_rtmps(sid, endpoint, key, name="Facebook Live"):
    body = {"type": "rtmps", "name": name, "auto_connect": True, "transport": {"endpoint": endpoint, "stream_key": key}}
    j = req("POST", f"/sessions/{sid}/outputs", headers={**AUTH, "Content-Type": "application/json", "Idempotency-Key": f"fb-{sid[:8]}-{uuid.uuid4().hex[:6]}"}, json=body)
    oid = j.get("output_id") or j.get("id")
    say_(f"rtmps output {oid} → {endpoint}")
    for _ in range(30):
        outs = req("GET", f"/sessions/{sid}/outputs", headers=AUTH)
        items = outs if isinstance(outs, list) else outs.get("outputs", outs.get("items", []))
        me = next((o for o in items if (o.get("output_id") or o.get("id")) == oid), None)
        if me:
            state = str(me.get("state") or me.get("status") or "").lower()
            say_(f"output state: {state}")
            if state in ("connected", "streaming", "live", "healthy"):
                return oid
            if state in ("failed", "error"):
                sys.exit(f"output failed: {me}")
        time.sleep(2)
    say_("output not confirmed connected in 60s — check GET outputs + FB Live Producer")
    return oid


# ---------- speak ----------
def speak(sid, text, mode="append", tts=None):
    body = {"text": text, "mode": mode, "command_id": f"maya-{uuid.uuid4().hex[:8]}"}
    if tts:
        body["tts_provider"] = tts
    t0 = time.time()
    req("POST", f"/sessions/{sid}/speak", headers={"Content-Type": "application/json"}, json=body)
    return time.time() - t0


def interrupt(sid):
    requests.post(f"{BASE}/sessions/{sid}/interrupt", timeout=10)


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up"); u.add_argument("--avatar", default="maya"); u.add_argument("--model", default="quicktalk")
    u.add_argument("--tts", default=E("OT_TTS", "openai")); u.add_argument("--stt", default=E("OT_STT", "funasr")); u.add_argument("--no-fb", action="store_true")
    u.add_argument("--rtmps-endpoint", default=""); u.add_argument("--stream-key", default="")
    s = sub.add_parser("say"); s.add_argument("text"); s.add_argument("--mode", default="append")
    sub.add_parser("status"); sub.add_parser("down"); sub.add_parser("interrupt")
    a = ap.parse_args()
    st = load_state()
    if a.cmd == "up":
        sid = create_session(a.avatar, a.model, a.tts, a.stt)
        st = {"sid": sid, "avatar": a.avatar, "model": a.model, "tts": a.tts, "started": time.time()}
        if not a.no_fb:
            if a.rtmps_endpoint and a.stream_key:
                ep, key, perma = a.rtmps_endpoint, a.stream_key, ""
            else:
                ep, key, perma = fb_create_live()
            st["permalink"] = perma
            st["output_id"] = attach_rtmps(sid, ep, key)
            say_(f"LIVE → comment here: {perma}")
        save_state(st)
        speak(sid, "Hey — I'm Maya. Yes, an AI host, live right now. Ask me anything in the chat.", mode="replace", tts=a.tts)
        say_("intro spoken; use `ot_live.py say \"...\"` or chat_bridge.py for comments")
    elif a.cmd == "say":
        if not st.get("sid"):
            sys.exit("no session — run `up` first")
        dt = speak(st["sid"], a.text, a.mode, st.get("tts"))
        say_(f"speak accepted in {dt:.2f}s: {a.text[:80]}")
    elif a.cmd == "interrupt":
        interrupt(st["sid"]); say_("interrupted")
    elif a.cmd == "status":
        if not st.get("sid"):
            sys.exit("no session")
        print(json.dumps({"session": requests.get(f"{BASE}/sessions/{st['sid']}", timeout=10).json(),
                          "outputs": req("GET", f"/sessions/{st['sid']}/outputs", headers=AUTH) if TOKEN else "no token"}, indent=2, ensure_ascii=False)[:3000])
    elif a.cmd == "down":
        sid = st.get("sid")
        if sid:
            if st.get("output_id"):
                requests.delete(f"{BASE}/sessions/{sid}/outputs/{st['output_id']}", headers=AUTH, timeout=10)
            requests.post(f"{BASE}/sessions/{sid}/stop", timeout=10); requests.delete(f"{BASE}/sessions/{sid}", timeout=10)
            say_("session stopped")
        if os.path.exists(STATE):
            os.remove(STATE)
        subprocess.run([sys.executable, os.path.join(HERE, "fb_tool.py"), "live", "current"], capture_output=True)
        say_("(end the FB live with: python fb_tool.py live end <live_video_id>)")


if __name__ == "__main__":
    main()
