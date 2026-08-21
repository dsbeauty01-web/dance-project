#!/usr/bin/env python3
"""Render a 10s preview mp4 for every baked avatar + one gallery HTML.
Run ON THE POD (volume mounted). CPU-only: ffmpeg slideshow from full_imgs.
Usage: gen_gallery.py /workspace/data/avatars /workspace/gallery"""
import os, subprocess, sys, json, html

def frames_dir(av_path):
    for cand in ("full_imgs", "full_body_img", "frames"):
        p = os.path.join(av_path, cand)
        if os.path.isdir(p): return p
    return None

def main():
    root, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cards = []
    for av in sorted(os.listdir(root)):
        ap = os.path.join(root, av)
        if not os.path.isdir(ap): continue
        fd = frames_dir(ap)
        n_frames = len(os.listdir(fd)) if fd else 0
        lat = os.path.join(ap, "latents.pt")
        lat_ok = os.path.isfile(lat) and os.path.getsize(lat) > 1_000_000
        status = "VALID" if (fd and n_frames > 60 and lat_ok) else "BROKEN"
        mp4 = os.path.join(out, f"preview_{av}.mp4")
        if fd and n_frames > 10 and not os.path.isfile(mp4):
            # find zero-padded pattern from the first file
            first = sorted(os.listdir(fd))[0]
            stem, ext = os.path.splitext(first)
            pat = os.path.join(fd, f"%0{len(stem)}d{ext}")
            subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","25","-i",pat,
                            "-frames:v","250","-vf","scale=540:-2",
                            "-c:v","libx264","-crf","28","-pix_fmt","yuv420p", mp4],
                           check=False)
        cards.append({"id": av, "frames": n_frames, "secs": round(n_frames/25,1),
                      "status": status,
                      "mp4": os.path.basename(mp4) if os.path.isfile(mp4) else None})
    rows = "\n".join(
        f"<div class='c {c['status']}'><h3>{html.escape(c['id'])} "
        f"<small>{c['frames']}f · {c['secs']}s · {c['status']}</small></h3>"
        + (f"<video src='{c['mp4']}' controls muted loop preload='none'></video>"
           if c["mp4"] else "<p>no frames</p>") + "</div>"
        for c in cards)
    open(os.path.join(out,"index.html"),"w",encoding="utf-8").write(f"""<!doctype html>
<meta charset=utf-8><title>Bake Gallery</title><style>
body{{background:#0a0824;color:#fff;font-family:sans-serif;padding:20px}}
.c{{display:inline-block;width:300px;margin:10px;vertical-align:top}}
.c video{{width:100%;border-radius:10px}} .BROKEN h3{{color:#ff6666}}
small{{color:#aaa;font-weight:400}}</style>
<h1>Bake Gallery — {len(cards)} avatars</h1>{rows}""")
    print(json.dumps(cards, indent=1))

if __name__ == "__main__":
    main()
