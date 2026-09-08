# CLI Session Report — DETECTION-MIGRATE (Freeze beta → MediaPipe)

- **Date:** 2026-09-08
- **Session:** https://claude.ai/code/session_01TrugoQNcQErCVndgk2cLVD
- **Repo:** `C:\Users\dsbea\repos\dance-project`
- **Branch:** `beta` (main FROZEN — nothing merged)
- **Tag:** `beta-b0.10` @ commit `84493f5`
- **Task source:** `nova-pack.zip` → START.md → `docs/DETECTION-MIGRATE.md`
- **Result:** Migration COMPLETE + proven. HOLD for founder play-test.

---

## 1. The job (from DETECTION-MIGRATE.md)
Swap the browser pose detector **MoveNet → MediaPipe Pose Landmarker** on the Freeze beta page ONLY, behind the `toNova()` adapter, recalibrate the stillness threshold, prove it, and hold. Touch DETECTION only — nothing else.

## 2. Commits this session
| commit | what |
|---|---|
| `43702f9` | beta(b0.10 wip): MediaPipe engine + adapter wired into Freeze beta |
| `335a473` | test: certify harness takes a page path (`/beta/freeze`) |
| `84493f5` | beta(b0.10): evidence + CHANGELOG + tag |

## 3. Every file I worked on (16 files, +676 / −46)

### Product code
| file | change | why |
|---|---|---|
| `shared/pose-engine.js` | **NEW (90 lines)** | MediaPipe Pose Landmarker via `@mediapipe/tasks-vision`; delegate **GPU→CPU→MoveNet** fallback; VIDEO mode, numPoses 1, masks off; self-hosted model; emits `onPose(toNova(result, engine))`; logs `[POSE] engine=<n> fps=<n>` every 5s. |
| `shared/pose-adapter.js` | verified verbatim (no edit) | Already present and byte-identical to movement-tracking SKILL §2. |
| `beta/freeze.html` | **edited (+121/−…)** | Removed always-on TensorFlow CDN tags; replaced the MoveNet `Pose` object with an engine-agnostic detector that reads **named joints via `toNova()` only** (grep-proof); vis gate 0.5 MP / 0.35 MoveNet; min 8 joints; `?pose=1` debug overlay; extended `__test` harness hooks (`poseFrame`/`poseStats`/`poseCal`); **2 bug fixes** (see §5). |
| `pod/rt_lk.py` | **edited (+24)** | Added `/beta/freeze` route + `/shared` and `/models` static mounts (BETA-TRACK STEP 2). No brain/voice logic touched. |
| `models/pose_landmarker_lite.task` | **NEW (5.78 MB)** | Self-hosted MediaPipe model (served under `/models/`, never the CDN). |

### Docs / evidence
| file | change |
|---|---|
| `docs/DETECTION-MIGRATE.md` | copied in from the pack |
| `CHANGELOG.md` | b0.10 line added |
| `docs/evidence/b0.10/DETECTION-EVIDENCE.md` | full evidence write-up |
| `docs/evidence/b0.10/recal-math.json` | synthetic-frame recalibration results |
| `docs/evidence/b0.10/recal-video.json` | real-engine run results |
| `docs/evidence/b0.10/pose-overlay-real-camera.png` | `?pose=1` overlay on a real dancer |
| `docs/evidence/b0.10/SESSION-REPORT.md` | this file |

### Test harness (reusable)
| file | change | why |
|---|---|---|
| `test/recal_pose.js` | **NEW (180 lines)** | Recalibration: synthetic toNova() frames through the real page math + real-engine fake-camera phase. |
| `test/recal_pose.sh` | **NEW (47 lines)** | Launches Chrome (Edge refuses fake capture here) + local server, drives `recal_pose.js`. |
| `test/camprobe.js` | **NEW (21 lines)** | Diagnosed the fake-camera flag issue. |
| `test/diag_page.js` | **NEW (37 lines)** | Reusable page-state dumper. |
| `test/certify_loop.sh` | edited (+12) | Takes a page path so `/beta/freeze` can be certified. |
| `test/run_session.js` | edited (+6) | `--path` arg, MSYS leading-slash normalization. |

## 4. The threshold result (recalibration)
Certified **0.045** still-threshold **HOLDS** across the migration.

| band | MediaPipe motion | vs 0.045 |
|---|---|---|
| still + breathing | ~0.020–0.024 | below → STILL ✓ |
| fidget / dance | 0.054 – 0.20 | above → breaks freeze ✓ |
| kid absent | present=0% | NOSHOW, never a miss ✓ |

MediaPipe's still-band sits ~14% above MoveNet's normalized band — inside the skill's predicted 10–20% shift — with a ≥2× margin to real movement. Per-kid calibration (`finishCal`) held the floor: `[CAL] freeze stillThr=0.045 from 240 samples`. No value invented.

Real engine, fake-camera dancer:
```
[POSE] engine=mediapipe fps=9 / 10 / 6 / 11
motion 0.134 > 0.045 → MOVING, present=true
```

## 5. Two latent bugs found & fixed (on beta) — REPORTED, not touched on main
1. **`if(window.Pose…)` guard was always false** — a top-level `const Pose` is not a window property, so the **real-camera detector never started** from the live/offline paths (machine tests masked it because `__test.pose()` sets stillness directly). Fixed with `window.Pose = Pose`. **The same dead guard exists on `main`'s `pod/pages/animal-freeze.html`.**
2. **`<base href="…github.io/dance-project/">`** pinned the relative engine import off-origin. Fixed by resolving against `location.href`.

## 6. MACHINE-CERTIFY on the live pod
2 EN sessions completed against `/beta/freeze`:

| session | G1 voice | G2 | G3 | G4 flow | G5 lock | **G6 body map** |
|---|---|---|---|---|---|---|
| en-1 | FAIL | PASS | PASS | FAIL | FAIL | **PASS** |
| en-2 | FAIL | PASS | PASS | FAIL | PASS | **PASS** |

**G6 (the detection grader) passes on the new engine.** G1/G4/G5 are the **pre-existing brain/voice-tuning failures** (name echo, intro 46–56s > 40s, intro line count) that also fail on main — out of scope for a detection-only session. The 3×-clean EN+HE bar cannot be met by a detection change alone; it is gated on separate brain work.

## 7. Pod ops this session
- Launched a SECURE RTX-4090 cert pod. `launch_pod.sh` **still omits `PUBLIC_KEY`** → SSH denied (pod seeds stale account key). Fix used: DELETE + recreate via REST with `env:{PUBLIC_KEY:<id_ed25519.pub>}`.
- Pod `gp7btnb9dz6hbf` booted in ~6 min; beta routes served 200. It self-exited ~11 min post-boot (RunPod "Exited by user" — likely volume single-pod contention). Deleted; **no pod running, no ongoing cost.**
- Fake-camera gotcha: the flag is **`--use-fake-device-for-media-STREAM`** on 2026 Chromium; the old `-capture` spelling is silently ignored. Edge refuses fake capture on this laptop — use Chrome, launched via PowerShell (node-spawn dies exit 21).

## 8. Grep-proof
`grep -nE "keypoints|estimatePoses|poseDetection|SINGLEPOSE|left_shoulder|right_shoulder" beta/freeze.html`
→ one hit, a code comment. No raw indices, no engine API in the detector.

## 9. Open items (not blockers)
- **Legal footer** left untouched (LAW-CONSENT, audited) — awaiting confirmation of what "clean the footer" meant.
- **Voice graders** (G1/G4/G5) — separate brain-tuning task if the founder wants full MACHINE-CERTIFY green.
- **Founder play-test** of `/beta/freeze?pose=1` on a fresh pod when ready.
