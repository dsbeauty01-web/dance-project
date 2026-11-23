"""NOVA-GO2 · the `matchcut` math in beta/freeze4.html (cutMatrix) — offline, no pod.
Renders, in headless Chrome, Nova's pane (640x720 and a phone 390x422 pane) three ways: her WIDE body frame
(nova_talk_calm.mp4 frame 0, as published 720x1280), the game clip frame 0 un-zoomed (the old hard cut), and the game
clip with the page's own cutMatrix() transform + clip-path (the matched frame). Pass = the matched frame is far closer
to the wide frame than the old cut, and her figure's box (non-room pixels) is within 3 px.
Usage: python3 test/matchcut_test.py <wide_frame.png 1080x1920> <clip_frame.png 1076x1924>"""
import sys, re, os, base64, tempfile, numpy as np, cv2
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); PAGE = open(os.path.join(HERE, '..', 'beta', 'freeze4.html')).read()
src = re.search(r"const CUT = \{.*?\n\}\n", PAGE, re.S); src = src.group(0) if src else None
fn = re.search(r"function cutMatrix\(\)\{.*?\n\}\n", PAGE, re.S).group(0)
cut = re.search(r"const CUT = \{[^\n]*\};", PAGE).group(0)
wide, clip = sys.argv[1], sys.argv[2]
w720 = cv2.resize(cv2.imread(wide), (720, 1280), interpolation=cv2.INTER_AREA); tmp = tempfile.mkdtemp()
cv2.imwrite(f"{tmp}/w.png", w720); cv2.imwrite(f"{tmp}/c.png", cv2.imread(clip))
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, 'rb').read()).decode()
def html(mode, W, H):
    return f"""<html><body style="margin:0;background:#fff"><div id=pane style="position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#fff">
<img id=nova src="{b64(tmp+'/c.png')}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain">
<img id=novaWide src="{b64(tmp+'/w.png')}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain"></div>
<script>const $=id=>document.getElementById(id);
for (const i of document.images) {{ Object.defineProperty(i,'videoWidth',{{get(){{return i.naturalWidth}}}}); Object.defineProperty(i,'videoHeight',{{get(){{return i.naturalHeight}}}}); }}
{cut}
{fn}
window.go=()=>{{ const m='{mode}'; if(m==='wide'){{ $('nova').style.display='none'; }} else {{ $('novaWide').style.display='none';
  if(m==='match'){{ const k=cutMatrix(); $('nova').style.transformOrigin='0 0'; $('nova').style.transform=k.m; $('nova').style.clipPath=k.zin; }} }} }};</script></body></html>"""
def fig_box(im):   # her figure = saturated purple/dark/pink pixels; the room is light pink/wood. Rough but stable for a size check.
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); m = ((hsv[..., 2] < 90) | ((hsv[..., 0] > 120) & (hsv[..., 0] < 150) & (hsv[..., 1] > 90))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)); n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(st[1:, 4])); x, y, w, h = st[i, :4]; return np.array([x, y, x + w, y + h])
ok = True
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for W, H in ((640, 720), (390, 422)):
        shots = {}
        for mode in ("wide", "old", "match"):
            pg = b.new_page(viewport={"width": W, "height": H}); pg.set_content(html(mode, W, H)); pg.wait_for_function("[...document.images].every(i=>i.complete)")
            pg.evaluate("go()"); pg.wait_for_timeout(100); fp = f"{tmp}/{mode}_{W}.png"; pg.screenshot(path=fp); shots[mode] = cv2.imread(fp); pg.close()
        d_old = float(np.abs(shots['old'].astype(int) - shots['wide']).mean()); d_m = float(np.abs(shots['match'].astype(int) - shots['wide']).mean())
        bw, bo, bm = fig_box(shots['wide']), fig_box(shots['old']), fig_box(shots['match'])
        err_m, err_o = int(np.abs(bm - bw).max()), int(np.abs(bo - bw).max())
        print(f"pane {W}x{H}: mean |diff| vs wide: old cut {d_old:.1f}, matched {d_m:.1f} · figure box wide {bw.tolist()} old {bo.tolist()} (off {err_o} px) matched {bm.tolist()} (off {err_m} px)")
        ok &= d_m < d_old / 2 and err_m <= max(3, H // 200)
        cv2.imwrite(f"/tmp/claude-0/novago/sheet/matchcut_{W}.png", np.hstack([shots['wide'], shots['old'], shots['match']]))
    b.close()
print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
