# Night run — spend log (cap $6.00)

Default for the whole run: zero GPU, zero paid APIs. Everything is browser-only (MoveNet in headless Chromium, replay tests).

| item | start (UTC) | end (UTC) | $ |
|---|---|---|---|
| Step 0 pod audit (read-only RunPod API list) | 2026-10-17 18:42 | 18:43 | 0.00 |

## Step 0 pod audit — 2026-10-17 18:42 UTC

RunPod account: balance $10.93 · **current spend $0.165/hr with ZERO pods running**: that is the disks of stopped pods.
24 pods, **all EXITED, all named `maya-*`. Not started by me and not touched (Maya law)**. Running: 0.

| id | name | status | $/hr when running | exited |
|---|---|---|---|---|
| 0yvlab94u3xa42 | maya-soulx-1013-0616-tier2-v2-live-r4 | EXITED | 0.89 | Oct 13 13:40 |
| 1f78gxbh3pxx90 | maya-wide-1013-0246-tier2-v2-r1 | EXITED | 0.89 | Oct 13 11:10 |
| 331cazw5hpp4z0 | maya-soulx-1013-2226-tier2-v2-live-r9 | EXITED | 0.89 | Oct 14 07:58 |
| 3k3ty1k8wpwv0w | maya-golden-1016-0109-golive-1 | EXITED | 0.89 | Oct 16 08:22 |
| 5pm1bdkrxk7c1n | maya-wide-1012-1530-golive | EXITED | 0.89 | Oct 12 15:54 |
| 5u5bzyrlfs64xw | maya-wide-1012-0020-tier2-live-2 | EXITED | 0.89 | Oct 12 08:53 |
| 6d79ypooavqjwg | maya-golden-diag2-1015 | EXITED | 0.89 | Oct 16 03:52 |
| 8qxogris2dro2b | maya-golden-1016-0410-golive-1 | EXITED | 0.89 | Oct 16 11:14 |
| aj8338he72u71a | maya-soulx-1013-0715-tier2-v2-live-r6 | EXITED | 0.89 | Oct 13 15:17 |
| ak4hnicl0qhpro | maya-wide-1012-2155-tier2-final | EXITED | 0.89 | Oct 13 05:48 |
| app5hs8ynxyfry | maya-golden-1016-0219-golive-1 | EXITED | 0.89 | Oct 16 11:10 |
| c6ebffwmeeo3ge | maya-wide-1013-0055-tier2-v2-dryrun | EXITED | 0.99 | Oct 13 08:19 |
| fsqik0m348160d | maya-wide-1012-1335-golive | EXITED | 0.89 | Oct 12 13:47 |
| i1mafwlzicil12 | maya-golden-1015-0704-golive-4 | EXITED | 0.89 | Oct 15 14:10 |
| jndyqtrphapj2l | maya-wide-1011-2344-tier2-first-live | EXITED | 0.82 | Oct 12 07:13 |
| lbaakprk59d1ca | maya-golden-1015-0331-golive-1 | EXITED | 0.89 | Oct 15 10:46 |
| m38cplk646s240 | maya-golden-1016-0135-golive-1 | EXITED | 0.89 | Oct 16 08:43 |
| o709q6ozqbio0t | maya-wide-1015-2053-golive | EXITED | 0.89 | Oct 16 03:56 |
| tf237ylhejpaky | maya-soulx-1014-2054-tier2-v2-live-r10 | EXITED | 0.89 | Oct 15 04:25 |
| tvn5wile2oauyb | maya-wide-1012-0532-tier2-dryrun | EXITED | 0.89 | Oct 12 12:36 |
| wb6lo7voizju4x | maya-wide-1013-0430-tier2-v2-r3 | EXITED | 1.09 | Oct 13 13:00 |
| xisugw15qquvew | maya-soulx-1013-1125-tier2-v2-live-r8 | EXITED | 0.89 | Oct 13 20:42 |
| yjf7r6gvmjubqd | maya-golden-diag-1015 | EXITED | 0.89 | Oct 16 03:35 |
| ytt0abrodiggmj | maya-wide-1012-0538-tier2-dryrun | EXITED | 0.89 | Oct 12 12:56 |

No Nova tester pod is listed (the 16:30 tester pod is not on this account's list right now).
| A–H (all browser-only: headless Chromium, MoveNet WASM, ffmpeg, Node) | 18:43 | 19:30 | 0.00 |

**Total: $0.00 of $6.00.** Pods started by me: 0. Paid API calls: 0. Render: unchanged.

## End-of-run pod listing — 2026-10-17 19:29 UTC

`spend/hr 0.165 · pods 24 · {'EXITED': 24} · running: []`. The same 24 Maya pods as Step 0, all EXITED, none running.
Pods I started: 0, so 0 are running.

## 2026-10-20: GROOVE-1080 job (cap $12, fal + RunPod)

| item | start | end | $ |
|---|---|---|---|
| fal Kling v2.1 pro i2v ×6 (A/B/C × 2 takes, 10 s each, $0.098/s from fal pricing API) | 09:12 | 09:18 | 5.88 |
| fal Kling v2.1 pro i2v ×4 round 2 (D subtle groove + foot taps ×2, E big groove ×2, cfg 0.7) | 09:31 | 09:37 | 3.92 |
| RunPod bake pod udzxei5g2u4iem (Secure 4090; no Community stock ×3), 3 bakes + verify | 10:05 | 10:23 | 0.27 |
| RunPod test pod fao8782p73h13a (Secure 4090): lipsync A/C, lk_bridge patch, stream stats, 60 s round | 10:21 | 10:36 | 0.22 |

**Job total: $10.29 of $12.00.** RunPod pods started for this job: 2, both terminated via REST (listing in docs/GROOVE-1080-REPORT.md).
Outside this job's cap: live Freeze pod `fp2duc119zwfhx` (Secure 4090, $0.89/hr) from the earlier v1.3 run, found EXITED at 10:20 UTC (not stopped by me).
