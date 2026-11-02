#!/usr/bin/env python3
"""repair_pylibs.py -- diagnose and repair /workspace/_sys/pylibs311_good/dist-packages.

WHY THIS EXISTS (2026-11-02, session novafix-intro -- this is damage this session caused):

To clear the volume's quota, free_quota.py deleted `__pycache__` directories and `*.pyc`
files. That is safe for a NORMAL install, where a .pyc under __pycache__ is only a cache of
a .py sitting next to it. It is NOT safe here: parts of this tree are in the LEGACY
sourceless layout, where the module IS `pkg/mod.pyc` with no `mod.py` anywhere. Deleting
those .pyc files deleted the modules. The stack then failed at import:

    bridge:  ModuleNotFoundError: No module named 'idna.core'
               (idna/__init__.py line 1 is real SOURCE -- so the tree is MIXED, which is
                why the deletion looked safe and was not)
    boot:    ModuleNotFoundError: No module named 'pip._vendor.certifi.core'
    boot:    ModuleNotFoundError: No module named 'flask'

Note the pip failure: the volume's own `pip` is one of the broken packages, so any repair
must run the CONTAINER's pip with PYTHONPATH unset, or it inherits the breakage it is
trying to fix. Every pip call here does `env -u PYTHONPATH`.

  --diagnose   count .py vs .pyc per top-level package and list the packages that now have
               NO importable .py at all. Read-only.
  --repair     resolve a target import, and for each `No module named 'X'` reinstall X into
               the SAME dist-packages directory with the container's pip, then try again.
               Converges on exactly the broken set instead of rebuilding 14 GB.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# module -> PyPI distribution, where they differ. Anything not here is tried as-is.
DIST = {
    "idna": "idna", "yarl": "yarl", "aiohttp": "aiohttp", "flask": "flask",
    "certifi": "certifi", "pip": "pip", "livekit": "livekit", "multidict": "multidict",
    "attr": "attrs", "attrs": "attrs", "yaml": "pyyaml", "pkg_resources": "setuptools",
    "setuptools": "setuptools", "jwt": "pyjwt", "dotenv": "python-dotenv",
    "google": "protobuf", "cv2": "opencv-python-headless", "PIL": "pillow",
    "sklearn": "scikit-learn", "serial": "pyserial", "dateutil": "python-dateutil",
    "werkzeug": "werkzeug", "jinja2": "jinja2", "click": "click", "itsdangerous": "itsdangerous",
    "markupsafe": "markupsafe", "charset_normalizer": "charset-normalizer",
    "aiosignal": "aiosignal", "frozenlist": "frozenlist", "async_timeout": "async-timeout",
    "propcache": "propcache", "aiohappyeyeballs": "aiohappyeyeballs",
    "requests": "requests", "urllib3": "urllib3", "six": "six",
    "protobuf": "protobuf", "websockets": "websockets", "numpy": "numpy",
}
MISSING_RE = re.compile(r"No module named '([^']+)'")

# NEVER auto-install these: each is hundreds of MB to multiple GB, and the volume this
# repairs has ~1.5 GB of headroom. 2026-11-02: `torch.masked.maskedtensor.core` was missing
# (one more sourceless .pyc casualty, in a corner of torch the live stack never imports) and
# an earlier version of this script answered by pip-installing TORCH into a volume that could
# not hold it -- minutes burnt, and a real risk of leaving a half-written torch that would
# shadow the working one. A deep submodule missing from a big package is reported, not fixed.
NEVER_INSTALL = {
    "torch", "torchvision", "torchaudio", "triton", "onnxruntime", "onnxruntime-gpu",
    "tensorflow", "scipy", "opencv-python", "opencv-python-headless", "transformers",
    "diffusers", "jaxlib", "jax", "pandas", "sympy", "mediapipe", "xformers",
}


def pip_target(dp, dist, extra=()):
    """Install ONE distribution into dp with the CONTAINER's pip.
    PYTHONPATH is unset: the volume's own pip is among the broken packages."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    cmd = [sys.executable, "-m", "pip", "install", "--no-input", "--disable-pip-version-check",
           "--target", dp, "--upgrade", "--no-deps", *extra, dist]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=env)
    return r.returncode, (r.stdout + r.stderr)[-1500:]


def try_import(dp, target):
    """Import `target` in a fresh interpreter with PYTHONPATH = the tree under repair."""
    env = dict(os.environ)
    env["PYTHONPATH"] = dp
    r = subprocess.run([sys.executable, "-c", f"import {target}; print('OK')"],
                       capture_output=True, text=True, timeout=180, env=env)
    return r.returncode == 0, (r.stdout + r.stderr)[-2500:]


def diagnose(dp):
    out = {"dist_packages": dp, "exists": os.path.isdir(dp), "packages": [],
           "no_py_at_all": [], "totals": {"py": 0, "pyc": 0, "so": 0}}
    if not out["exists"]:
        return out
    for name in sorted(os.listdir(dp)):
        p = os.path.join(dp, name)
        if not os.path.isdir(p) or name.endswith((".dist-info", ".egg-info")):
            continue
        npy = npyc = nso = 0
        for root, dn, fn in os.walk(p):
            for f in fn:
                if f.endswith(".py"):
                    npy += 1
                elif f.endswith(".pyc"):
                    npyc += 1
                elif f.endswith(".so"):
                    nso += 1
        out["totals"]["py"] += npy
        out["totals"]["pyc"] += npyc
        out["totals"]["so"] += nso
        rec = {"pkg": name, "py": npy, "pyc": npyc, "so": nso}
        out["packages"].append(rec)
        # a package directory with no .py and no .so cannot be imported at all any more
        if npy == 0 and nso == 0:
            out["no_py_at_all"].append(name)
    out["packages"].sort(key=lambda r: r["py"])
    out["n_packages"] = len(out["packages"])
    out["n_broken_dirs"] = len(out["no_py_at_all"])
    return out


def repair(dp, targets, rounds, log):
    res = {"dist_packages": dp, "installed": [], "tried": [], "failed": [], "targets": {}}
    for target in targets:
        for i in range(rounds):
            ok, err = try_import(dp, target)
            if ok:
                res["targets"][target] = {"ok": True, "rounds": i}
                log(f"  import {target}: OK after {i} install(s)")
                break
            m = MISSING_RE.search(err)
            if not m:
                res["targets"][target] = {"ok": False, "rounds": i, "err": err[-900:]}
                log(f"  import {target}: FAILED, and not a missing-module error:\n{err[-700:]}")
                break
            mod = m.group(1)
            top = mod.split(".")[0]
            dist = DIST.get(top, top)
            if dist in NEVER_INSTALL or top in NEVER_INSTALL:
                res["targets"][target] = {"ok": False, "rounds": i, "too_big": dist,
                                          "missing": mod, "err": err[-600:]}
                log(f"  import {target}: {mod} is missing from {dist}, which is on the "
                    f"NEVER_INSTALL list (too big for this volume). REPORTED, NOT INSTALLED.")
                break
            if dist in res["installed"] or dist in res["tried"]:
                # already reinstalled (or tried and failed) and the module is still missing:
                # retrying the same download is how an earlier version burnt a whole pod.
                res["targets"][target] = {"ok": False, "rounds": i,
                                          "stuck_on": mod, "err": err[-900:]}
                log(f"  import {target}: STUCK -- {mod} still missing after {dist}")
                break
            log(f"  {target}: missing {mod} -> pip install {dist} into the tree")
            res["tried"].append(dist)
            rc, outp = pip_target(dp, dist)
            if rc == 0:
                res["installed"].append(dist)
            else:
                res["failed"].append({"dist": dist, "rc": rc, "out": outp[-600:]})
                log(f"    pip {dist} rc={rc}: {outp[-300:]}")
        else:
            res["targets"][target] = {"ok": False, "rounds": rounds, "err": "round limit"}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist-packages", default="/workspace/_sys/pylibs311_good/dist-packages")
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--repair", action="store_true")
    ap.add_argument("--targets", default="flask,livekit.api,aiohttp,numpy")
    ap.add_argument("--rounds", type=int, default=14)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    dp = a.dist_packages
    blob = {}
    if a.diagnose:
        d = diagnose(dp)
        blob["diagnose"] = d
        print(f"dist-packages {dp}")
        print(f"  packages: {d.get('n_packages')}  "
              f".py files {d['totals']['py']}  .pyc {d['totals']['pyc']}  .so {d['totals']['so']}")
        print(f"  package dirs with NO .py and NO .so (unimportable): {d.get('n_broken_dirs')}")
        for n in d.get("no_py_at_all", [])[:40]:
            print("    BROKEN", n)
    if a.repair:
        lines = []

        def log(s):
            print(s, flush=True)
            lines.append(s)
        r = repair(dp, [t.strip() for t in a.targets.split(",") if t.strip()], a.rounds, log)
        r["log"] = lines
        blob["repair"] = r
        print(f"  installed: {', '.join(r['installed']) or '(none)'}")
        print("  targets: " + json.dumps({k: v.get("ok") for k, v in r["targets"].items()}))
    with open(a.report, "w") as f:
        json.dump(blob, f, indent=1)
    if a.repair:
        return 0 if all(v.get("ok") for v in blob["repair"]["targets"].values()) else 6
    return 0


if __name__ == "__main__":
    sys.exit(main())
