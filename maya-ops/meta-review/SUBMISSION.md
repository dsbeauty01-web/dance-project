# META APP REVIEW — submission pack for `pages_read_engagement` (Advanced Access)

**App:** livestream (1335138022110608) · **Business:** MythicMingle · **Prepared:** 2026-08-12

## Why we need review
Standard access proved unusable for server integration: system-user tokens are minted with
EMPTY scopes when the permission lacks Advanced Access (verified 2026-08-11 — the mint
"succeeds" and silently strips the scope). Advanced Access for `pages_read_engagement`
unlocks the permanent server token via the existing system user (id 122093295183446800,
already created and assigned to the page by script `scratchpad/sysuser.mjs` — re-run it
after approval and the token mints correctly).

## What the founder must do BEFORE submitting (10 min, one time)
1. **App icon** — upload any 1024×1024 PNG at App settings → Basic (currently empty; this
   alone makes the app "ineligible for submission").
2. **Category** — pick one on the same screen (suggest: Business and pages).
3. Data-use checkup if prompted — answers below are copy-paste ready.

## Copy-paste answers for the review form

**How will your app use pages_read_engagement?**
> Our app operates an AI-assisted live-shopping host for the Page owner's own live
> broadcasts. With the Page admin's consent, the app reads comments posted on the Page's
> live videos in real time so the human operator and the on-stream host can answer viewer
> questions during the broadcast. Comments are processed transiently to generate on-stream
> answers and an end-of-stream summary for the Page owner; they are not sold, shared, or
> used for advertising. Access can be revoked at any time via Business Integrations.

**Step-by-step reviewer instructions:**
> 1. Log in as a test user that admins a Facebook Page (or use the provided page).
> 2. Start a live video on the Page (Live Producer with any RTMP source).
> 3. Our server polls GET /{live-video-id}/comments (order=reverse_chronological,
>    live_filter=filter_low_quality) every 5 seconds.
> 4. Post a comment on the live video; within ~10 seconds the operator console displays
>    the comment and the host answers it on-stream by name.
> 5. Stop the live; polling stops automatically.

**Screencast:** record the M2 self-test (see maya-ops/M2-RUNBOOK.md) run on Facebook
instead of YouTube — one take covers both the demo recording and the review screencast.

## Facts to remember (from the meta-live-video-api skill)
- Page must have ≥100 followers and account ≥60 days for API lives — MythicMingle: 2,809 ✓
- Privacy policy + data deletion URLs already set: dsbeauty01-web.github.io/dance-project/privacy.html ✓
- App domains + OAuth redirect already configured ✓
- The "0 of 1 API call(s) required" counters on the Testing screen must be non-zero before
  submission — running the pipeline once against a real page live satisfies them.

## After approval (all scripted, zero founder)
`node scratchpad/sysuser.mjs` → mints the permanent system-user token WITH scopes →
save as META_SYSTEM_TOKEN → create n8n credential → attach to W1-FB → activate.
