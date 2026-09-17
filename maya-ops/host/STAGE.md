# GESTURES ON DEMAND — the plan, and what shipped (2026-09-17)

## The idea (yours, and it's the right one)
A viewer asks "can I see the serum?" — a real host says "sure, look" and the shot changes.
We were trying to make her BODY move on command, which this engine cannot do mid-sentence, and
which flickered every time we stitched poses. So we move the SHOT instead. Same effect on screen,
zero risk, and every piece already existed.

## What she does now
viewer: "can i see the bottle closer?"
  → she SAYS "Sure — look at this."          (spoken first; a silent cut reads as a glitch)
  → the shot cuts to the product clip         (director.py, 7–10s)
  → her answer continues over the product     (voice never stops)
  → back to her automatically

Mapped requests → what appears on screen:
| viewer asks | she says | shot |
|---|---|---|
| show me / can I see / closer / zoom | "Sure — look at this." | full cutaway, hero clip, 9s |
| how does it feel / texture / absorb / sticky | "Here's the texture — watch." | full cutaway, apply clip, 10s |
| how do I use it / routine | "Easiest if I show you." | picture-in-picture, apply, 10s |
| how big / size / how long does it last | "Let me show you the size." | picture-in-picture, hero, 7s |
| what's in it / ingredients / label | "Let me show you the label." | full cutaway, examine, 8s |
| price / how much / discount | "Here's today's price on screen." | price banner, 12s |
| link / where to buy / send me | "Link's going up now." | price banner with the link, 12s |

## Rules it enforces (each one is a bug we already lived through)
- She speaks the yes BEFORE the cut — never a silent shot change.
- 25-second cooldown per request type: asked twice, she answers, she doesn't re-cut. Rapid
  cutting reads as broken, not lively.
- Never cuts away mid-answer to another viewer.
- Never cuts on a medical question — that answer stays on her face. (Verified in QA.)
- If a clip is missing it degrades to a spoken answer + gesture, never a black frame. It scans
  CLIPS_DIR at startup and logs exactly which clips it found.
- A burst of people asking the same thing cuts ONCE, and the spoken yes opens the batched answer.

## Status
- QA: **22/22 PASS**, including "every show request gets a spoken yes + a shot change",
  "medical never triggers a cut", and "degrades when clips are missing".
- Needs `director.py` running (built, never yet proven on a live stream) and the product clips
  in CLIPS_DIR named with hero / apply / examine in the filename.
- Her body is still a single calm take. That is now fine — the shot is doing the moving. The
  9-clip gesture library in GESTURE-CLIPS.md is no longer urgent; it becomes polish, not the fix.

## What to expect on the next live
Comment "can i see it closer?" → within ~2s you hear "Sure — look at this," the frame becomes the
serum for 9 seconds while she keeps talking, then she's back. If the shot does NOT change, the
cause is director.py not running or CLIPS_DIR empty — the startup log says which.
