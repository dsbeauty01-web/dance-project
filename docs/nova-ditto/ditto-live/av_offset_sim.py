"""Prove the A3/A4 fix: OLD stamps at dequeue (compounds), NEW stamps at arrival (one offset).
Mimics lk_bridge: 20 ms engine frames into aq, drain_audio pulls and holds. Sped up 60x."""
import asyncio, time
DELAY = 1.8 / 1.0        # 1800 ms of real delay, real time so the test is quick
STEP  = 0.020 / 1.0      # 20 ms engine frames
N     = 50                # 1.2 s of speech

async def run(mode):
    aq = asyncio.Queue(maxsize=600)
    pub, t0, done = [], time.monotonic(), asyncio.Event()
    async def producer():
        for i in range(N):
            aq.put_nowait((time.monotonic(), i)); await asyncio.sleep(STEP)
    async def drain():
        got = 0
        while True:
            arrived, i = await aq.get()
            if mode == "old":
                arrived = time.monotonic()          # the 2026-11-01 bug: stamped at DEQUEUE
            left = (arrived + DELAY) - time.monotonic()
            if left > 0: await asyncio.sleep(min(left, DELAY))
            pub.append(time.monotonic() - t0); got += 1
            if got == N: done.set(); return
    p = asyncio.create_task(producer()); d = asyncio.create_task(drain())
    try: await asyncio.wait_for(done.wait(), timeout=20.0)
    except asyncio.TimeoutError: pass
    p.cancel(); d.cancel()
    print(f"        (producer itself emitted {N} frames over {N*0.020:.2f}s of wall time)")
    span = pub[-1] - pub[0] if len(pub) > 1 else 0
    audio_s = N * 0.020
    print(f"  {mode:4s}: published {len(pub)}/{N}  first at {pub[0]*1:.2f}s  last at {pub[-1]*1:.2f}s "
          f"(real-time scale)  span {span*1:.2f}s for {audio_s:.2f}s of sound  "
          f"-> {'OK' if span*1 < audio_s*1.3 else 'TOO SLOW x%.0f' % (span*1/audio_s)}")

async def main():
    print("drain_audio A/V offset, 50 frames of 20 ms audio, 1800 ms offset:")
    await run("old"); await run("new")
asyncio.run(main())
