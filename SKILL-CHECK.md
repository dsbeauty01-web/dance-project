# SKILL-CHECK — nova-go5 (Freeze v4 hybrid: live intro + talk fixes), 2026-11-24

Audit of the nova-go5 change against the 3 skills (movement-tracking, game-cues-lights, performance-feedback-ai).
Scope = what this branch changes; everything else is the nova-go4 build as it was. Evidence = file / log in `docs/evidence/2026-11-24-go5/`.

| Skill.Law | nova-go5 | Evidence |
|---|---|---|
| **A1-A7** detection (camera plane, relative, calibrate, gate, sustained, graded) | n/a: no detection code changed. The shoulder shrug check is the approved one, untouched (`beta/lib/shoulder-beat.js`, `test/shoulder_beat_f4_test.mjs` PASS) | pod EN + HE: a real lift → "Yes! The light caught it!" |
| **B1** immediate + proportional + multi-sensory | ✓ unchanged (light, burst, voice on a real lift) | pod `2g2lb5eo9vf7nd` rtlk |
| **B2** one concept per beat | ✓ the intro is now one beat per turn: name → chat → light → game rules (was one 9-s line: greeting + light at once) | `beta/freeze4.html` `v2vNameBeat` |
| **B3** external-focus wording | ✓ unchanged light lines; her replies may not tell the child how to dance (`REPLY_STYLE`) | `pod/rt_lk.py` |
| **B5** light language (gold, never red) | ✓ unchanged | — |
| **B6** layout / badge / exit / stars | ✓ unchanged (split screen, medal, no numbers): kid-screen guard clean | `tools/laws/kid-screen-guard.mjs` |
| **C1** ~4:1 encourage : correct | ✓ unchanged game lines; more star variants, no new corrections | `beta/lib/brain-local.js` |
| **C2** praise specific / event / malleable | ✓ new star lines name the animal and the stillness ("Statue bear! Not one wiggle!"); pet names banned in replies | `brain-local.js`, `REPLY_STYLE` |
| **C3** correction external + one + future | ✓ unchanged | — |
| **C4** silence on miss; ≤ 6 words, ≤ 1 per gap | ✓ unchanged gates; repeated openings no longer silence her (DE-CAN) | `test/brain_local_norepeat_test.mjs` |
| **C5** autonomy beats | ~ her name question and one light chat question are back (INTRO-V2V); no new game choice | rig `fin_en`, `fin_he` |
| **C6** enhanced-expectancy openers | n/a: not changed | — |
| **C8** never negative words | ✓ unchanged bans; meta lines ("I'll say it exactly as you asked") killed before they air | `pod/rt_lk.py` REFUSAL-KILL |
| **Truth law** | ✓ the light is never claimed without a real lift; director notes on light-on / win / release | rig + pods |
| **Memory** | ✓ she uses the child's name from the first answer to the goodbye ("Bye, Shuki!") | pod EN rtlk |

Open (not regressions): the 32-core EN host had 8 late chunks / 13 underruns (24-core sold out); no real person has played go5 yet.
