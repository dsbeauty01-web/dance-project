import asyncio, aiohttp, base64, json, sys, wave, subprocess, time
K=[l.split('=',1)[1].strip().strip('"\'') for l in open('/root/.maya/host.env') if l.startswith('OPENAI_API_KEY=')][0]
LINE="Hi! I'm Nova! Ooh, hold on... there's a magic light on your shoulder! Can you lift just that one, way up high? Yes! You got it!"
STYLE="You are Nova, a playful big-sister dance friend for kids. Bright, warm, quick, a little breathless with excitement. Never a calm narrator."
async def one(v, speed):
    async with aiohttp.ClientSession(trust_env=True) as s:
        async with s.ws_connect("wss://api.openai.com/v1/realtime?model=gpt-realtime-2", headers={"Authorization":"Bearer "+K}) as ws:
            await ws.send_json({"type":"session.update","session":{"type":"realtime","output_modalities":["audio"],"instructions":STYLE,"audio":{"output":{"format":{"type":"audio/pcm","rate":24000},"voice":v,"speed":speed}}}})
            await ws.send_json({"type":"response.create","response":{"conversation":"none","instructions":"Say ONLY this, word for word, in character: "+LINE,"input":[{"type":"message","role":"user","content":[{"type":"input_text","text":"Repeat after me word for word, excited and warm: "+LINE}]}]}})
            buf=bytearray(); t0=time.time()
            async for m in ws:
                e=json.loads(m.data); t=e.get("type","")
                if t in("response.output_audio.delta","response.audio.delta"): buf+=base64.b64decode(e["delta"])
                elif t=="error": print(v,"ERR",str(e.get("error"))[:160]); 
                elif t=="response.done": break
                if time.time()-t0>40: break
            if len(buf)<20000: print(v,"no audio"); return
            w=wave.open(f"{v}.wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(bytes(buf)); w.close()
            subprocess.run(["ffmpeg","-loglevel","error","-y","-i",f"{v}.wav","-b:a","128k",f"{v}.mp3"]); print(v,"ok %.1f s"%(len(buf)/48000))
async def main():
    for v in sys.argv[1:]: 
        try: await one(v, 1.05)
        except Exception as ex: print(v,"fail",repr(ex)[:120])
asyncio.run(main())
