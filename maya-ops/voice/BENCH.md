# Maya VOICE BENCH — pick once, LOCK forever (it's the brand)

**Rule (voice skill):** Maya gets a *designed stock voice*. **No cloning** — we have no
consented source voice. Bench candidates, founder blind-picks, then we **LOCK one voice**
and never change it (voice = brand identity).

## Candidates
- **gpt-4o-mini-tts**, re-instructed as a warm live-show host (the ladder's OpenAI rung).
- **ElevenLabs stock**, low-latency tier (`eleven_turbo_v2_5`): **Rachel · Sarah · Charlotte**
  (warm female presets). Add/swap IDs in `voice_bench.py:ELEVEN_VOICES`.

## Protocol
1. Same **30-second serum script** (below) on every candidate.
2. Streaming render; measure **TTFA** (time-to-first-audio) per render — **target <300ms**.
3. Save each wav to `renders/` → founder **blind-listens** (ignore the labels) → picks.
4. Record the pick in **LOCK** below; set it as the default voice in `tts_adapter.py`
   (`ELEVENLABS_VOICE_ID` or `OPENAI_TTS_VOICE`) and never change it.

Run (on the pod, key in env):
```
ELEVENLABS_API_KEY=... BENCH_TS=$(date -u +%FT%TZ) python maya-ops/voice/voice_bench.py
```

## The locked bench script (30s, ~75 words)
> Hey everyone, welcome in — I'm Maya. Today it's all about our concentrated vitamin C serum:
> twenty percent pure vitamin C, thirty milliliters. One drop every morning before your
> moisturizer, and over time your skin looks brighter and more even. Regular price is two
> forty-nine, but live with me right now it's just one forty-nine, with free shipping over
> two hundred. Tap the link below — I'd love for you to try it.

## Host instruction (gpt-4o-mini-tts)
> Warm, upbeat, genuine live-shopping host. Friendly and natural, like talking to a friend on
> camera. Conversational pacing, light real energy, never salesy, never robotic. Clear natural
> English, a smile in the voice.

## Status
- [x] Harness + protocol prepared (pod-free)
- [ ] ElevenLabs key provided (founder) — **blocks the run**
- [ ] Bench run on pod (fills the results table below)
- [ ] Founder blind-pick
- [ ] Voice LOCKED in `tts_adapter.py`

## LOCK (fill after the pick)
**Winner:** _pending_
**Engine / voice id:** _pending_
**TTFA:** _pending_
**Locked on:** _pending_

---
_Results tables are appended below by `voice_bench.py` on each run._
