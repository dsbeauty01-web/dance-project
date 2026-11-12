#!/usr/bin/env python3
"""free_quota.py -- survey a RunPod network volume's real usage and free space from a
strict ALLOW-LIST, never from a guess.

Why this exists: Nova's production volume 1ditrne6cb hit its quota on 2026-11-01. Every
write to /workspace failed with OSError Errno 122, and because `cp` opens its destination
before it discovers it cannot write, boot.sh's own deploy step TRUNCATED the live
commercial page and ~28 other files to 0 bytes. The live game served an empty body.

`df` is useless on these volumes: the MooseFS client reports the underlying multi-petabyte
cluster, not the 50 GB quota (tools/pod/quota_guard.sh, 2026-08-15, says the same). So
usage here is MEASURED with du, and headroom is MEASURED by actually writing a probe file.

Two modes:
  --survey   read-only. du totals, the 30 largest dirs, the 30 largest files, every
             0-byte file under pages/, and a real write probe. Writes nothing but its
             own report (to --report, which must NOT be on the volume).
  --clean    delete ONLY what matches an allow-list category, reporting bytes freed per
             category. Everything on the DENY list is refused even if a category matches
             it, and the deny check runs last so it always wins.

Categories (--cats, comma-separated, default all of the safe ones):
  caches     any path containing /.cache/, plus conda pkgs / npm _cacache
  pycache    __pycache__ directories and *.pyc
  logs       *.log, boot.console, nohup.out, core.*, *.core, crash dumps
  stale      /workspace/_repo* beyond the NEWEST one
  tmp        /workspace/tmp, a /tmp on the volume, *.tmp, *.part
  scratch    dated render-dump dirs -- NOT deleted unless named with --allow-scratch,
             only listed with sizes, because "clearly not a bake" is a judgement call

DENY (never touched, whatever else matches):
  */LiveTalking/data/avatars/**   the bakes -- treasure, repo law 8, archives may not exist
  /workspace/sources/**, /workspace/media/**  and any *.mp4 under them
  boot.sh, lk_bridge.py, rt_lk.py, and anything whose name contains "maya"
"""
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

# ---------------------------------------------------------------- deny list (wins always)
DENY_SUBSTR = (
    "/livetalking/data/avatars/",
    "/workspace/sources/",
    "/workspace/media/",
    "maya",
)
DENY_BASENAMES = {"boot.sh", "lk_bridge.py", "rt_lk.py", "deploy_from_git.sh",
                  ".deploy-token", "podsrv.py"}
# a bake can also sit directly under avatars/ with no trailing slash in the path we test
DENY_RE = re.compile(r"(^|/)(livetalking/data/avatars|sources|media)(/|$)", re.I)


def denied(path):
    """True if this path may never be deleted. Checked LAST so it always wins."""
    low = path.lower()
    if any(s in low for s in DENY_SUBSTR):
        return True
    if os.path.basename(path) in DENY_BASENAMES:
        return True
    if DENY_RE.search(low):
        return True
    # never delete a video that could be a source take
    if low.endswith(".mp4") and "/workspace/" in low and "/.cache/" not in low:
        return True
    return False


def du_bytes(path):
    """Real size on the volume, measured. -x so we never cross into the container disk.
    Used for the VOLUME TOTAL only -- it is one subprocess over millions of inodes."""
    try:
        r = subprocess.run(["du", "-sbx", path], capture_output=True, text=True, timeout=1800)
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.split()[0])
    except Exception:
        pass
    return -1


def size_of(path):
    """Size of one file or directory, in pure Python. On a MooseFS mount a `du` subprocess
    per candidate path costs ~100 ms and there can be thousands of candidates, so the
    per-path sizing is a single stat pass instead."""
    try:
        st = os.lstat(path)
    except OSError:
        return 0
    if stat.S_ISLNK(st.st_mode):
        return 0
    if stat.S_ISREG(st.st_mode):
        return st.st_size
    if not stat.S_ISDIR(st.st_mode):
        return 0
    total = 0
    for root, dnames, fnames in os.walk(path, topdown=True):
        for fn in fnames:
            try:
                s = os.lstat(os.path.join(root, fn))
                if stat.S_ISREG(s.st_mode):
                    total += s.st_size
            except OSError:
                continue
    return total


def human(n):
    if n < 0:
        return "?"
    for u in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return f"{n:.1f}{u}" if u != "B" else f"{n}B"
        n /= 1024.0
    return f"{n:.1f}P"


def write_probe(vol, mb):
    """Measure headroom by actually writing. df cannot answer this on a MooseFS quota."""
    p = os.path.join(vol, f".free_quota_probe.{os.getpid()}")
    try:
        with open(p, "wb") as f:
            f.write(b"\0" * (mb * 1024 * 1024))
            f.flush()
            os.fsync(f.fileno())
        got = os.path.getsize(p)
        return {"mb_asked": mb, "bytes_written": got, "ok": got >= mb * 1024 * 1024 - 4096}
    except OSError as e:
        return {"mb_asked": mb, "ok": False, "errno": e.errno, "err": f"{type(e).__name__}: {e}"}
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


# ---------------------------------------------------------------- survey
def survey(vol, report, topn=30):
    out = {"volume": vol, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    r = subprocess.run(["df", "-h", vol], capture_output=True, text=True)
    out["df_h"] = r.stdout.strip()
    out["df_note"] = ("df reports the underlying cluster, NOT the volume quota -- "
                      "see tools/pod/quota_guard.sh. Trust du_total and the write probe.")
    out["du_total_bytes"] = du_bytes(vol)
    out["du_total"] = human(out["du_total_bytes"])

    # 30 largest directories
    dirs = []
    try:
        r = subprocess.run(["du", "-bx", "--max-depth=4", vol],
                           capture_output=True, text=True, timeout=1800)
        for line in r.stdout.splitlines():
            try:
                n, p = line.split("\t", 1)
                dirs.append((int(n), p))
            except ValueError:
                continue
    except Exception as e:
        out["du_dirs_err"] = str(e)
    dirs.sort(reverse=True)
    out["largest_dirs"] = [{"bytes": n, "h": human(n), "path": p} for n, p in dirs[:topn]]

    # 30 largest files
    files = []
    for root, dnames, fnames in os.walk(vol, topdown=True):
        for fn in fnames:
            p = os.path.join(root, fn)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode):
                files.append((st.st_size, p))
    files.sort(reverse=True)
    out["largest_files"] = [{"bytes": n, "h": human(n), "path": p, "denied": denied(p)}
                            for n, p in files[:topn]]

    # every 0-byte file under pages/ -- the truncation damage
    zero = []
    pages = os.path.join(vol, "pages")
    for root, dnames, fnames in os.walk(pages):
        for fn in fnames:
            p = os.path.join(root, fn)
            try:
                if os.path.getsize(p) == 0:
                    zero.append({"path": p,
                                 "mtime": time.strftime("%Y-%m-%d %H:%M",
                                                        time.gmtime(os.path.getmtime(p)))})
            except OSError:
                continue
    out["zero_byte_under_pages"] = sorted(zero, key=lambda x: x["path"])
    out["zero_byte_count"] = len(zero)

    # headroom, measured in three sizes so "bytes not kilobytes" is visible
    out["write_probe"] = {f"{mb}MB": write_probe(vol, mb) for mb in (1, 64, 512)}

    # candidate categories, sized but NOT deleted
    out["candidates"] = {k: {"bytes": v["bytes"], "h": human(v["bytes"]), "n": len(v["paths"]),
                             "sample": v["paths"][:12]}
                         for k, v in collect(vol).items()}

    with open(report, "w") as f:
        json.dump(out, f, indent=1)
    return out


# ---------------------------------------------------------------- collect by category
def collect(vol):
    """Find every deletable path, by category. Nothing is deleted here."""
    cats = {k: {"paths": [], "bytes": 0} for k in
            ("caches", "pycache", "logs", "stale", "tmp", "scratch")}

    def add(cat, p):
        if denied(p):
            return
        cats[cat]["paths"].append(p)
        cats[cat]["bytes"] += size_of(p)

    # _repo clones: keep the NEWEST, the rest are stale
    repos = []
    try:
        for e in os.listdir(vol):
            p = os.path.join(vol, e)
            if e.startswith("_repo") and os.path.isdir(p):
                repos.append((os.path.getmtime(p), p))
    except OSError:
        pass
    repos.sort(reverse=True)
    for _, p in repos[1:]:
        add("stale", p)

    for name in ("tmp", "temp"):
        p = os.path.join(vol, name)
        if os.path.isdir(p):
            add("tmp", p)

    seen = set()
    for root, dnames, fnames in os.walk(vol, topdown=True):
        low = root.lower() + "/"
        # do not descend into the bakes or the sources at all
        if denied(root + "/"):
            dnames[:] = []
            continue
        # caches: a whole directory, so prune the walk under it
        is_cache = ("/.cache/" in low
                    or low.rstrip("/").endswith("/.cache")
                    or root.endswith("/_cacache")
                    or (root.endswith("/pkgs") and "conda" in low)
                    or root.endswith("/pip/cache")
                    or os.path.basename(root) in ("huggingface", "torch_extensions")
                    and "/.cache/" in low)
        if is_cache:
            if root not in seen:
                add("caches", root)
                seen.add(root)
            dnames[:] = []
            continue
        # ---- .pyc: a CACHE only when its source sits next to it ------------------------
        # 2026-11-02, the hard way: this tree is MIXED. Some modules are normal (mod.py +
        # __pycache__/mod.cpython-311.pyc, where the .pyc is pure cache) and some are in the
        # LEGACY SOURCELESS layout, where the module IS pkg/mod.pyc and no .py exists
        # anywhere. Deleting the second kind deletes the module. It broke idna.core, flask
        # and the volume's own pip, and took Nova's whole stack down with it.
        # So: a loose .pyc is a MODULE and is never touched, and a __pycache__ entry is only
        # a cache if the matching source really is in the parent directory.
        if os.path.basename(root) == "__pycache__":
            parent = os.path.dirname(root)
            evictable, keep = [], 0
            for fn in fnames:
                if not fn.endswith(".pyc"):
                    keep += 1
                    continue
                stem = fn.split(".")[0]            # mod.cpython-311.pyc -> mod
                if os.path.exists(os.path.join(parent, stem + ".py")):
                    evictable.append(os.path.join(root, fn))
                else:
                    keep += 1                      # sourceless: this .pyc IS the module
            if keep == 0 and evictable:
                add("pycache", root)               # every entry is a real cache: drop the dir
            else:
                for p in evictable:
                    add("pycache", p)
            dnames[:] = []
            continue
        for fn in fnames:
            p = os.path.join(root, fn)
            fl = fn.lower()
            if fl.endswith(".pyc"):
                continue                           # loose .pyc = sourceless module. NEVER.
            elif (fl.endswith(".log") or fl in ("boot.console", "nohup.out")
                  or fl.startswith("core.") or fl.endswith(".core")
                  or fl.endswith(".crash") or fl.endswith(".dmp")):
                add("logs", p)
            elif fl.endswith(".tmp") or fl.endswith(".part") or fl.endswith(".partial"):
                add("tmp", p)
        # dated scratch dumps: listed only, never auto-deleted. The signal is a directory
        # whose own name carries a YYYYMMDD stamp -- that is how previous sessions named
        # their render dumps. A bake never does (and avatars/ is denied above anyway).
        if re.search(r"[-_.]20\d{6}", os.path.basename(root)):
            add("scratch", root)
            dnames[:] = []
    return cats


# ---------------------------------------------------------------- clean
def clean(vol, cats_wanted, allow_scratch, report):
    found = collect(vol)
    res = {"volume": vol, "freed": {}, "errors": [], "skipped_scratch": []}
    before = du_bytes(vol)
    for cat, d in found.items():
        if cat == "scratch" and not allow_scratch:
            res["skipped_scratch"] = [{"path": p, "h": human(du_bytes(p))} for p in d["paths"]]
            continue
        if cat not in cats_wanted:
            continue
        freed, n_ok, errs = 0, 0, 0
        for p in d["paths"]:
            if denied(p):              # deny wins, checked again right before unlink
                continue
            try:
                sz = du_bytes(p) if os.path.isdir(p) else os.path.getsize(p)
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, ignore_errors=False)
                else:
                    os.remove(p)
                freed += max(sz, 0)
                n_ok += 1
            except Exception as e:
                errs += 1
                if len(res["errors"]) < 25:
                    res["errors"].append(f"{p}: {type(e).__name__}: {e}")
        res["freed"][cat] = {"bytes": freed, "h": human(freed), "deleted": n_ok, "failed": errs}
    after = du_bytes(vol)
    res["du_before"] = before
    res["du_after"] = after
    res["du_delta_bytes"] = before - after if before > 0 and after > 0 else -1
    res["du_delta"] = human(res["du_delta_bytes"])
    res["write_probe_after"] = {f"{mb}MB": write_probe(vol, mb) for mb in (1, 512, 2048)}
    p2 = res["write_probe_after"]["2048MB"]
    res["two_gb_free"] = bool(p2.get("ok"))
    with open(report, "w") as f:
        json.dump(res, f, indent=1)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--volume", default="/workspace")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--cats", default="caches,pycache,logs,stale,tmp")
    ap.add_argument("--allow-scratch", action="store_true",
                    help="also delete the dated render-dump dirs the survey listed")
    ap.add_argument("--report", required=True, help="MUST be off the volume")
    ap.add_argument("--topn", type=int, default=30)
    a = ap.parse_args()
    if os.path.abspath(a.report).startswith(os.path.abspath(a.volume) + os.sep):
        sys.exit("REFUSING: --report would be written to the volume we are trying to free")
    if a.survey:
        out = survey(a.volume, a.report, a.topn)
        print(f"du_total {out['du_total']}  zero-byte under pages: {out['zero_byte_count']}")
        for mb, p in out["write_probe"].items():
            print(f"  probe {mb}: ok={p.get('ok')} {p.get('err','')}")
        for c, v in out["candidates"].items():
            print(f"  cand {c:9s} {v['h']:>8s}  n={v['n']}")
        print(f"report -> {a.report}")
    if a.clean:
        res = clean(a.volume, set(x.strip() for x in a.cats.split(",") if x.strip()),
                    a.allow_scratch, a.report)
        for c, v in res["freed"].items():
            print(f"  freed {c:9s} {v['h']:>8s}  deleted={v['deleted']} failed={v['failed']}")
        print(f"  du {human(res['du_before'])} -> {human(res['du_after'])} (delta {res['du_delta']})")
        print(f"  2GB writable after: {res['two_gb_free']}")
        if res["skipped_scratch"]:
            print("  scratch NOT deleted (listed for a decision):")
            for s in res["skipped_scratch"]:
                print(f"    {s['h']:>8s}  {s['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
