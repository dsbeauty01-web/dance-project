# MAYA LOOP MODE — WHO DOES WHAT

**Written:** 2026-08-07 · The goal: Maya running a full selling stream from PRE-GENERATED
video (the Ctrip playlist design), with live reply-insertions — cheap enough to run for
hours, good enough to sell. Live/director mode stays as-is for demos.

The rule of the split: **you own truth, taste, and accounts. I own everything that is code.**

---

## PART 1 — YOUR LIST (nobody else can do these)

### A. Product truth (needed FIRST — everything builds on this)
- [ ] For each product you want in the stream (start with 2–3):
  - real name, real live price + regular price (the price ladder: regular → live → gift)
  - the free gift / coupon, if any
  - 3 selling points — not 5, not 1 — THREE (the playbook is strict on this)
  - one usage scenario ("in the evening after shower…")
  - one testimonial line you're allowed to use
  - shipping cost + delivery days + return policy (the #1 chat questions)
  - product photos: 2–3 per product, at least 1000px wide
- [ ] The forbidden list per product: anything you must NOT claim (health claims,
  "clinically proven", "הכי זול" — these get streams cut)

### B. Approvals (I draft, you approve — 15 minutes each round)
- [ ] Approve the Hebrew scripts I write from your product truth (5-part structure)
- [ ] Approve the "AI" disclosure label text + where it sits on screen (required by law
      on every platform — it gets baked into the video pixels)
- [ ] Pick her offline voice: I'll bake the same 3 sample lines in 2–3 Hebrew TTS voices,
      you pick one. (Loop mode can't use her live OpenAI voice — different pipe.)

### C. Accounts & money (your logins, your wallet)
- [ ] The 3 n8n credential clicks (OpenAI in W2, Google Sheets in W3, YouTube in W1)
      + give me the Leads sheet link — STILL OPEN from before
- [ ] A YouTube channel for the self-test (unlisted stream; needs live-streaming enabled —
      YouTube takes 24h to activate it the first time, so click "Go live" once NOW)
- [ ] Install OBS on this laptop (obsproject.com, 5 minutes) — it's not installed
- [ ] Say "bake" when you want the pod up for video generation (~2–4 pod-hours, ~$2–3
      per full bake run; same $0.74/hr pod, auto-stop armed)
- [ ] Security leftovers: delete the GitHub token, rotate the n8n key, rotate the 3 old
      leaked keys in boot.sh (GATE 0)

---

## PART 2 — MY LIST (all code; say "start loop mode" and I begin)

### Phase 1 — the bake pipeline (she records her product videos)
1. Script templater: your product truth → the 5-part Hebrew script (hook / 3 points /
   interaction / urgency / close) with the price repeated 3×.
2. Offline TTS → MuseTalk render on the pod: each script becomes her speaking it, 1080×1920,
   using the existing maya_idle bake + gesture clips at the section breaks.
3. Auto-cut into ≤15-second segments, each tagged {product, sequence} — this is what makes
   fast reply-insertion possible.
4. The AI disclosure label composited INTO the pixels of every segment.
→ Output: `maya-ops/playlist/<product>/*.mp4` on the volume + pushed to GitHub.

### Phase 2 — the playlist player (the stream itself)
5. Queue service on the pod: plays segments in order, loops the playlist, never starves.
6. RTMP out (and/or OBS virtual-camera path) so the SAME output feeds YouTube or Instagram.
7. Rotation: 2–3 script variants per product, switched every ~2h (recorded-as-live
   ban-signal countermeasure).

### Phase 3 — live reply insertion (what makes it feel alive)
8. Chat question → (n8n filter, already built) → LLM writes a ≤15s Hebrew answer →
   TTS + lipsync clip generated on the pod → inserted after the current segment →
   played ONCE and deleted. Target: answer on-stream within 10–40 seconds.
9. Keyword instant-answers for the big 5 (shipping / sizing / discount / material /
   after-sales) — pre-baked clips, zero generation wait.
10. Operator guardrails carried over: KILL switch works in loop mode too, forbidden-claims
    filter runs on every generated answer before it renders.

### Phase 4 — the self-test (M2 gate, on your unlisted YouTube)
11. Full dry run: playlist streaming, you ask questions from a second account, we measure
    comment→spoken-answer time, leads land in the sheet. The recording = your client demo.

---

## ORDER OF BATTLE (what actually happens next)

1. **You:** fill PART 1-A for 2–3 products (a voice message / rough notes is fine — I'll
   structure it). This unblocks everything.
2. **Me:** Phase 1 built + scripts drafted → you approve → "bake" → she records.
3. **You:** the n8n clicks + YouTube live enablement + OBS install (can happen in parallel).
4. **Me:** Phases 2–3.
5. **Together:** Phase 4 self-test → then it's demoable to a paying client.

My honest estimate: Phase 1 is the big one (~a day of my work + one bake run); 2 and 3 are
each a half-day; 4 is an hour once everything above exists.
