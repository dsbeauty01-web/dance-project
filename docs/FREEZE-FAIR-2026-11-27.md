# Fair Freeze: the animal is announced before the music stops (2026-11-27)

## What Refael reported
Play B (pod pxxtn3ptgpglkx, sha f66cc70): 1 star of 6, "scoring does not work; it worked before, the fix is on GitHub".

## What was measured (his own recording, play-20261127082412-0o0x.mp4)
Music stops taken from the recording's sound level; his body motion from a pose model run on his camera half of the
recording (6 upper joints, shoulder-widths per second; tool: MediaPipe lite, NOT the game's MoveNet, so the scale is
indicative; a truly still body reads 0.1-0.3 here).

| freeze | animal | music stop (s) | he became still (s after stop) | verdict in the game |
|---|---|---|---|---|
| 1 | flamingo | 68.2 | 2.3 | missed |
| 2 | bear | 80.5 | 2.5 | almost |
| 3 | frog | 91.2 | 2.8 | star (not explained by this measurement) |
| 4 | star | 104.3 | 2.2 | missed |
| 5 | statue | 115.6 | 2.15 | missed |
| 6 | bear | 126.4 | 1.85 | almost |

Every time he then held the pose perfectly still for about 2 s, after the 2.5 s judging window had closed.
Cause: the animal card appeared AT the stop (beta/freeze4.html onEvent 'freeze'), so the player moves INTO the pose
while the judge (0.6 s grace, breaks on 0.25 s of motion above 1.0-1.1 sw/s) is already running.

## What "worked before" on GitHub
main pod/pages/animal-freeze.html (READY.md scheduler, 2026-08-27): a live warning 4.5 s before every freeze that lands
about 3 s before it, and Nova's pose clip swapping in from T-0.6 s. The child knew the pose before the stop.

## The fix
- beta/lib/freeze-game.js: new pace value `cueS` (default 0 = off) and event `cue {animal, inS}` during the dance.
- beta/freeze4.html: passes cueS 3.0 (the main warning lead; fast proof mode 1.5 [CLI-FILL]); on `cue` the animal card
  and the caption "Get ready: <animal>!" show while the music still plays. Screen only: no voice line, nothing sent to
  her brain. `?cue=0` restores the old behaviour.
- The judge, its thresholds, the grace and the hold length are unchanged. Suites: freeze2_hold 13/13, freeze2_realdata
  12/12, live judge green, replay_all green.

## Not proven
Whether he now scores: only a real play shows it. Every freeze logs `judge freeze {...}` and `judge cue ...`.
QUESTION for Refael: partial credit ("almost" = silver) as the old game's fraction scoring had - not changed here.
