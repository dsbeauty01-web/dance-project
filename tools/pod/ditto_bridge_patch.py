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
  * The publish_track calls, the tracks, the room, the engine socket, the queues. Untouched.

THE AUDIO -- CORRECTED 2026-11-01 (session novalive-intro). This file used to say the audio
never enters lk_bridge.py and put the A/V offset in pod/rt_lk.py instead. That was assumption
A2 of docs/NOVA-DITTO.md and the 2026-10-31 probe on the REAL /workspace/lk_bridge.py KILLED it:

    AudioSource: 1        L120: asrc = rtc.AudioSource(AUDIO_SR, 1)
    publish_track: 2      L122 (atrack, SOURCE_MICROPHONE) + L140 (vt, SOURCE_CAMERA)

lk_bridge.py publishes BOTH tracks. One engine socket carries 'V' and 'A'; the audio lands in
`aq` and `drain_audio` pushes it into the LiveKit audio track. So the offset belongs HERE, in
drain_audio (anchors A3/A4 below), and NOT in rt_lk.py: holding /humanaudio back in rt_lk.py
delays the ENGINE itself and therefore the start of her turn -- that is added latency, not a
pure picture-against-sound offset.

THE AUDIO, FIXED 2026-11-02 (session novaditto-final). The 2026-11-01 version of A3/A4 above
turned the offset into a COMPOUNDING delay and that is why both Ditto takes came back silent
(max_volume -84.3 dB). Measured, in docs/nova-ditto/live/logs/novarec_bridge.log:

    bridge: published 2300 frames
    bridge: audio published 100 frames      <-- 100 audio frames = 2.0 s of 20 ms frames
    bridge: published 3300 frames
    bridge: audio published 200 frames      <-- the next 2.0 s took 1000 video frames

100 audio frames (2 s of sound) per 1000 video frames (40 s of picture): the audio track ran
about 20x slower than real time, so a 72 s take carried ~3 s of scattered sound and measured
as silence. The cause is one line: A3 stamped `_nf_arrived` AFTER `await aq.get()` returned,
i.e. at DEQUEUE time, not at arrival. `aq.get()` returns instantly on a non-empty queue, so
every frame was dequeued, stamped NOW, and then held a FULL av_delay_ms again -- each frame
paying the whole delay instead of the stream paying it once.

The fix: stamp the arrival time where the frame actually ARRIVES (A5, in handle_conn) and
carry it with the samples. Due times are then as far apart as the arrivals were -- a constant
offset, paid once. A4 also caps its sleep at av_delay_ms so no future stamping mistake can
compound again.

A5 does one more thing, and it is the second half of why Ditto was silent. nova_ditto.boot()
used to run in BOTH processes: rt_lk.py fed one DittoFace, lk_bridge.py published frames from a
DIFFERENT one that nobody ever fed (it posted silence to the server forever, and the two pumps
fought over one stateful body video). lk_bridge already receives her voice on the 'A' channel at
exactly AUDIO_SR = 16000, which is exactly what Ditto wants, so A5 feeds the face HERE, in the
publishing process, by READING the same samples the audio track publishes. Nothing is consumed
-- that is the contract ditto_renderer.py states. Run the brain WITHOUT NOVA_FACE (so it never
boots a second face) and the bridge WITH NOVA_FACE=ditto.

The anchors were verified against the real file, byte for byte: docs/nova-ditto/fullbody/
lk_bridge.real.py, md5 1c4448b475ae0cdd719aef4edaa90337, all four anchors count=1.
If --probe reports a missing anchor, STOP and send the probe log back -- do not hand-edit it.
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
_nf_ain = [0, 0]          # [engine audio frames IN, frames dropped because aq was full]
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

# A5: the 'A' branch of the engine socket reader -- the place the audio actually ARRIVES.
#   (1) stamp the arrival time and carry it with the samples, so A4 can apply a CONSTANT offset
#       instead of re-charging the whole delay to every frame (the 2026-11-01 silence bug);
#   (2) drive Ditto's lips from the SAME pcm, in the SAME process that publishes. Reading only.
# musetalk keeps the original line, byte for byte, in the else branch.
A5 = """            elif kind == b'A':
                (ln,) = struct.unpack('>I', await reader.readexactly(4))
                data = await reader.readexactly(ln)
                if not aq.full():
                    aq.put_nowait(np.frombuffer(data, dtype=np.int16).copy())
                last_frame = time.monotonic()
"""

A5_NEW = """            elif kind == b'A':
                (ln,) = struct.unpack('>I', await reader.readexactly(4))
                data = await reader.readexactly(ln)
                if _NOVA_FACE_DITTO:
                    _nf_pcm = np.frombuffer(data, dtype=np.int16).copy()
                    # LIPS: Ditto is fed here, in the publishing process, from her voice as the
                    # engine already resampled it (pcm16 mono 16 kHz = exactly what Ditto wants).
                    # This only READS the samples; the publish path below is untouched.
                    try:
                        _nova_ditto_face.feed_pcm16_16k(_nf_pcm)
                    except Exception as _nf_e:
                        print("bridge: ditto feed failed %r" % (_nf_e,), flush=True)
                    _nf_ain[0] += 1
                    # AUDIO IN, stamped at ARRIVAL: a constant offset, applied once (A4).
                    if not aq.full():
                        aq.put_nowait((time.monotonic(), _nf_pcm))
                    else:
                        _nf_ain[1] += 1
                    if _nf_ain[0] % 50 == 0:
                        print("bridge: audio IN %d frames from the engine (%d samples), aq=%d, dropped %d"
                              % (_nf_ain[0], _nf_pcm.shape[0], aq.qsize(), _nf_ain[1]), flush=True)
                else:
                    if not aq.full():
                        aq.put_nowait(np.frombuffer(data, dtype=np.int16).copy())
                last_frame = time.monotonic()
"""

# A3 / A4: the A/V OFFSET, in drain_audio -- the place the 2026-10-31 probe proved is correct.
# A3 unpacks the (arrival, pcm) pair A5 queued; A4 holds the frame until arrival + the delay.
# Measured from ARRIVAL, so it is a constant OFFSET, not a per-frame cost: frame i+1's due time is
# never earlier than frame i's, so order and throughput are unchanged. aq (maxsize 600) absorbs the
# backlog -- 1.8 s of 20 ms engine frames is ~90 entries.
A3 = "            pcm = await aq.get()\n            n = int(pcm.shape[0])\n"

A3_NEW = '''            pcm = await aq.get()
            if _NOVA_FACE_DITTO:
                _nf_arrived, pcm = pcm          # A5 queued (arrival_monotonic, samples)
            else:
                _nf_arrived = 0.0
            n = int(pcm.shape[0])
'''

A4 = "            await asrc.capture_frame(fr)\n"

A4_NEW = '''            if _NOVA_FACE_DITTO:
                # Every Ditto frame comes back (DITTO_PRIME + slack) x 40 ms behind the audio it
                # was drawn from (nova_ditto.next_frame_bgr waits for `slack` frames before it
                # starts its publish clock). Without this hold her lips run early by exactly that
                # much. musetalk takes neither branch: _nf_arrived is 0.0 and this block is skipped.
                # The sleep is CAPPED at av_delay_ms: the whole stream pays the offset once, and
                # no stamping mistake can ever turn it back into a per-frame cost (the bug that
                # made both 2026-11-01 Ditto takes silent).
                _nf_cap = _nova_ditto_face.av_delay_ms / 1000.0
                _nf_left = (_nf_arrived + _nf_cap) - time.monotonic()
                if _nf_left > 0:
                    await asyncio.sleep(min(_nf_left, _nf_cap))
            await asrc.capture_frame(fr)
'''

# ---- 2026-11-11 (session nova-take8c): the CPU anchors. OPTIONAL -- applied when present, logged when not.
# Measured on the 2026-11-11 live (docs/nova-ditto/take8/live-2026-11-11/): Ditto needed 1.10-1.20 s per 1 s chunk
# with the GPU ~1 % busy, paste-back 72 ms/frame against the co-host's ~17 ms (room2-wt health logs, same server,
# same 1080x1920 source). The co-host does two things Nova's bridge did not:
#   A6  it has no second face engine: here MuseTalk keeps sending 1080x1920 'V' frames and the bridge turned every
#       one into RGBA (8 MB of numpy per frame, 25/s, on the ONE asyncio thread) only to drop it unread under
#       NOVA_FACE=ditto. Now those bytes are read off the socket and discarded.
#   A7  it publishes ONE encoder, simulcast off (lk_cohost/ditto_avatar.py _Runner: "the stock runner publishes
#       with the SDK defaults (3 simulcast layers), which on the first GPU pod (323qoorgbxhxbs, 1080x1920) starved
#       the Ditto renderer of CPU: its writer fell to ~7 frames/s and the room saw ~5 fps"). Nova's take 1 recorder
#       received 180x322 = the LOWEST simulcast layer of the 720x1288 publish (take1.live_intro.json recorder w/h).
#       NOVA_DITTO_SIMULCAST=1 puts simulcast back for an A/B. NOVA_FACE=musetalk: both lines run exactly as before.
A6 = """                rgba = bgr_to_rgba(w, h, data)
                if vq.full():
"""

A6_NEW = """                if _NOVA_FACE_DITTO:
                    last_frame = time.monotonic(); frames += 1
                    continue                    # A6: MuseTalk's frame is not published under Ditto -- do not convert it
                rgba = bgr_to_rgba(w, h, data)
                if vq.full():
"""

A7 = "simulcast=True, video_encoding=rtc.VideoEncoding(max_framerate=25, max_bitrate=3_000_000)"

A7_NEW = ("simulcast=(not _NOVA_FACE_DITTO or _nf_os.environ.get('NOVA_DITTO_SIMULCAST', '0') == '1'), "
          "video_encoding=rtc.VideoEncoding(max_framerate=25, max_bitrate=3_000_000)")

# A8 (2026-11-11, nova-take8c, Part 2 "full switch to Ditto"): the bridge SAYS which engine draws her lips, as its
# LiveKit participant metadata {"face": "ditto"|"musetalk", "ready", "alarm", "w", "h"}. shared/nova-face.js reads it
# on every page and raises the repo's red banner when it is not Ditto or Ditto alarms (no silent fallbacks). An
# unpatched bridge sends no metadata at all, which the page treats the same way: no Ditto -> red banner.
A8 = '                print(f"bridge: video track published {w}x{h}", flush=True)\n'

A8_NEW = '''                print(f"bridge: video track published {w}x{h}", flush=True)
                await _nf_meta(room, w, h)
'''

A8B = '''            if n % 100 == 0:
                print(f"bridge: published {n} frames", flush=True)
'''

A8B_NEW = '''            if n % 100 == 0:
                print(f"bridge: published {n} frames", flush=True)
                await _nf_meta(room, w, h)
'''

META = '''
_nf_meta_last = [None]
async def _nf_meta(room, w, h):
    """A8: tell the page which face engine is live (participant metadata). Only sent when it changes."""
    import json as _nf_json
    m = {"face": _NOVA_FACE, "w": w, "h": h}
    if _NOVA_FACE_DITTO:
        m.update(ready=bool(_nova_ditto_face.ready), alarm=_nova_ditto_face.alarm,
                 av_delay_ms=round(_nova_ditto_face.av_delay_ms))
    s = _nf_json.dumps(m, sort_keys=True)
    if s == _nf_meta_last[0]:
        return
    try:
        await room.local_participant.set_metadata(s)
        _nf_meta_last[0] = s
        print("bridge: face metadata %s" % s, flush=True)
    except Exception as _nf_e:
        print("bridge: face metadata NOT set (%r) -- the page will show its red banner" % (_nf_e,), flush=True)
'''

# A9 (2026-11-11, nova-take8c): A8's set_metadata is DROPPED by LiveKit unless the bridge's token may update its own
# metadata (measured on the pod: "bridge: face metadata {...ditto...}" in bridge.log, yet a viewer joining later read
# metadata ''). Under NOVA_FACE=ditto the bridge's grant gains can_update_own_metadata; musetalk: unchanged.
A9 = "    g = api.VideoGrants(room_join=True, room=ROOM, can_publish=True, can_subscribe=True)\n"
A9_NEW = ("    g = api.VideoGrants(room_join=True, room=ROOM, can_publish=True, can_subscribe=True,\n"
          "                        **({'can_update_own_metadata': True} if _NOVA_FACE_DITTO else {}))\n")

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
    log("   anchors this patch needs (all five must be exactly 1):")
    ok = True
    for name, a in (("A1  return rgba.tobytes()", A1),
                    ("A2  w, h, rgba = await vq.get()", A2),
                    ("A5  elif kind == b'A': ... aq.put_nowait", A5),
                    ("A3  pcm = await aq.get() + n =", A3),
                    ("A4  await asrc.capture_frame(fr)", A4)):
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
    log("   THE AUDIO, settled 2026-10-31 and corrected here: 'AudioSource' above is 1 and")
    log("   'publish_track' is 2, so lk_bridge publishes BOTH tracks and the A/V offset belongs")
    log("   in drain_audio (A3/A4) -- which is where this patch now puts it. If a future file")
    log("   ever shows AudioSource: 0, A3/A4 are wrong for it: stop and re-site the offset.")
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
    out2b = out2.replace(A5, A5_NEW, 1)
    if out2b == out2:
        log("   REFUSING: A5 did not apply (the audio would have no arrival stamp and Ditto "
            "would never be fed in the publishing process)")
        return 2
    out2 = out2b
    out3 = out2.replace(A3, A3_NEW, 1)
    if out3 == out2:
        log("   REFUSING: A3 did not apply (the A/V offset would have no arrival stamp)")
        return 2
    out4 = out3.replace(A4, A4_NEW, 1)
    if out4 == out3:
        log("   REFUSING: A4 did not apply (the A/V offset would never be held)")
        return 2
    out2 = out4
    out2 = out2.replace(A1 + BOOT, A1 + BOOT + META, 1)
    for name, a, new in (("A6 drop MuseTalk frames under ditto", A6, A6_NEW),
                         ("A7 simulcast off under ditto", A7, A7_NEW),
                         ("A8 face metadata on publish", A8, A8_NEW),
                         ("A8b face metadata refresh", A8B, A8B_NEW),
                         ("A9 metadata grant under ditto", A9, A9_NEW)):
        n = out2.count(a)
        if n == 1:
            out2 = out2.replace(a, new, 1)
            log(f"   {name}: applied")
        else:
            log(f"   {name}: NOT applied (anchor count={n}) -- the bridge keeps its old behaviour here")

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
    log("     NOVA_FACE=ditto             -> frames from nova_ditto (Ditto server :8031); the")
    log("                                    engine's 'A' pcm16@16k both FEEDS Ditto's lips and")
    log("                                    publishes as before, offset once by av_delay_ms")
    log("   the downscale and both publish_track calls were NOT touched.")
    log("   RUN THE BRAIN WITHOUT NOVA_FACE: rt_lk.py must not boot a second DittoFace -- the one")
    log("   that publishes is the one that must be fed, and A5 feeds it here.")
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
