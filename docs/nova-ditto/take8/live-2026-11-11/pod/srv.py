import http.server, os, json, re, sys
OUT = "/root/out"; IN = "/root/in"; TOK = open("/root/.tok").read().strip()
os.makedirs(OUT, exist_ok=True); os.makedirs(IN, exist_ok=True)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=OUT, **k)

    def log_message(self, *a):
        pass

    def do_PUT(self):
        m = re.fullmatch(r"/put/([A-Za-z0-9_.-]{1,80})", self.path)
        if not m or self.headers.get("X-Tok") != TOK:
            self.send_response(403); self.end_headers(); return
        n = int(self.headers.get("Content-Length", "0"))
        p = os.path.join(IN, m.group(1)); tmp = p + ".part"
        with open(tmp, "wb") as f:
            left = n
            while left:
                b = self.rfile.read(min(left, 1 << 20))
                if not b: break
                f.write(b); left -= len(b)
        os.replace(tmp, p)
        b = json.dumps({"ok": True, "name": m.group(1), "bytes": os.path.getsize(p)}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


http.server.ThreadingHTTPServer(("0.0.0.0", 8040), H).serve_forever()
