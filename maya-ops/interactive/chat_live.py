"""
chat_live.py — the runner (ears -> brain -> dual out). Pod-side entry point.

Loop: drain ChatEars queue -> ChatBrain.ingest -> ChatBrain.tick -> execute plan:
  1) SPEAK the voice line (maya_rt Realtime), with the name-first filler if slow.
  2) POST a short text reply in the chat thread (YouTube insert / FB reply).
  3) CAPTURE lead rows (BUY/ME/LINK) to the leads sink.

Outbound actions are pluggable (Speaker/Replier/Leads) so this runs in DRY-RUN
offline (prints the plan) and self-tests without network. Real senders are guarded
by tokens and NEVER fabricate — if a channel is down, it logs and keeps the voice.
"""
from __future__ import annotations
import os, time, json, queue

from chat_brain import ChatBrain, FILLER_AFTER_S
from answer_discipline import AnswerGate
import chat_ears


# ---- pluggable outbound -------------------------------------------------------
def build_rt_msg(kind: str, name: str = "", text: str = "") -> dict:
    """Exact wire shape maya_rt's /rt WebSocket expects (pure -> testable).
    'chat' = a viewer message; maya_rt answers THEM by name, truth-gated, in its
    own voice. 'say' = operator line spoken verbatim (fallback)."""
    if kind == "chat":
        return {"type": "chat", "name": name, "text": text}
    return {"type": "say", "text": text}


class Speaker:
    """Director channel into maya_rt's /rt WebSocket (port 8765). Forwards the viewer
    message as a 'chat' event so Maya answers by name in her own voice; falls back to
    'say' (verbatim) if asked. Persistent WS on a background asyncio thread. NEVER
    fabricates — returns False if the socket is down (caller keeps the queue)."""
    def __init__(self, rt_url=os.environ.get("MAYA_RT_WS", "ws://127.0.0.1:8765/rt")):
        self.rt_url = rt_url
        self._ws = None
        self._loop = None
        self._start()

    def _start(self):
        import threading, asyncio
        def _runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect())
            self._loop.run_forever()
        threading.Thread(target=_runner, daemon=True).start()

    async def _connect(self):
        try:
            import websockets
            self._ws = await websockets.connect(self.rt_url, max_size=16 * 1024 * 1024)
        except Exception:
            self._ws = None

    def _send(self, msg: dict) -> bool:
        import asyncio, json as _json
        if not self._loop:
            return False
        async def _do():
            if self._ws is None:
                await self._connect()
            if self._ws is None:
                return False
            await self._ws.send(_json.dumps(msg))
            return True
        try:
            fut = asyncio.run_coroutine_threadsafe(_do(), self._loop)
            return bool(fut.result(timeout=5))
        except Exception:
            return False

    def chat(self, name: str, text: str) -> bool:
        return self._send(build_rt_msg("chat", name, text))

    def say(self, text: str) -> bool:
        return self._send(build_rt_msg("say", text=text))

    # back-compat: speak() = say verbatim
    def speak(self, text: str) -> bool:
        return self.say(text)


class Replier:
    """Posts a text reply back into the live chat thread."""
    def youtube(self, live_chat_id: str, text: str) -> bool:
        tok = chat_ears.yt_token()
        if not tok or not live_chat_id:
            return False
        try:
            import requests
            body = {"snippet": {"liveChatId": live_chat_id, "type": "textMessageEvent",
                                "textMessageDetails": {"messageText": text[:200]}}}
            r = requests.post(f"{chat_ears.YT_API}/liveChatMessages",
                              params={"part": "snippet"},
                              headers={"Authorization": "Bearer " + tok}, json=body, timeout=8)
            return r.ok
        except Exception:
            return False
    def facebook(self, comment_id: str, text: str, live_video_id: str = "") -> bool:
        """Post a TOP-LEVEL comment on the live video (visible in the main chat panel,
        refreshes live). Falls back to a nested reply under the viewer's comment."""
        tok = chat_ears.fb_page_token()
        if not tok:
            return False
        try:
            import requests
            # top-level on the live video (reply_text should already be "@Name — ...")
            if live_video_id:
                r = requests.post(f"{chat_ears.FB_GRAPH}/{live_video_id}/comments",
                                  params={"access_token": tok, "message": text[:1000]}, timeout=8)
                if r.ok:
                    return True
            # fallback: nested reply
            if comment_id:
                r = requests.post(f"{chat_ears.FB_GRAPH}/{comment_id}/comments",
                                  params={"access_token": tok, "message": text[:1000]}, timeout=8)
                return r.ok
            return False
        except Exception:
            return False


class Leads:
    """Appends BUY/ME/LINK leads. Default = local JSONL; swap for n8n W3 append."""
    def __init__(self, path=os.environ.get("LEADS_PATH", "/workspace/maya-ops/leads/leads.jsonl")):
        self.path = path
    def add(self, row: dict) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return True
        except Exception:
            return False


# ---- the loop -----------------------------------------------------------------
def run(catalog: dict, ears=None, speaker=None, replier=None, leads=None,
        dry_run=False, max_ticks=None, live_chat_id=None, on_plan=None, clock=time.time,
        fb_live_video_id=""):
    brain = ChatBrain(catalog, AnswerGate())
    ears = ears or chat_ears.ChatEars()
    speaker = speaker or (None if dry_run else Speaker())
    replier = replier or Replier()
    leads = leads or Leads()
    # truth-gate maya_rt to the same catalog: push product notes once at startup
    if not dry_run and hasattr(speaker, "_send"):
        facts = catalog.get("facts", {})
        notes = " · ".join(f"{k}: {v}" for k, v in facts.items())
        try:
            speaker._send({"type": "product", "notes": notes})
        except Exception:
            pass
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        ticks += 1
        # 1) drain all pending ingest events
        drained = 0
        while True:
            try:
                ev = ears.q.get_nowait()
            except queue.Empty:
                break
            if ev.get("type") == "status":
                print("[ears]", ev.get("text"))
                continue
            brain.ingest(ev); drained += 1
        # 2) one answer per tick (discipline gates the rest)
        plan = brain.tick(clock())
        if plan and plan.get("action") == "answer":
            if on_plan:
                on_plan(plan)
            if dry_run:
                print(f"[SPEAK] {plan['voice_text']}")
                print(f"[REPLY:{plan['platform']}] {plan['chat_reply']}")
                if plan.get("lead_row"):
                    print(f"[LEAD] {plan['lead_row']}")
            else:
                # forward the viewer message -> maya_rt "chat": she answers BY NAME in
                # her own (truth-gated, in-language) voice. This is the primary path.
                spoke = speaker.chat(plan["user_name"], plan["viewer_text"])
                if plan["platform"] == "youtube":
                    replier.youtube(live_chat_id, plan["chat_reply"])
                elif plan["platform"] == "facebook":
                    replier.facebook(plan.get("comment_id", ""), plan["chat_reply"], fb_live_video_id)
                if plan.get("lead_row"):
                    leads.add(plan["lead_row"])
                if not spoke:
                    print("[warn] voice channel down — not faking; kept queue")
        if max_ticks is None:
            time.sleep(0.25)
    return brain


if __name__ == "__main__":
    # offline end-to-end DRY-RUN: fake ears queue -> full pipeline -> printed plans
    import sys, chat_filter
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # so ₪ prints on Windows consoles
    except Exception:
        pass
    cat = json.load(open(os.path.join(os.path.dirname(__file__),
                    "..", "loop", "scripts", "serum-c.en.json"), encoding="utf-8"))
    ears = chat_ears.ChatEars()
    mk = chat_filter.make_event
    for e in [mk("youtube", "@dana 🌟", "u1", "hi maya!", 1.0),
              mk("youtube", "Noa", "u2", "how much and does it ship?", 1.2),
              mk("youtube", "Ron", "u3", "will it cure my acne?", 1.4),
              mk("youtube", "Gil", "u4", "BUY", 1.6),
              mk("facebook", "Sara", "f1", "what's the vitamin c percent?", 1.8)]:
        if e: ears.q.put(e)
    captured = []
    _t = [1000.0]
    def clock():
        _t[0] += 35    # advance >30s per tick so the 2/min gate doesn't starve the test
        return _t[0]
    run(cat, ears=ears, dry_run=True, max_ticks=8, on_plan=captured.append, clock=clock)
    intents = [p["intent"] for p in captured]
    assert intents and intents[0] == "purchase", intents
    assert any(p["intent"] == "medical" and "medical" in p["voice_text"].lower() for p in captured)
    assert any(p.get("lead_row") for p in captured), "BUY should capture a lead"
    # placeholder buy_url in the real catalog -> flagged, no invented link
    assert all("http" not in p["chat_reply"] for p in captured)
    # maya_rt wire-shape (the /rt intake she actually reads)
    assert build_rt_msg("chat", "Noa", "how much?") == {"type": "chat", "name": "Noa", "text": "how much?"}
    assert build_rt_msg("say", text="hi") == {"type": "say", "text": "hi"}
    print("\nchat_live DRY-RUN self-test: PASS (%d plans: %s)" % (len(captured), intents))
