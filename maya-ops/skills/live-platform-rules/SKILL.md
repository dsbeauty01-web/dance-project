---
name: live-platform-rules
description: Use this skill whenever planning, building, or writing anything that streams an AI host to a real platform — choosing platforms for Maya, writing client proposals, compliance questions, disclosure labels, or ban risks. Triggers on Instagram Live, YouTube Live, TikTok Shop, Amazon Live, Douyin, platform policy, AI disclosure, AI label, ban, unattended streaming, EU AI Act. Contains the per-platform legal/policy map for AI livestream hosts as of Aug 2026 — what is allowed, what label is required, what gets accounts banned.
---

# Live Platform Rules for AI Hosts — the compliance map (as of Aug 2026)

## The one universal rule

**Visible "AI" label + a real human able to take over, everywhere.** Every jurisdiction and
platform converges on disclosure + human-in-the-loop. Hiding the AI is the one strategy that is
illegal-or-bannable everywhere AND getting worse over time. Bake the label INTO the video
compositing layer (not a page overlay) so it survives every re-stream and screenshot.

## Platform-by-platform

| Platform | AI host in live selling | Requirements / notes |
|---|---|---|
| **Instagram / Meta** | ✅ Allowed | AI-generated video/audio incl. virtual hosts must be manually disclosed with Meta's tools; virtual-avatar content carries the "AI Generated" label. Automation rules (2026) reward human-centric tools, punish spam patterns. |
| **YouTube Live** | ✅ Allowed | Synthetic/AI-altered content must be flagged (disclosure required for monetization). Official liveChatMessages API = the clean chat-ingestion path. Best self-test platform (unlisted streams). |
| **Amazon Live** | ⚠️ Allowed-with-care | No explicit AI ban in content policy; bans center on impersonation, off-Amazon links, prohibited content. Vendors stream AI hosts today. Don't impersonate real people; disclose. |
| **TikTok Shop** | ❌ AI VOICE BANNED in shopping lives | 2026 rule, verbatim: "Don't use non-real-time verbal interaction such as AI-generated voices, audio recordings, or radio." Enforced via Account Health Rating (compounding penalties). Digital avatars limited to ≤50% of screen. AI in pre-production stays allowed with disclosure. Also: no music on Lives (even royalty-free), live eligibility ≥1,000 followers. |
| **Douyin (China ref.)** | ✅ with strict conditions | Conspicuous "AI生成" label, real-name registration of the human behind the avatar, real-person able to take over, real-time interaction required, **fully-unattended streams banned**. WeChat Channels bans virtual-human live entirely. |

## Legal layer (beyond platforms)

- **EU AI Act Art. 50 — in force Aug 2, 2026:** AI-generated commercial content must disclose
  synthesis AND preserve machine-readable watermarks. Fines up to €15M. Israeli clients selling
  to EU audiences are in scope — this is a selling point for our compliance-included retainer.
- **FTC (US):** "double disclosure" — paid partnership AND AI involvement; undisclosed synthetic
  endorsers are enforceable violations (~$53K per instance cited).
- **China (reference market):** AIGC Labeling Measures effective 2025-09-01 (explicit label +
  metadata watermark; deleting the metadata label is itself a violation).

## Ban triggers to engineer around (learned from China's enforcement, applies broadly)

1. **Unattended streaming** — no human monitoring/takeover → design the operator console +
   takeover as a non-optional part of every deployment.
2. **Recorded-as-live signals** — identical looping content for hours, slow/no chat response
   → rotate 3 script sets every ~2h; keep reply latency ≤40s.
3. **Undisclosed AI** → label baked into pixels.
4. **Regulated categories** — supplements, medical, weight loss, finance, "guaranteed results"
   → maintain a forbidden_claims list per product; block at the prompt AND post-check outbound text.
5. **Real-person impersonation / celebrity likeness** → only original avatars with documented
   consent chains (our Kling-generated Maya is clean; never clone a real person without a
   signed release).
6. **Absolute claims** ("100%", "cheapest", "cures") → strip at the script layer.

## What this means for Maya's go-to-market

- **Primary platforms: YouTube Live + Instagram Live.** Both allow disclosed AI hosts; YouTube
  is also the test bench (unlisted + official chat API).
- **TikTok Shop is a closed door for the AI-voice live format** — offer TikTok clients
  pre-recorded AI video + human-hosted lives instead. Re-check policy quarterly.
- **The pitch line compliance gives us:** "fully compliant AI host — labeled, human-supervised,
  EU-AI-Act ready" — turns regulation from a threat into the moat that DIY tools can't offer.
- Every client proposal includes: disclosure label spec, operator/takeover plan, forbidden-claims
  list, and platform-fit assessment. That paperwork IS part of the ₪8–15K setup fee.
