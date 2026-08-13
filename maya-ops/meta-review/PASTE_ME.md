# META APP REVIEW — copy-paste pack (livestream app, 1335138022110608)

Every field below is ready to paste. Icon: `maya_app_icon_1024.png` (in this folder).
**Category: Business.** Do NOT click Submit until the human reviews — this pack only prepares.

---

## App settings → Basic
- **App icon:** upload `maya_app_icon_1024.png`
- **Category:** Business
- **Privacy Policy URL:** `https://dsbeauty01-web.github.io/dance-project/privacy.html`
- **User data deletion:** Data deletion instructions URL → `https://dsbeauty01-web.github.io/dance-project/privacy.html`
- **App domains:** `dsbeauty01-web.github.io` (already set)

## Permission requested: `pages_read_engagement`

**What does your app use this permission for? (paste)**
> Our app operates an AI-assisted live-shopping host for a Facebook Page owner's own live
> broadcasts. With the Page admin's explicit consent, the app reads comments posted on the
> Page's live videos in real time so the human operator and the on-stream host can respond
> to viewers during the broadcast. Comments are processed transiently to generate on-stream
> replies and an end-of-stream summary for the Page owner. We do not sell, share for
> advertising, or retain comment data beyond the broadcast. Access is revocable at any time
> via Business Integrations.

**Step-by-step instructions for the reviewer (paste)**
> 1. Log in as a user who administers a Facebook Page (test page provided: MythicMingle).
> 2. Start a live video on the Page via Live Producer (any RTMP source).
> 3. Our server polls GET /{live-video-id}/comments (order=reverse_chronological,
>    live_filter=filter_low_quality) every 5 seconds using a Page access token.
> 4. Post a comment on the live video. Within ~10 seconds the operator console shows the
>    comment and the AI host answers it by name on-stream.
> 5. End the live; polling stops automatically.

## Screencast shot list (required video, ~2–3 min)
1. Show the app/operator console and the connected Facebook Page name.
2. Start the Facebook live (Live Producer → GO LIVE).
3. Split screen: the live video + a second phone posting a comment.
4. Show the comment appearing in the operator console within seconds.
5. Show/hear the AI host answering that viewer by name on-stream.
6. Show the AI-disclosure label visible on the broadcast the whole time.
7. End the stream; show polling stopped.

## The 5-minute human click sequence
1. App settings → Basic → upload icon, set Category=Business → **Save changes**.
2. Confirm Privacy + Data-deletion URLs are the privacy.html link → Save.
3. App Review → Permissions and Features → request **pages_read_engagement** (Advanced Access).
4. Paste the two answers above; attach the screencast.
5. Review everything, then click **Submit for review**. (CLI never clicks this.)

## After approval (CLI, zero human)
`node scratchpad/sysuser.mjs` re-mints the system-user token WITH scopes → create n8n
Facebook credential → attach to W1-FB → activate. Then Facebook auto-chat is live.
