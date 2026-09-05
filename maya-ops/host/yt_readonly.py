#!/usr/bin/env python3
"""
yt_readonly.py — YouTube live chat READ-ONLY, no Google permission needed (innertube via pytchat).
Feeds every viewer message into maya_host's /inject → she answers BY VOICE on stream.
(No text reply on YouTube until Google enables the channel's live API — that's the deal.)

  pip install pytchat requests
  python yt_readonly.py <VIDEO_ID>            # id from the live watch URL
  env: MAYA_INJECT_URL=http://127.0.0.1:8787/inject
"""
import os, sys, time, logging
import requests

try:
    import pytchat
except ImportError:
    sys.exit("pip install pytchat")

logging.basicConfig(level=logging.INFO, format="%(asctime)s yt-ro: %(message)s")
log = logging.getLogger()
INJECT = os.environ.get("MAYA_INJECT_URL", "http://127.0.0.1:8787/inject")


def main(video_id: str):
    seen = set()
    while True:
        try:
            chat = pytchat.create(video_id=video_id, interruptable=False)
            log.info("connected to %s", video_id)
            while chat.is_alive():
                for c in chat.get().sync_items():
                    if c.id in seen:
                        continue
                    seen.add(c.id)
                    if len(seen) > 5000:
                        seen.clear()
                    payload = {"name": c.author.name, "user_id": c.author.channelId or c.author.name,
                               "text": c.message, "platform": "youtube-ro"}
                    try:
                        requests.post(INJECT, json=payload, timeout=5)
                        log.info("%s: %s", c.author.name, c.message[:80])
                    except Exception as e:
                        log.warning("inject failed: %s", e)
                time.sleep(1)
            log.warning("chat ended/closed — reconnecting in 10s")
        except Exception as e:
            log.error("reader error: %s — retry in 15s", e)
            time.sleep(15)
            continue
        time.sleep(10)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: yt_readonly.py <VIDEO_ID>")
    main(sys.argv[1])
