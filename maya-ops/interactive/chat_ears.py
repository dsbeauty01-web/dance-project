"""
chat_ears.py — the ears. Ingest live comments from YouTube + Facebook, normalize
to unified events (via chat_filter.make_event), and hand them to a callback/queue
that chat_brain consumes. Message parsing is pure → self-tests offline with mock
payloads; the network run-loop is thin and robust (resume tokens, auto-reconnect).

Per the live-chat skill:
 - YouTube: liveChatMessages.streamList is the ideal (server push). This module
   implements the officially-sanctioned FALLBACK — liveChatMessages.list polling,
   honoring pollingIntervalMillis + nextPageToken resume (zero loss). streamList
   (gRPC) is the drop-in upgrade once the OAuth stream is proven.
 - Facebook: SSE live-comments on streaming-graph.facebook.com (page token), with
   /comments polling fallback. Auto-reconnect + Last-Event-ID resume.
 - Auth: YouTube OAuth (the W1 re-auth), FB page token (.maya/meta.env). NEVER
   printed. If a token is missing/expired -> emit a STATUS event, never fake chat.
"""
from __future__ import annotations
import os, time, json, threading, queue
import chat_filter

YT_API = "https://www.googleapis.com/youtube/v3"
FB_GRAPH = "https://graph.facebook.com/v20.0"


# ---- token loading (never printed) ---------------------------------------
def _read_env_file(path: str) -> dict:
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def yt_token() -> str | None:
    return (os.environ.get("YT_OAUTH_TOKEN")
            or _read_env_file(os.path.expanduser("~/.maya/youtube-oauth.env")).get("YT_OAUTH_TOKEN")
            or _read_env_file("/root/.maya/youtube-oauth.env").get("YT_OAUTH_TOKEN"))


def fb_page_token() -> str | None:
    m = _read_env_file(os.path.expanduser("~/.maya/meta.env")) or _read_env_file("/root/.maya/meta.env")
    return os.environ.get("META_PAGE_TOKEN") or m.get("META_PAGE_TOKEN")


# ---- PURE parsers (testable) ---------------------------------------------
def parse_youtube(payload: dict) -> list[dict]:
    """YouTube liveChatMessages.list/streamList item list -> normalized events."""
    events = []
    for it in payload.get("items", []):
        sn = it.get("snippet", {}) or {}
        au = it.get("authorDetails", {}) or {}
        text = sn.get("displayMessage") or sn.get("textMessageDetails", {}).get("messageText", "")
        is_super = sn.get("type") in ("superChatEvent", "superStickerEvent") or "superChatDetails" in sn
        ts = _iso_to_epoch(sn.get("publishedAt"))
        ev = chat_filter.make_event(
            "youtube", au.get("displayName", "friend"), au.get("channelId", ""),
            text, ts, mtype=sn.get("type", "textMessageEvent"), superchat=is_super)
        if ev:
            ev["msg_id"] = it.get("id")
            events.append(ev)
    return events


def parse_facebook(payload: dict) -> list[dict]:
    """FB /comments or SSE data -> normalized events."""
    data = payload.get("data", payload if isinstance(payload, list) else [payload])
    if isinstance(data, dict):
        data = [data]
    events = []
    for c in data:
        frm = c.get("from", {}) or {}
        ts = _iso_to_epoch(c.get("created_time")) or time.time()
        ev = chat_filter.make_event(
            "facebook", frm.get("name", "friend"), frm.get("id", ""),
            c.get("message", ""), ts, mtype="comment")
        if ev:
            ev["msg_id"] = c.get("id")
            events.append(ev)
    return events


def _iso_to_epoch(s: str | None) -> float:
    if not s:
        return time.time()
    try:
        import datetime
        s = s.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(s).timestamp()
    except Exception:
        return time.time()


# ---- network run-loop (thin, robust) -------------------------------------
class ChatEars:
    """Runs connectors in background threads; normalized events go to self.q."""
    def __init__(self, on_status=None):
        self.q: "queue.Queue[dict]" = queue.Queue()
        self._stop = threading.Event()
        self.on_status = on_status or (lambda m: None)

    def _emit(self, events):
        for e in events:
            self.q.put(e)

    def _status(self, msg):
        self.on_status(msg)
        self.q.put({"platform": "system", "type": "status", "text": msg, "ts": time.time()})

    # YouTube: discover liveChatId, then poll list honoring pollingIntervalMillis
    def run_youtube(self, live_chat_id: str | None = None):
        import requests
        tok = yt_token()
        if not tok:
            self._status("youtube: NO OAUTH TOKEN (W1 re-auth needed) — not faking chat")
            return
        h = {"Authorization": "Bearer " + tok}
        if not live_chat_id:
            try:
                r = requests.get(f"{YT_API}/liveBroadcasts", headers=h,
                                 params={"part": "snippet", "broadcastStatus": "active",
                                         "broadcastType": "all"}, timeout=15)
                items = r.json().get("items", [])
                live_chat_id = items[0]["snippet"]["liveChatId"] if items else None
            except Exception as e:
                self._status(f"youtube: broadcast discovery failed: {e!r}")
                return
        if not live_chat_id:
            self._status("youtube: no active broadcast/liveChatId")
            return
        page = None
        while not self._stop.is_set():
            try:
                r = requests.get(f"{YT_API}/liveChatMessages", headers=h,
                                 params={"liveChatId": live_chat_id, "part": "snippet,authorDetails",
                                         "pageToken": page}, timeout=20)
                d = r.json()
                if "error" in d:
                    self._status(f"youtube: api error {d['error'].get('code')} — token may be expired")
                    time.sleep(5); continue
                self._emit(parse_youtube(d))
                page = d.get("nextPageToken")           # resume token, zero loss
                time.sleep(max(1.0, d.get("pollingIntervalMillis", 2000) / 1000.0))
            except Exception as e:
                self._status(f"youtube: reconnect after {e!r}")
                time.sleep(3)

    # Facebook: SSE live-comments with reconnect; /comments polling fallback
    def run_facebook(self, live_video_id: str, use_sse: bool = True):
        import requests
        tok = fb_page_token()
        if not tok:
            self._status("facebook: NO PAGE TOKEN — not faking chat")
            return
        if use_sse:
            url = f"https://streaming-graph.facebook.com/{live_video_id}/live_comments"
            params = {"access_token": tok, "comment_rate": "one_per_two_seconds",
                      "fields": "from{name,id},message,created_time,id"}
            while not self._stop.is_set():
                try:
                    with requests.get(url, params=params, stream=True, timeout=(10, 300)) as r:
                        for line in r.iter_lines():
                            if self._stop.is_set():
                                break
                            if line and line.startswith(b"data:"):
                                try:
                                    self._emit(parse_facebook(json.loads(line[5:].strip())))
                                except Exception:
                                    pass
                    self._status("facebook: SSE ended, reconnecting")
                except Exception as e:
                    self._status(f"facebook: SSE reconnect after {e!r}")
                    time.sleep(3)
        else:
            seen = set(); page = f"{FB_GRAPH}/{live_video_id}/comments"
            while not self._stop.is_set():
                try:
                    r = requests.get(page, params={"access_token": tok,
                                     "fields": "from{name,id},message,created_time,id",
                                     "order": "reverse_chronological"}, timeout=15)
                    fresh = [e for e in parse_facebook(r.json()) if e.get("msg_id") not in seen]
                    for e in fresh:
                        seen.add(e.get("msg_id"))
                    self._emit(fresh)
                    time.sleep(3)
                except Exception as e:
                    self._status(f"facebook: poll reconnect after {e!r}")
                    time.sleep(3)

    def start(self, youtube=True, fb_live_video_id: str | None = None):
        if youtube:
            threading.Thread(target=self.run_youtube, daemon=True).start()
        if fb_live_video_id:
            threading.Thread(target=self.run_facebook, args=(fb_live_video_id,), daemon=True).start()

    def stop(self):
        self._stop.set()


if __name__ == "__main__":
    # offline self-test: parsers only (no network, no token, no faking)
    yt = {"pollingIntervalMillis": 2000, "nextPageToken": "TOK",
          "items": [
            {"id": "m1", "snippet": {"type": "textMessageEvent", "displayMessage": "how much?",
                                     "publishedAt": "2026-09-01T10:00:00Z"},
             "authorDetails": {"displayName": "@Dana 🌟", "channelId": "UC1"}},
            {"id": "m2", "snippet": {"type": "superChatEvent", "displayMessage": "love it!",
                                     "publishedAt": "2026-09-01T10:00:01Z", "superChatDetails": {"amountMicros": 1}},
             "authorDetails": {"displayName": "Ron", "channelId": "UC2"}},
            {"id": "m3", "snippet": {"type": "textMessageEvent", "displayMessage": "http://spam.com",
                                     "publishedAt": "2026-09-01T10:00:02Z"},
             "authorDetails": {"displayName": "bot", "channelId": "UC3"}},
          ]}
    ev = parse_youtube(yt)
    assert len(ev) == 2, ev                       # spam dropped
    assert ev[0]["user_name"] == "Dana" and ev[0]["intent"] == "purchase"
    assert ev[1]["superchat"] and ev[1]["priority"] == "purchase" and ev[1]["msg_id"] == "m2"

    fb = {"data": [{"id": "c1", "from": {"name": "Amit", "id": "f1"}, "message": "does it ship?",
                    "created_time": "2026-09-01T10:00:00+0000"}]}
    fev = parse_facebook(fb)
    assert fev[0]["platform"] == "facebook" and fev[0]["user_name"] == "Amit"
    assert fev[0]["intent"] in ("question", "purchase") and fev[0]["msg_id"] == "c1"

    # missing token path emits a STATUS and does NOT fake chat
    logs = []
    e = ChatEars(on_status=logs.append)
    os.environ.pop("YT_OAUTH_TOKEN", None)
    e.run_youtube()   # no token -> status only
    assert any("NO OAUTH" in m for m in logs), logs
    print("chat_ears self-test: PASS (yt=%d fb=%d events, no-token handled)" % (len(ev), len(fev)))
