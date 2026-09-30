# MOVES CATALOG — every action in every Nova game: how it's judged, the cue, the light, the reward

Live preview (runs this exact code on an animated child): the "Nova · every move, every light" artifact.
Code: `shared/move-judges.js` (judges) · `shared/move-recipes.js` (what the lights do per action) · `shared/nova-lights.js` (the effects) · `shared/motion-detect.js` (wave + bounce).

## 0 · The look rules (every game, no exceptions)
| Color | Meaning | Used for |
|---|---|---|
| **Cyan** | where to go / the moving light | pose outlines, hand rings, wave dots, comet, where-to-stand arrows, the beat ring |
| **Green** | this part is right | an arm that reached its place, a filled ring |
| **Soft orange** | this part must change (never red) | the wrong arm, the arm that wobbled in a freeze, hips that moved in a slide |
| **Gold** | you did it | bursts, "+100", "YES!", a full meter, the star snap |
| **Ice** | hold still | the freeze frost, "STATUE!", "SMART!" |
- Max 2–3 effects at once. Rewards are under 1 second so they never hide the next cue.
- Nothing punishes: a miss shows nothing (the recorded voice line does the encouraging).
- Every light follows the child's OWN body (smoothed, predicted 30ms ahead, 60fps) — never a fixed spot on the screen, except where-to-stand arrows.
- Progress is always shown before success: rings fill, limbs turn green part by part — the child sees how close he is.

## 1 · Every action
Distances are in the child's own body units: **sw** = shoulder width, **torso** = shoulder-to-hip length, **reach** = 1.35 sw.

### INTRO (all games)
| Action | Judge | Cue | While moving | OK | Tests |
|---|---|---|---|---|---|
| **Where to stand** | shoulder width 0.10–0.34 of the frame, centre ±0.18 | — | corner arrows pointing IN = step back · centre arrows pointing OUT = come closer · one arrow = move over | arrows disappear | 4 judge + 4 recipe |
| **Shoulder light** | one shoulder above the other by ≥ 0.15 sw (full = 0.2 sw); the other shoulder lifted doesn't count | empty ring above that shoulder | ring fills with the lift, shoulder glow grows | ring gold + burst + "YES!" | 5 + 1 |
| **Hello wave** | a hand above the shoulder swinging ≥ 2 turns of ≥ 0.22 sw within 1.6s | — | sparkles trail the waving hand | gold burst + "HI!" | 3 + 2 |

### FREEZE
| Action | Judge | Cue | While moving | OK / Near / Miss | Tests |
|---|---|---|---|---|---|
| **Dance** (music on) | — | speed glow on | every joint glows gold, brighter the faster it moves | — | 1 |
| **Freeze** (music stops) | the certified Hold judge scores (held / almost / missed); PartMotion finds WHICH part moved | frost starts at the feet | frost climbs to the head in 0.45s; the part that wobbles glows soft orange; a calm ice halo grows while held | held = snow + "STATUE!" · almost = "ALMOST!" · missed = nothing | 2 + 4 |
| **Star** (bonus) | arms up in a V + feet apart ≥ 0.75 | dashed star outline on the child | outline + hand rings fill | gold + "STAR!" | 2 + 1 |
| **Flamingo** | one knee ≥ 0.12 torso above the other (full 0.42) | flamingo outline | fills | gold + "FLAMINGO!" | 2 + 1 |
| **Frog** | hips drop toward the knees + knees wide | frog outline | fills | gold + "FROG!" | 2 |
| **Bear** | both arms out wide | bear outline | fills | gold + "BEAR!" | 1 |

### NOVA SAYS
| Action | Judge (per arm, 0→1) | Cue (when the command is spoken) | While moving | OK / Miss | Tests |
|---|---|---|---|---|---|
| **Arms up** | wrist from hanging (0) → out (0.5) → straight up (1); elbow up too; a V counts | dashed pose outline on the child + empty rings where the hands go | each arm cyan while moving → green when there; its ring fills | gold at both hands + "YES!" | 6 + 4 |
| **Arms out** | wrist ≥ 0.8 reach out, at shoulder height | outline + rings | same | same | 4 |
| **Hands on head** | wrists at the top of the head (≤ 0.25 sw) | rings on top of the head | same | same | 3 + 1 |
| **Left / right arm up** | that arm up, the other DOWN | one-arm outline | the wrong arm glows **soft orange** until it comes down | same | 4 + 1 |
| **The trick** | the game's certified judge | nothing (no outline — that's the trick) | — | still = icy "SMART!" · moved = playful "GOTCHA!" | 2 |

### WAVE (one arm)
| Action | Judge | Cue | While moving | OK | Tests |
|---|---|---|---|---|---|
| **Arm wave** shoulder→hand or hand→shoulder, either arm | ONE arm's joints rise one after another (3 joints; or elbow→wrist if the shoulder doesn't pop, with the other joint still low at each peak) | dots light up along his arm in wave order, synced to Nova's demo | the comet rides wherever his wave really is | gold burst + "YES!" at the end joint | 35 + 4 |

### UP GROOVE
| Action | Judge | Cue | While moving | OK / Near | Tests |
|---|---|---|---|---|---|
| **Bounce on the big beat** | deepest point of each bounce vs the beat: on ±130ms, near ±230ms (camera + speaker delay compensated) | a ring on the chest closes exactly on the beat | — | on = gold burst + gold ripple under the feet + "+100" · near = cyan ripple · off = nothing | 10 + 3 |

### UPPER BODY — confirm the game's real action list with the CLI
| Action | Judge | Cue | While moving | OK | Tests |
|---|---|---|---|---|---|
| **Chest slide** L/R | shoulders slide ≥ 0.28 sw over hips that stay within 0.14 sw of home | light rail across the chest + dashed ring on the hips | a bead rides with the chest (brighter at the ends); the hip ring turns orange if the hips move | the star snaps at that side + burst | 4 + 2 |
| **Shoulder pop** L/R | fast shoulder lift, then stop | empty ring above the shoulder | fills instantly | the star snaps on the shoulder | 1 |

## 2 · What the tests prove (and don't)
- move judges 42/42 · recipes 32/32 · wave + bounce 35/35 · stage 31/31 — plus the preview ran all 18 scenes twice with no errors, every move firing its success light.
- All on simulated children (jitter, near/far, slow laptop). NOT proven: real kids, real rooms, lighting, loose clothes, a child partly out of frame.
- Needs the whole body in view: star (feet), flamingo (knees), frog (knees) — for those, ask for the feet: `judgePresence(k, { needFeet: true })`.
