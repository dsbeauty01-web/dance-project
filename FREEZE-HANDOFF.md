# Animal Freeze — Session Handoff (2026-07-26)

Handoff for `animal-freeze.html` (standalone freeze-dance game, GitHub Pages:
https://dsbeauty01-web.github.io/dance-project/animal-freeze.html). Live Nova =
the SARAY V2V avatar iframe on pod **b9b6v8cljo578h** (room `nova-live`).

---

## ⛔ THE ONE BLOCKER (read first)

**Nova's avatar VIDEO is dark.** Root cause is NOT the game, device, code, or token:

```
LiveKit Cloud project novadance-1a7u3xfz:
  "connection minutes limit exceeded. please contact the project owner."
```

The browser cannot open a WebSocket to `novadance-1a7u3xfz.livekit.cloud` to
**subscribe** to the avatar's video track — the cloud refuses all new client
connections because the **connection-minutes quota is exhausted**. Verified three ways:
- Browser console: `room err could not establish signal connection: Encountered websocket error during connection establishment` (retries every region, all fail).
- Raw Node WebSocket to the signal endpoint: fails identically.
- `GET /rtc/validate` on the cloud: returns the quota message above.

Meanwhile the **publish side is healthy** (bridge publishing 12000+ frames, real
1076×1924 track live in the room) and **voice/brain works** (separate WS via the pod
proxy — a real conversation was confirmed in the pod logs). Only the browser→cloud
video subscribe is blocked.

⚠️ The pod's `lk_bridge` connected 24/7 is what **burns** these minutes. Leaving the
pod up keeps draining the quota (and GPU money).

**Fix = account action (owner):** upgrade the LiveKit plan, OR swap to another LiveKit
project (new URL+key+secret into `boot.sh` env on shared volume `1ditrne6cb` + restart),
OR self-host LiveKit on the pod. Nothing about the avatar's face is visible until this.

---

## ✅ What WORKS (verified this session)

- **Page loads clean** — 0 console errors on the live Pages URL (deployed `0471c0e`).
- **Pre-game ready-gate** (built this session): Nova loads → asks "ready?" → the
  **music holds** until the kid says **"yes"** (heard via the `kid-said` transcript)
  OR taps **"✋ I'm ready!"** → 3-2-1 → music. 25s soft-timeout so it never hangs;
  offline/pod-down skips the gate. **Headless-verified BOTH paths**: music gated
  (0 plays) until yes/tap, starts after, 0 console errors.
- **Voice / V2V brain** — works (mic chunks + OpenAI Realtime responses in pod logs;
  gate cycling). Model `gpt-realtime`, voice `marin`, room `nova-live`.
- **Speech log (transcripts)** — kid's real words → `#kid-bubble` (was already there);
  **Nova's real words → `#nova-say` (added this session, pod-side)**.
- **Pod-side features (DONE, do not re-patch):** `/set_avatar` (become-the-animal),
  tension-master persona injection, `nova-say`, and the `nova-cue` intent handler —
  all wired on BOTH sides (page ↔ rt_lk.py).
- **Full stack currently UP** on b9b6v8cljo578h: engine `:8010` + bridge `:9999` +
  rt_lk `:8765` (200). 3h auto-stop watchdog armed.

## ⚠️ What DOESN'T / UNVERIFIED

- **Avatar video** — dark (LiveKit quota, above). #1 blocker.
- ~~Full in-game timeline~~ — **VERIFIED ✅** (added post-write): a real-time headless
  playthrough (`scratchpad/qa_timeline.mjs`, SMART LAYER active) ran start-to-finish clean —
  reached the end screen **"🏆 ALL ANIMALS FROZEN!"**, all 5 stamps (⭐🐸🐻🦩⭐), score 1929,
  **0 console errors**. So the game logic + SMART LAYER + ready-gate are solid end-to-end.
- **Two taps to start** — "▶ Let's Play!" then "tap to talk to Nova" INSIDE the iframe
  (browser requires a gesture inside the iframe to grant the mic). UX wart, not a bug.
- **Live feel** — whether Nova reliably *asks* "ready?" (cue timing) and her voice/lipsync
  feel — needs Refael real-device play (I cannot test live voice; V2V is SACRED).

---

## BUILT this session  vs  LEFT from the call-and-response plan

**Built (call-and-response = the ready-gate):**
- `Ready` gate object + `runReadyGate()` (awaited in the start-btn handler BEFORE `countdown()`).
- `cueReady()` → sends `Live.cue` intent "greet + ask if ready" (fires on first iframe
  word and a 4s fallback; capped at 2 sends, pod-side overlap-gated).
- `#ready-bar` — low, non-blocking bar so Nova stays visible while she asks; `#ready-btn` tap fallback.
- Message-listener extended: any iframe word → `cueReady()`; kid text matching
  yes-words (`yes|yeah|ready|ok|go|sure|start|let's go|…`) → `Ready.hit()` → music starts.
- **rt_lk.py (pod)**: transcript-out emit — on `response.(output_)audio_transcript.done`
  → `nova_done` → page `parent.postMessage({type:'nova-said',text})` → the game's `NovaSay.log`.

**Already in the working copy (SMART LAYER — committed with the gate in `0471c0e`):**
- `Nova.cue(intent, ctx, pool)` — sends intent+context to her live brain instead of
  scripted lines; difficulty adaptation (`warnLead`/`effHold`), fake-outs on rounds 3-4
  (never the final), a "READY?" beat at song t≥20s, memory-based melts, no-repeat `Fallback` pools.

**Left / not built:**
- Unblock avatar video (LiveKit quota) — owner action.
- Full "live narration through the game on the game clock" (the broader in-game pitch
  plan) — the cue plumbing exists (`nova-cue`), but a per-beat spoken pitch plan for the
  whole song is not built here.
- One-tap start (merge the two mic gestures) — UX experiment, not attempted.

---

## Every file touched

**Repo (committed):**
- `animal-freeze.html` — ready-gate (CSS `#ready-bar`, HTML bar, `Ready`/`runReadyGate`/
  `cueReady`, listener extension, gate wired before countdown). Commit `0471c0e`
  (also carried the pre-existing SMART LAYER working-copy changes, as agreed).
- `FREEZE-HANDOFF.md` — this file.

**Pod b9b6v8cljo578h (shared volume `1ditrne6cb` — NOT a repo file):**
- `/workspace/rt_lk.py` — added the transcript-out emit (2 additive lines; no VAD/
  session/gating change — V2V pipe untouched). Backup at `/workspace/rt_lk.py.bak-transcript`.
  ⚠️ **Keep-vs-revert still pending Refael's call.** Do NOT re-patch rt_lk.py/app.py —
  they're "done" per the pod split.

**Scratchpad (throwaway test rigs, not in repo):** `qa_gate.mjs` (ready-gate test),
`qa_timeline.mjs` (full playthrough), `lk_sub_test.mjs` (LiveKit subscribe repro),
`lkcheck.py` (room participants), `patch_rtlk.py`, `start_rtlk.sh`, `arm_watchdog.sh`.

**Memory (outside repo):** `pod-ownership-split.md` (NEW), `animal-freeze-live-v2.md`,
`MEMORY.md` updated.

### Pod ownership (avoid collisions)
- **b9b6v8cljo578h = OURS** (freeze page → here). Pod-side done; frontend-only from here.
- **e7r72k1i9r4dcx = the other session's pod — leave alone.**
- Shared volume `1ditrne6cb`: don't edit `rt_lk.py`/`app.py`/`boot.sh` without flagging.
- `boot.sh` does `kill -9` on all services — run ONLY if `:8765` ≠ 200 (else it kills the live avatar).

---

## Top 3 next steps

1. **Unblock LiveKit** (owner action) — upgrade the `novadance-1a7u3xfz` plan, OR swap in
   another LiveKit project's URL+key+secret (into `boot.sh` env, then `boot.sh` since it'd
   be down), OR self-host LiveKit. This is the ONLY thing standing between "dark" and a
   visible avatar. Then re-run `scratchpad/lk_sub_test.mjs` — expect `videoW>0`.
2. **Real-device verify the call-and-response** — does Nova reliably ASK "ready?" and does
   "yes" start the music? If she doesn't ask cleanly, it's `cueReady` timing (tune the delay
   / retry), not the gate (gate + tap fallback are proven solid). Confirm her words show in
   `#nova-say`.
3. **Decide the two-tap → one-tap start UX** (merge the "Let's Play" gesture with the
   in-iframe "tap to talk" mic grant). (Full-timeline gameplay is already verified — see above.)

_Live now: pod up (watchdog 3h), page deployed. Voice + gate work; only the avatar video
is blocked on the LiveKit quota._
