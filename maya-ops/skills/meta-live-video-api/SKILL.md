---
name: meta-live-video-api
description: Use this skill when connecting Maya (or any system) to Facebook/Meta live streams — reading live comments, creating broadcasts, page tokens, app review, W1-FB wiring. Triggers on Facebook Live, Meta live, live_videos, live comments, Live Video API, page access token, Graph API streaming. Facts fetched from developers.facebook.com/documentation/live-video-api on 2026-08-09 — verified sections are marked; do not trust the UNVERIFIED section without testing.
---

# Meta Live Video API — verified facts (fetched 2026-08-09)

## VERIFIED from Meta docs

### Hard account requirements (since June 10, 2024)
- Facebook account at least **60 days old**
- Page (or professional-mode profile) with at least **100 followers**
→ A brand-new test page CANNOT go live via API. Check this FIRST at client onboarding.

### App requirements
- The app needs the **"Live Video API" feature via App Review** for full API broadcasting.
- The use-case in app creation: **"Access the Live Video API"** (under Content management).

### Permissions
- Publish to a **User profile**: `publish_video`
- Publish to a **Page**: `pages_manage_posts` + `pages_read_engagement`
- (Reading a Page's live comments rides on `pages_read_engagement` with a Page token.)

### Broadcasting endpoints
- Create + go live: `POST /me/live_videos?status=LIVE_NOW` → returns `id`, `stream_url`,
  `secure_stream_url` (RTMPS ingest: `rtmps://rtmp-api.facebook.com/rtmp/<key>`),
  `stream_secondary_urls`, `secure_stream_secondary_urls`.
- End broadcast: `POST /<LIVE_VIDEO_ID>?end_live_video=true`
- Delete the VOD: `DELETE /<LIVE_VIDEO_ID>`
- Reading the node: `GET /<LIVE_VIDEO_ID>` (note: `overlay_url` removed v24.0+).

### Reading live comments — `GET /v26.0/{live-video-id}/comments`
| param | type | default | notes |
|---|---|---|---|
| `filter` | enum | `toplevel` | `stream` or `toplevel` |
| `live_filter` | enum | `filter_low_quality` | whether low-quality comments are filtered out |
| `order` | enum | — | `chronological` / `reverse_chronological` |
| `since` | datetime | — | lower time bound |

- **Meta's own best practice, verbatim intent:** "continually poll for comments in the
  reverse chronological ordering mode."
- Response: `{ data: [Comment...], paging: {}, summary: { order, total_count, can_comment } }`
- Create/update/delete are NOT supported on this edge.
- Error codes: `100` invalid param · `200` permissions · `190` invalid token · `104` signature.
- Current documented Graph version: **v26.0**.

## UNVERIFIED (standard Graph knowledge — TEST before relying on it)
- `GET /{page-id}/live_videos?broadcast_status=["LIVE"]` to find the running live (W1-FB
  uses this; the fetched docs did not show this edge — verify on first real page).
- Comment fields `from{name,id}`, `message`, `created_time` (W1-FB requests these; `from`
  on Page-owned videos generally needs the Page's own token).
- SSE streaming endpoint (`streaming-graph.facebook.com/.../live_comments`) — referenced
  historically; the current docs pages did not surface it. Polling per Meta's best
  practice is the safe path.

## What this means for W1-FB (the n8n ear)
1. Switch polling to `order=reverse_chronological` (Meta's stated best practice) — the
   dedupe already handles replay; W1-FB was built chronological, flip it at activation.
2. Bump Graph version in URLs to **v26.0** (built with v21.0).
3. Keep `live_filter=no_filter` only if raw everything is wanted; default already drops
   low-quality spam BEFORE our own filter — consider keeping the default.
4. Client onboarding checklist gains: page ≥100 followers, account ≥60 days, app has the
   Live Video API use case, Page token in n8n credentials.
