#!/usr/bin/env python3
"""nfb_layers.py -- NOVA-FASTBOOT (2026-11-22): take /opt/ltenv (SoulX python env, torch 2.6) and /opt/maya-ops out of the
big private image ghcr.io/dsbeauty01-web/maya-lt:soulx-wide-v2 WITHOUT pulling that image.

Why: the 14.3 GB image pull was 9-31 min of every Nova boot (no STAGES line until it ended). Nova needs only ~6 GB of it
(the ltenv layers + the maya-ops code); the CUDA base, the MuseTalk copy /opt/mtenv (3.3 GB) and SRS are not used by the
dual face. So a pod on the common, host-cached runpod/pytorch image downloads just those layers once, applies them in
order (whiteouts honoured: the torch 2.4 -> 2.6 upgrade layer deletes files), and the result is packed onto the network
volume by nova_fastboot.sh. Later boots never run this; they unpack the pack from the volume.

  python3 nfb_layers.py <dest root, e.g. />          (token: $MAYA_ASSETS_TOKEN, read-only; never printed)
"""
import base64, json, os, shutil, subprocess, sys, tarfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = os.environ.get("NFB_IMAGE_REPO", "dsbeauty01-web/maya-lt")
TAG = os.environ.get("NFB_IMAGE_TAG", "soulx-wide-v2")
KEEP = ("opt/ltenv/", "opt/maya-ops/")
DEST = sys.argv[1] if len(sys.argv) > 1 else "/"
TMP = os.environ.get("NFB_LAYER_TMP", "/root/nfb_layers")


def bearer():
    tok = os.environ.get("MAYA_ASSETS_TOKEN") or os.environ.get("APP_GH_TOKEN")
    if not tok: raise SystemExit("NFB_LAYERS FAILED: no MAYA_ASSETS_TOKEN in env")
    b = base64.b64encode(f"x:{tok}".encode()).decode()
    r = urllib.request.Request(f"https://ghcr.io/token?scope=repository:{REPO}:pull", headers={"Authorization": "Basic " + b})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())["token"]


def get(url, bear, accept="application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json"):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + bear, "Accept": accept})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


def keep(name):
    n = name[2:] if name.startswith("./") else name
    return n if any(n.startswith(k) or n + "/" == k for k in KEEP) else None


def main():
    t0 = time.time(); bear = bearer()
    m = get(f"https://ghcr.io/v2/{REPO}/manifests/{TAG}", bear)
    cfg = get(f"https://ghcr.io/v2/{REPO}/blobs/{m['config']['digest']}", bear, "*/*")
    hist = [h.get("created_by", "") for h in cfg["history"] if not h.get("empty_layer")]
    layers = m["layers"]
    assert len(hist) == len(layers), (len(hist), len(layers))
    first = next(i for i, h in enumerate(hist) if "-m venv /opt/ltenv" in h)
    use = [(i, l) for i, l in enumerate(layers) if i >= first and "musetalk venv" not in hist[i]]
    if os.environ.get("NFB_TEST_MAX_MB"):                  # local self-test only: the small layers
        use = [(i, l) for i, l in use if l["size"] < float(os.environ["NFB_TEST_MAX_MB"]) * 1e6]
    print(f"layers {len(layers)}; using {len(use)} from #{first} ({sum(l['size'] for _, l in use) / 1e9:.2f} GB), "
          f"skipping the CUDA base and /opt/mtenv", flush=True)
    os.makedirs(TMP, exist_ok=True)

    def dl(il):
        i, l = il; f = f"{TMP}/{i:02d}.tgz"
        # curl drops the Authorization header on the cross-host redirect to the blob CDN (as it should)
        for a in range(3):
            rc = subprocess.run(["curl", "-fsSL", "--retry", "3", "-m", "1500", "-H", f"Authorization: Bearer {bear}",
                                 "-o", f, f"https://ghcr.io/v2/{REPO}/blobs/{l['digest']}"]).returncode
            if rc == 0 and os.path.getsize(f) == l["size"]: return i
            time.sleep(3)
        raise SystemExit(f"NFB_LAYERS FAILED: layer #{i} download rc={rc}")

    with ThreadPoolExecutor(8) as ex: list(ex.map(dl, use))
    gb = sum(l["size"] for _, l in use) / 1e9; dt = time.time() - t0
    print(f"downloaded {gb:.2f} GB in {dt:.0f} s ({gb * 1000 / max(dt, 1):.0f} MB/s)", flush=True)

    n_files = n_wh = 0
    for i, _ in use:
        with tarfile.open(f"{TMP}/{i:02d}.tgz", "r|gz") as tf:
            for mem in tf:
                n = keep(mem.name)
                if not n: continue
                d, b = os.path.split(n)
                if b == ".wh..wh..opq":                      # opaque dir: drop what earlier layers put there
                    p = os.path.join(DEST, d)
                    if os.path.isdir(p):
                        for x in os.listdir(p):
                            q = os.path.join(p, x); shutil.rmtree(q) if os.path.isdir(q) and not os.path.islink(q) else os.unlink(q)
                    n_wh += 1; continue
                if b.startswith(".wh."):                    # whiteout: the file/dir was deleted in this layer
                    p = os.path.join(DEST, d, b[4:])
                    if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(p)
                    elif os.path.lexists(p): os.unlink(p)
                    n_wh += 1; continue
                mem.name = n
                if mem.islnk(): mem.linkname = mem.linkname[2:] if mem.linkname.startswith("./") else mem.linkname
                p = os.path.join(DEST, n)
                if os.path.lexists(p) and not (mem.isdir() and os.path.isdir(p)):
                    if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(p)
                    else: os.unlink(p)
                tf.extract(mem, DEST, set_attrs=not mem.issym())
                n_files += 1
        os.unlink(f"{TMP}/{i:02d}.tgz")
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"NFB_LAYERS_OK {n_files} entries, {n_wh} whiteouts, {time.time() - t0:.0f} s total", flush=True)


if __name__ == "__main__":
    main()
