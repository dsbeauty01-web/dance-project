#!/usr/bin/env python3
"""deshear.py -- repair a Ditto render written at the wrong row stride.

ditto_server.py reports out_wh from cv2.VideoCapture on the SOURCE FILE, but Ditto resizes the
source to max_size=1920 on the long side before registering it. For a 1076x1924 full-body source
the real frames are 1074x1920, so drive.py told ffmpeg "-s 1076x1924" and every frame was read
2 px too wide and 4 rows too tall -- a progressive diagonal shear. The pixel data is intact; only
the row length used to lay it out was wrong.

This streams the decoded bytes back out and re-chunks them at the true size. Nothing is
interpolated or invented: byte N of the stream goes to the same pixel it always held.

  python3 -I deshear.py IN.mp4 OUT.mp4 --wrong 1076x1924 --true 1074x1920
"""
import argparse, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--wrong", required=True); ap.add_argument("--true", dest="true", required=True)
    ap.add_argument("--fps", default="25"); ap.add_argument("--crf", default="14")
    a = ap.parse_args()
    ww, wh = (int(x) for x in a.wrong.split("x"))
    tw, th = (int(x) for x in a.true.split("x"))
    tsz = tw * th * 3
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.inp, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE, bufsize=1 << 22)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{tw}x{th}", "-r", a.fps, "-i", "-", "-c:v", "libx264",
                            "-crf", a.crf, "-preset", "medium", "-pix_fmt", "yuv420p", a.out],
                           stdin=subprocess.PIPE, bufsize=1 << 22)
    buf = bytearray(); n = 0; total = 0
    while True:
        c = dec.stdout.read(1 << 22)
        if not c:
            break
        total += len(c); buf += c
        while len(buf) >= tsz:
            enc.stdin.write(bytes(buf[:tsz])); del buf[:tsz]; n += 1
            if n % 200 == 0:
                print(f"  {n} frames", flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    print(f"deshear: read {total} bytes ({total/(ww*wh*3):.2f} wrong-size frames) -> wrote {n} true "
          f"{tw}x{th} frames = {n/float(a.fps):.2f} s, {len(buf)} bytes left over", flush=True)


if __name__ == "__main__":
    main()
