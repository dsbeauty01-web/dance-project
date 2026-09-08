# CHANGELOG — Nova

Format: one line per beta version + every promotion to main.

## main
- 2026-09-06 — Hebrew across the whole game (lang persistence, Hebrew game cues, say-translation, sticky-Hebrew lock). PR #44.
- 2026-09-05 — Tester package: locked GitHub-Pages URL + pod auto-detect, waking-up state, parent consent gate (HE+EN), one-tap boot/schedule. PR #41/#42.
- 2026-09-03 — RELEASE: Freeze game machine-certified EN + HE (3 clean sessions/lang). PR #39.

## beta
- b0.10 — DETECTION: MediaPipe Pose Landmarker engine + adapter on Freeze beta (shared/pose-engine.js, GPU→CPU→MoveNet fallback, self-hosted model). Stillness detector reads named joints via toNova only (grep-proof). Recal harness: certified 0.045 still-threshold holds (MoveNet→MediaPipe shift +14%, within skill's 10-20%). Real-engine fake-camera run + ?pose=1 overlay captured. Fixed two latent bugs (dead window.Pose guard — also on main animal-freeze.html, reported; <base>-tag import mis-resolution). G6 body-map grader PASS on the live pod; G1/G4/G5 remain the pre-existing brain-tuning failures (out of scope for a detection session).
- b0.9 — Wave switched to the ADULT coach tier (calm/precise, ≤10 words, technical praise, external corrections) — was wrongly on the kids voice.
- b0.8 — Up Groove feedback-law block (4:1 ratio, external corrections, no trait praise).
- b0.7 — shared tier config (beta/tiers.js); real Up Groove/Wave synced into beta.
- b0.6 — movement-tracking A1: Upper Body stops SCORING front/back (depth, unjudgeable in 2D) — F/B is now an unscored vibe beat, never a miss.
- b0.5 — movement-tracking A3/A4: Freeze per-kid calibration window + stronger gate (0.35, 8 joints, EMA) + absent kid = NOSHOW not a miss.
- b0.1/S1 gap-fill (DEPLOY-TEST-ORDER) — movement-tracking skill → v2 (MediaPipe map, v1 kept as SKILL-v1.bak); `shared/pose-adapter.js` (skill §2 verbatim); `tools/beta-init.sh` recorded + run (new beta copies: wave, hello, upgroove); deploy-test docs → docs/; rollback.sh tested on beta-b0.1 in a clean clone (exit 0).
- b0.4 — game-cues-lights B3/B6: Upper Body cue TEXT chases the gold (not "hands on your waist"); Freeze gains an always-visible Exit button.
- b0.3 — game-cues-lights B5: Freeze's punishing RED moving-ring → soft warm amber (never red).
- b0.2 — performance-feedback-ai C1/C2/C3 + B3: feedback-law block into both game brains (4:1 encourage:correct, specific/malleable praise not trait, external-focus target cues not body parts, future-tense corrections).
- b0.1 — beta track opened from main; skills installed; guardian + rollback in place.
