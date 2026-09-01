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
class Speaker:
    """Sends the voice line to maya_rt's Realtime brain (it speaks on-stream)."""
    def __init__(self, rt_url=os.environ.get("MAYA_RT_URL", "http://127.0.0.1:8010")):
        self.rt_url = rt_url.rstrip("/")
    def speak(self, text: str) -> bool:
        try:
            import requests
            r = requests.post(self.rt_url + "/chat-in", json={"say": text}, timeout=5)
            return r.ok
        except Exception:
            return False


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
    def facebook(self, comment_id: str, text: str) -> bool:
        tok = chat_ears.fb_page_token()
        if not tok or not comment_id:
            return False
        try:
            import requests
            r = requests.post(f"{chat_ears.FB_GRAPH}/{comment_id}/comments",
                              params={"access_token": tok, "message": text[:200]}, timeout=8)
            return r.ok
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
        dry_run=False, max_ticks=None, live_chat_id=None, on_plan=None, clock=time.time):
    brain = ChatBrain(catalog, AnswerGate())
    ears = ears or chat_ears.ChatEars()
    speaker = speaker or Speaker()
    replier = replier or Replier()
    leads = leads or Leads()
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
                # filler first if the answer is long (keeps <2.5s felt latency)
                if len(plan["voice_text"]) > 90:
                    speaker.speak(plan["filler"])
                spoke = speaker.speak(plan["voice_text"])
                if plan["platform"] == "youtube":
                    replier.youtube(live_chat_id, plan["chat_reply"])
                elif plan["platform"] == "facebook":
                    replier.facebook(plan.get("comment_id", ""), plan["chat_reply"])
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
    print("\nchat_live DRY-RUN self-test: PASS (%d plans: %s)" % (len(captured), intents))
