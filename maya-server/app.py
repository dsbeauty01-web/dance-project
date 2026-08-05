#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# MAYA-SERVER — the switchboard (MAYA-PLAN 05, Phase 2).
#
# THIN BY DESIGN. The brain (pod/maya_rt.py) does the talking, n8n does the
# integrations, this process owns STATE and ROUTING and nothing else.
#
# THE ONE ARCHITECTURAL DECISION WORTH READING:
#   This server does NOT open its own websocket to the brain's /rt.
#   Every /rt connection creates a SEPARATE OpenAI Realtime session, so a second
#   one would give Maya two brains and two voices talking over each other on a
#   live stream. The stage page already holds the single brain session (its pod
#   iframe owns the mic and the LiveKit subscription), so the switchboard routes
#   director + n8n traffic THROUGH the stage socket, exactly as the Phase-1
#   director did through postMessage. Same message shapes, new transport —
#   which is why the director's buttons did not change (01, "every action routes
#   through one send()").
#
#   director ─POST─► maya-server ─WS /ws/stage─► maya-stage.html ─postMessage─►
#   pod page ─ws─► maya_rt.py ─► OpenAI Realtime + engine
#
# NO SILENT DROPS. If the stage is not connected, a director call returns 409
# with a reason. The freeze game shipped a bridge that swallowed unknown message
# types with no error and Nova sat mute for weeks; every drop here is loud.
# ═══════════════════════════════════════════════════════════════════════════════
import os, json, time, uuid, asyncio, statistics, re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

HERE = Path(__file__).resolve().parent
CATALOG_PATH = Path(os.environ.get("MAYA_CATALOG", HERE / "catalog.json"))
REPORT_DIR = Path(os.environ.get("MAYA_REPORTS", HERE / "reports"))
BRAIN_URL = os.environ.get("MAYA_BRAIN", "http://127.0.0.1:8765")
PORT = int(os.environ.get("MAYA_SERVER_PORT", "8000"))

app = FastAPI(title="maya-server", version="1.0")
# The stage and director are static pages served from anywhere (localhost during
# Phase 2, OBS's browser source later), so the switchboard cannot know its
# callers' origins. It carries no secrets and no cookies — the keys live in the
# n8n credential store and the pod env (KEYS LAW) — so open CORS is safe here.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


# ── CATALOG — the ONLY source of product truth (TRUTH LAW) ────────────────────
class Catalog:
    """products[] from catalog.json. A client edits a Google Sheet, n8n writes
    this file, /catalog/reload picks it up mid-stream without a restart."""

    def __init__(self, path: Path):
        self.path = path
        self.products: List[Dict[str, Any]] = []
        self.loaded_at = 0.0
        self.load()

    def load(self) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.products = data.get("products", [])
            self.loaded_at = time.time()
        except FileNotFoundError:
            self.products = []
        return len(self.products)

    def get(self, pid: Optional[str]) -> Optional[Dict[str, Any]]:
        if not pid:
            return None
        for p in self.products:
            if p.get("id") == pid:
                return p
        return None

    @staticmethod
    def notes(p: Optional[Dict[str, Any]]) -> str:
        """The PRODUCT NOTES block the brain receives. This string IS the truth
        boundary: a fact that is not in here is a fact Maya does not have. Built
        from catalog fields only — never from operator free text."""
        if not p:
            return ""
        bits = [f"Product: {p.get('name_en') or p.get('name_he')}."]
        if p.get("price"):
            bits.append(f"Price: {p['price']}" + (f" (was {p['old_price']})." if p.get("old_price") else "."))
        if p.get("stock_note"):
            bits.append(f"Stock: {p['stock_note']}.")
        if p.get("delivery_note"):
            bits.append(f"Delivery: {p['delivery_note']}.")
        for b in p.get("bullets", []):
            bits.append(str(b) + ("" if str(b).endswith(".") else "."))
        return " ".join(bits)


CATALOG = Catalog(CATALOG_PATH)


# ── SESSION STATE ─────────────────────────────────────────────────────────────
STATE: Dict[str, Any] = {
    "stream_id": None,
    "client": os.environ.get("MAYA_CLIENT", "demo"),
    "scene": "open",
    "active_product": None,
    "answer_mode": "approve",   # 02 §4: approve for pilots, auto at trust
    "started": None,
    "hold": False,
    "lang": "he",
}

# ONE CLOCK (master plan law 7): every countdown and every session duration is
# derived from this single server-side timestamp. The freeze game ran timers on
# the page AND the pod and they drifted apart.
CLOCK = {"t0": None}

METRICS: Dict[str, Any] = {
    "messages_in": 0,
    "messages_answered": 0,
    "messages_dropped": 0,
    "latencies_ms": [],           # chat-in -> maya-said, per answered message
    "leads": 0,
    "per_product_questions": {},  # product_id -> count
    "said_lines": 0,
    "claim_alerts": [],           # outbound text that hit a forbidden_claim
    "voice_cost_est_usd": 0.0,    # from brain vitals; stays 0.0 until it reports
}

QUEUE: Dict[str, Dict[str, Any]] = {}   # msg_id -> queued viewer message
LEADS: List[Dict[str, Any]] = []


# ── MODERATION (05 §Moderation & safety) ──────────────────────────────────────
# Belt and suspenders over the brain's own truth gate. Two directions:
#   IN  — spam/abuse never reaches the prompt and never reaches the public rail.
#   OUT — if a line Maya SAID contains a product's forbidden claim, the operator
#         is alerted. A post-check cannot unsay it (the ghost-praise lesson), so
#         this is an alarm, not a filter — the real block is the truth gate.
BLOCKLIST = [w.strip().lower() for w in os.environ.get(
    "MAYA_BLOCKLIST", "זונה,שרמוטה,כוס אמك,fuck,bitch,whore,nigger,retard").split(",") if w.strip()]
LINK_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
REPEAT_RE = re.compile(r"(.)\1{6,}")


def moderate_in(name: str, text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {"ok": False, "reason": "empty"}
    low = t.lower()
    for w in BLOCKLIST:
        if w and w in low:
            return {"ok": False, "reason": "abuse"}
    t = LINK_RE.sub("", t).strip()          # link-strip: no promo spam on the rail
    t = REPEAT_RE.sub(r"\1\1\1", t)          # repeat-collapse: "אאאאאאאא" -> "אאא"
    if not t:
        return {"ok": False, "reason": "link_only"}
    if len(t) > 300:
        t = t[:300]
    return {"ok": True, "name": (name or "").strip()[:40] or "צופה", "text": t}


def forbidden_hits(text: str) -> List[str]:
    p = CATALOG.get(STATE["active_product"])
    if not p:
        return []
    low = (text or "").lower()
    return [c for c in p.get("forbidden_claims", []) if c and c.lower() in low]


# ── SOCKETS ───────────────────────────────────────────────────────────────────
class Hub:
    """One list of stage sockets, one of director sockets. A send to an empty
    stage list raises — the caller turns that into a 409 rather than pretending
    the message was delivered."""

    def __init__(self):
        self.stage: List[WebSocket] = []
        self.director: List[WebSocket] = []

    async def _fanout(self, socks: List[WebSocket], msg: Dict[str, Any]) -> int:
        dead, sent = [], 0
        for ws in list(socks):
            try:
                await ws.send_json(msg)
                sent += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in socks:
                socks.remove(ws)
        return sent

    async def to_stage(self, msg: Dict[str, Any]) -> int:
        n = await self._fanout(self.stage, msg)
        if n == 0:
            raise HTTPException(status_code=409, detail=(
                "stage not connected — open maya-stage.html with ?api=<this server> "
                "(nothing was sent; the brain never received this)"))
        return n

    async def to_director(self, msg: Dict[str, Any]) -> int:
        return await self._fanout(self.director, msg)


HUB = Hub()


def snapshot() -> Dict[str, Any]:
    p = CATALOG.get(STATE["active_product"])
    lat = METRICS["latencies_ms"]
    return {
        "state": STATE,
        "product": p,
        "queue": list(QUEUE.values()),
        "vitals": {
            "messages_in": METRICS["messages_in"],
            "messages_answered": METRICS["messages_answered"],
            "messages_dropped": METRICS["messages_dropped"],
            "queue_depth": len(QUEUE),
            "leads": METRICS["leads"],
            "median_latency_ms": int(statistics.median(lat)) if lat else None,
            "said_lines": METRICS["said_lines"],
            "voice_cost_est_usd": round(METRICS["voice_cost_est_usd"], 4),
            "elapsed_s": int(time.time() - CLOCK["t0"]) if CLOCK["t0"] else 0,
            "stage_connected": len(HUB.stage) > 0,
        },
    }


async def push_director(kind: str, **extra):
    await HUB.to_director({"ev": kind, **extra, "snap": snapshot()})


# ── SESSION ───────────────────────────────────────────────────────────────────
@app.post("/session/start")
async def session_start(body: Dict[str, Any] = Body(default={})):
    import aiohttp
    brain_ok, brain_info = False, None
    try:  # wake-pod check: refuse to pretend a dead brain is a live one
        async with aiohttp.ClientSession() as s:
            async with s.get(BRAIN_URL + "/health", timeout=aiohttp.ClientTimeout(total=8)) as r:
                brain_info = await r.json()
                brain_ok = bool(brain_info.get("ok"))
    except Exception as e:
        brain_info = {"error": str(e)}

    STATE["stream_id"] = body.get("stream_id") or f"maya-{int(time.time())}"
    STATE["client"] = body.get("client", STATE["client"])
    STATE["answer_mode"] = body.get("answer_mode", STATE["answer_mode"])
    STATE["lang"] = body.get("lang", STATE["lang"])
    STATE["scene"] = "open"
    STATE["hold"] = False
    STATE["started"] = time.time()
    CLOCK["t0"] = time.time()
    for k, v in (("messages_in", 0), ("messages_answered", 0), ("messages_dropped", 0),
                 ("leads", 0), ("said_lines", 0), ("voice_cost_est_usd", 0.0)):
        METRICS[k] = v
    METRICS["latencies_ms"], METRICS["per_product_questions"], METRICS["claim_alerts"] = [], {}, []
    QUEUE.clear(); LEADS.clear()
    if not STATE["active_product"] and CATALOG.products:
        STATE["active_product"] = CATALOG.products[0]["id"]
    await push_director("session")
    return {"ok": True, "stream_id": STATE["stream_id"], "brain_ok": brain_ok,
            "brain": brain_info, "catalog": len(CATALOG.products), "state": STATE}


@app.post("/session/end")
async def session_end():
    lat = METRICS["latencies_ms"]
    report = {
        "stream_id": STATE["stream_id"],
        "client": STATE["client"],
        "started": STATE["started"],
        "ended": time.time(),
        "duration_s": int(time.time() - CLOCK["t0"]) if CLOCK["t0"] else 0,
        "messages_in": METRICS["messages_in"],
        "messages_answered": METRICS["messages_answered"],
        "messages_dropped": METRICS["messages_dropped"],
        "median_answer_latency_ms": int(statistics.median(lat)) if lat else None,
        "leads": LEADS,
        "per_product_questions": METRICS["per_product_questions"],
        "said_lines": METRICS["said_lines"],
        "claim_alerts": METRICS["claim_alerts"],
        # Honest nulls: peak viewers needs a platform API we do not have yet, and
        # pod cost is billed by RunPod, not observable from here. Never fake a
        # number that a client will read as measured.
        "peak_viewers": None,
        "voice_cost_est_usd": round(METRICS["voice_cost_est_usd"], 4),
        "pod_cost_usd": None,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"session-report-{STATE['stream_id'] or 'unknown'}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    await push_director("session_end", report=report)
    return {"ok": True, "report": report, "path": str(path)}


@app.get("/state")
async def get_state():
    return snapshot()


@app.get("/health")
async def health():
    return {"ok": True, "service": "maya-server", "stage_connected": len(HUB.stage),
            "director_connected": len(HUB.director), "catalog": len(CATALOG.products)}


# ── CATALOG ───────────────────────────────────────────────────────────────────
@app.get("/catalog")
async def get_catalog():
    return {"products": CATALOG.products, "loaded_at": CATALOG.loaded_at,
            "active": STATE["active_product"]}


@app.post("/catalog/reload")
async def reload_catalog():
    n = CATALOG.load()
    await push_director("catalog")
    return {"ok": True, "products": n}


@app.post("/catalog")
async def put_catalog(body: Dict[str, Any] = Body(...)):
    """The client edits a Google Sheet, n8n pushes the rows here (Phase 3). Writes
    catalog.json and reloads it live — no restart, mid-stream safe.

    REFUSES a bad payload rather than accepting it. An empty or malformed products list
    would leave Maya with NO facts at all, and under TRUTH LAW no facts means she answers
    "I'll check that for you" to every question for the rest of the stream. A sync that
    fails loudly is recoverable; one that silently empties her is not."""
    products = body.get("products")
    if not isinstance(products, list) or not products:
        raise HTTPException(400, "products must be a non-empty list — refusing to empty the catalog")
    bad = [p for p in products if not isinstance(p, dict) or not p.get("id")
           or not (p.get("name_he") or p.get("name_en"))]
    if bad:
        raise HTTPException(400, f"{len(bad)} row(s) missing id or name — nothing was written")

    payload = {"_meta": {"source": body.get("source", "n8n sheet sync"), "synced_at": time.time()},
               "products": products}
    CATALOG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    n = CATALOG.load()

    # If the active product vanished from the sheet, do NOT silently switch what she is
    # selling on air — hold the old id, tell the operator, and let them choose.
    warning = None
    if STATE["active_product"] and not CATALOG.get(STATE["active_product"]):
        warning = (f"active product '{STATE['active_product']}' is no longer in the catalog — "
                   "pick another before the next scene change")
    await push_director("catalog", warning=warning)
    return {"ok": True, "products": n, "warning": warning}


# ── DIRECTOR ACTIONS ──────────────────────────────────────────────────────────
@app.post("/scene")
async def set_scene(body: Dict[str, Any] = Body(...)):
    scene = body.get("scene")
    if scene not in ("open", "product", "offer", "close"):
        raise HTTPException(400, "scene must be open|product|offer|close")
    if body.get("product_id"):
        if not CATALOG.get(body["product_id"]):
            raise HTTPException(404, f"no product {body['product_id']} in catalog")
        STATE["active_product"] = body["product_id"]
    STATE["scene"] = scene
    p = CATALOG.get(STATE["active_product"])
    # product panel data + the notes go together: a scene switch that changed the
    # product must never leave the brain holding the previous product's notes
    # (MAYA-CONTRACT: "Never keep stale notes after a product switch").
    await HUB.to_stage({"act": "scene", "name": scene, "product": p, "notes": Catalog.notes(p)})
    await push_director("scene")
    return {"ok": True, "scene": scene, "product": p}


@app.post("/say")
async def say(body: Dict[str, Any] = Body(...)):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text required")
    hits = forbidden_hits(text)   # operator lines are checked too — a regulated
    if hits:                      # claim is illegal whoever typed it
        METRICS["claim_alerts"].append({"src": "operator", "text": text, "hits": hits, "ts": time.time()})
        await push_director("claim_alert", text=text, hits=hits)
    await HUB.to_stage({"act": "say", "text": text})
    return {"ok": True, "forbidden_hits": hits}


@app.post("/cue")
async def cue(body: Dict[str, Any] = Body(...)):
    intent = (body.get("intent") or "").strip()
    if not intent:
        raise HTTPException(400, "intent required")
    await HUB.to_stage({"act": "cue", "intent": intent, "ctx": body.get("ctx", "")})
    return {"ok": True}


@app.post("/gesture")
async def gesture(body: Dict[str, Any] = Body(...)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    await HUB.to_stage({"act": "gesture", "name": name})   # manual always preempts (03 rule 2)
    return {"ok": True}


@app.post("/hold")
async def hold(body: Dict[str, Any] = Body(...)):
    on = bool(body.get("on"))
    STATE["hold"] = on
    await HUB.to_stage({"act": "hold", "on": on})
    await push_director("hold")
    return {"ok": True, "hold": on}


@app.post("/kill")
async def kill():
    """OPERATOR SUPREMACY: one call does all three — brain hold, intake pause,
    stage BRB overlay. Three separate calls means three chances to half-stop."""
    STATE["hold"] = True
    await HUB.to_stage({"act": "kill"})
    await push_director("kill")
    return {"ok": True, "hold": True, "intake": "paused"}


# ── CHAT PATH (n8n W2 -> here -> brain) ───────────────────────────────────────
@app.post("/chat-in")
async def chat_in(body: Dict[str, Any] = Body(...)):
    """Called by n8n W2 with an already-classified message. Answer-mode decides
    whether it reaches Maya's mouth now, or waits for the operator."""
    mod = moderate_in(body.get("name", ""), body.get("text", ""))
    METRICS["messages_in"] += 1
    if not mod["ok"]:
        METRICS["messages_dropped"] += 1
        await push_director("chat_dropped", reason=mod["reason"])
        return {"ok": False, "dropped": mod["reason"]}

    item = {
        "id": body.get("msg_id") or uuid.uuid4().hex[:10],
        "platform": body.get("platform", "youtube"),
        "name": mod["name"],
        "text": mod["text"],
        "lang": body.get("lang", STATE["lang"]),
        "priority": body.get("priority", "question_product"),
        "product_id": body.get("product_id") or STATE["active_product"],
        "ts": time.time(),
        "status": "queued",
    }
    pid = item["product_id"]
    if pid:
        METRICS["per_product_questions"][pid] = METRICS["per_product_questions"].get(pid, 0) + 1

    # The rail shows only what passed moderation (05: spam never on screen).
    try:
        await HUB.to_stage({"act": "rail", "name": item["name"], "text": item["text"]})
    except HTTPException:
        pass   # no stage yet is not a reason to lose the message from the queue

    if STATE["answer_mode"] == "auto" and not STATE["hold"]:
        return await _release(item)

    QUEUE[item["id"]] = item
    await push_director("chat_queued", item=item)
    return {"ok": True, "queued": item["id"], "mode": STATE["answer_mode"]}


async def _release(item: Dict[str, Any]):
    item["status"] = "sent"
    item["sent_ts"] = time.time()
    await HUB.to_stage({"act": "chat", "name": item["name"], "text": item["text"],
                        "lang": item["lang"], "priority": item["priority"], "id": item["id"]})
    QUEUE.pop(item["id"], None)
    PENDING[item["id"]] = item          # waits for maya-said to close the latency loop
    await push_director("chat_sent", item=item)
    return {"ok": True, "sent": item["id"]}


PENDING: Dict[str, Dict[str, Any]] = {}


@app.post("/chat-approve/{msg_id}")
async def chat_approve(msg_id: str):
    item = QUEUE.get(msg_id)
    if not item:
        raise HTTPException(404, "no such queued message")
    return await _release(item)


@app.post("/chat-reject/{msg_id}")
async def chat_reject(msg_id: str):
    item = QUEUE.pop(msg_id, None)
    if not item:
        raise HTTPException(404, "no such queued message")
    METRICS["messages_dropped"] += 1
    await push_director("chat_rejected", item=item)
    return {"ok": True}


@app.post("/chat-answer/{msg_id}")
async def chat_answer(msg_id: str, body: Dict[str, Any] = Body(...)):
    """manual mode: the operator writes the answer, Maya voices it verbatim."""
    item = QUEUE.pop(msg_id, None)
    if not item:
        raise HTTPException(404, "no such queued message")
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text required")
    await HUB.to_stage({"act": "say", "text": text})
    item["status"] = "answered_by_operator"
    METRICS["messages_answered"] += 1
    await push_director("chat_answered", item=item)
    return {"ok": True}


@app.post("/answer-mode")
async def answer_mode(body: Dict[str, Any] = Body(...)):
    mode = body.get("mode")
    if mode not in ("auto", "approve", "manual"):
        raise HTTPException(400, "mode must be auto|approve|manual")
    STATE["answer_mode"] = mode
    await push_director("answer_mode")
    return {"ok": True, "answer_mode": mode}


@app.get("/queue")
async def get_queue():
    return {"queue": list(QUEUE.values()), "mode": STATE["answer_mode"]}


# ── LEADS (n8n W3 mirrors them here so the director can toast them) ───────────
@app.post("/lead")
async def lead(body: Dict[str, Any] = Body(...)):
    item = {"ts": time.time(), "platform": body.get("platform", "youtube"),
            "name": body.get("name", ""), "handle": body.get("handle", ""),
            "product": body.get("product") or STATE["active_product"],
            "message": body.get("message", "")}
    LEADS.append(item)
    METRICS["leads"] += 1
    await push_director("lead", lead=item)
    return {"ok": True, "leads": METRICS["leads"]}


@app.get("/leads")
async def get_leads():
    return {"leads": LEADS}


# ── VITALS from the brain (via the stage socket or direct POST) ───────────────
@app.post("/vitals")
async def vitals(body: Dict[str, Any] = Body(...)):
    _absorb_vitals(body)
    await push_director("vitals")
    return {"ok": True}


def _absorb_vitals(v: Dict[str, Any]):
    if v.get("cost_est"):
        try:
            METRICS["voice_cost_est_usd"] += float(v["cost_est"])
        except (TypeError, ValueError):
            pass


def _absorb_said(text: str):
    METRICS["said_lines"] += 1
    hits = forbidden_hits(text)
    if hits:
        METRICS["claim_alerts"].append({"src": "maya", "text": text, "hits": hits, "ts": time.time()})
    # close the latency loop for the oldest message still waiting on an answer
    if PENDING:
        mid = sorted(PENDING, key=lambda k: PENDING[k]["sent_ts"])[0]
        item = PENDING.pop(mid)
        METRICS["messages_answered"] += 1
        METRICS["latencies_ms"].append(int((time.time() - item["sent_ts"]) * 1000))
    return hits


# ── WEBSOCKETS ────────────────────────────────────────────────────────────────
@app.websocket("/ws/stage")
async def ws_stage(ws: WebSocket):
    await ws.accept()
    HUB.stage.append(ws)
    await ws.send_json({"act": "hello", "state": STATE,
                        "product": CATALOG.get(STATE["active_product"]),
                        "notes": Catalog.notes(CATALOG.get(STATE["active_product"]))})
    await push_director("stage_connected")
    try:
        while True:
            data = await ws.receive_json()
            ev = (data.get("ev") or "").lower()
            if ev == "said":
                hits = _absorb_said(data.get("text", ""))
                await push_director("said", text=data.get("text", ""), hits=hits)
            elif ev == "vitals":
                _absorb_vitals(data)
                await push_director("vitals")
            elif ev == "status":
                await push_director("status", speaking=data.get("speaking"))
            elif ev == "gesture":
                await push_director("gesture", tag=data.get("tag"))
    except WebSocketDisconnect:
        pass
    finally:
        if ws in HUB.stage:
            HUB.stage.remove(ws)
        await push_director("stage_disconnected")


@app.websocket("/ws/director")
async def ws_director(ws: WebSocket):
    await ws.accept()
    HUB.director.append(ws)
    await ws.send_json({"ev": "hello", "snap": snapshot()})
    try:
        while True:
            await ws.receive_text()   # director talks over REST; this keeps the socket open
    except WebSocketDisconnect:
        pass
    finally:
        if ws in HUB.director:
            HUB.director.remove(ws)


@app.exception_handler(HTTPException)
async def http_exc(request, exc: HTTPException):
    # Loud, structured errors — "OAI: error" with no type/code cost a full
    # debugging cycle on Nova; the same rule applies to this server's own faults.
    return JSONResponse(status_code=exc.status_code,
                        content={"ok": False, "status": exc.status_code, "detail": exc.detail})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
