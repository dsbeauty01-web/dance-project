# MAYA PHASE 2 — the switchboard, the chat layer, and what the wiring check found

**Date:** 2026-08-05 · **Branch:** `maya-p0` · **Pod:** `tn2wyavs39v9s9` (Secure 4090, EU-RO-1)

---

## 1. What Gate 1 could not have passed, and why

The stack was alive — engine, bridge and brain all up, Hebrew end to end, zero OpenAI
errors. But the founder reported she "talks by herself" and could not be driven. Three
defects in the pod page explain all of it, and none of them could show up in the GATE 1
contract run, because that harness drove the brain's websocket **directly** and never
crossed the page:

| # | defect | effect on the stream |
|---|---|---|
| 1 | The page's `postMessage` forward-list only accepted Nova's legacy `nova-*` names. `say`, `cue`, `chat`, `scene`, `product` and **`persona`** were dropped with no log. | The director looked fully wired and drove nothing. She ran her base prompt — her own instructions were the only ones that ever reached her — so she talked on her own. |
| 2 | The brain emits `{type:'gesture',tag}` at speech-start; the page never forwarded it to the parent. | The `[TAG]` → gesture path existed on both ends with nothing joining them. She never gestured on her own words. |
| 3 | The start gate called `/set_avatar?id=nova_idle`. | RESOLUTION LAW violation (1076×1924 vs 1080×1920) **and the wrong face**: click start on Maya's stream and Nova appears. |

MAYA-CONTRACT.md predicted #1 in bold — *"any type added here must also be added to the
bridge forward-list — a missing bridge entry is silent"* — and it happened anyway. The
forward-list is now a table with every contract type in it, and an un-openable socket
logs `DROPPED <type>` instead of returning quietly.

Also fixed: `maya-director.html`'s preview iframe was the literal string
`maya-stage.html?scene=open`, so `?saray=` could never reach it and the preview was
offline against every pod that will ever exist. It now forwards the director's own query
string.

## 2. `maya-server` — the switchboard (plan 05)

FastAPI, ~450 lines, `maya-server/app.py`. State and routing only.

**The one architectural decision:** this server never opens its own connection to the
brain. Every `/rt` connection is a separate OpenAI Realtime session, so a second one
would put two brains and two voices on one live stream. The stage page holds the single
session; everything routes through its socket.

```
director ──POST──► maya-server ──WS /ws/stage──► maya-stage.html ──postMessage──►
pod page ──ws──► maya_rt.py ──► OpenAI Realtime + avatar engine
```

The same reasoning closed a hazard that shipped in Phase 1: the director's preview is a
full copy of the stage, so in backend mode both would mount a pod iframe and she would
speak twice. The preview now runs with `?preview=1` — scenes, product panel and chat rail
still update, only her video and voice are absent.

Endpoints: `session/start|end` · `scene` · `say` · `cue` · `gesture` · `hold` · `kill` ·
`chat-in` · `chat-approve|reject|answer/{id}` · `answer-mode` · `lead` · `vitals` ·
`catalog[/reload]` · `state` · `ws/stage` · `ws/director`.

**No silent drops:** with no stage connected, a director call returns **409 with a reason**.

**Truth boundary:** the `notes` string the brain receives is built from `catalog.json`
fields only, never from operator text, so the product panel cannot advertise a price Maya
is forbidden to say. `forbidden_claims` raise an operator alert on outbound lines — an
alarm, not a filter, because a post-check cannot unsay a sentence.

**Honest numbers:** the session report writes `peak_viewers: null` and `pod_cost_usd: null`
rather than inventing figures a client would read as measured.

## 3. Contract test — 22 assertions, no GPU needed

```bash
node tools/qa-maya-backend.mjs http://localhost:8000     # 22 passed, 0 failed
```

It stands in for the stage with a plain websocket and asserts what actually arrives:
every route's shape, the 409-not-a-silent-drop rule, scene-carries-its-notes, approve /
auto / manual modes, abuse dropped, forbidden-claim alert, lead counted, report written.
It waits on events, never on a fixed quiet window — the pacing fault that scored two false
failures in GATE 1.

`maya-stage.html` and `maya-director.html` were added to `tools/laws/check-syntax.js`.

## 4. n8n layer (plan 04) — `n8n/`, importable

- **W1** YouTube ingest — 5s poll, `liveChatMessages.list`, forwards only new ids
  (without that de-dupe she re-answers the same viewer every 5 seconds).
- **W2** priority queue — spam/abuse filter → ONE gpt-4o-mini call per cycle → priority
  (buy_intent first, noise never reaches her) → same-question dedupe naming all askers →
  `/chat-in`; buy_intent forks to W3 in parallel so capture never waits for her mouth.
  A failed classifier call degrades to "treat as product question", flagged, never silent.
- **W3** lead capture — classifier `buy_intent` **or** a literal trigger word (two
  independent paths: the classifier can be wrong, "אני רוצה" cannot) → Sheets + director toast.

Wiring order and the sheet's header row are in `n8n/README.md`.

## 5. Still open

| item | note |
|---|---|
| **Conversation / auto-talk** | Not verified. Two of its likely causes are fixed (persona now arrives; every speech path is reachable), but `turn_detection.create_response:true` means she answers any audio the mic passes. Needs a live pass with the founder. |
| **Tag leak** (T2) | `[WAVE]` can still reach the transcript. Real fix is keyword auto-triggers from `maya-gestures.json`, pre-synthesis — not a post-filter. |
| **SAY verbatim** (T3) | Now actually testable: before this session the message never reached the brain from the page. |
| **Backend reachability** | maya-server runs on the pod and is reached from the laptop through an SSH tunnel (`-L 8000:127.0.0.1:8000`). Cloud n8n cannot reach it until the pod is recreated with an `8000/http` port — RunPod fixes ports at creation. |
| **GATE 0** | Still the three un-rotated keys, still plaintext in `/workspace/boot.sh`. |
| **Push** | Nothing on GitHub; needs interactive credentials. |

## 6. Cost

Pod `tn2wyavs39v9s9` at $0.74/hr with a **3-hour self-stop** armed (`/root/maya-watchdog.sh`,
REST endpoint, pod id literal — `$RUNPOD_POD_ID` is empty in a non-interactive ssh shell
and would have POSTed to `/pods//stop` and never stopped anything).
