#!/usr/bin/env python3
"""repair_torch.py -- repair the torch install in /workspace/_sys/pylibs311_good/dist-packages
that this session's own mistake gutted.

WHAT HAPPENED, exactly, so the next session does not repeat it:
  repair_pylibs.py resolved `import torch` on the volume tree and found
  `torch.masked.maskedtensor.core` missing -- one more legacy-sourceless .pyc casualty, in a
  corner of torch the live stack never touches. The script answered the only way it knew:
      pip install --target <tree> --upgrade --no-deps torch
  `--upgrade` makes pip REMOVE the installed distribution before it writes the new one, and
  the new one is a ~2.8 GB unpack into a volume with ~1.5 GB of headroom. The run was killed
  to stop it writing -- but pip had already done the removal half, so torch lost files:
      OSError: .../torch/lib/libtorch_global_deps.so: cannot open shared object file
  torch and torchvision both stopped importing. MuseTalk needs torch, so this is production
  damage, not a cosmetic problem. repair_pylibs.py now carries a NEVER_INSTALL list so no
  future run can aim a multi-GB wheel at this volume.

THE REPAIR, cheapest first, because the volume cannot hold a fresh torch:
  1. DONOR COPY. Other python3.11 trees on the same volume (opentalking/.venv, and any other
     site-packages) may hold the SAME torch version. Same version + same ABI means the
     missing files can simply be copied back. Costs only the bytes that are actually missing.
  2. If no donor matches, report the exact version needed and the free space, and stop.
     Guessing a different torch version into a shared tree is how you break MuseTalk subtly.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

TREE = "/workspace/_sys/pylibs311_good/dist-packages"


def ver_of(tree):
    """torch version from its dist-info, or from torch/version.py if the dist-info went."""
    try:
        for e in os.listdir(tree):
            if e.startswith("torch-") and e.endswith(".dist-info"):
                return e[len("torch-"):-len(".dist-info")].split("+")[0], e
    except OSError:
        pass
    vp = os.path.join(tree, "torch", "version.py")
    if os.path.exists(vp):
        for ln in open(vp, errors="replace"):
            if ln.strip().startswith("__version__"):
                return ln.split("=", 1)[1].strip().strip("'\"").split("+")[0], None
    return None, None


def find_donors(root, skip):
    """Every python3.11 site-packages/dist-packages on the volume that has a torch.

    The known locations are checked FIRST and the full walk is skipped if one of them has a
    torch: os.walk over a 48 GB MooseFS volume costs minutes, and this runs against a pod
    self-stop deadline."""
    out = []
    for cand in ("opentalking/.venv/lib/python3.11/site-packages",
                 "LiveTalking/.venv/lib/python3.11/site-packages",
                 "_sys/pylibs311/dist-packages",
                 "venv/lib/python3.11/site-packages",
                 ".venv/lib/python3.11/site-packages"):
        p = os.path.join(root, cand)
        if os.path.abspath(p) == os.path.abspath(skip):
            continue
        if os.path.isdir(os.path.join(p, "torch")):
            v, _ = ver_of(p)
            out.append({"tree": p, "version": v, "py311": True, "via": "known-path"})
    if out:
        return out
    for dirpath, dnames, fnames in os.walk(root):
        dnames[:] = [d for d in dnames if d not in (".git", "__pycache__")]
        base = os.path.basename(dirpath)
        if base not in ("site-packages", "dist-packages"):
            continue
        if os.path.abspath(dirpath) == os.path.abspath(skip):
            continue
        if os.path.isdir(os.path.join(dirpath, "torch")):
            v, di = ver_of(dirpath)
            out.append({"tree": dirpath, "version": v,
                        "py311": "python3.11" in dirpath or "311" in dirpath})
        dnames[:] = []
    return out


def missing_files(tree, donor):
    """Files present in the donor's torch but absent from ours."""
    miss, nbytes = [], 0
    dsrc = os.path.join(donor, "torch")
    ddst = os.path.join(tree, "torch")
    for dirpath, dn, fn in os.walk(dsrc):
        rel = os.path.relpath(dirpath, dsrc)
        for f in fn:
            s = os.path.join(dirpath, f)
            d = os.path.join(ddst, rel, f) if rel != "." else os.path.join(ddst, f)
            if not os.path.exists(d):
                try:
                    n = os.path.getsize(s)
                except OSError:
                    continue
                miss.append((s, d, n))
                nbytes += n
    return miss, nbytes


def importable(tree, mod="torch"):
    env = dict(os.environ)
    env["PYTHONPATH"] = tree
    r = subprocess.run([sys.executable, "-c",
                        f"import {mod};print({mod}.__version__)"],
                       capture_output=True, text=True, env=env, timeout=300)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=TREE)
    ap.add_argument("--volume", default="/workspace")
    ap.add_argument("--report", required=True)
    ap.add_argument("--allow-mismatch", action="store_true",
                    help="copy from a donor whose torch version differs. Dangerous; off by default.")
    ap.add_argument("--apply", action="store_true",
                    help="actually copy the missing files from a version-matched donor")
    a = ap.parse_args()
    res = {"tree": a.tree}
    ours, di = ver_of(a.tree)
    res["our_version"] = ours
    res["our_dist_info"] = di
    ok, msg = importable(a.tree)
    res["import_before"] = {"ok": ok, "msg": msg}
    print(f"our torch version: {ours}  dist-info: {di}")
    print(f"import torch before: ok={ok} {msg}")

    donors = find_donors(a.volume, a.tree)
    res["donors"] = donors
    print(f"donor trees with a torch: {len(donors)}")
    for d in donors:
        print(f"  {d['version']!s:<12} py311={d['py311']}  {d['tree']}")

    # 2026-11-02: this used to fall back to "any python3.11 donor" when no version matched.
    # That is wrong and it cost this session real damage: the only donor was torch 2.10.0
    # against our 2.9.1+cu129, and it copied 3707 files (22.5 MB of mostly C++ headers) of
    # the WRONG version into a shared production tree -- and still did not fix the fault,
    # because 2.10.0 does not ship libtorch_global_deps.so at all. A version mismatch now
    # REFUSES unless it is asked for explicitly.
    match = [d for d in donors if d["version"] and ours and d["version"] == ours]
    if not match and a.allow_mismatch:
        match = [d for d in donors if d["py311"]]
        if match:
            print(f"WARNING --allow-mismatch: copying from torch {match[0]['version']} "
                  f"into a torch {ours} tree. This can make things worse.")
    res["chosen"] = match[0] if match else None
    if not match:
        res["verdict"] = ("NO VERSION-MATCHED DONOR on the volume. Do NOT guess another "
                          f"version into a shared tree. torch {ours} needs ~2.8 GB to reinstall, "
                          "more than this volume has -- so pull the single missing file out of "
                          "the correct wheel with tools/pod/zipgrab.py instead. See "
                          "docs/nova-ditto/live/torchfix/README.md.")
        print(res["verdict"])
        json.dump(res, open(a.report, "w"), indent=1)
        return 3

    donor = match[0]["tree"]
    miss, nbytes = missing_files(a.tree, donor)
    res["missing_count"] = len(miss)
    res["missing_bytes"] = nbytes
    res["missing_sample"] = [os.path.relpath(d, a.tree) for _, d, _ in miss[:25]]
    print(f"missing from our torch vs {donor}: {len(miss)} files, {nbytes/1e6:.1f} MB")
    for _, d, n in miss[:25]:
        print(f"   {n:>12d}  {os.path.relpath(d, a.tree)}")
    if not a.apply:
        res["verdict"] = "survey only; rerun with --apply to copy"
        json.dump(res, open(a.report, "w"), indent=1)
        return 0

    copied, failed = 0, []
    for s, d, n in miss:
        try:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            tmp = d + ".repair-new"
            shutil.copyfile(s, tmp)
            shutil.copymode(s, tmp)
            os.replace(tmp, d)
            copied += 1
        except Exception as e:
            failed.append(f"{os.path.relpath(d, a.tree)}: {type(e).__name__}: {e}")
            try:
                os.remove(d + ".repair-new")
            except OSError:
                pass
            if len(failed) > 30:
                break
    res["copied"] = copied
    res["failed"] = failed[:30]
    print(f"copied {copied}/{len(miss)}; {len(failed)} failed")
    for m in ("torch", "torchvision"):
        ok, msg = importable(a.tree, m)
        res[f"import_after_{m}"] = {"ok": ok, "msg": msg}
        print(f"import {m} after: ok={ok} {msg}")
    res["verdict"] = "repaired" if res["import_after_torch"]["ok"] else "still broken"
    json.dump(res, open(a.report, "w"), indent=1)
    return 0 if res["import_after_torch"]["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
