#!/usr/bin/env python3
"""boot_wrap.py -- build a one-run wrapper around the volume's /workspace/boot.sh.

WHY A SCRIPT AND NOT sed. /workspace/boot.sh is NOT tools/pod/boot.sh. The volume's copy
(measured 2026-11-02, session novaditto-final) is an older variant with a different shape:

  * it has TWO deploy paths, not one -- an inline `deploy_from_git()` function called by a bare
    `deploy_from_git` line, AND an if/elif that runs /workspace/_repo/tools/pod/deploy_from_git.sh
    or /workspace/_deploy_step.sh. A sed written against the repo's single-line deploy matched
    neither, which is how the first run of this session refused to boot.
  * it carries plaintext secrets in `export` lines. Nothing here prints the file, and the diff
    this writes is redacted before it is saved.

THREE REWRITES, each asserted. If any assertion fails the wrapper is NOT written and the exit
code is non-zero -- booting the volume's boot.sh unchanged is worse than not booting.

  1. PYTHONPATH   the hardcoded volume tree -> whatever actually imports torch (--pypath).
                  Optional: skipped if the line is not there.
  2. DEPLOY       every line that INVOKES a deploy becomes an echo. The deploy is what
                  truncated /workspace/pages on 2026-11-01 (quota: every cp opened its
                  destination, truncated it, then failed to write) and it prints a remote URL
                  carrying the volume's deploy token when it fails. /workspace/pages is whole
                  and this session does not risk it. The function DEFINITION is left alone;
                  only the calls are neutralised, so the file stays valid bash.
  3. NOVA_FACE    every `lk_bridge.py` launch gets `env NOVA_FACE=ditto` on its own line, and
                  rt_lk.py must NOT get it. The process that PUBLISHES has to be the one that
                  is FED (ditto_bridge_patch.py anchor A5); a second DittoFace in the brain
                  renders frames nobody publishes and fights the bridge's pump over one
                  stateful body video. Asserted both ways.

  python3 -I boot_wrap.py --src /workspace/boot.sh --out /root/boot_novaditto.sh \
                          --pypath /root/torchfix:/workspace/_sys/... --diff /root/out/bootwrap.diff
"""
import argparse
import difflib
import re
import subprocess
import sys

# anything that could carry a secret out of boot.sh and into a log or a commit
REDACT = [
    (re.compile(r'(export\s+\w*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|CONFIG_ID)\w*=)\S+', re.I), r'\1<REDACTED>'),
    (re.compile(r'(https?://)[^/@\s]+@'), r'\1<REDACTED-TOKEN>@'),
    (re.compile(r'gh[psuor]_[A-Za-z0-9]{16,}'), '<REDACTED>'),
    (re.compile(r'x-access-token:[A-Za-z0-9_-]+'), 'x-access-token:<REDACTED>'),
]

# a line INVOKES a deploy if it calls one of these. The `deploy_from_git() {` definition line
# is excluded by the `(` guard, so the function body stays intact and the file stays valid bash.
DEPLOY_CALL = re.compile(
    r'(^\s*deploy_from_git\s*$)'
    r'|(\bbash\s+\S*deploy_from_git\.sh\b)'
    r'|(\bbash\s+\S*_deploy_step\.sh\b)'
    r'|(^\s*\S*deploy_from_git\.sh\b)')
SKIP_ECHO = 'echo "[DEPLOY] SKIPPED by novaditto wrapper (page-truncation + token-print trap)"'


def redact(s):
    for pat, rep in REDACT:
        s = pat.sub(rep, s)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/workspace/boot.sh")
    ap.add_argument("--out", default="/root/boot_novaditto.sh")
    ap.add_argument("--pypath", default="")
    ap.add_argument("--diff", default="")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    n_py = n_dep = n_br = 0
    out = []
    for ln in lines:
        body, nl = ln.rstrip("\n"), ("\n" if ln.endswith("\n") else "")
        if a.pypath and re.match(r'^export PYTHONPATH=\S+\s*$', body):
            out.append(f"export PYTHONPATH={a.pypath}{nl}")
            n_py += 1
            continue
        if DEPLOY_CALL.search(body) and body.strip() and "{" not in body:
            indent = body[:len(body) - len(body.lstrip())]
            out.append(f"{indent}{SKIP_ECHO}{nl}")
            n_dep += 1
            continue
        if "lk_bridge.py" in body and re.search(r'\bpython\d?\s+(-u\s+)?lk_bridge\.py', body):
            if "NOVA_FACE=ditto" not in body:
                body = re.sub(r'\b(python\d?\s+(?:-u\s+)?lk_bridge\.py)',
                              r'env NOVA_FACE=ditto \1', body, count=1)
                n_br += 1
            out.append(body + nl)
            continue
        out.append(ln)
    new = "".join(out)

    # ---- assertions. Nothing is written unless every one of these holds.
    problems = []
    if n_dep == 0:
        problems.append("no deploy invocation found to neutralise -- refusing to run a boot.sh "
                        "whose deploy step I cannot see")
    for ln in new.splitlines():
        if DEPLOY_CALL.search(ln) and "{" not in ln and SKIP_ECHO not in ln:
            problems.append(f"a deploy invocation survived: {ln.strip()[:80]!r}")
    br = [l for l in new.splitlines() if re.search(r'\bpython\d?\s+(-u\s+)?lk_bridge\.py', l)]
    if not br:
        problems.append("no lk_bridge.py launch found")
    for l in br:
        if "NOVA_FACE=ditto" not in l:
            problems.append(f"a bridge launch has no NOVA_FACE: {l.strip()[:80]!r}")
    for l in new.splitlines():
        if re.search(r'\bpython\d?\s+(-u\s+)?rt_lk\.py', l) and "NOVA_FACE" in l:
            problems.append(f"the BRAIN would see NOVA_FACE: {l.strip()[:80]!r}")

    print(f"[boot_wrap] rewrites: PYTHONPATH={n_py} deploy_calls_neutralised={n_dep} "
          f"bridge_launches={len(br)} (tagged {n_br})", flush=True)
    if problems:
        for p in problems:
            print(f"[boot_wrap] REFUSING: {p}", flush=True)
        return 2

    open(a.out, "w", encoding="utf-8").write(new)
    r = subprocess.run(["bash", "-n", a.out], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[boot_wrap] REFUSING: the wrapper is not valid bash: {r.stderr.strip()[:300]}", flush=True)
        return 3
    if a.diff:
        d = "".join(difflib.unified_diff(src.splitlines(keepends=True), new.splitlines(keepends=True),
                                         "boot.sh", "boot_novaditto.sh", n=0))
        open(a.diff, "w", encoding="utf-8").write(redact(d))
        print("[boot_wrap] diff (redacted):", flush=True)
        for l in redact(d).splitlines():
            print("   " + l, flush=True)
    print(f"[boot_wrap] WROTE {a.out}, valid bash", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
