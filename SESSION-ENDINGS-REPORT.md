# SESSION RECORDING + SMART ENDINGS + AUTO-ANALYSIS — Build Report
**Date:** 2026-07-27 · **Branch:** main (both repos) · **Status:** built + self-tested; **not yet committed/pushed or deployed** (awaiting your go).

---

## TL;DR
All three builds are done and tested. The whole backend data path is proven against the **live** Supabase DB. Both game files boot cleanly with the worker down. Every ending renders correctly for all 6 games with **no zeros anywhere**. Two things need **you** before it's live: (1) deploy the worker + set 2 Render env vars, (2) commit/push the frontend. Details at the bottom.

---

## ⚠️ Important thing I found
The Supabase project you pointed me at was **not fresh** — it's a **>1-year-old project (created 2025-06-02) that was PAUSED** (free-tier auto-pause). Nothing could reach it. I **restored** it (non-destructive) via the Management API; it's now `ACTIVE_HEALTHY`. The only project on the account is `dcqgcuielogmjzlrlkku` (EU-central-1), so that's the one we're using.

Also: the key you pasted (`sbp_…`) is a **Personal Access Token** (account-level), not a project key. I used it (read-only + the restore) to discover the project and pull the real **`service_role`** key. **Please rotate the `sbp_` token** — it was pasted in plaintext. The `service_role` key lives only in `novapython/.env` (gitignored) — never in any client file, never committed.

---

## BUILD 1 — Session recording ✅

**Supabase** (project `dcqgcuielogmjzlrlkku`): `sessions` table created exactly to spec + RLS **enabled with no policies** (only the `service_role` key, which bypasses RLS, can touch it — the browser never gets near it). Two SQL functions give atomic jsonb work:
- `append_session_events(id, events, transcript)` — atomic array append (no read-modify-write race).
- `merge_session_feedback(id, feedback)` — shallow merge so partial feedback posts accumulate.

**Worker** (`novapython`, new files):
- `supabase_client.py` — dependency-light PostgREST layer over the existing `httpx` (no heavy `supabase` SDK). No-ops if env unset; every call best-effort.
- `session_api.py` — router `/api/v1`:
  - `POST /session/start {session_id, lang, device, app_version}` → country resolved from IP, **IP then discarded**, row inserted.
  - `POST /session/events {session_id, events, transcript}` → batched atomic append.
  - `POST /session/end {session_id, stats}` → set `ended_at` + stats, **fires Build-3 analysis in the background** (never blocks the response).
  - `POST /session/feedback {session_id, feedback}` → merge.
- Wired into `server.py` (`include_router`). CORS was already `*`, so GitHub Pages is allowed.

**Privacy:** country code only (edge headers first, else one guarded geo lookup), **IP never stored/logged**. No name/email/IP columns. A name can only ever appear incidentally inside transcript text (acceptable per spec).

**Client** (`dance-project/nova-session-rec.js`, shared by both files):
- `session_id = crypto.randomUUID()`, POST `/start` on load; batches every 30s + on `visibilitychange`/`pagehide`/`beforeunload` (fetch `keepalive:true`).
- In `nova-commercial.html` it **taps the existing `LOG_BUFFER`** (events ship as-is; transcript derived from `HEARD`→kid / `NOVA-SAID`→nova) — minimal edits to the 7.9k-line file.
- In `animal-freeze.html` (which had no logging infra) I added explicit hooks at the iframe message handler (transcript) and `endFreeze` (events).
- **Fire-and-forget:** everything wrapped; a dead worker = zero difference to the kid (proven — see QA).

## BUILD 2 — Smart endings, all games ✅
`dance-project/nova-ending.js` — **one component, all 6 games**, configured per game:
1. **Her moment** — praise built from THIS session's real data, by name (commercial: last `memory.moments`; freeze: best animal + seconds held). No data → celebrates presence ("you SHOWED UP and danced with me").
2. **Feedback ask** — "So… how was it for YOU?" → 😍 🙂 😕 whole-row buttons, one tap, **8s silent skip**. Then "Tell me one thing!" → mic already live, next kid line tagged `feedback_said` → `feedback.said`, **5s silent skip**. She reacts to the face in character.
3. **Hook** — per-game "tomorrow…" line (all 6 written) + "See you next time, [name]!"
4. **Exactly two buttons:** 🔁 Play again · 👋 Bye Nova.
5. Captures `{face, said, hook_shown}` + `/end` at arc completion (idempotent). EN + HE.

**Hard rules honored:** never a zero / "0 pts" / empty star row — the old star+points reveal is **replaced** by celebration-only text (raw numbers go to the DB record, not the kid's screen). Works in live / voice-only / silent (text always carries her lines).

**Voice + the SACRED-V2V law:** in **live** mode the worker's own goodbye stays her voice — the client does **not** speak over her (one-mouth law); the data-driven praise shows as text. In non-live modes the ending voices its exact lines via `/v2/tts`. *(If you'd rather she speak the exact data-driven praise line even in live mode, that needs a worker-side "say this line" path — that touches the sacred pipe, so I left it out. Your call.)*

## BUILD 3 — Auto-analysis ✅
- `session_analysis.py` — on `/session/end`, one cheap `gpt-4o-mini` call (input = events + transcript + stats) → the 6-line report (ENGAGEMENT / BEST MOMENT / STRUGGLE / CUE HEALTH / FEEDBACK / ONE FIX) saved to `analysis`. **Guardrail:** prompt forbids any speculation about the child's home/health/family — session observations only.
- **Daily rollup:** `POST /api/v1/rollup/daily` (idempotent per-day, writes a `game='_daily'` row). Render can't run reliable in-process cron, so **point a daily ping at this endpoint** (Render Cron Job / cron-job.org / GH Action). Protect it by setting `NOVA_ROLLUP_SECRET` (send as `X-Rollup-Secret`).

---

## QA RESULTS

1. **Full pipeline (backend, live DB):** insert → 2-batch atomic append (→ 2 events + 2 transcript) → end+stats → 2 partial feedback posts **merged into one object** → read back → cleanup. Also driven through the **real FastAPI router** (start/events/feedback/end all `{ok:true}`, row verified). `set_analysis` write + rollup **upsert-replace** verified. ✅ *(The OpenAI analysis call itself couldn't run locally — no local key — but it's the same pattern as your working `/v2/tts` and runs on Render.)*
2. **Kill-the-worker:**
   - *Client unit:* `fetch` forced to always reject → `NovaRec` start/event/transcript/feedback/end/flush/double-end **never threw**; 5 rejections all swallowed. ✅
   - *Both pages headless with worker down + faked camera:* `nova-commercial.html` and `animal-freeze.html` both boot, `NovaRec` initialized with a valid UUID, `NovaEnding.show` present, **zero errors from my code**. ✅
   - *Backend:* env unset → endpoints return `{ok:false}`, no crash. ✅
3. **Endings screenshots:** all 6 games + zero-check rendered and captured → `tools/end-<game>.png` (faces stage) and `tools/end-<game>-hook.png` (hook stage). Each shows the personalized moment + 3 faces + correct per-game hook + exactly 2 buttons. Rig: `tools/qa-smart-endings.js` → summary **PASS** (no zeros / 3 faces / 2 buttons across all).
4. **The zero-check:** empty session (no data) → ending celebrates presence, **no zeros anywhere** (asserted in the rig against the rendered text). ✅

Screenshots + machine-readable results: `tools/end-*.png`, `tools/smart-endings-qa.json`.
QA rigs added: `tools/qa-smart-endings.js`, `tools/qa-rec-smoke.js`, `tools/endings-preview.html`.
**No scratchpad patches were needed** — both game files were clean per the Treaty and edited directly (named-file edits only).

### Redacted sample `sessions` row (shape)
```json
{
  "id": "3599b460-…-52e6b54c3b74",
  "started_at": "2026-07-27T…Z", "ended_at": "2026-07-27T…Z",
  "country": "TH", "lang": "en", "device": "mobile", "app_version": "commercial-v1", "game": "joined",
  "events": [{"t": 1.0, "type": "GAME-HIT", "msg": "rib slide"}, …],
  "transcript": [{"t": 1.0, "who": "nova", "text": "YESSS!"}, {"t": 2.0, "who": "kid", "text": "look!"}],
  "stats": {"score": 420, "hits": 7, "maxCombo": 4},
  "analysis": "ENGAGEMENT: finished, talked back\nBEST MOMENT: rib slide @1.0s\n…",
  "feedback": {"face": "love", "said": "more please", "hook_shown": true}
}
```

---

## WHAT YOU NEED TO DO (to make it live)

1. **Worker (Render):** set two env vars, then deploy (push `novapython` → Render auto-deploys):
   - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` — **the exact values are in `novapython/.env`** (gitignored; I did not print the key here). Copy them into the Render dashboard.
   - Optional: `NOVA_ROLLUP_SECRET` (protect the rollup endpoint), `NOVA_ANALYSIS_MODEL` (default `gpt-4o-mini`), `NOVA_GEOIP=0` to disable the geo lookup.
   - Until deployed, `/api/v1/*` doesn't exist on Render yet — the client just no-ops harmlessly.
2. **Frontend (GitHub Pages):** commit + push `dance-project` (the 2 new JS files + the edits to `nova-commercial.html` and `animal-freeze.html`). I have **not** committed anything yet.
3. **Daily rollup:** schedule a once-a-day `POST` to `https://novapython.onrender.com/api/v1/rollup/daily` (with the `X-Rollup-Secret` header if you set the secret).
4. **Rotate the `sbp_` Personal Access Token** (it was pasted in plaintext).
5. **Real-device test:** the ending's live-voice path and the "tell me one thing" mic capture need a real phone/session to confirm end-to-end (headless can't exercise the LiveKit/SARAY voice).

## Files
**Worker (`novapython`):** `supabase_client.py`, `session_analysis.py`, `session_api.py` (new); `server.py`, `.gitignore`, `.env` (edited/created).
**Frontend (`dance-project`):** `nova-session-rec.js`, `nova-ending.js` (new); `nova-commercial.html`, `animal-freeze.html` (edited); `tools/qa-smart-endings.js`, `tools/qa-rec-smoke.js`, `tools/endings-preview.html`, `tools/end-*.png`, `tools/smart-endings-qa.json` (new).
