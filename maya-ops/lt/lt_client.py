#!/usr/bin/env python3
"""
lt_client.py — LiveTalking (open-source) API client. Exact routes from the official docs (§5):
  POST /human            {sessionid, text, type: "echo"|"chat", interrupt: bool}
  POST /set_audiotype    {sessionid, audiotype, reinit: bool}     0 = talking take · 1 = idle (auto when silent) · ≥2 = action clip
  POST /interrupt_talk   {sessionid}
  POST /is_speaking      {sessionid} → {"data": true|false}
  POST /humanaudio       multipart file + sessionid                (external audio → lips; present on current builds)
With --transport rtcpush the push session is created at startup and is sessionid 0.

FREE-EDITION SEMANTICS (design around them, do not fight them):
  · an action clip (≥2) plays, with its own audio, only while she is NOT speaking; /human speech takes over instantly
  · after /human, the silent-state video is whatever audiotype is set → set idle (1) right after sending speech,
    or the action clip loops forever when she stops talking
  · a gesture that should "go with" an answer is fired PRE_SPEECH_SEC before /human — on camera it reads as one move
"""
from __future__ import annotations
import os, time, json
import requests

E = os.environ.get
BASE = E("LT_BASE", "http://127.0.0.1:8010").rstrip("/")
SID = int(E("LT_SESSION_ID", "0"))
PRE_SPEECH_SEC = float(E("LT_PRE_SPEECH_SEC", "0.6"))     # gesture lead time before speech starts
IDLE = int(E("LT_IDLE_AUDIOTYPE", "1"))


class LiveTalking:
    def __init__(self, base: str = BASE, sid: int = SID, dry: bool = False):
        self.base, self.sid, self.dry = base.rstrip("/"), sid, dry
        self.timeline: list = []

    # ---------- low level ----------
    def _post(self, path: str, payload: dict, timeout: float = 10) -> dict:
        self.timeline.append({"t": time.time(), "path": path, **{k: v for k, v in payload.items() if k != "sessionid"}})
        if self.dry:
            return {"code": 0, "data": "dry"}
        r = requests.post(self.base + path, json={"sessionid": self.sid, **payload}, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"code": 0, "raw": r.text[:200]}

    # ---------- speech ----------
    def speak(self, text: str, interrupt: bool = False) -> dict:
        """One call per answer: LiveTalking streams it sentence-by-sentence through its own TTS → whole-sentence audio, no packages."""
        return self._post("/human", {"text": text, "type": "echo", "interrupt": interrupt})

    def speak_audio(self, wav_path: str) -> bool:
        """External audio (e.g. ElevenLabs WAV) → lips. Uses /humanaudio; returns False if the build lacks it."""
        self.timeline.append({"t": time.time(), "path": "/humanaudio", "file": os.path.basename(wav_path)})
        if self.dry:
            return True
        with open(wav_path, "rb") as f:
            r = requests.post(self.base + "/humanaudio", files={"file": (os.path.basename(wav_path), f, "audio/wav")},
                              data={"sessionid": str(self.sid)}, timeout=30)
        return r.status_code < 300

    def interrupt(self) -> None:
        self._post("/interrupt_talk", {})

    def is_speaking(self) -> bool:
        if self.dry:
            return False
        try:
            j = self._post("/is_speaking", {}, timeout=3)
            return bool(j.get("data"))
        except Exception:
            return False

    def wait_silent(self, max_sec: float = 30.0, poll: float = 0.25) -> bool:
        t0 = time.time()
        while time.time() - t0 < max_sec:
            if not self.is_speaking():
                return True
            time.sleep(poll)
        return False

    # ---------- gestures ----------
    def audiotype(self, n: int, reinit: bool = True) -> dict:
        return self._post("/set_audiotype", {"audiotype": int(n), "reinit": reinit})

    def idle(self) -> dict:
        return self.audiotype(IDLE)

    def gesture_then_speak(self, gesture_audiotype: int | None, text: str, interrupt: bool = False) -> None:
        """The free-edition move that reads as 'gesture while talking':
           fire the clip → let it be seen for PRE_SPEECH_SEC → speak → immediately point the silent state back to idle."""
        if gesture_audiotype is not None and gesture_audiotype >= 2:
            self.audiotype(gesture_audiotype)
            time.sleep(PRE_SPEECH_SEC)
        self.speak(text, interrupt=interrupt)
        self.idle()

    def dump_timeline(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for e in self.timeline:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    lt = LiveTalking(dry=True)
    lt.gesture_then_speak(2, "Rafael — hi and welcome! Ask me anything about the serum.")
    lt.gesture_then_speak(3, "Rafael — it's one-forty-nine, 149 shekels live right now. Link below.")
    for e in lt.timeline:
        print(e["path"], {k: v for k, v in e.items() if k not in ("t", "path")})
