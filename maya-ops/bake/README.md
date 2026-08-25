# maya-ops/bake — serum bake sources + masters (2026-08-25)
Masters are the QC'd, bake-safe re-encodes. The heavy `.mp4` files are **gitignored** (regenerable
from the Downloads originals with the command below; the pod session reads them from the working tree).

## Masters in `src/` (1920×1080, 24fps, no audio, H.264 crf16)
| Master | Role | From (Downloads original) | QC verdict | ~size |
|---|---|---|---|---|
| `serum_present_src.mp4` | **PRIMARY bake source** | `inyUdTrS5MYS1I_vq1Ebx_output.mp4` (14s) | **BAKE-READY** — frontal medium-large face, **mouth closed throughout**, bottle stable, no ghost/double-face. Strongest source. | 6.8 MB |
| `serum_close_src.mp4` | SECONDARY bake source | `SV6XX7Eea7OhJ9L8pBSqm_output.mp4` (15s) | **BAKE-READY** — mouth closed, no ghost; note a wide→**extreme-closeup zoom** (framing changes a lot). Bake only if time (per order). | 8.7 MB |
| `cutaway_examine.mp4` | OBS cutaway (not a bake) | `LYe6THt5xHClXCNHctV1c_output.mp4` (12s) | B-roll — examining/tilting bottle. | 6.8 MB |
| `cutaway_apply.mp4` | OBS cutaway (not a bake) | `8ztOV8tdknc3xx8ik8WYP_output.mp4` (12s) | B-roll — applying serum. | 8.2 MB |

**No trimming was needed** — dense frame scan of both bake sources found no ghost/double-face, no
open-mouth/talking, no deformed hands or morphing bottle.

## Host-identity note (flag for the human)
The serum host is a **photorealistic woman** (dark hair, blazer). This is a **completely different look**
from `maya_rapa` (stylized 3D cartoon dancer). Switching `maya_rapa` ⇄ `maya_serum` live = cartoon ⇄
real person — a hard visual jump. Not a bake blocker; raising it so it's a deliberate choice.

## Regenerate a master (exact command)
```
ffmpeg -i IN.mp4 -vf "scale=1920:1072:flags=lanczos,pad=1920:1080:0:4" \
  -r 24 -an -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p OUT.mp4
```
Originals are kept untouched in `~/Downloads` (and in `mayabake.zip`).

## Rejected
`rejected/REJECTED_male-hand-bottle.mp4` — "a hand enters frame…" clip; the hand reads as a **male
hand** → breaks the single-host illusion. Do not use.

## Next (STEP 2 — needs a pod + human go)
Bake `maya_serum` from `src/serum_present_src.mp4` via the volume `bake.sh` flow (same as rapa:
`python -m avatars.musetalk.genavatar --file … --avatar_id maya_serum`). Verify latents>1MB + frame
counts, register on volume `1ditrne6cb`. Optional `maya_serum_close` from `serum_close_src.mp4` if time.
