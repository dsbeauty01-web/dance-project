#!/usr/bin/env python3
"""ditto_bridge_patch.py -- switch /workspace/lk_bridge.py to the Ditto face, BEHIND A FLAG.

Same pattern as tools/pod/downscale_lk_bridge.py (2026-10-22): back up first, write-then-mv
atomically, refuse to apply if the result does not compile, log the md5 before and after.
Idempotent: running it twice changes nothing.

  python3 ditto_bridge_patch.py --probe     read-only: md5, which anchors are present, what the
                                            publish path looks like, where the audio goes.
                                            RUN THIS FIRST and keep the log.
  python3 ditto_bridge_patch.py --apply     install nova_ditto.py + patch lk_bridge.py
  python3 ditto_bridge_patch.py --revert    restore the newest .bak-ditto-* backup

THE FLAG
  NOVA_FACE=musetalk (default, or unset)  nothing changes. The patched file takes the SAME
                                          branch it takes today -- the original line, untouched.
  NOVA_FACE=ditto                         the publish loop takes its frames from nova_ditto
                                          (the Ditto server on 127.0.0.1:8031) instead of the
                                          MuseTalk video queue.

WHAT THIS SCRIPT DOES **NOT** TOUCH, ON PURPOSE
  * The publish settings. The 720x1288 downscale and the 3 Mbit + simulcast publish that are
    already on the volume (docs/CHOPPY-FIX-2026-10-21.md) stay exactly as they are: the ditto
    branch is inserted ABOVE the downscale line, so Ditto's 1080x1920 frames go through the
    same downscale and the same publish_track call as MuseTalk's do today.
  * The audio. Nova's reply audio never enters lk_bridge.py -- it goes
    OpenAI Realtime -> rt_lk.py -> POST /humanaudio -> the LiveTalking engine, which is what
    publishes it (pod/rt_lk.py, feed_engine / engine_worker). So the PRIME x 40 ms audio delay
    is applied in pod/rt_lk.py, which IS in git, instead of being guessed at here.
    See docs/NOVA-DITTO.md, "What was assumed".

[ASSUMPTION -- not verified in this container] lk_bridge.py is volume-only; it is not in this
repo and this session could not read it. The two anchors below are quoted from work that DID
patch it: tools/pod/downscale_lk_bridge.py (both anchors, applied and measured on 2026-10-22)
and docs/GROOVE-1080-REPORT.md (the publish_track call). If --probe reports a missing anchor,
STOP and send the probe log back -- do not hand-edit the bridge.
"""
import argparse
import hashlib
import os
import py_compile
import re
import shutil
import sys
import time

TARGET_DEFAULT = "/workspace/lk_bridge.py"
SIDECAR_SRC_DEFAULT = "/workspace/_repo/tools/pod/nova_ditto.py"   # deploy_from_git.sh checkout
SIDECAR_DST = "nova_ditto.py"                                      # installed next to the bridge
WD_DEFAULT = "/workspace/gallery/wd"

# ----------------------------------------------------------------- the patch

# A1: module level, straight after the frame-to-bytes helper. Proven insertion point --
#     downscale_lk_bridge.py appends its own helper here (`src.count(a1) == 1`).
A1 = "    return rgba.tobytes()\n"

BOOT = '''
# ---- NOVA_FACE (2026-10-30, nova-ditto): musetalk (default) | ditto -------------------------
# musetalk: every branch below takes the original path, so behaviour is unchanged.
# ditto:    frames come from the Ditto server (maya-lt maya-ops/lt/ditto_server.py on :8031)
#           via /workspace/nova_ditto.py. Ditto repaints only her lips on a pre-made body video.
import os as _nf_os
_NOVA_FACE = (_nf_os.environ.get("NOVA_FACE", "musetalk") or "musetalk").strip().lower()
_NOVA_FACE_DITTO = (_NOVA_FACE == "ditto")
_nova_ditto_face = None
print("[NOVA_FACE] %s" % _NOVA_FACE, flush=True)
if _NOVA_FACE_DITTO:
    import sys as _nf_sys
    if "/workspace" not in _nf_sys.path:
        _nf_sys.path.insert(0, "/workspace")
    import nova_ditto as _nova_ditto
    _nova_ditto_face = _nova_ditto.boot(wait=True)
    if not _nova_ditto_face.ready:
        # NO SILENT FALLBACKS (Nova law 4): publishing MuseTalk frames while the pod claims to
        # be running Ditto would be a lie on screen. Die loudly instead.
        raise RuntimeError(
            "NOVA_FACE=ditto but the Ditto server on :%s never answered ready. "
            "Start it first: DITTO_SRC=<body.mp4> bash ditto_up.sh" % _nf_os.environ.get("DITTO_PORT", "8031"))
    print("[NOVA_FACE] ditto ready -- delay the audio by %.0f ms (DITTO_PRIME %d + slack %d)"
          % (_nova_ditto_face.av_delay_ms, _nova_ditto_face.prime, _nova_ditto_face.slack), flush=True)
# ---- end NOVA_FACE ---------------------------------------------------------------------------
'''

# A2: the publish loop's one source of frames. downscale_lk_bridge.py inserts its
#     `w, h, rgba = _downscale(w, h, rgba)` immediately AFTER this same line, so replacing the
#     line (and not the line after it) leaves the downscale in place, below the branch.
A2 = "            w, h, rgba = await vq.get()\n"

A2_NEW = '''            if _NOVA_FACE_DITTO:
                # 25 fps off nova_ditto's own monotonic clock; run_in_executor so the pacing
                # sleep never blocks the event loop. None = still warming up.
                _nf_g = None
                while _nf_g is None:
                    _nf_g = await asyncio.get_event_loop().run_in_executor(
                        None, _nova_ditto_face.next_frame_rgba)
                w, h, rgba = _nf_g
            else:
                w, h, rgba = await vq.get()
'''

MARK = "_NOVA_FACE_DITTO"          # idempotency marker


# ----------------------------------------------------------------- helpers

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


class Log:
    def __init__(self, wd):
        self.lines = []
        self.path = None
        try:
            os.makedirs(wd, exist_ok=True)
            self.path = os.path.join(wd, "ditto_patch.log")
        except Exception:
            pass

    def __call__(self, s=""):
        print(s, flush=True)
        self.lines.append(s)

    def close(self):
        if self.path:
            try:
                with open(self.path, "a") as f:
                    f.write("\n".join(self.lines) + "\n")
                print(f"\nlog: {self.path}", flush=True)
            except Exception:
                pass


# ----------------------------------------------------------------- probe

PROBE_PATTERNS = [
    ("publish_track", r"publish_track"),
    ("TrackPublishOptions", r"TrackPublishOptions"),
    ("VideoSource", r"rtc\.VideoSource|VideoSource\("),
    ("AudioSource", r"rtc\.AudioSource|AudioSource\("),
    ("audio frame / capture", r"AudioFrame|capture_frame"),
    ("simulcast / bitrate", r"simulcast|max_bitrate|VideoEncoding"),
    ("the video queue", r"vq\.get\(\)|vq\.put"),
    ("the downscale patch", r"_downscale\("),
    ("NOVA_FACE (this patch)", r"_NOVA_FACE_DITTO"),
]


def probe(target, log):
    log(f"== probe {target}")
    if not os.path.exists(target):
        log(f"   MISSING -- {target} does not exist. On the pod it is created by the volume, "
            f"not by git (docs/CHOPPY-FIX-2026-10-21.md).")
        return False
    src = open(target, encoding="utf-8", errors="replace").read()
    log(f"   md5 {md5(target)}   {len(src)} bytes   {src.count(chr(10))} lines")
    log("")
    log("   anchors this patch needs (both must be exactly 1):")
    ok = True
    for name, a in (("A1  return rgba.tobytes()", A1), ("A2  w, h, rgba = await vq.get()", A2)):
        n = src.count(a)
        log(f"     {'OK ' if n == 1 else 'BAD'}  {name}  count={n}")
        ok = ok and n == 1
    log("")
    log("   what is in the file (every matching line -- this is what to send back):")
    lines = src.splitlines()
    for name, pat in PROBE_PATTERNS:
        hits = [(i + 1, l.strip()) for i, l in enumerate(lines) if re.search(pat, l)]
        log(f"     {name}: {len(hits)}")
        for i, l in hits[:6]:
            log(f"        L{i}: {l[:160]}")
        if len(hits) > 6:
            log(f"        ... {len(hits) - 6} more")
    log("")
    log("   KEY QUESTION for the audio: if 'AudioSource' / 'AudioFrame' above is 0, lk_bridge")
    log("   publishes VIDEO only and the audio track comes from the LiveTalking engine, which")
    log("   is what pod/rt_lk.py's NOVA_FACE=ditto delay assumes. If it is NOT 0, the audio is")
    log("   published here and the delay belongs here instead -- say so before applying.")
    log(f"   already patched: {'yes' if MARK in src else 'no'}")
    return ok


# ----------------------------------------------------------------- apply

def install_sidecar(target, sidecar_src, log):
    dst = os.path.join(os.path.dirname(target) or ".", SIDECAR_DST)
    if not os.path.exists(sidecar_src):
        log(f"   SIDECAR MISSING: {sidecar_src}")
        log( "   (it is tools/pod/nova_ditto.py in dsbeauty01-web/dance-project; the pod gets it")
        log( "    from the checkout that tools/pod/deploy_from_git.sh keeps at /workspace/_repo)")
        return None
    same = os.path.exists(dst) and md5(dst) == md5(sidecar_src)
    shutil.copyfile(sidecar_src, dst)
    log(f"   sidecar {'unchanged' if same else 'installed'}: {dst}  md5 {md5(dst)}")
    return dst


def apply(target, sidecar_src, log):
    if not probe(target, log):
        log("")
        log("REFUSING: the anchors are not what this patch expects. Nothing was written.")
        return 2
    log("")
    log("== apply")
    src = open(target, encoding="utf-8").read()
    before = md5(target)
    if install_sidecar(target, sidecar_src, log) is None:
        log("REFUSING: no sidecar, so the patched bridge could not import nova_ditto.")
        return 2
    if MARK in src:
        log(f"   lk_bridge.py already patched -- no change (md5 {before})")
        return 0

    out = src.replace(A1, A1 + BOOT, 1)
    if out == src:
        log("   REFUSING: A1 did not apply")
        return 2
    out2 = out.replace(A2, A2_NEW, 1)
    if out2 == out:
        log("   REFUSING: A2 did not apply")
        return 2

    bak = f"{target}.bak-ditto-{int(time.time())}"
    shutil.copy2(target, bak)
    log(f"   backup {bak}")
    tmp = target + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out2)
    try:
        py_compile.compile(tmp, doraise=True)
    except Exception as e:
        os.remove(tmp)
        log(f"   REFUSING: the patched file does not compile: {e!r}")
        log(f"   {target} is untouched (md5 {md5(target)})")
        return 3
    os.replace(tmp, target)
    log(f"   APPLIED   md5 {before} -> {md5(target)}")
    log("")
    log("   behaviour now:")
    log("     NOVA_FACE unset / musetalk  -> `w, h, rgba = await vq.get()`, exactly as before")
    log("     NOVA_FACE=ditto             -> frames from nova_ditto (Ditto server :8031)")
    log("   the downscale and the publish_track call were NOT touched.")
    log("   REMEMBER: also run this on rt_lk.py's side -- NOVA_FACE=ditto there feeds Ditto the")
    log("   audio and delays /humanaudio by (DITTO_PRIME + slack) x 40 ms. Without it the lips")
    log("   are early by that much.")
    return 0


def revert(target, log):
    d = os.path.dirname(target) or "."
    base = os.path.basename(target)
    baks = sorted(f for f in os.listdir(d) if f.startswith(base + ".bak-ditto-"))
    if not baks:
        log(f"   no .bak-ditto-* backup next to {target}")
        return 1
    newest = os.path.join(d, baks[-1])
    log(f"== revert {newest} -> {target}")
    log(f"   md5 {md5(target)} -> {md5(newest)}")
    shutil.copy2(newest, target)
    log("   REVERTED")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--sidecar", default=SIDECAR_SRC_DEFAULT)
    ap.add_argument("--wd", default=WD_DEFAULT)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    a = ap.parse_args()
    log = Log(a.wd)
    log(f"ditto_bridge_patch  {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}")
    try:
        if a.probe:
            rc = 0 if probe(a.target, log) else 2
        elif a.apply:
            rc = apply(a.target, a.sidecar, log)
        else:
            rc = revert(a.target, log)
    finally:
        log.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
