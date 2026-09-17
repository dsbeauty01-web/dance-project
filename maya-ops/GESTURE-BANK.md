# GESTURE BANK — every clip and avatar on `maya-persist`
Surveyed 2026-09-17 on pod `78gdi0glzbk0mn` · volume `8gu2r2r0hr` (US-TX-3) · measured with ffprobe

## ⚠️ Headline: there is NO product footage on this volume

Every video here is **Maya herself**. Nothing shows the serum bottle, the texture on skin, or the
label. The stage/cutaway feature (`stage.py` + `director.py`) needs `hero` / `apply` / `examine`
clips **of the product** — none exist, so shot changes stay disabled and she degrades to spoken
answers.

`serum_present_src.mp4` is named for the serum but is Maya presenting it — it is the **avatar
source take**, not a cutaway.

---

## Avatar source takes (drive the talking head)

| File | Duration | Res / fps | What she does |
|---|---|---|---|
| `maya-ops/host/serum_present_src.mp4` | **14.04 s** | 1920×1080 @25 | Waist-up presenting take. **Single continuous shot, 0 cuts** — this is the one registered as `maya_present` and the reason the face stopped flickering. |
| `maya_avatar/source/maya.mp4` | 15.08 s | 1920×1080 @25 | Original Maya source take, registered as avatar `maya`. |
| `maya-ops/bake/maya_gesture_src.mp4` | 22.40 s | 1920×1080 @25 | Stitched gesture reel (idle→show→idle→point→idle→listen→idle). **This is the stitched build that jumped every ~3 s** — registered as `maya_gesture`. Do not use for live. |

## Gesture segments — `maya-ops/bake/src1080/` (1920×1080 @25)

| File | Duration | What she does |
|---|---|---|
| `maya_idle.mp4` | 3.52 s | Neutral idle, small natural motion — the connective tissue between beats |
| `maya_show.mp4` | 3.52 s | Open-palm "show" / presenting gesture |
| `maya_point.mp4` | 3.00 s | Points (toward product / link) |
| `maya_listen.mp4` | 3.52 s | Attentive listening pose — for while a viewer types |

## Gesture work-in-progress — `maya-ops/bake/_gesture_work/` (1920×1080 @25)

Ordered segments of the same reel; `01_show`, `03_point`, `05_listen` alternate with idles.

| File | Duration | File | Duration |
|---|---|---|---|
| `00_idle.mp4` | 3.53 s | `04_idle.mp4` | 3.53 s |
| `01_show.mp4` | 3.53 s | `05_listen.mp4` | 3.53 s |
| `02_idle.mp4` | 3.53 s | `06_idle.mp4` | 3.53 s |
| `03_point.mp4` | 3.02 s | | |

## Recordings / proofs (not usable as clips)

| File | Duration | Res / fps | What it is |
|---|---|---|---|
| `maya_present_rec.mp4` | 60.01 s | 1280×720 @30 | Screen capture of a live session |
| `maya_gesture_rec.mp4` | 45.02 s | 1920×1080 @25 | Capture of the gesture avatar running |
| `maya_live_60s.mp4` | 60.02 s | 1920×1080 @25 | 60 s live proof recording |
| `maya_voiceD.mp4` | 40.00 s | 1280×720 @**1000 fps** | Voice-D proof. The 1000 fps header is malformed — treat as audio proof only |

## Registered avatars (`opentalking/examples/avatars/`)

| Avatar id | Source | Status |
|---|---|---|
| **`maya_present`** | `serum_present_src.mp4` | ✅ **The live one.** Single take, no flicker |
| `maya_gesture` | `maya_gesture_src.mp4` | ⚠️ Stitched — visibly jumps every ~3 s |
| `maya` | `maya_avatar/source/maya.mp4` | Original, superseded |

Plus ~20 stock OpenTalking avatars (`anchor`, `newscaster`, `office-woman`, `singer`, …) — unused.

---

## What to shoot to unlock the stage feature

Three short product clips, 1920×1080 @25 to match, named so `stage.py` finds them in `CLIPS_DIR`:

| Needed | Filename | Length | Content | Triggered by |
|---|---|---|---|---|
| `hero` | `hero_serum.mp4` | ~9 s | The bottle, slow rotate, clean background | "can i see it closer", "show me" |
| `apply` | `cutaway_apply.mp4` | ~10 s | One drop on skin, spreading, absorbing | "how does it feel", "how do i use it" |
| `examine` | `cutaway_examine.mp4` | ~8 s | Close on the label / ingredient list | "what's in it", "ingredients" |

Until these exist, `stage clips available: NONE` and she answers those questions **in words only** —
which `stage.py` handles deliberately: it speaks the yes and simply does not cut, rather than
cutting to a black frame.
