# Night item F: frame rate (measured 2026-10-17, headless Chromium, no GPU)

## Replay harness (recorded keypoints, test/proof/perf.mjs)

| game | CPU | lights fps | judged fps | ≥ 24? |
|---|---|---|---|---|
| freeze | 1× | 60.1 | 60.1 | yes |
| copy | 1× | 31.9 | 31.9 | yes |
| groove | 1× | 60.1 | 60.1 | yes |
| freeze | 4× | 60.0 | 60.0 | yes |
| copy | 4× | 32.0 | 32.0 | yes |
| groove | 4× | 58.4 | 58.4 | yes |

## Live camera path (fake webcam → MoveNet in the page, CPU-only WASM, test/proof/perf-live.mjs)

This is the worst case: no GPU. A laptop's browser runs MoveNet on WebGL/GPU, which this container doesn't have.

| | CPU | lights fps | judged fps |
|---|---|---|---|
| before (MoveNet on every frame) | 1× | 17.6 | 17.6 |
| before | 4× | 5.0 | 5.0 |
| **after** (frame-skip when a detection takes > 25 ms) | 1× | **36.1** | 18.1 |
| **after** | 4× | **9.7** | 4.9 |

Frame-skip doubles the lights without losing judged frames. **CPU-only at 4× is still below 24 fps.** MoveNet runs on
the page's main thread. The next step is a Web Worker for the detector, so the lights can stay at 60 fps whatever
the detector does. Not built tonight.

## Laws at low frame rates (test/replay/fps.mjs, in CI)

Every game gives the same verdicts judged at 30, 12 and 6 fps: still → star, dancer → none, empty → skip, the game ends.
The judges work per second (energy in shoulder-widths per second, holds in seconds), not per frame.
