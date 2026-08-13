# TikTok — SETUP KIT (2026-08)

**Read `../compliance/TIKTOK.md` first.** Short version: TikTok is an **awareness / funnel**
channel for Maya, **not** a live-selling channel. Live AI-voice hosting is banned in TikTok
Shop LIVEs. What we set up here is a **disclosed, pre-recorded** presence that drives viewers
to the YouTube/Facebook live where selling actually happens.

## What TikTok allows for an AI avatar (the guardrails)
- ✅ Pre-recorded clips with the **"AI-generated" content label** on every post + a bio note.
- ✅ Product explainers / teasers — catalog-true facts only (same truth-gate as the brain).
- 🚫 NO AI voice in a Shop LIVE. 🚫 NO avatar >50% of frame in Shop LIVE. 🚫 NO fabricated
  testimonials/claims. 🚫 NO music on Lives.

## Setup — do-it-now checklist (no dev API needed)
1. **Account**: a TikTok **Business** account for the brand (Settings → Account → Switch to Business).
2. **Bio note**: add "Contains AI-generated content" + a link to the live (Linktree/YouTube/FB).
3. **Per-post disclosure**: when posting, toggle **"AI-generated content"** ON (Post screen →
   More options → AI-generated content). This is mandatory, not optional.
4. **Content source**: reuse the loop-mode bakes / gesture clips — the "AI · Maya" label is
   already burned into the pixels, which doubles as visible disclosure.
5. **CTA**: every clip ends "Live now on YouTube/Facebook — link in bio." TikTok = top of funnel.

## Content workflow (repeatable)
```
catalog fact → 15–30s vertical clip (bake/gesture) → burn "AI · Maya" label (already done)
  → post with AI-generated toggle ON → caption w/ product + "live in bio" → pin best performer
```

## If you later want AUTOMATED posting (optional, review-gated)
TikTok's **Content Posting API** (developers.tiktok.com) can auto-publish clips, but like Meta
it requires:
- A registered TikTok developer app + **audit/approval** of the app.
- User OAuth with `video.publish` scope.
- Unaudited apps can only post to **private/self-only** — public posting needs the audit.
→ Same shape as the Meta review wall. Not worth it until the manual channel proves traction.
Manual posting (checklist above) needs **zero** approval and can start today.

## n8n automation hook (later)
Once the Content Posting API app is approved, a `W-TT` workflow mirrors W1's shape:
schedule → pick next baked clip from Drive → Content Posting API publish (AI-label flag set) →
log to a sheet. Skeleton not built yet — gated on the app audit above.

## Revisit
TikTok's AI-in-live stance is moving fast. Re-check this + `../compliance/TIKTOK.md` **2026-11**.
