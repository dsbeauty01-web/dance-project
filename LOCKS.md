# LOCKS — founder-approved milestones, rollback-forever

Append-only. A row is added ONLY when the founder says **LOCKED** and the CLI runs
`tools/lock.sh <name> "<desc>"`, which tags the commit (`locked/<name>-<date>`) and pushes it.
Any locked point is restorable forever: `git checkout <tag>`.

| Date | Tag / Ref | What is locked |
|------|-----------|----------------|
| 2026-07-08 | milestone-1 | First green milestone baseline (July) |
| 2026-07-16 | DIRECTOR-GOLD | Certified commercial intro — greet→name→shoulder-light→offer games (golden) |
| 2026-08-07 | dd671f9 (FREEZE V2.1) | Freeze game DONE + founder-approved — page is game master, brain is voice only |
| 2026-08-08 | 959024c | marin IS Nova's voice (OpenAI Realtime primary) |

<!-- lock.sh appends new rows below this line -->
