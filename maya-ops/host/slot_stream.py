#!/usr/bin/env python3
# slot_stream.py — RELIABLE render-and-insert. Static concat playlist of "slots" (proven to
# stream to FB). Idle fills slots; when an answer is ready we OVERWRITE an upcoming slot file
# with the answer clip → concat plays it when reached (~10s). No pipe/FIFO. Comment -> coral
# voice on the live.
import os, sys, time, json, threading, subprocess, requests

VD="/workspace/vd"; SEGS=f"{VD}/segs"; SLOTS=f"{VD}/slots"; LT="/workspace/LiveTalking"
OVERLAY="/workspace/overlay.png"; BAKE="maya_serum_close"; LOG=f"{VD}/slot.log"
G="https://graph.facebook.com/v21.0"; SLOT_SECS=5.0; NSLOTS=160
os.makedirs(SLOTS,exist_ok=True)
E={l.split('=',1)[0].strip():l.split('=',1)[1].strip() for l in open('/root/.maya/host.env',encoding='utf-8',errors='ignore') if l.strip() and not l.startswith('#') and '=' in l}
PTOK=E['FB_PAGE_TOKEN']; PID=E['FB_PAGE_ID']; OAI=E['OPENAI_API_KEY']
VIDEO_ID=open(f"{VD}/video_id.txt").read().strip(); RTMP=open(f"{VD}/rtmp.txt").read().strip()
CAT=json.load(open('/workspace/maya-ops/loop/scripts/serum-c.en.json',encoding='utf-8')); F=CAT['facts']; DEFL=CAT['deflections']
def log(m): s=time.strftime('%H:%M:%S ')+m; print(s,flush=True); open(LOG,'a',encoding='utf-8').write(s+'\n')

CANON=["-vf","scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0e0b08,fps=25,format=yuv420p",
 "-c:v","libx264","-preset","veryfast","-profile:v","main","-g","50","-keyint_min","50","-sc_threshold","0",
 "-c:a","aac","-b:a","160k","-ar","44100","-ac","2"]
def norm(src,dst): subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",src,*CANON,dst],check=True)

def answer_for(text,name):
    # SHORT answers = faster render (speech length ~ render time). Keep name-first.
    t=text.lower()
    if any(w in t for w in ["cure","acne","eczema","pregnant","medical","treat","heal","disease","dermat"]): return f"{name}, I can't give medical advice — but I'll tell you exactly what's in it."
    if any(w in t for w in ["price","how much","cost","shekel","nis","buy","order","ship"," me"]): return f"{name}, it's 149 shekels live, link below!"
    if any(w in t for w in ["how","use","apply","drop","morning","routine"]): return f"{name}, one drop every morning before your moisturizer."
    if any(w in t for w in ["what","ingredient","vitamin","percent"]): return f"{name}, it's 20 percent pure vitamin C, 30 milliliters."
    if any(w in t for w in ["hi","hey","hello","shalom"]): return f"Hi {name}, welcome to the live! Ask me anything about the serum."
    return f"{name}, great question! 20 percent vitamin C, 149 shekels live today."

def coral(text,wav):
    mp3=wav[:-4]+".mp3"
    r=requests.post("https://api.openai.com/v1/audio/speech",headers={"Authorization":"Bearer "+OAI},
      json={"model":"gpt-4o-mini-tts","voice":"coral","input":text,"instructions":"Warm upbeat live-show host, smiling voice.","response_format":"mp3"},timeout=60)
    r.raise_for_status(); open(mp3,'wb').write(r.content)
    subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",mp3,"-ar","16000","-ac","1",wav],check=True)

def render_answer(text,name,idx):
    # FAST: coral TTS -> warm render -> use output DIRECTLY as the slot clip (skip overlay+
    # normalize; render_server already outputs 1920x1080 h264 + aac 44100, concat re-encodes).
    wav=f"{VD}/a{idx}.wav"; raw=f"{VD}/a{idx}_raw.mp4"; mp3=wav[:-4]+".mp3"
    coral(text,wav)  # writes both mp3 (24kHz, full quality) + wav (16kHz for lip-sync)
    # pass mp3 as the OUTPUT audio so the voice is warm, not thin/robotic
    r=requests.post("http://127.0.0.1:8791/render",json={"wav":wav,"out":raw,"audio":mp3},timeout=120)
    if r.status_code!=200 or r.json().get("rc",1)!=0: raise RuntimeError("render:"+r.text[:100])
    return raw

start_time=[0.0]
def build_and_stream():
    segs=sorted(f"{SEGS}/{f}" for f in os.listdir(SEGS) if f.endswith('.mp4'))
    # fill slots round-robin with idle segments (normalized copies so concat is happy)
    for i in range(NSLOTS):
        dst=f"{SLOTS}/s{i:03d}.mp4"
        subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",segs[i%len(segs)],"-c","copy",dst],check=True)
    with open(f"{VD}/playlist.txt","w") as f:
        for i in range(NSLOTS): f.write(f"file 'slots/s{i:03d}.mp4'\n")
    log(f"{NSLOTS} slots built; starting stream")
    start_time[0]=time.time()
    ff=subprocess.Popen(["/usr/bin/ffmpeg","-nostdin","-re","-f","concat","-safe","0","-i",f"{VD}/playlist.txt",
        "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-g","50","-r","25","-b:v","4500k","-maxrate","4500k","-bufsize","9000k",
        "-c:a","aac","-b:a","160k","-ar","44100","-f","flv",RTMP],cwd=VD,stderr=open(f"{VD}/ff.log","wb"))
    log("stream ffmpeg pid "+str(ff.pid))

def current_slot(): return int((time.time()-start_time[0])/SLOT_SECS)

def poll():
    seen=set()
    r=requests.get(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK,"fields":"id","limit":50}).json()
    for c in r.get('data',[]): seen.add(c['id'])
    log(f"poller ready; ignoring {len(seen)} existing"); idx=[0]
    while True:
        try:
            r=requests.get(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK,"fields":"id,from{name,id},message","order":"chronological","limit":25}).json()
            for c in r.get('data',[]):
                if c['id'] in seen: continue
                seen.add(c['id'])
                if str(c.get('from',{}).get('id'))==str(PID): continue
                name=(c.get('from',{}).get('name','friend').split() or ['friend'])[0]; text=c.get('message','')
                t0=time.time(); log(f"COMMENT {name}: {text}")
                ans=answer_for(text,name)
                requests.post(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK},data={"message":f"@{name} — "+ans.split('— ',1)[-1]})
                idx[0]+=1
                try:
                    clip=render_answer(ans,name,idx[0])
                    slot=current_slot()+2   # ~10s ahead
                    dst=f"{SLOTS}/s{slot%NSLOTS:03d}.mp4"
                    subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",clip,"-c","copy",dst],check=True)
                    log(f"VOICE ready {time.time()-t0:.1f}s -> plays at slot {slot%NSLOTS} (~{2*SLOT_SECS:.0f}s)")
                except Exception as e: log("render FAIL:"+repr(e)[:140])
            time.sleep(2)
        except Exception as e: log("poll err:"+repr(e)[:120]); time.sleep(3)

if __name__=="__main__":
    build_and_stream(); time.sleep(4); poll()
