# READ THIS FIRST — one file puts Nova's stack back

**Session `novafix-intro`, 2026-11-02. This directory exists because I broke something and
ran out of account balance before I could put it back. The fix is one file and one command.**

## What is broken

`/workspace/_sys/pylibs311_good/dist-packages/torch` is missing **one** file:

```
torch/lib/libtorch_global_deps.so
```

so `import torch` fails with

```
OSError: /workspace/_sys/pylibs311_good/dist-packages/torch/lib/libtorch_global_deps.so:
         cannot open shared object file: No such file or directory
```

`torch` and `torchvision` therefore do not import, the LiveTalking/MuseTalk app cannot start,
and `:8765` never answers — so **the live game does not boot even though its pages are now
fine.** Everything else imports: numpy 2.4.4, cv2 5.0.0, scipy 1.17.1, soundfile 0.14.0,
av 18.1.0 (`../logs/pod4_torch_integrity.txt`).

## The fix

`libtorch_global_deps.so` in this directory is the real file from the real wheel —
`torch-2.9.1+cu129-cp311-cp311-manylinux_2_28_x86_64.whl`, which is the exact version the
volume had (`torch-2.9.1+cu129.dist-info`). 17353 bytes,
sha256 `2eaab74d60647976a45caf4e0643d8b1b568f7202aa1cc861fdff70cea8dbf48`.

On a pod with the volume mounted:

```bash
cp /workspace/_repo/docs/nova-ditto/live/torchfix/libtorch_global_deps.so \
   /workspace/_sys/pylibs311_good/dist-packages/torch/lib/
PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages python3 -c "import torch;print(torch.__version__)"
```

It costs 17 KB, which the volume has (512 MB of headroom was measured after the cleanup).
If that import still fails and names a *different* missing file, fetch that one the same
cheap way — `tools/pod/zipgrab.py` pulls a single member out of the remote wheel with HTTP
range requests instead of downloading 2.5 GB:

```bash
python3 tools/pod/zipgrab.py \
  "https://download.pytorch.org/whl/cu129/torch-2.9.1%2Bcu129-cp311-cp311-manylinux_2_28_x86_64.whl" \
  'libtorch_cpu\.so$' ./libtorch_cpu.so
```

## How I broke it, in one paragraph, so nobody repeats it

Clearing the quota, I deleted `*.pyc`. That is safe for a normal install and was not safe
here: part of that tree is in the **legacy sourceless layout**, where `pkg/mod.pyc` *is* the
module and no `.py` exists. Nine packages lost their modules that way (flask, werkzeug,
click, itsdangerous, idna, certifi, edge_tts, websockets, aiortc) — all reinstalled and
importing. While resolving the same failure for torch, my repair script found
`torch.masked.maskedtensor.core` missing and answered with
`pip install --target <tree> --upgrade torch` — a ~2.8 GB unpack aimed at a volume with
1.5 GB free. `--upgrade` **removes before it writes**. I killed the run to stop it writing,
but the removal half had already happened, and that is the missing `.so`.

Both root causes are fixed in git, not just worked around:

* `tools/pod/free_quota.py` — a loose `.pyc` is never touched; a `__pycache__` entry is
  deleted only when the matching `.py` really is in the parent directory.
* `tools/pod/repair_pylibs.py` — a `NEVER_INSTALL` list (torch, torchvision, triton,
  onnxruntime, scipy, opencv, transformers, …) so no run can aim a multi-GB wheel at this
  volume again, and a `tried` list so a failed install is never retried in a loop.

One more thing I got wrong, for completeness: `tools/pod/repair_torch.py` was meant to copy
the missing files from a **version-matched** torch elsewhere on the volume. The only donor
was `opentalking/.venv` at torch **2.10.0** against our **2.9.1**, and my fallback accepted
it anyway. It copied 3707 files / 22.5 MB — almost all C++ headers under `torch/include/`,
which are compile-time only and inert at runtime, plus a few `.py`. It did **not** fix the
problem, because 2.10.0 does not ship `libtorch_global_deps.so` at all. Those copied files
all carry an mtime of **2026-11-02 04:08 UTC**, so they are easy to identify and remove:

```bash
find /workspace/_sys/pylibs311_good/dist-packages/torch -newermt "2026-11-02 04:05" \
     -not -newermt "2026-11-02 04:10" -type f    # add -delete once you have read the list
```

I would rather hand you that command than pretend the copy was harmless.
