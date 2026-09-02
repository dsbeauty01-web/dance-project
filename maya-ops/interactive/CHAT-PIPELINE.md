# Maya live-chat pipeline (T1–T3 built, pod-free, tested)

Implements the `live-chat` skill: viewer types -> Maya answers BY NAME on air +
posts a text reply + captures BUY leads. Built & unit-tested off the pod.

## Modules (maya-ops/interactive/)
| file | role | test |
|---|---|---|
| `chat_ears.py`   | INGEST — YouTube `liveChatMessages.list` (poll+resume token; streamList = upgrade) + Facebook SSE `live_comments` (poll fallback). Pure parsers `parse_youtube/parse_facebook`. | `python chat_ears.py` |
| `chat_filter.py` | Normalize + spam/link drop + injection tag (text is DATA) + name sanitize (single capitalized token, >20 shortened) + intent classify (purchase/question/greeting/medical/other). | `python chat_filter.py` |
| `chat_brain.py`  | Orchestrator — dedupe, skill-ordered priority (purchase>question>greeting; superchat top), truth-gated answer from `serum-c.en.json` facts/deflections, name-first, dual-out plan, latency log. Reuses `answer_discipline.AnswerGate`. | `python chat_brain.py` |
| `chat_live.py`   | Runner — ears→brain→**dual out**: SPEAK (maya_rt `/chat-in`), POST reply (YT insert / FB comment), CAPTURE lead (jsonl / n8n W3). DRY-RUN + injectable clock. | `python chat_live.py` |

## Data flow
comment → chat_ears (normalize) → queue → chat_brain.ingest → tick (gate+priority)
→ plan{voice_text, chat_reply, lead_row} → chat_live: speak + reply + lead.

## Discipline enforced (from the skill)
name-first · ≤2 answers/min · 8s cue gap · never same user twice while others wait ·
purchase>question>greeting · superchat tops · medical→deflection (never a claim) ·
injection text NEVER obeyed · buy link ONLY on purchase intent · latency logged
(comment ts → answer) to `maya-ops/metrics/chat_latency.log` · filler "Name — one sec…"
if answer would exceed 1.5s · NEVER fake chat when a pipe is down (emits STATUS).

## 🚧 HUMAN GATES before it can run live (T4)
1. **YouTube OAuth re-auth** (the W1 click) → token in `~/.maya/youtube-oauth.env`
   as `YT_OAUTH_TOKEN` (read chat + post replies). ⚠️ account had a "Verify it's you"
   failure 2026-09-01 — clear that first or the token won't hold.
2. **Facebook**: page token already in `.maya/meta.env` (`META_PAGE_TOKEN`); needs a
   live FB video id passed to `ChatEars.run_facebook`.
3. **Payment/buy_url**: still `PLACEHOLDER_SET_BY_HUMAN` in `serum-c.en.json`. Until a
   real link is set, purchase replies post WITHOUT a link and flag `[NEEDS-HUMAN]`.
4. ✅ **maya_rt wiring DONE**: `chat_live.Speaker` connects to maya_rt's real `/rt`
   WebSocket (port 8765) and forwards each admitted viewer message as
   `{"type":"chat","name","text"}` — maya_rt's existing chat handler answers them
   BY NAME in her own truth-gated voice. At startup it pushes the catalog facts via
   `{"type":"product","notes":...}` so her answers match the catalog. `build_rt_msg`
   wire-shape is unit-tested.

## T4 — prove it live (one pod session, ask first)
Unlisted broadcast, planted set + 2 humans: greeting→name hello · price→link reply ·
BUY→lead row + on-air confirm · medical trap→deflection · injection→ignored ·
kill the stream→auto-reconnect + "catching up…" once. Evidence + latency table
(<2.5s median) → `maya-ops/evidence/`. Pods down after, report cost.
