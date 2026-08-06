# START HERE — every CLI session, read this first

This project has been worked on by ~40 CLI sessions. Fixes were applied, then
silently overwritten or lost by later sessions — the same fixes re-ordered
dozens of times. That era is over. Fixes are now **walls**.

## The law of laws

- **[LAWS.md](LAWS.md) is APPEND-ONLY.** Add laws; change a law's `status` only
  on a written founder decision. **Never delete a law or its test.**
- Every law has a **marker** — a literal string that must exist in the code. CI
  (`.github/workflows/laws.yml`) runs `tools/laws/run-all.sh` on every push:
  - each `tools/laws/law-*.js` checks one law,
  - `check-syntax.js` compiles every inline `<script>` + shared JS,
  - `check-markers.js` greps every ACTIVE marker in LAWS.md against the code.
- **If your change breaks a law-test, you RESTORE the law — you never delete the
  test.** Removing a marker without a written founder decision is a **treaty
  violation** (`law-treaty`).
- A build can be RED for exactly one reason: an ACTIVE law's marker vanished.
  Fix = put the law back, not silence the alarm.

## Run the walls before you push

```bash
bash tools/laws/run-all.sh      # PASS / FAIL / known-LOST per law; exits red on a real regression
```

Green means every active law holds. `LOST` lines are the red-list
(pre-Guardian losses, see GUARDIAN-REPORT.md) — they do not block, but do not
add to them.

## Adding or restoring a law

1. Land the code (the marker string must exist in the file).
2. Add a row to LAWS.md — the human section **and** the machine block at the
   bottom: `law-id | active | file1,file2 | marker one ;; marker two`.
3. If it deserves a rich test, add `tools/laws/law-<id>.js` (copy an existing
   one — they are ~10 lines).
4. Run `bash tools/laws/run-all.sh` — it should be green.

## Standing project laws (see LAWS.md for all)

- **law-treaty** — one session per flagship file; `git add` **named files only**,
  never `-A`/`.`; `git status` before every commit; an unauthored change = STOP + ask.
- **law-v2v** — the voice-to-voice pipe is SACRED. No interruption guards / ear
  shields / VAD ctor changes. Change only behind a spoken-WAV probe.
