# CORRECTION (session `novarec`, 2026-11-02): this was NEVER a one-file fix

**Do not spend a pod on the cp below. It cannot work.** The previous session's diagnosis —
"`/workspace/_sys/pylibs311_good/dist-packages/torch` is missing **one** file" — was taken
from the text of the import error and never checked against the directory. Measured on pod
`novarec` 2 at 04:35:45Z, 3 seconds of `ls`:

```
/workspace/_sys/pylibs311_good/dist-packages/torch       drwxrwxrwx 45   (exists)
/workspace/_sys/pylibs311_good/dist-packages/torch/lib   ls: No such file or directory
.so files under .../torch                                1        (only _C.cpython-311-x86_64-linux-gnu.so)
du -sh .../torch                                         878M     (a cu129 torch is ~2.9 GB)
```

**The whole `torch/lib/` directory is gone**, not one member of it. The interrupted
`pip install --target <tree> --upgrade torch` removed every shared library torch loads —
`libtorch_cpu.so`, `libtorch_cuda.so`, `libc10*.so`, the lot, roughly 2 GB. `import torch`
names `libtorch_global_deps.so` only because `_load_global_deps()` is the FIRST thing
`torch/__init__.py` does, so it is the first casualty to be reported, not the only one.

The cp fails exactly as you would expect a cp into a directory that does not exist:

```
cp: cannot create regular file '.../torch/lib/libtorch_global_deps.so': No such file or directory
```

ENOENT on create = missing parent. That cost pod 1 of this session (~$0.04 and 5 minutes).

Also worth knowing, because it rules out the obvious theory: **the volume is writable.**
A 1 MB `dd` onto `dist-packages` ran at 69 MB/s. Quota was not the problem here.

## What actually works, and what it costs

The missing ~2 GB **cannot be put back on this volume** — a 2 GB write still fails
(docs/LIVE-INTRO.md §1). So torch goes on the **container disk** instead, and the volume is
never written at all:

```bash
mkdir -p /root/torchfix
env -u PYTHONPATH python3 -m pip install --target /root/torchfix \
  --index-url https://download.pytorch.org/whl/cu129 \
  "torch==2.9.1+cu129" "torchvision==0.24.1+cu129"
PYTHONPATH=/root/torchfix:/workspace/_sys/pylibs311_good/dist-packages \
  python3 -c "import torch,torchvision;print(torch.__version__,torchvision.__version__)"
```

Measured on pod 2: **84 seconds**, 7.4 GB on an 80 GB container disk, and
`2.9.1+cu129 0.24.1+cu129` imports. The versions are pinned to what the volume's own
`torch-2.9.1+cu129.dist-info` / `torchvision-0.24.1+cu129.dist-info` say it had, so nothing
downstream sees a different torch than it was built against.

`/root/torchfix` goes **first** on `PYTHONPATH`, which shadows the broken tree without
touching it. `boot.sh` hardcodes

```
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages
```

so the run uses a copy of boot.sh with that **one line** rewritten
(`/root/boot_novarec.sh`, made by `sed` and verified by `diff` in the job log). The volume's
`boot.sh` is not edited. See `docs/nova-ditto/live/novarec_job2.sh` stage 1.

**This is a per-pod cost, not a repair.** Every new pod pays those 84 seconds again. The
volume's torch stays broken until somebody either grows the 50 GB quota or clears ~3 GB on it
and reinstalls torch there properly. Nothing in this lane needs that to record.

## The file in this directory

`libtorch_global_deps.so` is still here and is still genuinely the right file
(torch-2.9.1+cu129-cp311-cp311-manylinux_2_28_x86_64.whl, 17353 bytes, sha256
`2eaab74d60647976a45caf4e0643d8b1b568f7202aa1cc861fdff70cea8dbf48` — verified again this
session). It is just nowhere near sufficient. It is kept because if `torch/lib` is ever
restored and only this member is missing, it is the cheap fix, and because
`tools/pod/zipgrab.py` beside it is the general tool:

```bash
python3 tools/pod/zipgrab.py \
  "https://download.pytorch.org/whl/cu129/torch-2.9.1%2Bcu129-cp311-cp311-manylinux_2_28_x86_64.whl" \
  'libtorch_cpu\.so$' ./libtorch_cpu.so
```

## The original note, kept for the record

How it broke, from the session that broke it: clearing the volume quota deleted `*.pyc`,
which is safe for a normal install and not safe in the **legacy sourceless layout** where
`pkg/mod.pyc` *is* the module — that took out flask, werkzeug, click, itsdangerous, idna,
certifi, edge_tts, websockets and aiortc (all reinstalled). Resolving the same class of
failure for torch, `repair_pylibs.py` found `torch.masked.maskedtensor.core` missing and
answered with `pip install --target <tree> --upgrade torch`, a ~2.8 GB unpack aimed at
~1.5 GB of headroom. `--upgrade` removes before it writes, the run was killed to stop it
writing, and the removal half had already finished. Both root causes are fixed in git:
`tools/pod/free_quota.py` never touches a loose `.pyc`, and `tools/pod/repair_pylibs.py`
carries `NEVER_INSTALL`.

`tools/pod/repair_torch.py` then copied 3707 files / 22.5 MB from a **2.10.0** donor against
our 2.9.1 — almost all C++ headers under `torch/include/`, compile-time only and inert at
runtime. It did not help. Those files all carry mtime 2026-11-02 04:08 UTC:

```bash
find /workspace/_sys/pylibs311_good/dist-packages/torch -newermt "2026-11-02 04:05" \
     -not -newermt "2026-11-02 04:10" -type f    # add -delete once you have read the list
```

One more lesson from the donor diff, now that the directory has actually been looked at: that
diff reported only 22.5 MB missing *because it compared against a 2.10.0 tree whose own
`torch/lib` layout differs*, and nobody read the implication that a 2 GB `lib/` was absent
from both sides of the comparison. **Check the directory, not the error string.**
