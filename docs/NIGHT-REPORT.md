# NIGHT RUN — 17 Oct 2026 (18:42 – 19:30 UTC)

```
NIGHT RUN — 2026-10-17
Mission phases: 1 ✅  2 ✅ tool ready (GUESS/STAND-IN pending clips)  3 ✅  4 ✅  5 ✅  6 (needs Refael)
Backlog: A ✅  B ✅  C ✅  D ✅  E ✅  F ✅ (with an honest limit)  G ✅  H ✅
Replay tests: 146/146 green (112 table rows + 9×3 low-fps checks + 25 judge tests)   CI: green on every push
Videos: docs/evidence/night/b-doctor.mp4 (29 s) · docs/evidence/night/e-demo.mp4 (60 s)
        + the 6h set: docs/evidence/6h/p1-freeze.mp4 · p3-copy.mp4 · p4-groove.mp4 · p5-launcher.mp4 · p6-live-camera-path.mp4
Laws check: numbers=0  red=0  fake-credit=0 (3 found and removed tonight)  skip-on-unseen=yes
SPEND: total $0.00 of $6.00 cap · pods started: 0 · pods still running that I started: 0 (listing in docs/NIGHT-SPEND.md) · paid API calls: 0 · Render changes: none
Pods found at Step 0 that I did NOT start: 24 × maya-* pods, all EXITED (none running). They still bill $0.165/hr
  (~$4/day) for their stopped disks. Not touched (Maya law). Full list in docs/NIGHT-SPEND.md
Beta Pages URL: https://dsbeauty01-web.github.io/nova-play/6h/beta/index.html — NOT LIVE YET (404): needs the
  PowerShell copy from the chat (my push to nova-play was blocked by the session's safety check)
NEEDS REFAEL (max 3): 1) the 3 phone clips (ref-still / ref-sway / ref-dance)  2) one real play per game + "Save my play"
  (after the PowerShell copy above)  3) PROMOTE decision
Blocked / honest problems: see below
```

## What got done tonight

| item | result | proof |
|---|---|---|
| Step 0 | NOVA-GO.md isn't in the repo; mission status read from beta: phases 1–5 done, 6 needs Refael | docs/NIGHT-SPEND.md |
| A edge cases | all 24 repo videos pose-tracked + 42 synthetic edge clips (half-body, too-close, too-far, dark, jitter, one-arm-hidden) → **66 clips × 3 games all PASS** (ends, truth audit, no star from noise) | test/replay/edge.mjs |
| B Camera Doctor | one pre-game screen for every game: step back / come closer / move this way / I can see you ✓; never blocks (6 s) | test/replay/doctor.mjs 11/11 · b-doctor.mp4 |
| C Hebrew + English | every screen in both, RTL right, no numbers | docs/evidence/night/c-screens-en.png, c-screens-he.png |
| D brain events | `window.novaEvents`: round_start · hit · skip_unseen · miss · medal, also in the saved file | test/replay/events.mjs: 18/18 match the tables 1:1 |
| E demo mode | beta/demo.html loops the 3 real games on recordings, "Tap to play!" | e-demo.mp4 |
| F performance | frame-skip for slow detectors; Laws proven at 30 · 12 · 6 fps | docs/evidence/night/f-perf.md · test/replay/fps.mjs |
| G Save my play | ⬇ on every medal screen, `<game>-<timestamp>-play.json` with events | docs/evidence/night/g-*-play.json |
| H GAMES.md | one page per game in plain words, every number with its source | docs/GAMES.md |

## Fake-credit paths found and removed tonight (by the edge clips)

1. **Groove starred a frozen body on a jittery camera.** The 0.25 GUESS floor was below camera noise. New floor 0.43 = 2 × the
   measured noise of a body that can't move (0.215). STAND-IN until Refael's ref-still.
2. **Groove's bonus star came from noise.** Jitter makes fake "bounces", and at ±150 ms random bounces land on-beat 65 %
   of the time. Now only bounces in bars where the player really moved count.
3. **Copy gave "right hand up" with BOTH arms up and the left one hidden.** One-hand poses now have to SEE the other arm down.

## Honest problems

- **Speed without a GPU:** with MoveNet on the CPU, the page judges 18 fps (5 fps on a slow CPU). Frame-skip doubled the
  lights (36 fps), but a slow CPU-only machine is still under 24. The rules still hold at 6 fps. Next step, not built:
  MoveNet in a Web Worker. A normal laptop uses its GPU, so a real-camera play will tell us more.
- **Freeze calls gentle swaying "still"** (dance-active: energy 1.19). That's how the September real-body measurement set
  it: only clear dancing is caught. Refael's clips will confirm or move it.
- **Groove "on the beat" bonus** still rewards bouncing more than timing (±150 ms covers 65 % of the beat). Needs a decision:
  ±80 ms, or an 80 % bar.
- **Copy:** "arms out" has no held clip, so it's unproven; "hands on head" has no clip and its targets are a GUESS.
- **Tags** `beta-night-01 … 08` exist only locally: this session can't push tags (proxy 403). Commits are all on `beta`.
- **Hosting:** GitHub Pages serves `main` only; raw.githack shows ads. The `nova-play/6h/` copy needs Refael's PowerShell
  paste from the chat.
