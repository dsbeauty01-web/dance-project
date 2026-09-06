#!/usr/bin/env python3
# render_server.py — WARM MuseTalk render server. Loads model+avatar ONCE, then
# renders each wav in ~5-8s (vs 95s cold). POST /render {"wav","out"} -> {"rc","sec"}.
import os, sys, types, subprocess, json, threading, time
os.chdir("/workspace/LiveTalking")
sys.path.insert(0, "/workspace/LiveTalking")
sys.path.insert(0, "/workspace/_sys/pylibs311_good/dist-packages")
import numpy as np, soundfile as sf
import utils
import avatars.musetalk_avatar as M
from avatars.musetalk_avatar import MuseReal, load_model, load_avatar
from http.server import BaseHTTPRequestHandler, HTTPServer

FPS = 25; B = 8
AVATAR = os.environ.get("BAKE", "maya_serum_close")
print("[render_server] loading model...", flush=True)
model = load_model()
avatar = load_avatar(AVATAR)
shim = types.SimpleNamespace()
shim.vae, shim.unet, shim.pe, shim.timesteps, shim.audio_processor = model
(shim.frame_list_cycle, shim.mask_list_cycle, shim.coord_list_cycle,
 shim.mask_coords_list_cycle, shim.input_latent_list_cycle) = avatar
mirror_index = M.mirror_index
length = len(shim.input_latent_list_cycle)
H, W = shim.frame_list_cycle[0].shape[:2]
audio_processor = model[4]
_lock = threading.Lock()
print(f"[render_server] READY {W}x{H} cyclelen={length}", flush=True)


def render(wav, out):
    wav_data, sr = sf.read(wav, dtype="float32")
    if wav_data.ndim > 1:
        wav_data = wav_data.mean(axis=1)
    WIN = int(round(30.0 * sr)); chunks = []; seg = 0
    while seg < len(wav_data):
        s = wav_data[seg:seg + WIN]
        feat = audio_processor.audio2feat(s)
        seg_frames = min(int(round(len(s) / sr * FPS)), int(len(feat) * FPS / 50.0))
        chunks.extend(audio_processor.feature2chunks(feature_array=feat, fps=FPS, batch_size=seg_frames))
        seg += WIN
    ff = ["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
          "-map", "0:v:0", "-map", "1:a:0", "-shortest",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "128k", "-ar", "16000", "-movflags", "+faststart", out]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    index = 0; i = 0
    while i < len(chunks):
        cb = chunks[i:i + B]; shim.batch_size = len(cb)
        pred = MuseReal.inference_batch(shim, index, cb)
        for j in range(len(cb)):
            idx = mirror_index(length, index + j)
            try:
                frame = MuseReal.paste_back_frame(shim, pred[j], idx)
            except Exception:
                frame = shim.frame_list_cycle[idx]
            proc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
        index += len(cb); i += len(cb)
    proc.stdin.close()
    return proc.wait()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(b'{"ok":true}')
    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        d = json.loads(self.rfile.read(n) or b"{}")
        t0 = time.time()
        try:
            with _lock:
                rc = render(d["wav"], d["out"])
            body = json.dumps({"rc": rc, "sec": round(time.time() - t0, 1)}).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"error": repr(e)[:200]}).encode()
            self.send_response(500)
        self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8791), Handler).serve_forever()
