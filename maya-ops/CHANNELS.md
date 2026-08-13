# MAYA — CHANNEL WIRING MATRIX (2026-08-13)

How each channel connects to Maya, and the **honest** status of each link. Two separate
things per channel: **BROADCAST** (her face/voice going out) and **INGEST** (viewer
messages coming back in to be answered).

## The pipeline (shared by all channels)
```
viewer msg → [W2] filter → OpenAI classify → prioritize ─┬─→ /chat-in → seller brain (W4) → she answers
                                                          └─(buy_intent)→ [W3] → Google Sheet row
```
W2, W3 **fixed + proven** this session (see evidence/2026-08-13-pipeline). W4 needs pod to confirm.

---

## YOUTUBE
| | Status | Detail |
|---|---|---|
| **Broadcast** | ✅ WORKS | ffmpeg gesture-loop → YouTube RTMP. Ran 46 min live earlier. Script: `deploy/yt-testcast.sh`. |
| **Ingest** (W1) | ❌ BLOCKED | `W1 YouTube chat ingest` errors: *"credential configured to prevent use within an HTTP Request node."* The `youTubeOAuth2Api` cred can't be used in a generic HTTP node. |
| **Fix** | needs user | In each W1 HTTP node set Authentication → **Predefined Credential Type → YouTube OAuth2 API** (the sanctioned path), and re-auth the YouTube OAuth (token may be stale). Then W1 polls live chat → W2. Not needed for the demo (we inject planted Qs). |

## FACEBOOK
| | Status | Detail |
|---|---|---|
| **Broadcast** | ✅ WORKS | ffmpeg gesture-loop → FB RTMP (`rtmps://live-api-s.facebook.com:443/rtmp/<key>`). Went live on the Page this session. Script: `/tmp/fb-testcast.sh` on pod (mirror of yt-testcast). Grab a fresh stream key from Live Producer each session. |
| **Ingest** (W1-FB) | ❌ BLOCKED | `W1-FB Facebook Live chat ingest` exists but needs `pages_read_engagement` — **App Review**. App is Published + Business category; review pack ready in `meta-review/PASTE_ME.md`. Human clicks Submit; then Meta's clock. |
| **App status** | ✅ | App `livestream` (1335138022110608) Published, Category = Business and pages, privacy + icon + domains all set. |

## TIKTOK
| | Status | Detail |
|---|---|---|
| **Broadcast (live)** | 🚫 POLICY-BANNED | TikTok Shop LIVE bans AI voice / synthetic hosts; avatar ≤50% frame. Do **not** run her as a TikTok live host. |
| **Posts (pre-recorded)** | ✅ ALLOWED w/ discipline | Disclosed "AI-generated" label + bio note; catalog-true only. The loop bakes double as this content. |
| **Ingest** | n/a | No live-comment ingest (policy + no granted API). TikTok is an **awareness → drive-to-YouTube/FB** channel. See `tiktok/SETUP.md`. |

## DIRECT INJECTION (the demo path — always works)
| | Status | Detail |
|---|---|---|
| **Inject** | ✅ | POST planted messages straight to W2 `webhook/maya-chat`, or to the pod switchboard `/chat-in`. This is how the client demo runs — no dependency on YouTube/FB OAuth. `scratchpad/fire-test.mjs`. |

---

## BOTTOM LINE
- **Broadcast out:** YouTube ✅, Facebook ✅, TikTok (pre-recorded) ✅.
- **Answer-back pipeline:** W2 + W3 **fixed & proven**; W4 (brain) pending pod.
- **Auto-ingest of live comments:** YouTube + Facebook both blocked on OAuth/App-Review
  (user actions). Until then, the demo uses **direct injection**, which is fully wired.
- **The gap that matters for a real unattended live:** comment ingest. Everything from the
  webhook inward now works.
