# NOVA SAYS — QA Q1→Q10 · old → new log

Spec: `Downloads/NOVASAYS-QA.md` (architect, 2026-09-24) · applied in the order given (Q1→Q10)
Branch `novasays-v3` · commit **`210bd76`** off `3932115` · script.json **3.2 → 3.3**
Evidence: `test/novasays_qa_bench.js` **64/64** · Nova Laws **14/14 green**
**Timing budget: NOTHING APPLIED — held for founder decision** (see the last section)

---

## script.json — every value

| Key | Old | New |
|---|---|---|
| `version` | `3.2` | `3.3` |
| `peakMs.gest_star` | — (not in file) | `720` |
| `peakMs.gest_clap` | — | `2080` |
| `peakMs.gest_lefthand` | — | `2480` |
| `peakMs.gest_righthand` | — | `2640` |
| `peakMs.gest_bear` | — | `3840` |
| `windowOpensAtPeakFrac` | — | `0.8` |
| `freezeWindowPadS` | — | `1.2` |
| `tune.provisionalMoveMult` | — (hardcoded `×4` in the page) | `10` |
| `tune.moveFloorMult` | — (no floor existed) | `3` |
| `tune.jumpRejectSW` | — (no reject existed) | `0.8` |
| `tune.nominalFps` | — | `15` |

No existing value was changed. `capSeconds` stays **210**, all 11 `tune` thresholds keep their
shipped values, `bakeMs` untouched.

---

## beta/novasays.html — every behaviour

### Q1 · window opens at the gesture's peak
| | Old | New |
|---|---|---|
| order | `await speakLine(line, go)` → `go()` fires demo+light on the **last word** → `sleep(150)` → window | `speakLine(line)` started, **demo+light fire immediately**, then `await` the line |
| window opens at | the **line's end** | `max(line end, 0.8 × peak)` |
| armsUp (peak 720ms) | line end | line end — unchanged, star peaks early |
| clap (peak 2080ms) | line end, **0.08s before her arms arrive** | ≥1.66s, after |
| leftArm (peak 2480ms) | line end, **0.48s before** | ≥1.98s |
| rightArm (peak 2640ms) | line end, **0.64s before** | ≥2.11s |
| freeze (peak 3840ms) | line end, **1.84s before** | ≥3.07s |
| light duration | `w` (the window only) | `0.8×peak/1000 + winSecs` — stays lit through the wait `[CLI-FILL]` |
| practice | 3 hand-rolled inline call sites | shares `callCommand()` with the game |
| peak source | — | `S.peakMs` with in-page literals as fallback |

### Q2 · arms out of frame
| | Old | New |
|---|---|---|
| void gate | `K.armsVisible(k)` — **all 6 joints** at `vis>0.6` | `bodyVisible(k)` — **2 shoulders** at `vis>0.4` |
| `armUp` | `vis(wrist) && vis(shoulder) && …` → **false when the wrist leaves frame** | wrist if visible → else elbow at `thr.reach × 0.5` → else `lastWristAbove[side]` |
| effect | a close child doing "arms UP" correctly → window **voided, scored nothing** | scored |

### Q3 · freeze holdable
| Round | Old window | New window |
|---|---|---|
| 1 (win 2.4s) | 2.40s | **2.40s** (unchanged) |
| 2 (win 2.0s) | 2.00s | **2.20s** |
| 3 (win 1.6s) | 1.60s — below the 1.0s hold + 0.3-0.5s EMA settle | **2.20s** |
| non-freeze | round win | round win (unchanged) |

### Q4 · the provisional fallback
| | Old | New |
|---|---|---|
| `CAL.move` when the practice arm-up is missed | `CAL.still × 4` | `CAL.still × 10` |
| floor on `thr.move` | none | `max(thr.move, CAL.still × 3)` |
| **measured threshold k** | **1.90** | **3.70** |
| false GOTCHA on a still child | architect's sim: 12% (1% flips) · 25% (3% flips) · 13% (fps drop) | **0% in all 5 simulated conditions** |
| `CAL.still` default | `0.004` | `0.004 × NFPS` (units follow Q5) |
| `[CAL]` log | still, move, reach, rest, thr | **+ `k`, + `provisional:true/false`** |
| `remember()` | `calibration X→Y` | + `(PROVISIONAL — arm-up never measured)` when it applies |
| practice retry | already existed (one `practice.retry`) | unchanged — now routed through `callCommand` |

### Q5 · frame-rate independence
| | Old | New |
|---|---|---|
| energy | `energy*0.6 + ((sum/n)/sw(k))*0.4` — **per frame** | `… / dt` — **per second**, `dt = max(0.016, Δt)` |
| provisional `thr.move` | `0.012` | `0.012 × 15 = 0.18` |
| provisional `thr.freeze` | `0.006` | `0.006 × 15 = 0.09` |
| **measured: same 1.0s arm raise** | scaled with 1/fps | **8fps 1.548 · 15fps 1.573 · 30fps 1.574 (spread ×1.02)** |

### Q6 · keypoint flips
| | Old | New |
|---|---|---|
| per-joint displacement | always summed | skipped when `jump / sw(k) > 0.8` |
| measured: 1.5-shoulder-width one-frame jump | added energy | **adds none** (0.00000 → 0.00000) |
| measured: real fast movement | registered | **still registers** (1.3067) |

### Q7 · stalled camera
| | Old | New |
|---|---|---|
| window stalled past `t1 + 400ms`, real | `'miss'` — punished an unwatched child | `'void'` |
| window stalled past `t1 + 400ms`, trick | `'held'` — **paid +2 stars** to an unwatched child | `'void'` |
| healthy window | closes on its own verdict at `t1` | unchanged (verified `'held'` still resolves) |

### Q8 · the medal maximum
| | Old | New |
|---|---|---|
| computed | `maxStars = maxFor(S.rounds)` once, **at boot** | `addToMax(steps)` per round, **after the adaptive change** |
| streak bonus | `floor(totalDecisions / 5)` over the script | same, over decisions actually played |
| **measured max** (round 2 eased 3→2 tricks) | **38** | **37** |
| a child scoring 30 | 30/38 = 79% → **silver** | 30/37 = 81% → **gold** |
| new log | — | `[MEDAL] 30/37 = 81% 🥇` |

### Q9 · the listening streak
| | Old | New |
|---|---|---|
| `'effort'` branch | `missRun=0; addStars(1)` — **streak untouched** | `missRun=0; streak=0; addStars(1)` |
| effort star | awarded | **still awarded** |
| 5 wrong moves | could earn a "Super listener!" bonus | **earns none** |

### Q10 · overlapping clips
| | Old | New |
|---|---|---|
| `fb.comeback` | `speakLine('fb.comeback')` — not awaited, overlapped `fb.welcome` | `await speakLine('fb.comeback')` |
| all call sites | 1 of 20 un-awaited | **20 of 20** awaited or captured-and-awaited |
| deferred by design | — | `const lineP = speakLine(lineId)` … `await lineP` (Q1 needs it) |

---

## New files

| File | What |
|---|---|
| `test/novasays_qa_bench.js` | **64 checks, 64 passing.** The judge, calibration and timing maths are **sliced out of `beta/novasays.html`** with a brace-matching extractor and run in a `vm` sandbox — it tests shipped code, and fails loudly if a function is renamed rather than silently testing nothing. Reverting Q4 inside it reproduces the architect's **k=1.90** exactly. |
| `test/novasays_budget.js` | Timing budget from the **real mp3 durations**, parsed from MP3 frame headers (ffprobe costs 4.6s per spawn on this laptop — 74 clips would be 6 minutes). Verified against ffprobe: `cmd.armsUp.real.1.mp3` = 1.9189s both ways. |

**Honest limit of the bench:** the "Q4 reverted" column cannot reproduce the architect's original
12-25% false-GOTCHA rates, because Q5 and Q6 are sliced from the shipped page and cannot be switched
off. That column is labelled as such in the output. What it does prove is the threshold moving off
k=1.90, which is the specific thing Q4 changes.

---

## HELD FOR YOUR DECISION — the timing budget

Nothing here is applied. Measured, not estimated:

| | Worst case | vs 210s cap |
|---|---|---|
| **English** | **226.2s** | over by 16s |
| **Hebrew (he-m)** | **246.4s** | **over by 36s** |

The QA's estimate was ~226s — English matches it almost exactly. **But its budget was English-only,
and Hebrew is 20s worse.**

Neither option the QA offers clears the cap:

| Option | Saves | Result |
|---|---|---|
| **A** · cut round 3 from 11 → 9 steps | 11s | 215s — still over |
| **B** · re-bake every gesture peak under 1.2s | **4s** (not the ~36s hoped) | 223s — still over |
| **A + B** | 15s | ~211s — still over |

**Why B barely helps:** the window opens at `max(line end, 0.8 × peak)`, and the ~2s spoken line
already dominates for every command except `rightArm` and `freeze`. The time is in the windows, the
feedback clips and the gaps — not in the gestures.

**What I would measure before cutting anything:** the largest single block is **71s of LIVE phases**
(intro + 2 cards + ending) and that number is an **estimate that has never been measured on a pod**.
It could be well out in either direction. Cutting a round-3 step is cutting the lightning round —
the best part of the game — to fit a budget whose biggest line item is a guess.

---

## Still not done (unchanged by this work)

- **The fake-camera harness** — the game page gets a 0×0 track where a standalone page gets 320×240.
  So judge accuracy, the scenario cases and the per-child threshold numbers remain **unmeasured**.
- **No child has played this game.** Everything above is machine evidence.
