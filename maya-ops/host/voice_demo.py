#!/usr/bin/env python3
"""
voice_demo.py — RENDER-AND-INSERT voice on the FB stream (Ctrip playlist-queue).
Runs ON THE POD. Deliverable: Refael HEARS Maya say her answer on the live.

Pipeline:
  persistent ffmpeg (concat demuxer reading a FIFO of `file` lines) -> FB RTMP.
  default: loop idle.mp4 (gesture flow). On each new viewer comment:
    text -> coral TTS -> render_talking(maya_serum_close) -> overlay+normalize
    -> insert clip NEXT in the playlist -> she SPEAKS it -> idle resumes.
  Also posts the text reply. Target comment->voice <=~12s.
"""
import os, sys, time, json, threading, subprocess, queue, re
import requests

VD = "/workspace/vd"; os.makedirs(VD, exist_ok=True)
FIFO = f"{VD}/pl.fifo"
IDLE = f"{VD}/idle.mp4"
LT = "/workspace/LiveTalking"
OVERLAY = "/workspace/overlay.png"
BAKE = "maya_serum_close"
LOG = f"{VD}/voice_demo.log"
G = "https://graph.facebook.com/v21.0"

def env(p):
    d={}
    for l in open(p,encoding='utf-8',errors='ignore'):
        l=l.rstrip('\n')
        if l and not l.startswith('#') and '=' in l:
            k,v=l.split('=',1); d[k.strip()]=v.strip()
    return d
E = env('/root/.maya/host.env')
PTOK=E['FB_PAGE_TOKEN']; PID=E['FB_PAGE_ID']; OAI=E['OPENAI_API_KEY']
VIDEO_ID=open(f"{VD}/video_id.txt").read().strip()
CAT=json.load(open('/workspace/maya-ops/loop/scripts/serum-c.en.json',encoding='utf-8'))
F=CAT['facts']; DEFL=CAT['deflections']

def log(m):
    s=time.strftime('%H:%M:%S ')+m; print(s,flush=True); open(LOG,'a',encoding='utf-8').write(s+'\n')

CANON=["-vf","scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0e0b08,fps=25,format=yuv420p",
       "-c:v","libx264","-preset","veryfast","-profile:v","main","-g","50","-keyint_min","50","-sc_threshold","0",
       "-c:a","aac","-b:a","160k","-ar","44100","-ac","2"]

def normalize(src,dst):
    subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",src,*CANON,dst],check=True)

# ---------- answer text (truth-gated, no LLM needed) ----------
def answer_for(text,name):
    t=text.lower()
    if any(w in t for w in ["cure","acne","eczema","rosacea","pregnant","medical","treat","heal","disease","dermat"]):
        return DEFL['medical']
    if any(w in t for w in ["price","how much","cost","shekel","₪","nis","buy","me","order","ship"]):
        return f"{name} — it's {F['price_live']} live right now, down from {F['price_regular']}, with {F['shipping']}. Tap the link below to order!"
    if any(w in t for w in ["how","use","apply","drop","morning","routine"]):
        return f"{name} — {F['usage']}. {F['active_ingredient']}, {F['volume']}."
    if any(w in t for w in ["what","ingredient","vitamin","percent"]):
        return f"{name} — it's {F['what_it_is']}, with {F['active_ingredient']}, {F['volume']}."
    return f"{name} — great question! It's {F['active_ingredient']}, one drop every morning. {F['price_live']} live today."

def coral_tts(text,wav):
    mp3=wav[:-4]+".mp3"
    r=requests.post("https://api.openai.com/v1/audio/speech",headers={"Authorization":"Bearer "+OAI},
        json={"model":"gpt-4o-mini-tts","voice":"coral","input":text,
              "instructions":"Warm, upbeat live-show host. Smiling voice, natural pace, talking to one person.",
              "response_format":"mp3"},timeout=60)
    r.raise_for_status(); open(mp3,'wb').write(r.content)
    subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",mp3,"-ar","16000","-ac","1",wav],check=True)

def render_answer(text,name,idx):
    wav=f"{VD}/ans_{idx}.wav"; raw=f"{VD}/ans_{idx}_raw.mp4"; ov=f"{VD}/ans_{idx}_ov.mp4"; final=f"{VD}/ans_{idx}.mp4"
    coral_tts(text,wav)
    # WARM render server (model preloaded) -> ~5-8s instead of 95s
    r=requests.post("http://127.0.0.1:8791/render",json={"wav":wav,"out":raw},timeout=120)
    if r.status_code!=200 or r.json().get("rc",1)!=0:
        raise RuntimeError("render server: "+r.text[:120])
    # overlay branding, then normalize to canon
    if os.path.exists(OVERLAY):
        subprocess.run(["/usr/bin/ffmpeg","-nostdin","-y","-loglevel","error","-i",raw,"-i",OVERLAY,
                        "-filter_complex","[0:v][1:v]overlay=0:0","-map","0:a?","-c:a","aac",ov],check=True)
        normalize(ov,final)
    else:
        normalize(raw,final)
    return final

# ---------- playlist pusher (gapless concat over FIFO -> RTMP) ----------
insert_q=queue.Queue()
def pusher(rtmp):
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)
    ff=subprocess.Popen(["/usr/bin/ffmpeg","-nostdin","-re","-fflags","+genpts","-f","concat","-safe","0",
        "-protocol_whitelist","file,pipe,fifo","-i",FIFO,
        "-c:v","libx264","-preset","veryfast","-tune","zerolatency","-pix_fmt","yuv420p",
        "-g","50","-keyint_min","50","-sc_threshold","0","-r","25","-b:v","4500k","-maxrate","4500k","-bufsize","9000k",
        "-c:a","aac","-b:a","160k","-ar","44100","-vsync","cfr","-f","flv",rtmp],stderr=open(f"{VD}/ff.log","wb"))
    log("pusher ffmpeg started pid "+str(ff.pid))
    w=open(FIFO,'w')
    # prime with idle a few times
    for _ in range(2): w.write(f"file '{IDLE}'\n"); w.flush()
    while True:
        try:
            clip=insert_q.get(timeout=0.5)
            w.write(f"file '{clip}'\n"); w.flush(); log("QUEUED answer clip "+clip)
        except queue.Empty:
            pass
        # keep idle flowing (top up)
        w.write(f"file '{IDLE}'\n"); w.flush()
        time.sleep(0.2)

# ---------- comment poller ----------
seen=set(); idx=[0]
def poll():
    # ignore pre-existing comments
    r=requests.get(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK,"fields":"id","limit":50}).json()
    for c in r.get('data',[]): seen.add(c['id'])
    log(f"poller start; ignoring {len(seen)} existing comments")
    while True:
        try:
            r=requests.get(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK,
                "fields":"id,from{name,id},message,created_time","order":"chronological","limit":25}).json()
            for c in r.get('data',[]):
                if c['id'] in seen: continue
                seen.add(c['id'])
                frm=c.get('from',{})
                if str(frm.get('id'))==str(PID): continue  # our own reply
                name=(frm.get('name','friend').split() or ['friend'])[0]
                text=c.get('message','')
                t0=time.time(); log(f"COMMENT {name}: {text}")
                ans=answer_for(text,name)
                # text reply (top-level)
                requests.post(f"{G}/{VIDEO_ID}/comments",params={"access_token":PTOK},data={"message":f"@{name} — {ans.split('— ',1)[-1]}"[:1000]})
                # render voice clip + insert
                idx[0]+=1
                try:
                    clip=render_answer(ans,name,idx[0])
                    insert_q.put(clip)
                    log(f"VOICE ready in {time.time()-t0:.1f}s -> {clip}")
                except Exception as e:
                    log("render FAIL: "+repr(e)[:160])
            time.sleep(3)
        except Exception as e:
            log("poll err: "+repr(e)[:120]); time.sleep(3)

def main():
    rtmp=open(f"{VD}/rtmp.txt").read().strip()
    # normalize idle once
    if not os.path.exists(IDLE):
        log("normalizing idle..."); normalize("/workspace/gesture_flow_clean.mp4",IDLE)
    threading.Thread(target=pusher,args=(rtmp,),daemon=True).start()
    time.sleep(6)
    poll()

if __name__=="__main__": main()
