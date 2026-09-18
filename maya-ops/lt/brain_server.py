#!/usr/bin/env python3
"""
brain_server.py — Maya's brain exposed as an OpenAI-compatible LLM endpoint for OpenTalking.

OpenTalking calls any OpenAI-compatible /v1/chat/completions. Point it here:
  OPENTALKING_LLM_BASE_URL=http://127.0.0.1:8795/v1   OPENTALKING_LLM_API_KEY=maya   OPENTALKING_LLM_MODEL=maya-brain
Every user message OpenTalking sends (a viewer comment, or the console) goes through OUR brain:
catalog truth gate, medical deflection, instant Q&A layer, memory, lead capture — then the answer text
returns as a normal completion (streaming supported), and OpenTalking speaks it (TTS → lips).

Reuses maya_host.py classes (same folder). Viewer name: send it as the first line "NAME: text" or via
the optional `user` field; the bridge does this for FB comments.

  python brain_server.py         # :8795
  curl localhost:8795/v1/chat/completions -H 'Content-Type: application/json' \
       -d '{"model":"maya-brain","messages":[{"role":"user","content":"Dana: how much is the serum?"}]}'
"""
import json, os, re, sys, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maya_host import CFG, Brain, Catalog, ChatEvent, CostMeter, Memory, OutputGate, Outputs, classify, MEDICAL_DEFLECTION  # noqa: E402
from instant import Instant  # noqa: E402

PORT = int(os.environ.get("BRAIN_PORT", "8795"))
meter = CostMeter(CFG)
mem = Memory(CFG.db_path)
cat = Catalog(CFG.catalog_path, CFG.product_key)
out = Outputs(CFG, meter)
brain = Brain(CFG, cat, mem, meter, leads=out.lead)
gate = OutputGate(CFG, meter)
INSTANT = Instant(cat.product)
MAX_WORDS = int(os.environ.get("MAYA_MAX_WORDS", "32"))
LAT = []


def cap_words(text: str, n: int = MAX_WORDS) -> str:
    """Spoken answers stay short: cut at the last sentence boundary within n words (never mid-sentence)."""
    words = text.split()
    if len(words) <= n:
        return text
    sents = re.split(r"(?<=[.!?…])\s+", text)
    out, count = [], 0
    for s in sents:
        w = len(s.split())
        if out and count + w > n:
            break
        out.append(s); count += w
    return " ".join(out) if out else " ".join(words[:n]) + "."


def split_name(text: str):
    m = re.match(r"^\s*([A-Za-z\u0590-\u05FF][\w\u0590-\u05FF ,.'&-]{0,60}?):\s+(.*)$", text.strip(), re.S)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", text.strip())


_SAY_RE = re.compile(r'"say"\s*:\s*"(.*?)(?:"\s*[,}]|$)', re.S)


def unwrap_envelope(s: str) -> str:
    """Never let a tool envelope reach TTS.

    A model that answers with {"say": "...", "lead": true} must be spoken as its `say`
    field only — otherwise she reads a brace and a quote out loud (she did, on air,
    2026-09-15, on the buy-link path). Handles a leading 'Name — ' prefix, and salvages
    the text when the JSON is truncated mid-string, which strict json.loads would drop.
    """
    if not s or "{" not in s:
        return s
    m = re.search(r"\{.*\}?", s, re.S)
    if not m:
        return s
    prefix, blob = s[:m.start()].strip(), m.group(0)
    inner = None
    try:
        d = json.loads(blob)
        if isinstance(d, dict) and isinstance(d.get("say"), str):
            inner = d["say"]
    except Exception:
        pass
    if inner is None:
        m2 = _SAY_RE.search(blob)
        if m2:
            inner = m2.group(1)
    if inner is None:
        return s
    inner = inner.replace('\\"', '"').strip()
    if not inner:
        return s
    if prefix:
        bare = prefix.rstrip("—- ").strip().lower()
        if bare and not inner.lower().startswith(bare):
            inner = f"{prefix} {inner}".strip()
    return inner


def answer(user_text: str, platform: str = "opentalking") -> str:
    t0 = time.time()
    name, text = split_name(user_text)
    ev = ChatEvent(platform, name.lower(), name, text, f"ot-{uuid.uuid4().hex[:8]}", time.time())
    c = classify(ev)
    if c.get("drop"):
        return f"{name} — let's keep it about the product. Ask me anything about the serum."
    mem.viewer_seen(ev, c["intent"])
    first = name.split()[0] if name else ""
    ins = None if c["intent"] == "medical" else INSTANT.match(text)
    if c["intent"] == "medical":
        say = MEDICAL_DEFLECTION.format(name=first or "Honest answer")
    elif ins:  # instant layer: 0 ms, catalog-true
        say = f"{first} — {ins}" if first else ins
        if c["intent"] == "purchase":
            mem.add_lead(ev, "purchase"); out.lead(ev, "purchase")
    else:
        act = brain.decide(ev, "ANSWER")
        say = cap_words(act.get("say") or "")
        if act.get("intent") == "purchase" and not act.get("lead_captured"):
            mem.add_lead(ev, "purchase"); out.lead(ev, "purchase")
    say = unwrap_envelope(say)   # every path: instant, LLM and deflection
    ok, why = gate.check(say)
    if not ok:
        say = f"{name.split()[0]} — let me stick to the catalog: twenty percent vitamin C, one drop every morning."
    lat = time.time() - t0
    LAT.append(lat); del LAT[:-50]
    mem.log_answer(ev, say, lat); mem.log_utterance(say, "answer")
    print(f"[brain {lat:.2f}s] {name}: {text[:60]!r} → {say[:90]!r}", flush=True)
    return say


def sse_chunk(cid, model, delta=None, finish=None):
    d = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()), "model": model,
         "choices": [{"index": 0, "delta": ({"content": delta} if delta else {}), "finish_reason": finish}]}
    return f"data: {json.dumps(d, ensure_ascii=False)}\n\n".encode()


class H(BaseHTTPRequestHandler):
    def _json(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            return self._send(200, {"object": "list", "data": [{"id": "maya-brain", "object": "model", "owned_by": "maya"}]})
        med = round(sorted(LAT)[len(LAT) // 2], 2) if LAT else None
        self._send(200, {"ok": True, "brain_latency_median_s": med, "product": cat.product.get("name"), "cost": meter.snapshot()})

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            return self._send(404, {"error": "not found"})
        j = self._json()
        msgs = j.get("messages") or []
        user = next((m.get("content", "") for m in reversed(msgs) if m.get("role") == "user"), "")
        if isinstance(user, list):  # multimodal content array
            user = " ".join(p.get("text", "") for p in user if isinstance(p, dict))
        text = answer(user or "hi", platform=j.get("user", "opentalking"))
        model = j.get("model", "maya-brain"); cid = "chatcmpl-" + uuid.uuid4().hex[:12]
        if j.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
            for sent in re.split(r"(?<=[.!?…])\s+", text):  # sentence chunks → TTS can start early
                if sent.strip():
                    self.wfile.write(sse_chunk(cid, model, delta=sent + " ")); self.wfile.flush()
            self.wfile.write(sse_chunk(cid, model, finish="stop")); self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
            return
        self._send(200, {"id": cid, "object": "chat.completion", "created": int(time.time()), "model": model,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": len(user.split()), "completion_tokens": len(text.split()), "total_tokens": len(user.split()) + len(text.split())}})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"brain_server on :{PORT}  product={cat.product.get('name')}  (OPENTALKING_LLM_BASE_URL=http://127.0.0.1:{PORT}/v1)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
