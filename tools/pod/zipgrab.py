#!/usr/bin/env python3
"""Fetch ONE member out of a remote zip (a pip wheel) with HTTP range requests, so a 11 KB
stub does not cost a 2.5 GB download. Reads the EOCD, then the central directory, then only
the bytes of the member asked for."""
import io, re, struct, sys, urllib.request, zipfile, zlib

UA = {"User-Agent": "curl/8.5.0"}

def head_len(url):
    r = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(r, timeout=120) as f:
        return int(f.headers["Content-Length"])

def rng(url, a, b):
    h = dict(UA); h["Range"] = f"bytes={a}-{b}"
    r = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(r, timeout=300) as f:
        return f.read()

def members(url):
    n = head_len(url)
    tail = rng(url, max(0, n - 100_000), n - 1)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0: raise SystemExit("no EOCD")
    cd_size, cd_off = struct.unpack("<II", tail[i+12:i+20])
    if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        j = tail.rfind(b"PK\x06\x06")
        cd_size, cd_off = struct.unpack("<QQ", tail[j+40:j+56])
    cd = rng(url, cd_off, cd_off + cd_size - 1)
    out, p = [], 0
    while p < len(cd) - 4 and cd[p:p+4] == b"PK\x01\x02":
        cm, = struct.unpack("<H", cd[p+10:p+12])
        csz, usz = struct.unpack("<II", cd[p+20:p+28])
        nl, el, cl = struct.unpack("<HHH", cd[p+28:p+34])
        lho, = struct.unpack("<I", cd[p+42:p+46])
        name = cd[p+46:p+46+nl].decode("utf-8", "replace")
        if csz == 0xFFFFFFFF or lho == 0xFFFFFFFF:
            ex = cd[p+46+nl:p+46+nl+el]; q = 0
            while q < len(ex) - 4:
                hid, hsz = struct.unpack("<HH", ex[q:q+4])
                if hid == 1:
                    vals = struct.unpack("<" + "Q"*(hsz//8), ex[q+4:q+4+(hsz//8)*8])
                    k = 0
                    if usz == 0xFFFFFFFF: usz = vals[k]; k += 1
                    if csz == 0xFFFFFFFF: csz = vals[k]; k += 1
                    if lho == 0xFFFFFFFF: lho = vals[k]
                q += 4 + hsz
        out.append({"name": name, "csz": csz, "usz": usz, "lho": lho, "cm": cm})
        p += 46 + nl + el + cl
    return out

def grab(url, m, dest):
    lh = rng(url, m["lho"], m["lho"] + 29)
    nl, el = struct.unpack("<HH", lh[26:30])
    start = m["lho"] + 30 + nl + el
    raw = rng(url, start, start + m["csz"] - 1)
    data = zlib.decompress(raw, -15) if m["cm"] == 8 else raw
    open(dest, "wb").write(data)
    return len(data)

if __name__ == "__main__":
    url, pat, dest = sys.argv[1], sys.argv[2], sys.argv[3]
    ms = members(url)
    hits = [m for m in ms if re.search(pat, m["name"])]
    print(f"{len(ms)} members, {len(hits)} match {pat!r}")
    for m in hits[:10]:
        print(f"  {m['usz']:>12d}  {m['name']}")
    if not hits: raise SystemExit(2)
    n = grab(url, hits[0], dest)
    print(f"wrote {n} bytes -> {dest}  ({hits[0]['name']})")
