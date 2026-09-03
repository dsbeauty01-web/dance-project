# META APP REVIEW — copy-paste pack (livestream app `1335138022110608`)

Every block is paste-ready. Icon: `maya_app_icon_1024.png` (this folder). **Category: Business.**
Do NOT click **Submit** until you've reviewed — this pack only prepares the fields.

---

## App settings → Basic
- **App icon:** upload `maya_app_icon_1024.png`
- **Category:** Business
- **Privacy Policy URL:** `https://dsbeauty01-web.github.io/dance-project/privacy.html`
- **User data deletion:** Data deletion instructions URL → `https://dsbeauty01-web.github.io/dance-project/privacy.html`
- **App domains:** `dsbeauty01-web.github.io`

---

## Permission 1 — `pages_read_engagement`
**How will your app use this permission? (paste)**
> On the Page owner's own Facebook Live broadcasts, and with the Page admin's consent, our app
> polls GET /{live-video-id}/comments (reverse_chronological, every ~5 seconds) with a Page token
> to read viewer comments in real time. We use the comment text, the author's display name, the
> comment id and created_time solely to let the AI host answer viewers by name during the
> broadcast and to build an end-of-stream summary for the Page owner. Comments are processed
> transiently and are not sold, shared for advertising, or retained beyond the broadcast. Access is
> revocable at any time via Business Integrations.

## Permission 2 — `pages_manage_engagement`
**How will your app use this permission? (paste)**
> During the Page's own live broadcast, when a viewer comment is a question or shows purchase
> intent, our app posts a short written reply on that comment as the Page (POST
> /{comment-id}/comments), addressing the viewer by name and including the product link only on
> purchase intent. This lets viewers who aren't listening to audio still receive a written answer
> and a tappable link in the thread. We only write short reply text generated from the Page owner's
> own product information; we do not delete or hide user content except obvious spam, and we do not
> use this data for advertising. Rate-limited to at most two replies per minute.

## Permission 3 — `pages_manage_posts`
**How will your app use this permission? (paste)**
> Our app creates and runs the Page's live shopping broadcasts programmatically:
> POST /{page-id}/live_videos?status=LIVE_NOW to start (streaming our video to the returned RTMPS
> ingest) and POST /{live-video-id}?end_live_video=true to stop. This enables scheduled, unattended
> live sessions for the Page owner without manually opening Live Producer. We create only the Page
> owner's own live video objects (title, description, status); no personal data is involved.

## Permission 4 — `publish_video`
**How will your app use this permission? (paste)**
> Our app publishes the live video created above to the Page so the AI host's broadcast appears as a
> normal Facebook Live on the Page owner's own Page. We publish only the video/audio stream our
> system generates for the Page owner's live shopping session; the recording remains as the Page's
> VOD or is deleted at the owner's request. No viewer personal data is published.

---

## Reviewer step-by-step (paste into each permission's "instructions" box)
> 1. Log in as an admin of the provided test Page (MythicMingle).
> 2. In the operator console, click Start live — the Page goes LIVE (uses pages_manage_posts +
>    publish_video).
> 3. From a second account, post: a greeting, "how much?", "does it ship free?", "I want to buy",
>    and "will it cure acne?".
> 4. Within ~10s each: the console shows the comment (pages_read_engagement); the host answers by
>    name on-stream; the Page posts a written reply under the comment (pages_manage_engagement);
>    the purchase reply includes the product link; the medical question gets a safe deflection.
> 5. Click End live — the broadcast ends and polling stops.

## Screencast (one take, ~2–3 min) — clips per SUBMISSION.md
1. read: comment appears in console within ~5s → host answers by name.
2. reply: Page posts a written by-name reply; "I want to buy" reply carries the link.
3. start/stop: Start live + End live from the console (no Live Producer).
4. publish: open the public Page — Maya playing as a normal Live, AI-disclosure label visible throughout.

## Human click sequence (~10 min)
1. App settings → Basic → upload icon, Category=Business, confirm both URLs → Save.
2. Update privacy policy per `PRIVACY-PATCH.md` (must name comments + usernames) → Save/redeploy.
3. Fix Page role per `PAGE-TASKS-FIX.md` (full control on MythicMingle).
4. App Review → Permissions and Features → request all 4 (Advanced Access): paste each block above.
5. Add use case "Access the Live Video API" (Content management) if not present.
6. Attach the screencast, review everything, then click **Submit for review**.
