# DEPLOY-TEST ORDER — start small: Wave then Hello, on the beta track, promote only on the founder's word

## Why these two first
Wave (adult, 28s) and Hello (kids, 111s) are the two games with the least existing tuning debt — they prove the new MediaPipe engine + the tier system on both tiers BEFORE the big Freeze/Upper Body/Up Groove work.

## Sessions (one bounded CLI session each — fresh session per step)
S1 · Foundation: install skills → CLAUDE.md → beta-init.sh → tracks.yml + rollback test → `shared/pose-adapter.js` (skill §2) → tag beta-b0.1. Report.
S2 · WAVE-BETA.md → /beta/wave → harness 3× EN+HE → recording + beeps → HOLD (founder plays).
S3 · (after "approved") HELLO-BETA.md → /beta/hello → same → HOLD.
S4 · Founder says "PROMOTE v1.1" (wave) / "PROMOTE v1.2" (hello) → PRs to main titled exactly that → CI green → merge → verify commercial links.
S5 · Only then: GAMES-TIERED.md sessions for Freeze / Upper Body / Up Groove.

## Laws
Beta only · main frozen · skills read before code · ORIGINS wins · no invented values · pods self-stop · evidence per session · ambiguity = QUESTION.

## First paste to the CLI
"Read DEPLOY-TEST-ORDER.md. Run S1. Report, hold."
