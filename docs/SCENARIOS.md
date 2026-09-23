# NOVA SAYS v3.2 — SCENARIOS (what happens in every situation)

The game is ~2:50 for one child aged 5-8. Every scenario below has a coded answer in `beta/novasays.html`. Nothing waits forever; nothing is ever negative.

## A · DETECTION HONESTY (no invented numbers)
| # | Situation | What the game does |
|---|---|---|
| A1 | Every child is a different size / distance | **Calibrates on the child.** Practice starts with "First — stand still like a statue!" (2s) → the child's STILL level. Then the practice "arms up" → the child's MOVING level and arm REACH. Every threshold is a fraction between the child's own still and moving levels (tunables in script.json, set by harness runs — never my constants). |
| A2 | Child still moving from the last command when a trick starts | **Settle gate:** a trick window only opens once the child has settled (below their moving threshold) or after 1.0s max; the first 300ms of every trick window is ignored. A late move from the previous command never counts as GOTCHA. |
| A3 | Child does the WRONG move on a real command (claps on "arms up") | Round 1: any clear movement = an **effort ⭐** ("you tried!"). Rounds 2-3: no star, silent. Never "wrong". |
| A4 | Left vs right confusion (5-8 year olds, mirror image of Nova) | **Either arm counts, every round.** Left/right commands teach the words, never punish them. |
| A5 | Freeze held in any pose (arms still up from the last command) | Counts — freeze = stillness in whatever pose. |

## B · THE CHILD'S BEHAVIOUR
| # | Situation | What the game does |
|---|---|---|
| B1 | Shy child — doesn't move at all | 3 misses in a row → clip "Let's do it together!" + the next window is 50% longer. Never a comment on the misses. |
| B2 | Hyper child — dances non-stop, every trick is GOTCHA | 2 GOTCHAs in a row → clip "Freeze your body — only move on Nova says!" and the next trick waits for a settle (A2). |
| B3 | Child gets caught on every trick | Streak resets only; stars already won stay. Ending facts lead with what went right. Always a medal. |
| B4 | Child perfect in round 1 | Round 2 keeps its 3 tricks. If round 1 had a GOTCHA, round 2 plays with 2 tricks (adaptive) — the game stays winnable. |
| B5 | Child talks / shouts during a round | Mic is closed to the brain during rounds — she never answers mid-round. Nothing breaks. |
| B6 | Child never says "yes" at the start | ✓ button always visible; the brain re-invites once (existing WAIT law); nothing starts on its own. |
| B7 | Child wants to stop | ⏸ pauses everything (audio, sequencer, judges); ✕ exits. |

## C · THE CAMERA
| # | Situation | What the game does |
|---|---|---|
| C1 | Child leaves the frame mid-round | Sequencer pauses between steps → clip "Where did you go? Come back!" + the arms gate → on return, clip "There you are!" → continues. A window open when the child left is voided (no miss, no gotcha). |
| C2 | Child too close (only face) / sitting | The arms gate shows green/orange joint dots and "step back" until shoulders+elbows+wrists are seen ≥ 0.8s. |
| C3 | Dark room / low confidence | Same gate; after 8s of failing, the message adds "turn on a light". |
| C4 | A parent walks into frame | MoveNet tracks one person; the settle gate + calibration keep a passing adult from triggering a GOTCHA in most cases. Known limit — logged in the debug strip. |

## D · THE SYSTEM
| # | Situation | What the game does |
|---|---|---|
| D1 | Her brain doesn't answer at a handoff | Fallback clip after 3s; the game continues. |
| D2 | Pod / bridge disconnects mid-game | Pause + "Nova is reconnecting…"; resume when her video returns; after 20s, the ending plays from clips with the real stars. |
| D3 | Tab hidden / child switches window | Everything pauses (audio + sequencer); resumes on return. |
| D4 | A clip or bake missing at start | Red banner, the game refuses to start. Never a silent substitute. |
| D5 | The 3:00 cap is near | Round 3 skips to "Last one… FREEZE!" and the ending. |
| D6 | Autoplay blocks sound | The ▶ tap unlocks audio before anything plays. |
