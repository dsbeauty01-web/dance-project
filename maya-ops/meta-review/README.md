# maya-ops/meta-review — Meta App Review pack (Maya Live)

Built 2026-09-03. App ID `1335138022110608` · Page `MythicMingle` (`1100248523396303`) · Graph `v26.0`.

## Contents
- **submission.html** — open this. Per-permission justification (paste into Meta's form) +
  screencast shot-script, the pre-submission gate, and your dashboard click-steps.
- **exchange_token.sh** — mints long-lived User + Page tokens into `~/.maya/meta.env`
  (`META_USER_TOKEN_LL`, `META_PAGE_TOKEN_LL`). Re-run when the short-lived token is refreshed.

## The 4 scopes requested
| Scope | Why Maya needs it |
|---|---|
| `pages_show_list` | list the owner's Pages so they can pick one to connect |
| `pages_read_engagement` | read live-video comments (the "ear") |
| `pages_manage_posts` | create + end the live video post on the Page |
| `publish_video` | push the RTMPS broadcast (Live Video API) |

## Honest status
- Privacy policy patched (`privacy.html`) with a permission→data map — **must be deployed at a
  public URL** and pasted into App Settings → Basic.
- Long-lived tokens minted + validated (`is_valid:true`).
- **Not submitted, not live.** Submission and approval are manual + Meta-side (days). The
  test-user creation and the Submit button are dashboard clicks only the account owner can do
  (see submission.html → "Your dashboard steps").
- Hard gate to check first: FB account ≥60 days, Page ≥100 followers, app has the
  "Access the Live Video API" use case.
