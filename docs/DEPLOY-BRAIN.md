# Deploying the brain — merge to main IS the deploy (LAW-PODS-10-BRAINDEPLOY)

**The gap this closes.** The volume's hand-written `deploy_from_git()` (added 2026-09-08)
copied `pages/ shared/ models/ beta/` at every boot — but never `pod/rt_lk.py`. So a merge
to main deployed the pages and silently did **not** deploy the brain. Every brain fix
needed a manual `scp`, and the volume copy drifted from git (it was only luck that v1.0.6's
volume brain was byte-identical to main). The deploy step now lives in git as
`tools/pod/deploy_from_git.sh`, and boot.sh only calls it.

## Install (one time per volume)

The volume's `/workspace/boot.sh` must call the repo's step. Replace the body of its
`deploy_from_git()` with — or add immediately after the existing call:

```sh
bash /workspace/_repo/tools/pod/deploy_from_git.sh || echo "[DEPLOY] step failed"
```

The repo is pulled before this line runs, so from that moment on **every future change to
the deploy step ships by merge** — no volume edit ever again.

> **GOTCHA (cost a boot on 2026-09-08):** never `scp`-overwrite `/workspace/boot.sh` while a
> boot is running it — bash re-reads the file at its old byte offset and corrupts mid-boot.
> Edit only when no boot is in flight, and write-then-`mv` atomically.

## What it does

| step | behaviour |
|---|---|
| pull | fetch + `reset --hard origin/main` into `/workspace/_repo` (token from `/workspace/.deploy-token`) |
| pages | `pod/pages/*.html` → `/workspace/pages/`, `shared/*.js`, `models/*.task`, `beta/*` |
| **brain** | `pod/rt_lk.py` → `/workspace/rt_lk.py` |
| backup | `rt_lk.py.bak-predeploy` every deploy |
| drift guard | live brain ≠ what we last deployed (`/workspace/.deploy-rtlk.md5`) ⇒ it was hand-edited ⇒ saved as `rt_lk.py.bak-drift-<utc>` and shouted in the log. main still wins, but evidence is never destroyed silently |
| proof | md5 transition + `+adds -dels` in the log; full diff written to `/root/deploy-rtlk.diff` |
| restart | brain not running (the boot case) ⇒ boot's step 7 starts the new file. Already running ⇒ kill, restart detached, poll `:8765` for 60s |
| rollback | new brain does not answer ⇒ restore `bak-predeploy`, restart, log `ROLLBACK OK`/`ROLLBACK FAILED`, exit 1 |

Env overrides: `NOVA_REPO_DIR`, `NOVA_WORKSPACE`, `NOVA_DEPLOY_BRANCH`, `NOVA_DEPLOY_RESTART=0`
(copy only, never touch a running brain), `NOVA_DEPLOY_HEALTH_TRIES`, `NOVA_DEPLOY_DIFF`,
`NOVA_BRAIN_LOG`.

## Proof on the next boot

1. Before booting, confirm main's brain differs from the volume's (otherwise the run proves
   nothing): `md5sum /workspace/rt_lk.py` vs `md5sum /workspace/_repo/pod/rt_lk.py`.
2. Boot normally, then read `/root/boot.log`:

```
[DEPLOY] pages synced from main@<sha>: animal-freeze.html nova-commercial.html ...
[DEPLOY] brain rt_lk.py DEPLOYED from main@<sha>: md5 <old> -> <new> (+N -M lines, diff: /root/deploy-rtlk.diff)
[DEPLOY] brain not running — boot starts the new file at step 7 (no restart needed)
```

3. The diff: `head -40 /root/deploy-rtlk.diff` — must show the merged change (for v1.0.7,
   the `REINVITE_LINES` block).
4. Independent check: `md5sum /workspace/rt_lk.py /workspace/_repo/pod/rt_lk.py` — identical.
5. Live-pod re-run (no reboot): `bash /workspace/_repo/tools/pod/deploy_from_git.sh` right
   after a merge must log `brain RESTARTED and healthy on :8765`.

A second boot with nothing merged must log `brain rt_lk.py already at main@<sha> — UNCHANGED`
and touch nothing.

## Sandbox evidence (2026-09-18, no pod needed)

`tools/pod/deploy_from_git.sh` was exercised against a fake remote + fake `/workspace`
before it ever ran on a pod:

- drifted volume brain ⇒ `WARNING ... hand-edited`, `bak-drift-*` written, main deployed
- idempotent re-run ⇒ `UNCHANGED`, exit 0
- brain fix merged ⇒ deployed, `bak-predeploy` holds the old file, diff file matches
- pages-only merge ⇒ pages updated, brain untouched
- **restart path** (real process on `:8765`) ⇒ `brain RESTARTED and healthy`
- **rollback path** (deliberately broken brain on main) ⇒ `ROLLING BACK` → `ROLLBACK OK`,
  health back to 200, live file back to the previous version, exit 1

Two defects were found and fixed by that sandbox run: a `:`-delimited copy table ate the
drive letter on non-pod paths, and `pgrep` was assumed present (now falls back to `ps`).
