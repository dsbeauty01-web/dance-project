# CHANGELOG — Nova

Format: one line per beta version + every promotion to main.

## main
- 2026-09-06 — Hebrew across the whole game (lang persistence, Hebrew game cues, say-translation, sticky-Hebrew lock). PR #44.
- 2026-09-05 — Tester package: locked GitHub-Pages URL + pod auto-detect, waking-up state, parent consent gate (HE+EN), one-tap boot/schedule. PR #41/#42.
- 2026-09-03 — RELEASE: Freeze game machine-certified EN + HE (3 clean sessions/lang). PR #39.

## beta
- b0.1/S1 gap-fill (DEPLOY-TEST-ORDER) — movement-tracking skill → v2 (MediaPipe map, v1 kept as SKILL-v1.bak); `shared/pose-adapter.js` (skill §2 verbatim); `tools/beta-init.sh` recorded + run (new beta copies: wave, hello, upgroove); deploy-test docs → docs/; rollback.sh tested on beta-b0.1 in a clean clone (exit 0).
- b0.4 — game-cues-lights B3/B6: Upper Body cue TEXT chases the gold (not "hands on your waist"); Freeze gains an always-visible Exit button.
- b0.3 — game-cues-lights B5: Freeze's punishing RED moving-ring → soft warm amber (never red).
- b0.2 — performance-feedback-ai C1/C2/C3 + B3: feedback-law block into both game brains (4:1 encourage:correct, specific/malleable praise not trait, external-focus target cues not body parts, future-tense corrections).
- b0.1 — beta track opened from main; skills installed; guardian + rollback in place.
