#!/usr/bin/env python3
"""ditto_pack_get.py <release tag> <scratch dir> [<unpack root, default /workspace>] -- fetch AND unpack the prebuilt
Ditto folder (BOOT-FIX 2026-11-05). Built by .github/workflows/build-ditto-pack.yml (ditto_up.sh DITTO_SETUP_ONLY=1,
same pins) and stored as release assets of dsbeauty01-web/maya-lt, plus ditto-pack.sha256.

Two layouts:
  shards (ditto-pack-v2+): ditto-pack-0.tgz ... -7.tgz, each an independent tar.gz. Every shard is streamed
         curl -> sha256 -> tar at the same time, so unpacking overlaps the download and uses one core per shard.
         Run #15 (v1 layout) spent 81 s downloading and 175 s gunzipping on one core; this removes the second part.
  parts  (ditto-pack-v1): ditto-pack.tgz.part-aa ... = ONE tar.gz split; downloaded in parallel, checked, then
         unpacked with a single tar.
The API answers each asset with a redirect to GitHub's file CDN; curl drops the token on that cross-host hop.
Exit 0 = every piece downloaded, sha256-verified and unpacked. Anything else = the caller installs the slow way.
Needs MAYA_ASSETS_TOKEN (read access to the repo). Never prints it.
"""
import concurrent.futures as cf, hashlib, json, os, subprocess, sys, time, urllib.request

REPO = os.environ.get("DITTO_PACK_REPO", "dsbeauty01-web/maya-lt")
TOK = os.environ.get("MAYA_ASSETS_TOKEN") or os.environ.get("GH_TOKEN") or ""
UA = "maya-launch/0.1"


def api(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                                 headers={"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
                                          "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def curl_args(asset):
    return ["curl", "-sSfL", "--connect-timeout", "20", "-m", "400", "-A", UA,
            "-H", f"Authorization: Bearer {TOK}", "-H", "Accept: application/octet-stream",
            f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}"]


def get(asset, dest):
    out = os.path.join(dest, asset["name"])
    t = time.time()
    for attempt in range(3):
        r = subprocess.run(curl_args(asset) + ["-o", out], capture_output=True, text=True)
        if r.returncode == 0 and os.path.getsize(out) == asset["size"]:
            dt = time.time() - t
            print(f"part {asset['name']} {asset['size']/1e6:.0f} MB in {dt:.0f} s ({asset['size']/1e6/max(dt,0.1):.0f} MB/s)", flush=True)
            return out
        print(f"part {asset['name']} try {attempt+1} failed: rc={r.returncode} {(r.stderr or '').strip()[:120]}", flush=True)
    raise RuntimeError(f"could not download {asset['name']}")


def stream(asset, want_sha, root):
    """curl | (sha256 + tar -xz) for one independent shard; up to 3 tries (tar overwrites what a failed try left)."""
    t = time.time()
    for attempt in range(3):
        cu = subprocess.Popen(curl_args(asset), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tar = subprocess.Popen(["tar", "-xzf", "-", "-C", root], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        h, n = hashlib.sha256(), 0
        try:
            for b in iter(lambda: cu.stdout.read(1 << 22), b""):
                h.update(b); n += len(b); tar.stdin.write(b)
        except BrokenPipeError:
            pass
        try:
            tar.stdin.close()
        except Exception:
            pass
        crc, trc = cu.wait(), tar.wait()
        if crc == 0 and trc == 0 and n == asset["size"] and h.hexdigest() == want_sha:
            dt = time.time() - t
            print(f"shard {asset['name']} {n/1e6:.0f} MB fetched+unpacked in {dt:.0f} s ({n/1e6/max(dt,0.1):.0f} MB/s)", flush=True)
            return n
        print(f"shard {asset['name']} try {attempt+1} failed: curl={crc} tar={trc} bytes={n}/{asset['size']} "
              f"sha={'ok' if h.hexdigest() == want_sha else 'MISMATCH'} {(cu.stderr.read() or b'').decode(errors='replace').strip()[:100]}"
              f"{(tar.stderr.read() or b'').decode(errors='replace').strip()[:100]}", flush=True)
    raise RuntimeError(f"could not fetch/unpack {asset['name']}")


def main():
    tag, dest = sys.argv[1], sys.argv[2]
    root = sys.argv[3] if len(sys.argv) > 3 else "/workspace"
    os.makedirs(dest, exist_ok=True)
    t0 = time.time()
    assets = {a["name"]: a for a in api(f"releases/tags/{tag}").get("assets", [])}
    if "ditto-pack.sha256" not in assets:
        raise SystemExit(f"release {tag}: no ditto-pack.sha256 ({sorted(assets)[:6]})")
    want = {}
    for line in open(get(assets["ditto-pack.sha256"], dest)):
        h, _, name = line.strip().partition("  ")
        if h and name:
            want[os.path.basename(name)] = h
    shards = sorted(n for n in assets if n.startswith("ditto-pack-") and n.endswith(".tgz"))
    parts = sorted(n for n in assets if n.startswith("ditto-pack.tgz.part-"))
    if shards:
        total = sum(assets[n]["size"] for n in shards)
        print(f"pack {tag}: {len(shards)} shards, {total/1e9:.2f} GB, streamed into {root}", flush=True)
        with cf.ThreadPoolExecutor(max_workers=len(shards)) as ex:
            list(ex.map(lambda n: stream(assets[n], want.get(n), root), shards))
        dt = time.time() - t0
        print(f"PACK_OK {total/1e9:.2f} GB fetched, verified and unpacked in {dt:.0f} s ({total/1e6/max(dt,0.1):.0f} MB/s)", flush=True)
        return
    if not parts:
        raise SystemExit(f"release {tag}: no pack shards or parts ({sorted(assets)[:6]})")
    total = sum(assets[n]["size"] for n in parts)
    print(f"pack {tag}: {len(parts)} parts, {total/1e9:.2f} GB", flush=True)
    with cf.ThreadPoolExecutor(max_workers=min(6, len(parts))) as ex:
        files = list(ex.map(lambda n: get(assets[n], dest), parts))
    dl = time.time() - t0
    for f in files:
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 22), b""):
                h.update(b)
        if want.get(os.path.basename(f)) != h.hexdigest():
            raise SystemExit(f"sha256 mismatch on {os.path.basename(f)}")
    t1 = time.time()
    r = subprocess.run(f"cat {' '.join(files)} | tar -xzf - -C {root}", shell=True, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"unpack failed: {r.stderr.strip()[:200]}")
    for f in files:
        os.remove(f)
    print(f"PACK_OK {total/1e9:.2f} GB downloaded in {dl:.0f} s ({total/1e6/max(dl,0.1):.0f} MB/s), verified in {t1-t0-dl:.0f} s, "
          f"unpacked in {time.time()-t1:.0f} s", flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"PACK_FAIL {type(e).__name__}: {str(e)[:200]}", flush=True)
        sys.exit(1)
