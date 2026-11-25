# NOVA-FASTBOOT — Nova's live build in ~4 minutes instead of 15-40 (2026-11-22)

Branch `nova-fastboot` (from `nova-play-fix` 1a0670a). Default behaviour is unchanged: the fast way is only used when
the launcher gets `NF_VOLUME=<network volume id>`.

## 1. Where the time went (measured)
| Step | Old way (image `maya-lt:soulx-wide-v2`, no volume) | Fast way, 1st cold boot | Fast way, 2nd cold boot |
|---|---|---|---|
| pod created -> first STAGES line | **9-31 min** (pull of a 14.3 GB private image from ghcr) | **4 s** | **4 s** |
| Ditto ready | +72 s (6.4 GB pack from GitHub) | +65 s after boot (11 GB unpacked copy from the volume, 38 s) | +69 s |
| SoulX weights | fetched every boot (~1 min, 7.8 GB) | already on the volume, read in place | same |
| SoulX face renderer warm-up (torch.compile) | 189 s | 342 s (compile cache empty) | **134 s** (compile cache on the volume) |
| face :8010 http=200 | 15-40 min after create | 7 min 23 s | **3 min 51 s** |
| speed line | | 8 min 9 s: p50 131 ms, late **1**/110, underruns **1** | 4 min 37 s: p50 134 ms, late **3**/92, underruns **4** |

The image pull was the whole problem; a network volume cannot cache a container image, so the image had to change.
The image is now the common `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` (the co-host's image, cached
on RunPod hosts), and everything Nova needs that it lacks comes from her volume.

Both fast cold boots landed on hosts capped at 13.6 CPU cores (the 24-core floor had no free 4090 in EU-RO-1 at
11:00-11:45 UTC). The second boot's speed line missed the target (3 late / 4 underruns); its render times are the
same as the passing boot, so this points at the weak host, not at the volume. NOT PROVEN on a 24+ core host yet.

## 2. What is stored, where
Network volume **`pqbavl4mct` nova-vol**, 60 GB, **EU-RO-1** (it was empty: only `nova-fastboot/` is on it now; the
production volume `nova-groove-vol` was not touched). Volume price (RunPod, $0.07/GB/month) ≈ **$4.20/month** for its
60 GB — the volume already existed, so this is not a new cost. Everything is under `/nfb/nova-fastboot/` (26 GB):
- `packs/ltenv.tar` 6.4 GB — `/opt/ltenv` (SoulX python env, torch 2.6.0+cu124, diffusers 0.34.0, livekit, playwright) + `/opt/maya-ops`. Taken once from the big image's own layers (`tools/pod/nfb_layers.py`: only the 6 GB of layers Nova uses, whiteouts honoured), never by pulling the image.
- `packs/ditto.tar` 11 GB — `/workspace/ditto` (the Ditto pack, unpacked).
- `soulxroot/` — SoulX-FlashHead weights + code + `ACTIVATE.sh` (`/opt/soulxroot` links here).
- `cache/inductor` 329 MB, `cache/triton` 823 MB — the SoulX warm-up compile cache (cut the warm-up from 342 s to 134 s).
- A pod mounts the volume at `/nfb`; tars are unpacked to the pod's own disk (ltenv 29-32 s, Ditto 38-42 s, in parallel).

No silent fallback: a missing part is written to STAGES as `VOLUME PART MISSING: <part> - fetching`, fetched the old
way, and saved to the volume at the end of that run. The script only ever adds files to the volume.

## 3. The command
```
cd dance-project/tools/pod
NF_VOLUME=pqbavl4mct NF_BRANCH=nova-fastboot python3 nova_play.py create <40-char commit of nova-fastboot>
# "no longer any instances available" = no 24-core 4090 free in EU-RO-1 -> add NF_MIN_VCPU=16 (weaker host, see §1)
```
`NF_BRANCH` is the branch the pod plays (page + brain). After this branch is merged, use the merged branch; the
fast-boot files are `tools/pod/nova_fastboot.sh`, `tools/pod/nfb_layers.py` and the `NFB` lines of `nova_final_pod.sh`.
`NF_NAME` (default `nova-final`) names the pod. The volume pins pods to EU-RO-1 and allows one pod at a time.

## 4. Proposed skill text (nova-live-check §2, replace the timeline bullet; do not edit the skill without Refael)
> **Fast boot (2026-11-22, branch nova-fastboot):** `NF_VOLUME=pqbavl4mct NF_BRANCH=<branch> python3 nova_play.py create <sha>`.
> Common image + Nova's parts from her volume `nova-vol` (EU-RO-1): first STAGES line 4 s after create, Ditto ready
> ~70 s, face ready ~4 min, speed line ~4.5 min (was 15-40 min, of which the 14.3 GB image pull alone was 9-31 min).
> STAGES lines `nfb ltenv: volume pack ... unpacked` and `weights baked (volume ...)` prove the fast path was used; any
> `VOLUME PART MISSING` line means that part was fetched the slow way and saved for next time. Only one pod can use the
> volume at a time. If create says no instances, retry with `NF_MIN_VCPU=16`; a 13.6-core host gave late 3 /
> underruns 4 on one of two boots — check the speed line before handing out a link.
> Traps: the common image has no `Python.h` (triton needs it at the SoulX warm-up; `python3.10-dev` is installed by
> the script) and no python3.10 (installed by apt); never `rm` anything under `/nfb`.

## 5. Pods used (all terminated by id, gone confirmed)
| pod | what | minutes | cost |
|---|---|---|---|
| eamh46fgumc9yz nova-fastboot-prep | filled the volume; face died (no Python.h, fixed in 209e282) | 31.7 | $0.47 |
| wwqxbdhpqxalnz nova-fastboot-cold1 | cold boot from the volume, PASS (late 1, underruns 1), A proof pictures OK | 12.0 | $0.18 |
| wrm6c1gljzu4bk nova-fastboot-cold2 | cold boot, warm compile cache: face in 3 min 51 s; speed late 3 / underruns 4 | 8.3 | $0.12 |
