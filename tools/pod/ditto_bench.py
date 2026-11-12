#!/usr/bin/env python3
"""ditto_bench.py -- is the Ditto server on this pod fast enough for a LIVE 25 fps stream? (session nova-take8c, 2026-11-11)

Feeds the server exactly the way the live sidecar does: one 1 s chunk (16000 float32 @ 16 kHz) per second of wall time,
voice with gaps of silence, and times every POST /render. Then a burst (chunks back to back) for the raw capacity.
Also records the pod's CPU quota / throttling (cgroup) and GPU load, because the 2026-11-11 live measured 1.1-1.2 s per
1 s chunk with the GPU ~1 % busy -- a CPU problem, not an engine one.

  python3 ditto_bench.py VOICE16K.wav --secs 60 --out DIR [--port 8031] [--burst 15] [--mp4 frames.mp4]

Bars (the mission's): live real time needs p95 <= ~800 ms per 1 s chunk (co-host on L40S: p95 350-535 ms).
Writes DIR/bench_<tag>.json. Needs numpy (+ ffmpeg on PATH for --mp4). No GPU code here: it is a client.
"""
import argparse, json, os, subprocess, sys, time, urllib.request, wave
import numpy as np


def cg():
    out = {"nproc": os.cpu_count()}
    for f in ("/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us", "/sys/fs/cgroup/cpu/cpu.cfs_period_us"):
        try: out[os.path.basename(f)] = open(f).read().strip()
        except Exception: pass
    for f in ("/sys/fs/cgroup/cpu.stat", "/sys/fs/cgroup/cpu/cpu.stat"):
        try:
            out["cpu_stat"] = dict(l.split() for l in open(f).read().strip().splitlines()); break
        except Exception: pass
    try: out["loadavg"] = open("/proc/loadavg").read().split()[:3]
    except Exception: pass
    return out


def gpu():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e:
        return f"n/a {e}"


def post(url, a, timeout=5.0):
    rq = urllib.request.Request(url + "/render", data=a.astype(np.float32).tobytes(),
                                headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("voice"); ap.add_argument("--secs", type=int, default=60)
    ap.add_argument("--out", default="."); ap.add_argument("--port", type=int, default=8031); ap.add_argument("--burst", type=int, default=15)
    ap.add_argument("--tag", default="alone"); ap.add_argument("--mp4", default=""); ap.add_argument("--mp4-secs", type=int, default=30)
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}"
    w = wave.open(a.voice); assert w.getframerate() == 16000 and w.getnchannels() == 1, "16 kHz mono wav"
    v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    gap = np.zeros(16000 * 2, np.float32)                       # 2 s of silence between her sentences
    track = np.concatenate([v, gap])
    while len(track) < a.secs * 16000: track = np.concatenate([track, v, gap])
    track = track[:a.secs * 16000]
    h0 = json.loads(urllib.request.urlopen(url + "/health", timeout=5).read())
    cg0 = cg(); t_start = time.time()
    ms, late_wall, frames = [], 0, []
    ff = None
    if a.mp4:
        W, H = h0["info"]["out_wh"]
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "25", "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", a.mp4 + ".v.mp4"],
                              stdin=subprocess.PIPE)
    gpus = []
    for k in range(a.secs):                                      # REAL TIME: chunk k is sent at t_start + k (+ its 1 s of audio)
        due = t_start + k + 1.0
        while time.time() < due: time.sleep(0.002)
        t = time.time()
        meta = post(url, track[k * 16000:(k + 1) * 16000])
        d = (time.time() - t) * 1000; ms.append(d)
        if time.time() > due + 1.0: late_wall += 1
        if ff and k < a.mp4_secs:
            f = np.load(meta["path"]); ff.stdin.write(np.ascontiguousarray(f).tobytes())
        if k % 10 == 5: gpus.append(gpu())
    if ff:
        ff.stdin.close(); ff.wait()
        pcm = (track[: a.mp4_secs * 16000] * 32767).astype(np.int16)
        prime = int(h0.get("prime", 35))                         # frames are PRIME x 40 ms behind the audio -> delay the audio
        pcm = np.concatenate([np.zeros(prime * 640, np.int16), pcm])[: a.mp4_secs * 16000]
        open(a.mp4 + ".pcm", "wb").write(pcm.tobytes())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.mp4 + ".v.mp4", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", a.mp4 + ".pcm",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", a.mp4])
        for p in (a.mp4 + ".v.mp4", a.mp4 + ".pcm"):
            try: os.remove(p)
            except Exception: pass
    cg1 = cg()
    bt = time.time(); bms = []
    for k in range(a.burst):                                     # capacity: back to back, voice
        t = time.time(); post(url, track[(k % a.secs) * 16000:((k % a.secs) + 1) * 16000]); bms.append((time.time() - t) * 1000)
    burst_s = time.time() - bt
    h1 = json.loads(urllib.request.urlopen(url + "/health", timeout=5).read())
    s = sorted(ms)
    res = {"tag": a.tag, "secs": a.secs, "realtime_ms_p50": round(s[len(s) // 2], 1), "realtime_ms_p95": round(s[int(0.95 * (len(s) - 1))], 1),
           "realtime_ms_max": round(s[-1], 1), "chunks_over_1000ms": sum(1 for x in ms if x > 1000), "chunks_over_800ms": sum(1 for x in ms if x > 800),
           "burst_chunks": a.burst, "burst_s": round(burst_s, 2), "burst_x_realtime": round(a.burst / burst_s, 2),
           "server_health_end": {k: h1.get(k) for k in ("ms_p50", "ms_p95", "late", "debt", "putback_ms_p95", "renders", "error")},
           "server_info": h1.get("info"), "cgroup_before": cg0, "cgroup_after": cg1, "gpu_samples": gpus, "ms_all": [round(x) for x in ms]}
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, f"bench_{a.tag}.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("tag", "realtime_ms_p50", "realtime_ms_p95", "realtime_ms_max", "chunks_over_800ms", "burst_x_realtime", "server_health_end")}))


if __name__ == "__main__":
    sys.exit(main())
