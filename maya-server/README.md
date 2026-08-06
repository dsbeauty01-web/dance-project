# maya-server — the switchboard (Phase 2)

State + routing. The brain talks, n8n integrates, this owns neither.

## Run it

```bash
pip install -r requirements.txt
MAYA_BRAIN=http://127.0.0.1:8765 python app.py       # listens on :8000
```

Env: `MAYA_SERVER_PORT` (8000) · `MAYA_BRAIN` (http://127.0.0.1:8765) ·
`MAYA_CATALOG` (./catalog.json) · `MAYA_REPORTS` (./reports) · `MAYA_BLOCKLIST` (csv).

It runs best **on the pod**, next to the brain: `/session/start` health-checks the brain
over localhost, and the alternative is a public port on someone's laptop.

## Verify it (do this before every stream)

```bash
node tools/qa-maya-backend.mjs http://localhost:8000
```

22 assertions, no GPU and no OpenAI key needed — it stands in for the stage with a plain
websocket and checks what actually arrives. Nothing ships without its verify step passing.

## The one thing to understand

**This server never opens its own connection to the brain.** Every `/rt` connection is a
separate OpenAI Realtime session, so a second one would give Maya two brains and two
voices on one live stream. The stage page holds the single session; the switchboard routes
through the stage socket:

```
director ──POST──► maya-server ──WS /ws/stage──► maya-stage.html ──postMessage──►
pod page ──ws──► maya_rt.py ──► OpenAI Realtime + avatar engine
```

If the stage is not connected, director calls return **409 with a reason**. They are never
accepted and dropped — that failure mode cost Nova weeks.

## Pages

```
maya-director.html?saray=<pod-8765-url>&api=http://localhost:8000
maya-stage.html?saray=<pod-8765-url>&api=http://localhost:8000&scene=open
```

Drop `&api=` and both pages fall back to Phase-1 behaviour (director → stage by
postMessage, hardcoded demo product). The demo that already works does not depend on this
server being up.

## Answer modes

| mode | who answers | when to use |
|---|---|---|
| `approve` | operator releases each message (default) | pilots, first client streams |
| `auto` | everything that passed W2 goes straight to Maya | once you trust the filter |
| `manual` | operator types, Maya voices it verbatim | sensitive Q&A, regulated claims |

## Truth boundary

`catalog.json` is the only source of product facts. The `notes` string the brain receives
is built from catalog fields only — never from operator free text — so the panel can never
advertise a price Maya is forbidden to say. `forbidden_claims` per product raises an
operator alert if a regulated phrase appears in an outbound line; it is an **alarm, not a
filter**, because a post-check cannot unsay a sentence. The real block is the brain's
pre-synthesis truth gate.
