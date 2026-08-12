# VISEME-DEMO: capture Nova's REAL voice (marin, via an ephemeral realtime key)
# saying the 25s demo line. Output: nova-voice.wav (24kHz mono PCM16).
import asyncio
import base64
import json
import os
import wave

import aiohttp

LINE = ("Hi! I'm Nova, your magical AI dance teacher! Ooh — do you see that? "
        "There's a magic light glowing right on your shoulder! Give it a tiny "
        "little shrug... yes, just like that! That move is called an isolation, "
        "and you found it all by yourself. Ready to pick a dance game with me? "
        "We've got Freeze, Wave, and Up Groove — which one feels like YOU today?")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova-voice.wav")


async def main():
    async with aiohttp.ClientSession() as http:
        r = await http.post("https://novapython.onrender.com/v2/realtime-key",
                            json={"scene": "intro"})
        js = await r.json()
        secret, model = js["client_secret"], js["model"]
        pcm = bytearray()
        async with http.ws_connect(
                f"wss://api.openai.com/v1/realtime?model={model}",
                headers={"Authorization": f"Bearer {secret}"}, heartbeat=20) as ws:
            await ws.send_json({"type": "response.create", "response": {
                "instructions": "Say EXACTLY this, warmly and playfully, nothing else: " + LINE}})
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                e = json.loads(msg.data)
                t = e.get("type", "")
                if t in ("response.output_audio.delta", "response.audio.delta"):
                    pcm += base64.b64decode(e.get("delta", ""))
                elif t == "response.done":
                    break
                elif t == "error":
                    print("ERR", str(e)[:200])
                    break
        with wave.open(OUT, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(bytes(pcm))
        print("saved", OUT, len(pcm) // 48000, "sec")

asyncio.run(main())
