# SKILL-CHECK — Animal Freeze vs Upper Body (b0.1 audit, 2026-09-07)

Audit of the two games against the 3 installed skills (movement-tracking, game-cues-lights, performance-feedback-ai). Evidence = file:line. No code changed — this is the founder's fix list. **HOLD for approval.**

| Skill.Law | Freeze (`pod/pages/animal-freeze.html`) | Upper Body (`pod/pages/upperbody.html`) | Proposed fix (one line) |
|---|---|---|---|
| **A1** Camera-plane only | ✓ Scores only stillness, no depth/rotation (:1285-1286) | ✗ Scores FRONT/BACK torso via shoulder-WIDTH depth proxy (:538-539, dirs B/F :156-161, :438) | Drop F/B scored moves (or rescore as x-plane lean); never reward toward/away depth. |
| **A2** Relative not absolute | ✓ Motion shoulder-normalized `/sw` (:1283-1285) | ✓ Shoulder-center vs baseline, hip reference (:524-526,:540) | Keep. |
| **A3** Calibrate per kid | ✗ No calibration window; fixed thresholds (:1439,:1286) | ✓ Demo-window per-kid thresholds (:430-444,:606) | Add a no-score baseline window to Freeze; threshold = fraction of that kid's range. |
| **A4** Smooth + gate | ~partial gate 0.3 (<0.35), min 4 joints (<8), no EMA; absent kid = credit not NOSHOW (:1277-1278,:1498) | ✓ EMA, gate .35, min 13 joints (:522,:483,:473) | Raise Freeze gate to 0.35, ~8 joints, EMA, treat no-pose as NOSHOW. |
| **A5** Velocity assists slow kids | n/a (stillness game) | ✓ Moving-toward counts (:536-537) | Keep. |
| **A6** Sustained-only penalties | ~partial 0.7s grace, no explicit ≥400ms gate (:1439-1444) | ✓ Wobble only at >400ms, playful not penalty (:544-548) | Add ≥400ms sustained-motion gate before Freeze docks credit. |
| **A7** Graded windows | ✓ PERFECT/partial/0 (:1440-1444) | ~partial per-move binary; only round verdict graded (:540-542,:635) | Give Upper Body per-move PERFECT/GOOD/OK tiers. |
| **B1** Immediate+proportional+multi-sensory | ✓ frost/shatter/pts + ding + voice | ✓ flare/pop + tick + voice (:418) | Keep. |
| **B2** ≤1 concept/beat, progressive disclosure | ~partial one cue at a time, no round-1-teach/strip (:366-378) | ✓ CUES_R1 teaches, CUES_LATER strips (:495-504) | Freeze: teach in round 1, strip hints later. |
| **B3** External-focus wording | ✓ cues the goal/animal (:1518-1519) | ✗ persona+cues name body parts: torso/hips/waist (:171-184,:497-498) | Recut Upper Body cues to target-only ("chase the gold"); delete body-part wording. |
| **B4** Graded timing, no fast-spam | ✓ graded, unspammable (:1440) | ~partial binary window, no anti-spam (:540) | Add graded windows + settle check so a wiggle can't score. |
| **B5** Light language (GOLD only; ice=freeze; never red) | ✗ no gold mid-game; action light ice-blue; ring turns **RED** while moving (:48-49,:1500) | ✓ gold is sole action color; "wrong"=lilac not red; ice for freeze (:378,:401) | Remove red moving-ring; add a gold action light, ice-blue for freeze only. |
| **B6** Layout / badge / pause+exit / stars | ~partial fixed split; numeric score; **no exit btn** (:33,:78,:243) | ✓ phase-adaptive 66/34↔60/40, badge, pause+exit, ⭐ (:45-49,:113,:135,:641) | Freeze: add exit button + phase-adaptive split; swap live numeric score for stars. |
| **C1** ~4:1 encourage:correct | ✗ not found in TENSION_MASTER/rt_lk (:397-414) | ✗ not found in UB_COACH (:171-184) | Add explicit praise:correct ratio to personas + a page-side counter. |
| **C2** Praise specific/event/malleable (not trait) | ~partial event-anchored but trait fallbacks ("ICE LEGEND!") (:1534,:1563) | ~partial "praise only what camera saw", no malleable rule (:183) | Add "praise the action THIS time, never a trait"; drop legend/incredible fallbacks. |
| **C3** Correction external+one+future | ~partial future but internal "hold still" (:1564-1565) | ~partial future but rides internal directions (:659) | Rewrite corrections as single future external cues ("next one, reach the gold further"). |
| **C4** Silence on miss; sound on hit; ≤6 words ≤1/gap | ~partial HOLD silence + ding, but voices verdict on a moved miss (:1516,:1550) | ✓ total silence till verdict, no-miss-sound, ≤6 words (:413,:184) | Freeze: go silent (ding only) on a moved round. |
| **C5** Autonomy beats | ✗ mid-game choices forbidden; only ending question (:410,:1767) | ~partial "ready for next" yes/no, not a real choice (:660) | Offer a real choice at phase edges ("faster or same next?"). |
| **C6** Enhanced-expectancy openers | ✗ not found | ~partial "Round 3 FASTER" is a warning not a boost (:595) | Add "you've got this one" lines before FAST/STAB rounds. |
| **C7** Between-rounds: 1 strength+1 cue+1 choice | n/a (continuous 11 freezes) | ✓ between() = strength+weakest+ready (:659-661) | Keep. |
| **C8** Never negative words | ✓ banned + enforced (:413,:1550) | ✓ banned + shared rt_lk enforcement (:184) | Keep — best-enforced law in both. |

## TOP FIXES (ranked)
1. **Upper Body A1/B3 — untrackable move + body-part cues:** it SCORES front/back torso depth via a shoulder-width proxy (:538-539) and its cues name torso/hips/waist (:171-184). Most fundamental violation — camera can't honestly judge it, coaching points the wrong way. Rescore F/B as an x-plane action; recut cues target-only.
2. **Freeze B5 — punishing red + no gold:** the hold-ring flips RED while a child moves (:49,:1500); no gold action light anywhere. Kill the red state, add gold.
3. **Freeze A3/A4 + Skill-C gaps in both prompts:** Freeze has no per-kid calibration + weak gate (0.3/4 joints/no EMA); neither persona carries the Skill-C feedback block (no 4:1 ratio, no malleable-vs-trait, no external-future correction). Add a calibration window + a shared feedback-law block.
