# Privacy policy patch — cover all 4 scopes

**File:** privacy.html (hosted at dsbeauty01-web.github.io/dance-project/privacy.html)
**Status check (2026-09-03):** the policy ALREADY names the read-side data, verbatim:
> "…comments posted on live videos of the connected Page (commenter display name, comment text,
> and time)."
So `pages_read_engagement` (comments + user names) is already disclosed ✓. The patch below adds the
**write/publish** behaviors of the 3 new scopes. Reviewers reject apps whose policy doesn't cover
every requested permission — this closes that gap.

---

## EDIT 1 — extend "Data we access"
Append to the existing bullet list:

> - **Replies we post on your behalf:** when you enable auto-replies, the app writes short reply
>   comments **as the connected Page** on viewer comments during your live (the reply text is
>   generated from your own product information). We do not delete or hide viewer comments except
>   obvious spam.
> - **Live videos we create:** with your authorization the app creates and ends **your Page's own
>   live video broadcasts** (title, description, status) and publishes the video/audio stream our
>   system generates for your live shopping session.

## EDIT 2 — extend "How we use it"
Append:

> Commenter display names and comment text are used only to (a) show comments to the stream
> operator, (b) let the AI host answer viewers by name on-stream, and (c) post a short written
> reply to the commenter during the same broadcast. We do **not** use any of this data for
> advertising, profiling, or sale, and we do not share it with third parties. The video content we
> publish is the AI host stream you requested for your own Page.

## EDIT 3 — extend "Storage and retention"
Ensure it states:

> Viewer comment data (names, text, time) is held only in memory for the duration of the live
> broadcast to generate on-stream answers and an end-of-stream summary for you, then discarded.
> Reply text we post lives on Facebook as your Page's comment and is governed by Facebook's own
> retention. We store no viewer personal data on our servers after the broadcast ends.

## EDIT 4 — "Data deletion" (confirm present)
Confirm the section tells users they can revoke access anytime via **Facebook → Settings → Business
Integrations**, and that removing the app stops all access immediately. (Already required by Meta;
keep the existing data-deletion URL.)

---

### Data-collection summary the reviewer looks for (must be true after the patch)
| data | collected? | why | retained? |
|---|---|---|---|
| commenter display name | yes | answer viewers by name | in-memory, broadcast only |
| comment text | yes | generate the answer/reply | in-memory, broadcast only |
| comment id + time | yes | dedupe/order | in-memory, broadcast only |
| your public profile (name, id) | yes | Facebook Login identity | account link only |
| Pages you manage | yes | pick the Page to connect | config only |
| reply text we post as the Page | written | on-stream written answer | lives on Facebook |
| live video objects | created/published | run your live shopping | on your Page |
| advertising / profiling / sale | **NO** | — | — |
