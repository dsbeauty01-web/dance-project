# META APP REVIEW — full submission pack (4 scopes)

**App:** livestream (`1335138022110608`) · **Page:** MythicMingle (`1100248523396303`, 2,809 followers ✓ ≥100) · **Account age:** ≥60 days ✓
**Privacy Policy:** https://dsbeauty01-web.github.io/dance-project/privacy.html
**Prepared:** 2026-09-03 · Rebuilt to the meta-live-video-api skill (Live Video API use case, Graph v26.0).

> This pack PREPARES the submission. The human clicks **Submit** — the CLI never does.
> Each of the 4 permissions below has: a **justification** (workflow → data → benefit, no
> generic filler) and a **video shot-script**. Privacy patch = `PRIVACY-PATCH.md`.
> Page-role fix (MODERATE/MANAGE) = `PAGE-TASKS-FIX.md`. Paste-ready fields = `PASTE_ME.md`.

---

## Product one-liner (top of the review form)
Maya is an **AI-assisted live-shopping host for the Page owner's OWN Facebook Live broadcasts**.
On the Page's own live video, she reads viewer comments in real time, answers each viewer
**by name** on-stream and in a written reply, and sends the product link on purchase intent.
An **"AI host" disclosure label** is visible on the broadcast the entire time. Comments are
processed **transiently** for on-stream answers + an end-of-stream summary for the Page owner —
never sold, never used for ads, revocable anytime via Business Integrations.

---

## 1) `pages_read_engagement`  — read the live comments
**Workflow:** During the Page's own live video, our server polls
`GET /v26.0/{live-video-id}/comments?order=reverse_chronological&live_filter=filter_low_quality`
every ~5s using the Page token, dedupes by comment id, and pushes each new comment into the host's
answer queue.
**Data used:** comment `message`, author `from{name,id}`, comment `id`, `created_time`. Held only
in memory for the broadcast; discarded after the end-of-stream summary.
**Benefit (why the app fails without it):** without reading comments the host is blind to the
audience — she cannot answer questions or greet viewers by name, which is the entire product.
**Shot-script (clip 1, ~40s):**
1. Show operator console + connected Page name "MythicMingle".
2. On a second phone, post a comment "how much is the serum?" on the live.
3. Console shows that exact comment (name + text) appearing within ~5s.
4. Cut to the host answering that viewer by name on-stream.

## 2) `pages_manage_engagement`  — reply to comments as the Page
**Workflow:** When a comment is a question or purchase-intent, the app posts a short written
reply on that comment as the Page: `POST /v26.0/{comment-id}/comments` with a name-first line
(and the product link only on purchase intent). Rate-limited to ≤2/min, never the same user twice
in a row.
**Data used:** writes a short reply string (the host's answer); reads nothing new beyond scope 1.
**Benefit:** viewers who can't hear audio (muted/scrolling) still get a written, by-name answer
and a tappable link in the thread — this is what converts a comment into a click. Read-only alone
leaves every question silently unanswered in the thread.
**Shot-script (clip 2, ~40s):**
1. Post a comment "does it ship free?" on the live.
2. Host answers on-stream AND a written reply from the Page appears under that comment by name.
3. Post "I want to buy" → the Page reply includes the product link.
4. Show the reply was authored by the Page (MythicMingle), not a personal profile.

## 3) `pages_manage_posts`  — create & run the live video via API
**Workflow:** The app creates the broadcast programmatically:
`POST /v26.0/{page-id}/live_videos?status=LIVE_NOW` (title/description set), takes the returned
`secure_stream_url` (RTMPS) and streams Maya's video to it from our GPU pod; ends with
`POST /v26.0/{live-video-id}?end_live_video=true`.
**Data used:** creates a live video object owned by the Page (title, description, status). No
personal data.
**Benefit:** enables scheduled, unattended live shopping — the Page owner doesn't have to open
Live Producer and click Go Live for every session; the app starts/stops the broadcast on schedule.
**Shot-script (clip 3, ~30s):**
1. Trigger "Start live" in the operator console (no manual Live Producer).
2. The Page's live video appears on the Page feed as LIVE.
3. Trigger "End live" → the broadcast ends from the console.

## 4) `publish_video`  — publish the broadcast video to the Page
**Workflow:** The live video created in (3) publishes its RTMPS video stream as a live Page post;
on end, the recording remains as the Page's VOD (or is deleted via `DELETE /{id}` if the owner
opts out).
**Data used:** the outgoing video/audio stream Maya generates. No viewer personal data.
**Benefit:** the AI host actually appears as a normal Facebook Live on the Page — without this the
broadcast can be created but not published as video to the audience.
**Shot-script (clip 4, ~30s):**
1. With the live running (from clip 3), open the public Page as a viewer.
2. Show Maya's video playing as a normal Page Live, AI-disclosure label visible.
3. Show viewer count / the live badge on the public watch view.

---

## Reviewer test instructions (one combined run covers all 4)
1. Log in as an admin of the test Page **MythicMingle** (provided).
2. In the operator console click **Start live** → confirm the Page goes LIVE (scopes 3+4).
3. From a second account, post: a greeting, "how much?", "does it ship free?", "I want to buy",
   and a medical question ("will it cure acne?").
4. Within ~10s each: the console shows the comment (scope 1); the host answers by name on-stream;
   the Page posts a written reply (scope 2); purchase reply includes the product link; the medical
   one gets a safe deflection (no medical claim).
5. Click **End live** → broadcast ends, polling stops.
Screencast = clips 1–4 above in one take (~2–3 min). AI-disclosure label visible throughout.

## Eligibility checklist (must be green before Submit)
- [ ] App icon uploaded (`maya_app_icon_1024.png`) + Category = Business (App settings → Basic)
- [ ] Privacy Policy URL + Data-deletion URL = the privacy.html link (both set)
- [ ] Privacy policy updated per `PRIVACY-PATCH.md` (names comments + usernames as collected)
- [ ] "Access the Live Video API" use case added (Content management)
- [ ] Page role fixed to full control per `PAGE-TASKS-FIX.md` (MythicMingle tasks currently only
      MESSAGING+CREATE_CONTENT — need MODERATE+MANAGE for reply/moderation)
- [ ] Pipeline run once against a real Page live so the "API calls required" counters are non-zero
- [ ] Screencast recorded (clips 1–4)

## After approval (scripted, zero human)
`node scratchpad/sysuser.mjs` re-mints the system-user token WITH the 4 scopes → save as
META_SYSTEM_TOKEN → n8n Facebook credential → attach to W1-FB + chat_live → activate.
