# LIVE-INTRO — the quota is cleared and the pages are back. There is still no recording, and the volume needs one 17 KB file put back.

**Session `novafix-intro`, 2026-11-02. Four pods, 65 min of pod time ≈ $0.96 measured;
account balance went $1.4334 → −$0.0404, a delta of $1.47 including storage on six network
volumes. Pods remaining: 0. The $3 cap was not reached — the ACCOUNT ran out of money.**

> **Read `docs/nova-ditto/live/torchfix/README.md` before booting the live stack.** One file,
> `torch/lib/libtorch_global_deps.so`, is missing from the volume's python tree because of a
> mistake this session made. The real file is committed next to that README with the command
> to drop it in. Until it is in place `import torch` fails, the MuseTalk app cannot start and
> `:8765` never answers — **the pages are fixed but the stack will not boot.**

| the mission | state |
|---|---|
| free the quota on `1ditrne6cb` | **DONE.** 2.1 GB freed. A 1 MB write failed before; 512 MB writes now |
| restore the truncated pages | **DONE and verified.** 0 files of 0 bytes under `/workspace/pages` |
| prove the live page over HTTP (`curl` + `JUDGE-TRUTH`) | **NOT DONE** — blocked by the torch file above |
| face engine: probe + apply the Ditto patch | **DONE.** probe 4/4 on the pristine file, `apply rc=0`, and the patched bridge ran: `[DITTO] publish clock started`, `video track published 720x1288` |
| **the recording of the real intro as a conversation** | **NOT MADE.** She never spoke. Nothing was captured that could be dressed up as a recording |

---

## 1. The quota — cleared, and measured by writing, not by `df`

`df` is useless on these volumes: it reports the underlying cluster, `2.2P 1.8P 493T 78%`,
not the 50 GB quota (`tools/pod/quota_guard.sh` says the same, 2026-08-15). So headroom here
is measured by **actually writing a file**:

| | 1 MB | 512 MB | 2 GB |
|---|---|---|---|
| before the clean | **FAIL** Errno 122 | FAIL | FAIL |
| after the clean | **OK** | **OK** | FAIL |

`du` on the volume: **50.3 GB → 48.2 GB** on a 50 GB quota. Freed, by category:

| category | freed | items |
|---|---|---|
| `__pycache__` + `*.pyc` | **1.9 GB** | 1810 |
| logs (`*.log`, `nohup.out`, `core.*`) | 17.3 MB | 221 |
| package caches (`/.cache/`, `_cacache`, conda pkgs) | 11.7 MB | 5 |
| `tmp` / `*.tmp` / `*.part` | 1 B | 1 |
| stale `_repo*` clones beyond the newest | 0 B | 0 |

**Nothing on the deny list was touched**: `LiveTalking/data/avatars` (the bakes — 13.4 GB,
treasure, repo law 8), `sources/`, `media/`, any `*.mp4`, `boot.sh`, `lk_bridge.py`,
`rt_lk.py`, anything named `maya*`. Full survey — the 30 largest directories, the 30 largest
files, every 0-byte file under `pages/`, and the write probes — in
`docs/nova-ditto/live/logs/quota_survey.txt`.

**The 2 GB gate fired and I did not guess.** After the allow-list, 2 GB still would not
write, so the job stopped and asked. I continued on a measured basis rather than deleting
more: the deploy needs ~30 MB and 512 MB was proven writable, i.e. ~20× headroom. The
`scratch` list it offered was **7.3 MB total and half of it was wrong** — my date regex had
matched python `dist-info` directories whose *version strings* contain dates
(`types_pyyaml-6.0.12.20260906.dist-info`, `types_protobuf-7.34.1.20260518.dist-info`).
Deleting those would have corrupted the envs. That is exactly why dated directories are
listed and never auto-deleted.

## 2. The pages — restored, with the file-by-file proof

`boot.sh`'s own deploy at `NOVA_DEPLOY_BRANCH=nova-ditto` rewrote them, as §8 of the previous
report predicted it would once there was room.

* **86** files were 0 bytes, not the ~28 previously found.
* After the deploy: **72 of 86 non-zero, 0 missing.**
* The **14** that stayed at 0 were *all* `*.novalive-new` — the previous session's abandoned
  atomic-repair temp files, referenced by nothing. Deleted.
* **Fresh scan afterwards: 0 files of 0 bytes under `/workspace/pages`.**

```
/workspace/pages/beta/freeze.html                  147542 bytes   <- THE COMMERCIAL PAGE
/workspace/pages/models/pose_landmarker_lite.task 5777746 bytes
/workspace/pages/shared/light-engine.js             28207 bytes
/workspace/pages/shared/pose-engine.js               4946 bytes
/workspace/pages/upperbody.html                     39733 bytes
/workspace/pages/beta/wave.html                     13062 bytes
```

`logs/pages_restore_verify.txt` · `logs/pages_check_pod2.txt` · `logs/deploy.log`

**What is still missing is the HTTP proof.** `curl /beta/freeze?intro=freeze` needs a running
brain, and the brain cannot start until the torch file is back. The bytes are on disk and
`deploy.log` shows them written; the `http=200 … JUDGE-TRUTH=n` line is not yet measured, so
it is not claimed.

The deploy also moved the brain: `rt_lk.py` md5 `b57bd139` → `9f64d1e6`
(`nova-ditto@aa35c85`), which is what `NOVA_DEPLOY_BRANCH=nova-ditto` means. The volume's
previous file was kept by the deploy itself at
`/workspace/rt_lk.py.bak-drift-20261102T030813Z`.

## 3. The face engine — the patch applied, and Ditto reached the live path

This is the step the quota blocked on 2026-11-01, and it worked:

```
probe /workspace/lk_bridge.py   md5 1c4448b475ae0cdd719aef4edaa90337
  OK  A1  return rgba.tobytes()        count=1
  OK  A2  w, h, rgba = await vq.get()  count=1
  OK  A3  pcm = await aq.get() + n =   count=1
  OK  A4  await asrc.capture_frame(fr) count=1
apply rc=0   APPLIED  1c4448b4... -> e9be0f4fa9560bff522e95687b093cde
```

Ditto came up on the full-body bank in **150 s** and **175 s** on two pods
(`ready: true`, `src_frames 344`, `out_wh [1074, 1920]`), and with `NOVA_FACE=ditto` the
patched bridge genuinely drove it:

```
[DITTO 04:02:11] publish clock started with 10 frames of slack -- audio must be delayed 1800 ms
bridge: video track published 720x1288
bridge: engine connected
BRIDGE_DROP: IncompleteReadError ... frames_this_conn=0
bridge: engine disconnected
```

So the Ditto side of the live path is real and publishing. The engine then disconnected
because the engine is the MuseTalk app, and the app was dead on the torch import. **Whether
her lips move in the live path is therefore still unmeasured** — `frames_this_conn=0` means
no engine frame ever arrived, so nothing can be concluded about her mouth.

**A trap for the next session.** `apply()` calls `probe()` first and refuses on anything but
4/4, *even when the file already carries the `_NOVA_FACE_DITTO` marker*. So on an
already-patched bridge the probe reports `A3 count=0` and the run silently falls back to
MuseTalk. The right order is **`--revert` → `--probe` → `--apply`**, which is what
`novafix_job4.sh` does.

## 4. What I broke, and what it costs to put right

Full detail and the fix: **`docs/nova-ditto/live/torchfix/README.md`**.

1. **Nine packages, from deleting `*.pyc`.** Part of
   `/workspace/_sys/pylibs311_good/dist-packages` is in the legacy **sourceless** layout,
   where `pkg/mod.pyc` *is* the module. Deleting those deleted the modules: flask, werkzeug,
   click, itsdangerous, idna, certifi, edge_tts, websockets, aiortc. **All nine reinstalled
   and importing.** The tree holds 13921 `.py` files and 281 `.so` — it was never a .pyc-only
   tree, which is precisely why the deletion looked safe. `free_quota.py` is fixed at source
   and has a fixture covering a mixed package.
2. **torch, from a repair that was worse than the fault.** Resolving the same class of
   failure, `repair_pylibs.py` found `torch.masked.maskedtensor.core` missing — a corner of
   torch the live stack never imports — and answered with
   `pip install --target <tree> --upgrade torch`: a ~2.8 GB unpack aimed at 1.5 GB of
   headroom. `--upgrade` removes before it writes. I killed it to stop it writing; the
   removal had already happened. **`torch/lib/libtorch_global_deps.so` is gone and torch and
   torchvision do not import.** `NEVER_INSTALL` now makes that impossible.
3. **A version-mismatched donor copy.** `repair_torch.py` was meant to restore missing files
   from a *version-matched* torch elsewhere on the volume. The only donor was
   `opentalking/.venv` at **2.10.0** against our **2.9.1+cu129**, and my fallback took it
   anyway: 3707 files / 22.5 MB copied, almost all C++ headers under `torch/include/`
   (compile-time only, inert at runtime) plus a few `.py`. It did not help — 2.10.0 does not
   ship `libtorch_global_deps.so`. Every copied file carries mtime **2026-11-02 04:08 UTC**;
   the README gives the `find` that lists them.

**The honest fix is already in the repo and costs 17 KB**, pulled from the correct wheel with
`tools/pod/zipgrab.py` (HTTP range reads — one member, not a 2.5 GB download).

## 5. Why there is still no recording

Everything the recording needs was proven to work on pod 4 — **Chromium 156.0.8078.4 launched
and verified**, Ditto ready, the bridge patched, the harness present and previously proven
end to end. The one missing piece was the brain, and the brain was down because of §4.2.

The honest order of events, including my own waste:

| pod | min | $ | what it bought | what it cost |
|---|---|---|---|---|
| `mcyb9x7k84u18p` | 17.6 | 0.261 | **quota freed, pages restored**, Ditto 175 s, patch applied | my `*.pyc` deletion took the stack down |
| `dhj8awp0qk0qsj` | 21.0 | 0.311 | the 9 broken packages found and fixed; pages confirmed whole | I ran `apt` and `playwright install --with-deps` in parallel, they fought over the dpkg lock, Chromium never installed |
| `5i3vcssa0p466s` | 6.2 | 0.092 | Chromium fixed and verified | I had put `torch` in the repair targets; killed to stop it writing, which is §4.2 |
| `mk9l6u4d70b9s1` | 20.1 | 0.298 | probe 4/4 → apply rc=0 → Ditto live on the bridge | torch already broken, so no brain and no recording |
| | **64.9** | **$0.96** | | |

Pod 4 was not terminated by me: **RunPod stopped it at ~04:12 when the account balance went
negative.** Its last step would have been `--revert` on `lk_bridge.py`, so:

> **`/workspace/lk_bridge.py` is LEFT PATCHED** (md5 `e9be0f4fa9560bff522e95687b093cde`), with
> its backup still beside it as `lk_bridge.py.bak-ditto-*`. This is safe to leave: with
> `NOVA_FACE` unset or `musetalk` the patched file behaves exactly as before, and `boot.sh`
> does not set `NOVA_FACE`. To restore the original anyway:
> `python3 tools/pod/ditto_bridge_patch.py --revert`.
> `/workspace/nova_ditto.py` (the sidecar) was also left in place.

**On the money, so the number is not misread.** $0.96 is the measured create→terminate
lifetime of my four pods at $0.89/h. The account delta was $1.47, and the difference is
per-second billing plus storage on six network volumes, most of which are not this lane's.
The binding constraint was never the $3 cap — **the account only had $1.43 when I started**,
and I spent it on four pods instead of one because of three bugs of my own. One pod, written
correctly, would have done the whole job in about 20 minutes.

A side effect worth stating: when the balance went negative, the only other pod on the
account, `clat--body` (another session's), also stopped appearing. I never touched it, but my
spending is part of why the account hit zero.

## 6. The security item, still open

`boot.sh`'s deploy prints the **full remote URL on a failed deploy**, and that URL carries the
volume's GitHub deploy token in clear text (`/workspace/.deploy-token`), so it lands in
`/root/boot.log` verbatim every time a deploy fails. **That token should be rotated**, and
`deploy_from_git.sh` should print the URL without its userinfo. Every log in this directory is
passed through a redactor (`https://…@` → `<REDACTED-TOKEN>`, `x-access-token:…`, `gh[psuor]_…`)
before it leaves the pod, and the committed set was scanned again before the commit; nothing
is known to have leaked.

## 7. What the next session should do, in order

1. **Put the 17 KB file back** — `docs/nova-ditto/live/torchfix/README.md`. Then
   `import torch` and `:8765` should come up, and the live game works again.
2. **Take the HTTP proof** the moment it does: `curl /beta/freeze?intro=freeze` must be
   non-empty and contain `JUDGE-TRUTH`. That closes §2.
3. Optionally remove the 22.5 MB of 2.10.0 headers (the `find` is in the README).
4. **Then the recording is a short job on one pod**, and `novafix_job4.sh` is that pod:
   serial apt → Chromium (verified), repair, Ditto on `nova_fb_bank.json` (~150 s),
   `--revert → --probe → --apply`, `boot.sh` with `NOVA_FACE=ditto`, then
   `live_intro_harness.py`. Budget ~20 min of 4090. **Add money to the account first** — it
   is currently at −$0.04, and nothing can be created until it is positive.
5. Play the kid live off the brain websocket, as the mission asks. Do not send a canned
   script: read her line, then answer it.
