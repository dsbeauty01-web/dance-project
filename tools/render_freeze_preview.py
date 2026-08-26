#!/usr/bin/env python3
"""FREEZE-STRUCTURAL-FIX Mission A: deterministic offline render of the game audio.

Freeze = the melody strips to a naked, grid-locked percussion pulse (NO silence),
the dancer freezes on the strip, then the melody slams back. Her "FREEZE!" sting
fires only AT the cut. Instant edges (3ms anti-click fade only), sample-accurate —
this file IS the strip-feel the page's WebAudio engine (Mission B) must reproduce.

Any array change re-renders in seconds:
    python tools/render_freeze_preview.py <song.mp3> <sting.mp3> <out.mp3> [win_start win_end]
Default window = the FULL track. Also writes tools/qa/bare_beat_129.wav (the game loop).
"""
import sys, os, subprocess
import numpy as np
import soundfile as sf

SR = 44100
BPM = 129.2
BEAT = 60.0 / BPM

# FREEZE-PRECISE-FIX approved array: 10-14s gaps, one 3.5s fake-out stab (#6),
# 3.5s holds (founder ear-check 2026-08-26: +1s each), 6s final star.
# Every `at` is beat-snapped to the track grid at render.
FREEZES = [
    {"at": 11.6,  "hold": 3.5, "clip": "statue"},
    {"at": 24.0,  "hold": 3.5, "clip": "bear"},
    {"at": 35.5,  "hold": 3.5, "clip": "flamingo"},
    {"at": 48.5,  "hold": 3.5, "clip": "frog"},
    {"at": 61.0,  "hold": 3.5, "clip": "statue"},
    {"at": 65.5,  "hold": 3.5, "clip": "bear"},     # THE STAB (fake-out, 1s of melody after #5 then BAM)
    {"at": 77.5,  "hold": 3.5, "clip": "flamingo"},
    {"at": 90.0,  "hold": 3.5, "clip": "frog"},
    {"at": 102.0, "hold": 3.5, "clip": "statue"},
    {"at": 113.5, "hold": 3.5, "clip": "bear"},
    {"at": 125.0, "hold": 6.0, "clip": "star"},
]

MUSIC_GAIN = 0.6
BEAT_GAIN  = 0.85
STING_GAIN = 0.95

def load(path, sr=SR):
    tmp = path + ".tmp.wav"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",path,"-ac","1","-ar",str(sr),tmp], check=True)
    y, _ = sf.read(tmp); os.remove(tmp)
    return y.astype(np.float32)

def snap(t, offset):
    return round(offset + round((t - offset) / BEAT) * BEAT, 3)

def beat_offset(y, sr=SR):
    """First strong onset in the opening (pure numpy) -> phase for the 129-BPM grid."""
    hop = 512
    n = len(y)//hop
    e = np.array([np.sqrt(np.mean(y[i*hop:(i+1)*hop]**2)) for i in range(n)])
    d = np.diff(e); d[d < 0] = 0
    look = int(2.0*sr/hop)
    if len(d) < 4: return 0.0
    thr = d[:look].max()*0.5
    idx = np.argmax(d[:look] > thr)
    return (idx*hop/sr) % BEAT

def kick(sr=SR):
    d=0.16; t=np.arange(0,d,1.0/sr); f=110*np.exp(-18*t)+45
    ph=2*np.pi*np.cumsum(f)/sr
    return (0.9*np.sin(ph)*np.exp(-18*t)).astype(np.float32)

def woodblock(sr=SR):
    d=0.05; t=np.arange(0,d,1.0/sr)
    return (0.5*np.sin(2*np.pi*1500*t)*np.exp(-90*t)).astype(np.float32)

def build_beat(nsamp, offset, sr=SR):
    out=np.zeros(nsamp+sr, dtype=np.float32); k=kick(); w=woodblock()
    t=offset
    while t*sr < nsamp:
        s=int(t*sr); out[s:s+len(k)]+=k
        m=int((t+BEAT/2)*sr); out[m:m+len(w)]+=w
        t+=BEAT
    return out[:nsamp]

def edgefade(seg, ms=3):
    n=int(SR*ms/1000)
    if len(seg)>2*n: seg[:n]*=np.linspace(0,1,n); seg[-n:]*=np.linspace(1,0,n)
    return seg

def main():
    song, stingf, out = sys.argv[1], sys.argv[2], sys.argv[3]
    y = load(song); sting = load(stingf)
    wa = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    wb = float(sys.argv[5]) if len(sys.argv) > 5 else len(y)/SR
    off = beat_offset(y)
    beat_full = build_beat(len(y), off)
    qa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa")
    os.makedirs(qa, exist_ok=True)
    sf.write(os.path.join(qa, "bare_beat_129.wav"), beat_full, SR)

    frs = [dict(f, at=snap(f["at"], off)) for f in FREEZES]
    a,b=int(wa*SR),min(int(wb*SR),len(y))
    mel=y[a:b].copy()*MUSIC_GAIN; bea=beat_full[a:b].copy()*BEAT_GAIN; n=len(mel)
    mask=np.zeros(n,dtype=bool); cuts=[]
    for f in frs:
        if wa<=f["at"]<wb:
            hs=int((f["at"]-wa)*SR); he=int((f["at"]+f["hold"]-wa)*SR)
            mask[hs:min(he,n)]=True; cuts.append(hs)
    mix=np.where(mask,bea,mel).astype(np.float32)
    for e in np.where(np.diff(mask.astype(int))!=0)[0]:
        lo=max(0,e-int(SR*0.003)); hi=min(n,e+int(SR*0.003)); mix[lo:hi]=edgefade(mix[lo:hi].copy())
    for c in cuts:
        end=min(n,c+len(sting)); mix[c:end]+=sting[:end-c]*STING_GAIN
    mix=np.clip(mix,-1,1)
    if out.lower().endswith(".mp3"):
        tmp=out+".tmp.wav"; sf.write(tmp, mix, SR)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",tmp,"-b:a","192k",out], check=True)
        os.remove(tmp)
    else:
        sf.write(out, mix, SR)
    print(f"wrote {out} ({n/SR:.1f}s) freezes: "+", ".join(f'{f["at"]}({f["clip"]})' for f in frs if wa<=f["at"]<wb))
    print("ARRAY(snapped): "+", ".join(f'{f["at"]}/{f["hold"]}s' for f in frs))
    print(f"beat-1 offset {off:.3f}s @ {BPM} BPM")

if __name__ == "__main__":
    main()
