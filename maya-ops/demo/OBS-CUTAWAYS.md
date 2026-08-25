# OBS Cutaways — Serum (2026-08-25)
Two approved B-roll clips of the serum, used as **cutaways** during the live selling stream.
Masters live at `maya-ops/bake/src/` (1920×1080, 24fps, no audio).

## The two scenes
| Scene name | Source master | Shows | ~len |
|---|---|---|---|
| **CUT_EXAMINE** | `cutaway_examine.mp4` | Maya examining / tilting the bottle toward camera | 12s |
| **CUT_APPLY** | `cutaway_apply.mp4` | Maya applying / demonstrating the serum | 12s |

## THE RULE (read before wiring)
- Cutaways play **while the LIVE voice keeps talking** — they are B-roll over her ongoing speech.
- **Never** show a **baked Maya face fullscreen while the voice is speaking** *unless it is the ACTIVE
  MuseTalk avatar* (i.e. the lips are actually being driven). A baked clip has a still/closed mouth;
  showing it fullscreen during speech = talking with no lip movement = broken.
- So: cutaways are for **product B-roll moments** (hands, bottle, texture), or as a lower-third / PiP
  while the MuseTalk avatar stays the main face. They are **not** a substitute for the talking avatar.

## Wiring (OBS)
1. Copy the two masters into your OBS assets folder (wherever your "Maya" scene collection reads media
   from — e.g. `…/OBS/assets/serum/`). *(Exact path is machine-specific — set it once on the demo box.)*
2. Add two scenes, `CUT_EXAMINE` and `CUT_APPLY`, each a Media Source pointing at its master, set to
   **loop**, no audio.
3. If `obs-websocket` is configured, these can be triggered programmatically (scene-switch by name)
   from the sales driver; otherwise they're manual operator cuts. *(obs-websocket not confirmed set up —
   left as a manual scene for now; do not fake green.)*

## Rejected
- `maya-ops/bake/rejected/REJECTED_male-hand-bottle.mp4` — "a hand enters frame…" clip. Rejected:
  the hand reads as a **male hand**, breaks the single-host illusion. **Do not use** (bake or cutaway).
