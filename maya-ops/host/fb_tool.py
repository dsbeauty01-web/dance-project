#!/usr/bin/env python3
"""
fb_tool.py — Facebook plumbing done right, once.

TOKENS
  python fb_tool.py token --user-token EAAB...     # short user token → long-lived (60d) → PAGE token (does not expire)
  python fb_tool.py check                          # expiry + scopes of the saved FB_PAGE_TOKEN (via /debug_token)
LIVE
  python fb_tool.py live create --title "..."      # creates LIVE_NOW → prints live_video_id, VIDEO id, rtmp, permalink
  python fb_tool.py live resolve <live_video_id>   # the id comments actually land on (live_video.video.id)
  python fb_tool.py live end <live_video_id>
  python fb_tool.py live current                   # finds the page's active LIVE + its video id

WHY the resolve step: comments and replies belong to the VIDEO object (live_video.video.id),
not the live_video id — polling/replying on the wrong one is why replies "didn't show".

ENV (~/.maya/host.env): FB_APP_ID FB_APP_SECRET FB_PAGE_ID FB_PAGE_TOKEN FB_API_VERSION(v21.0)
Writes FB_PAGE_TOKEN / FB_LIVE_VIDEO_ID / FB_VIDEO_ID back into ~/.maya/host.env.
"""
import argparse, os, re, sys, time
import requests

ENV_PATH = os.path.expanduser("~/.maya/host.env")


def load_env():
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))


def save_env(k: str, v: str):
    lines = open(ENV_PATH, encoding="utf-8").read().splitlines() if os.path.exists(ENV_PATH) else []
    lines = [l for l in lines if not l.startswith(k + "=")] + [f"{k}={v}"]
    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_PATH, 0o600)


load_env()
E = os.environ.get
G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"
PAGE = E("FB_PAGE_ID", "")


def get(path, **params):
    r = requests.get(f"{G}/{path}", params=params, timeout=15).json()
    if "error" in r:
        sys.exit(f"FB error on {path}: {r['error'].get('message')} (code {r['error'].get('code')})")
    return r


def post(path, **data):
    r = requests.post(f"{G}/{path}", data=data, timeout=15).json()
    if "error" in r:
        sys.exit(f"FB error on {path}: {r['error'].get('message')} (code {r['error'].get('code')})")
    return r


def cmd_token(user_token: str):
    ll = get("oauth/access_token", grant_type="fb_exchange_token", client_id=E("FB_APP_ID"),
             client_secret=E("FB_APP_SECRET"), fb_exchange_token=user_token)["access_token"]
    pages = get("me/accounts", access_token=ll).get("data", [])
    page = next((p for p in pages if p["id"] == PAGE), None)
    if not page:
        sys.exit(f"page {PAGE} not in /me/accounts — user must be admin with full tasks")
    tok = page["access_token"]
    save_env("FB_PAGE_TOKEN", tok)
    print("PAGE TOKEN saved to", ENV_PATH, "| tasks:", ",".join(page.get("tasks", [])))
    cmd_check(tok)


def cmd_check(tok: str = ""):
    tok = tok or E("FB_PAGE_TOKEN", "")
    if not tok:
        sys.exit("no FB_PAGE_TOKEN")
    app_tok = f"{E('FB_APP_ID')}|{E('FB_APP_SECRET')}"
    d = get("debug_token", input_token=tok, access_token=app_tok)["data"]
    exp = d.get("expires_at", 0)
    when = "NEVER (permanent page token)" if not exp else time.strftime("%Y-%m-%d %H:%M", time.localtime(exp))
    print("valid:", d.get("is_valid"), "| expires:", when, "| scopes:", ",".join(d.get("scopes", [])))
    need = {"pages_manage_engagement", "pages_read_engagement", "pages_manage_posts", "pages_show_list"}
    missing = need - set(d.get("scopes", []))
    print("MISSING SCOPES:" if missing else "scopes OK", ",".join(sorted(missing)))


def live_create(title: str):
    tok = E("FB_PAGE_TOKEN")
    r = post(f"{PAGE}/live_videos", status="LIVE_NOW", title=title,
             description="AI host Maya. Vitamin C serum, 20%, one drop every morning. Live price 149 ILS. Link below.",
             access_token=tok)
    info = get(r["id"], fields="id,permalink_url,secure_stream_url,stream_url,video", access_token=tok)
    vid = (info.get("video") or {}).get("id", "")
    save_env("FB_LIVE_VIDEO_ID", r["id"]); save_env("FB_VIDEO_ID", vid)
    print("live_video_id:", r["id"]); print("VIDEO id (comments live here):", vid)
    print("rtmp:", info.get("secure_stream_url") or info.get("stream_url"))
    print("permalink: https://www.facebook.com" + info.get("permalink_url", ""))


def live_resolve(live_id: str):
    info = get(live_id, fields="id,status,video,permalink_url", access_token=E("FB_PAGE_TOKEN"))
    vid = (info.get("video") or {}).get("id", "")
    save_env("FB_LIVE_VIDEO_ID", live_id); save_env("FB_VIDEO_ID", vid)
    print("status:", info.get("status"), "| VIDEO id:", vid, "| permalink: https://www.facebook.com" + info.get("permalink_url", ""))


def live_current():
    r = get(f"{PAGE}/live_videos", fields="id,status,video,permalink_url", broadcast_status='["LIVE"]', access_token=E("FB_PAGE_TOKEN"))
    for v in r.get("data", []):
        if v.get("status") == "LIVE":
            live_resolve(v["id"]); return
    print("no active LIVE")


def live_end(live_id: str):
    post(live_id, end_live_video="true", access_token=E("FB_PAGE_TOKEN")); print("ended", live_id)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("token"); t.add_argument("--user-token", required=True)
    sub.add_parser("check")
    l = sub.add_parser("live"); l.add_argument("action", choices=["create", "resolve", "end", "current"]); l.add_argument("arg", nargs="?"); l.add_argument("--title", default="Vitamin C Serum — LIVE | Maya (AI Host)")
    a = ap.parse_args()
    if a.cmd == "token": cmd_token(a.user_token)
    elif a.cmd == "check": cmd_check()
    elif a.action == "create": live_create(a.title)
    elif a.action == "resolve": live_resolve(a.arg)
    elif a.action == "current": live_current()
    elif a.action == "end": live_end(a.arg)
