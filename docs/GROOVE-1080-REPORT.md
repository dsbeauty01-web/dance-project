# GROOVE-1080: new 1080p groove bodies for Freeze (2026-10-20)

## Result
| step | status |
|---|---|
| Generate (fal Kling v2.1 pro i2v, ref = idle_sway t=1.0 s as start AND tail) | ✅ 10 takes; founder approved, CLI picked |
| Bake nova_groove_{a,b,c}_1080 + bake_verify + registry | ✅ all PASS, 1076×1924, 242 frames |
| Lipsync test A (+ C) | ❌ **not a PASS** → lips stay off the new bodies |
| Stream: lk_bridge.py top layer 10 Mbit/s, no 360/180 simulcast | ✅ applied on the volume, measured |
| beta/freeze.html wiring (one commit, FREEZE-APPROVED) | ✅ b40fde8, pushed to beta |
| Test pod 33cdsguzn1bh5c on **beta**: /beta/freeze serves JUDGE-TRUTH + new ids; real round recorded | ✅ A rounds 1-4 → seam swap → B rounds 5-7, no page errors |
| Deploy bug found + fixed: NOVA_DEPLOY_BRANCH never took effect | ✅ d65a228 on beta |

## Picks (founder: "all are quite good, you choose")
| body | avatar_id | take | why |
|---|---|---|---|
| A, rounds 1-4 | nova_groove_a_1080 | round 2 D-take2 (subtle groove + foot taps) | most motion of the steady-head takes (body 3.42, feet 3.04 vs round-1 A ≈1.9 / 1.2); head range 46 px |
| B, rounds 5+ | nova_groove_b_1080 | round 2 E-take1 (big groove) | big arms + side sways, faces camera throughout (E2 turns her back at 5 s) |
| C, calm pre-game | nova_groove_c_1080 | round 1 C-take2 (half-time sway) | steadiest head of all takes (31.5 px/s) |

Every take: 1076×1924 · 24 fps · 10.08 s · loop seam first↔last frame < 1/255. Sources: beta/sources/groove-1080/ (+ round2/); volume copies: /workspace/sources/groove-1080/.
Known limit: the D/A take settles in its last ~4 s (start = end frame makes Kling land early).

## Bake (pod udzxei5g2u4iem, /workspace/gallery/groove-1080-20261020/bake.log)
Command (= tools/bake_all.sh): `python -m avatars.musetalk.genavatar --file <src> --avatar_id <id> --save_path /root/av_local` → quota_guard → cp → bake_verify.sh
```
PASS nova_groove_c_1080 — frames=242 latents=3941KB full_imgs=242 mask=242
PASS nova_groove_a_1080 — frames=242 latents=3941KB full_imgs=242 mask=242
PASS nova_groove_b_1080 — frames=242 latents=3941KB full_imgs=242 mask=242
RES all three 1076x1924. Old bakes untouched (script refuses to overwrite an existing id).
```

## Lipsync verdict: FAIL (measured, with a control)
Test: live engine, body switched to A, `Live.say("Hi friend! I'm Nova, let's dance and freeze together! שלום חבר! אני נובה, בוא נרקוד ונקפא ביחד!")`, recorded from the received stream **with her audio** (beta/sources/groove-1080/tests/lipsync-test-A.mp4; first pass video-only: lipsync-test-C.mp4, mouth-A.png, mouth-C.png).
Metric: mouth-box activity (face template-tracked) during speech vs silence; control = nova_idle2, whose lips are known to work (control-idle2.mp4).
| body | speech captured | mouth activity speech vs silence |
|---|---|---|
| nova_idle2 (control) | 1.5 s | 4.87 vs 3.35 (**+45 %**: lips react) |
| nova_groove_a_1080 | 1.4 s | 2.64 vs 2.57 (**+3 %**: lips do not react) |
- Sharpness is good (crisp 1080p face, no smear). But MuseTalk barely opens her mouth on the A body: FAIL.
- Note: she spoke only ~1.5 s of the line (the brain shortened it), so this is a short sample, but the control under the same conditions clearly passes.
- Per the job rule: **no phase change.** In GAME her voice stays in the AIR on A and B; holds mute; intro/ending keep lips on nova_idle2 (`LIPS_ON_A=false`, `TALK_BODY='nova_idle2'`; `?lipsA=1` / `?talk=c` for re-tests only).

## Stream: /workspace/lk_bridge.py (backup lk_bridge.py.bak-20261020; md5 c2378e46… → 47d011c3…)
Before (line 123-124: no encoding options → LiveKit defaults: simulcast 180p/360p/full, ~5 Mbit/s):
```
                await room.local_participant.publish_track(
                    vt, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA))
```
After:
```
                await room.local_participant.publish_track(
                    vt, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA, simulcast=False, video_encoding=rtc.VideoEncoding(max_framerate=25, max_bitrate=10_000_000)))
```
Measured from the live track: `simulcast=false layers=["1076x1924@10000000"]`, ~9.1-10.2 Mbit/s, avg QP 6-11 (was 17-28 at 5 Mbit/s).
Published size = the bake's frame size (VideoSource(w,h)); the new bodies are 1076×1924, so "1080×1920" needs no code change.
Trade-off: with no low layers, a viewer below ~10 Mbit/s gets stalls instead of a softer picture. Watch for this on the founder's connection.

## Page wiring (beta/freeze.html)
- GROOVE_A rounds 1-4, GROOVE_B rounds 5+ (`grooveFor(idx)`), requested at endFreeze, **swapped only at the loop seam** (`Body.tick`, loopTime within 0.12 s of 0 / loopDur; never during a hold).
- NEUTRAL data per body from tools/find_neutrals.py on the sources (×0.96 for 24→25 fps); the freeze-clip in-points it found match the page's existing values exactly.
- The phase guard accepts A or B; voice routing goes through `gameRoute()` (air unless LIPS_ON_A and body A).
- CALM_BODY (C) is wired as an id and selectable with `?talk=c`; the default talk body stays nova_idle2 because lipsync was not proven.

## Round recording on the real beta page (test pod 33cdsguzn1bh5c, NOVA_DEPLOY_BRANCH=beta @ d65a228)
beta/sources/groove-1080/tests/rec70-beta/round-70s-beta.mp4 (1076×1924, 85.7 s, video + her voice) · console.log · page-g5/30/55/68s.jpg · seam-strip.png
```
pre   [BODY] nova_groove_a_1080 phase=game          ← A from beat one
g+12.7..51.8  rounds 1-4 STAR/BEAR/FLAMINGO/FROG on A, pose clips on holds
g+51.8 [BODY] want nova_groove_b_1080 (waits for seam)
g+58.0 [SEAM] swap nova_groove_a_1080 -> nova_groove_b_1080 loopT 0.09
g+62.4..81.2  rounds 5-7 STAR/BEAR/FLAMINGO on B
```
Seam check: the largest frame diff in the 56-60 s window is 10.6 (B's normal big-move frames reach ~20; median 1.96). The strip shows one continuous standing pose, so the swap cannot be seen.
(NOSHOW on every round = the headless fake camera has no kid in it; judging is unchanged v1.3.)
Earlier harness run on main's page: tests/rec60/round-60s-nova-stream.mp4.

## Issues hit
1. Push access: resolved (dance-project attached with push). Before that, sending page code to the pod any other way was blocked as data exfiltration, correctly.
2. tools/pod/deploy_from_git.sh: the volume repo is a single-branch clone of main, so `fetch origin beta` never made origin/beta and the reset failed silently; NOVA_DEPLOY_BRANCH=beta deployed main. Fixed on beta (d65a228, explicit refspec + logged failure). This pod got a one-line pre-fetch in its start command.
3. Live pod fp2duc119zwfhx went EXITED on its own around 10:20 UTC (not stopped by me).

## Spend: see docs/NIGHT-SPEND.md
fal 9.80 · bake pod 0.27 · test pod #1 0.22 · test pod #2 (beta) running for the founder's live play.

## Pods after the job
```
ae0iuznsz957oc bakeoff-st4-4090 RUNNING   (not mine)
bmcbcp6z3454zj hp-animals-4090 RUNNING    (not mine)
fp2duc119zwfhx nova-live-fresh EXITED
1oq9evl38daht3 nova-live-fresh EXITED
```

## READY FOR PROMOTE v1.4: **YES, after the founder's live play**
Proven on a beta pod: 1080p bodies bake-verified; A from beat one; seam-only swap to B after round 4 with no visible jump; JUDGE-TRUTH v1.3 intact; stream single-layer 10 Mbit/s; no page errors.
Lipsync on the new bodies FAILED, so the page keeps voice in the air (no phase change), as the rule says.
Still to confirm by the founder (not testable headless): (1) it plays smoothly on the founder's own connection with the 10 Mbit/s single layer (no low-bitrate fallback now); (2) a real kid's freezes are judged as before.
PROMOTE must include d65a228 (deploy fix). Do NOT merge until the founder says go.
