# MAYA CONTRACT v1 — message types between page/backend and `maya_rt.py`

**Status:** v1, 2026-08-04. Phase 0 deliverable.
**Why this file exists:** the freeze game shipped with an *undocumented* contract. The page sent
`nova-pick` and `nova-fact` that the brain implemented but nobody had written down, so nobody
noticed the page never sent them — Nova sat in her intro for weeks and could not praise a freeze.
Maya's contract is explicit, versioned, and covered by a contract test (08, standing rule 5).

**Transport:** browser page ⇄ `wss://<pod>-8765/rt` (JSON frames), same shape as Nova's relay.
The pod page bridges `postMessage` → websocket. **Any type added here must also be added to the
bridge forward-list** — a missing bridge entry is silent, and cost a full debugging cycle on Nova.

---

## Inbound (→ brain)

| type | from | payload | brain action | must-not |
|---|---|---|---|---|
| `say` | director / backend | `text` | Speak verbatim, once. De-dupe identical lines within a session. | Never re-word an operator line. |
| `cue` | director / backend | `intent`, `ctx` | Improvise ONE short line fulfilling `intent`, using `ctx` as facts. | Never read the intent aloud. |
| `chat` | n8n → backend | `name`, `text`, `lang`, `priority` | Answer that viewer **by name**, per current answer-mode. | Never answer a viewer whose message failed moderation. |
| `scene` | backend | `scene`, `product_notes` | `session.update`: swap the scene block. Fire scene-default gesture. | Never carry a previous scene's urgency into `open`. |
| `product` | backend | `notes` | Replace the PRODUCT NOTES block; reset the catalog truth gate. | Never keep stale notes after a product switch. |
| `hold` | director | `on` (bool) | `on`: drop mic frames, cancel in-flight speech, refuse ALL speech-producing input. `off`: resume. | Never leave a queued response able to fire during hold. |
| `persona` | page | `text` | **REPLACE** session instructions with `CORE_LAWS + text`. Never append. | Never append — see Nova lesson below. |

### Two Nova lessons baked in from day one

1. **`persona` REPLACES, never appends.** Nova's handler did `PROMPT + persona`. `PROMPT` was
   ~6.8 KB of ordered intro script and outranked every short game persona, so she ran the kids'
   intro *inside* the freeze game. Maya has no intro script to leak, but the handler must still
   replace, so a scene/persona switch is authoritative.

2. **`hold` must gate EVERY speech path, not just the mic.** The first Nova fix gated only audio
   and she still spoke three times when poked, because `text`, `cue` and `fact` each call
   `response.create` independently. Gate them all.

### `session.update` requires `"type": "realtime"`

Omitting it makes the update **fail silently** — the only symptom is a bare `OAI: error` and a
persona that never applies. Always send:

```json
{"type":"session.update","session":{"type":"realtime","instructions":"..."}}
```

Log the error `type/code/message/param` on every OpenAI error. A bare "error" line hid this bug
for a whole debugging cycle.

---

## Outbound (brain →)

| type | payload | consumer | notes |
|---|---|---|---|
| `maya-said` | `text` | page, backend, transcript | Emitted at speech **end**. |
| `gesture` | `tag` | page gesture engine | Emitted at speech **START**, not text-generation. See below. |
| `vitals` | `latency_ms`, `tokens`, `cost_est` | director console | Feeds the $/hr measurement Gate 2 needs. |
| `status` | `state`, `speaking` | page | `speaking:false` is the safe window for queued sends. |

### Why `gesture` fires at speech-start

Avatar swap is near-instant; the voice pipeline is **1–3 s**. Measured on Nova's identical stack:
**1.47 / 1.71 / 1.95 / 2.65 / 3.84 s → median 1.95 s.** Emitting the gesture when the text is
generated puts the wave up to two seconds before the word. Emit when TTS audio starts.

---

## Truth gate (sales version of MOVE-TRUTH LAW)

Product claims — price, stock, delivery, specs — are legal **only** if the fact is present in the
active `product_notes`. No note → no claim → "I'll check that for you" and route to operator.

The gate runs **pre-synthesis**, not as a post-filter. Nova's ghost-praise bug proved a
post-filter is too late: the line is already spoken by the time you inspect it.

---

## Contract test (standing rule 5)

`tools/qa-maya-contract.js` (or `.ps1` where node is unavailable) sends **every** inbound type and
asserts a response or observable effect:

- `say` → matching `maya-said` within 5 s
- `cue` → a `maya-said` that is NOT the intent text
- `chat` → reply containing the viewer's name
- `scene` → subsequent line reflects the new scene
- `product` → a claim about the new product is allowed; a claim about the old one is refused
- `hold on` → **zero** `maya-said` under a typed poke, a cue AND a fact
- `hold off` → speech resumes
- `persona` → instruction replacement verified by asking a question only the new persona answers

Runs in CI. **The freeze game died on an untested contract; Maya will not.**

---

## Changelog

- **v1 (2026-08-04):** initial contract. Types: say, cue, chat, scene, product, hold, persona.
  Outbound: maya-said, gesture, vitals, status.
