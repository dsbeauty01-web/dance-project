import py_compile, shutil, os, time
P="/workspace/lk_bridge.py"; WD="/workspace/gallery/wd"; os.makedirs(WD, exist_ok=True)
src=open(P).read()
helper='''
# DOWNSCALE (2026-10-22): publish 720x1288 (0.129 bpp @3Mbit/25fps) instead of 1076x1924
# (0.06 bpp = bitrate starvation). numpy-only nearest-neighbour, index maps cached per (w,h).
_RIDX = {}
_TW, _TH = 720, 1288
def _downscale(w, h, rgba):
    if (w, h) == (_TW, _TH):
        return w, h, rgba
    m = _RIDX.get((w, h))
    if m is None:
        yi = (np.arange(_TH) * h // _TH).astype(np.intp)
        xi = (np.arange(_TW) * w // _TW).astype(np.intp)
        m = (yi, xi); _RIDX[(w, h)] = m
    yi, xi = m
    a = np.frombuffer(rgba, dtype=np.uint8).reshape(h, w, 4)
    return _TW, _TH, np.ascontiguousarray(a[yi][:, xi]).tobytes()
'''
log=open(WD+"/downscale_patch.log","w")
def w_(s): log.write(s+"\n")
if "_downscale(" in src:
    w_("already patched — no change")
else:
    c=0
    a1="    return rgba.tobytes()\n"
    if src.count(a1)==1: src=src.replace(a1, a1+helper); c+=1
    else: w_("ANCHOR1 count=%d (expected 1)"%src.count(a1))
    a2="            w, h, rgba = await vq.get()\n"
    if src.count(a2)==1: src=src.replace(a2, a2+"            w, h, rgba = _downscale(w, h, rgba)\n"); c+=1
    else: w_("ANCHOR2 count=%d (expected 1)"%src.count(a2))
    if c==2:
        shutil.copy2(P, P+".bak-downscale-%d"%int(time.time()))
        open(P+".new","w").write(src)
        try:
            py_compile.compile(P+".new", doraise=True)
            os.replace(P+".new", P); w_("APPLIED 720x1288 downscale (2 anchors)")
        except Exception as e:
            os.remove(P+".new"); w_("COMPILE FAIL: %r"%e)
    else:
        w_("NOT APPLIED (anchors matched=%d)"%c)
w_("target bpp @720x1288,3Mbit,25fps = %.4f"%(3_000_000/(720*1288*25)))
# show the publish line now in effect
for i,l in enumerate(open(P),1):
    if "VideoSource(" in l or "max_bitrate" in l or "_downscale(" in l: w_("L%d: %s"%(i,l.rstrip()))
log.close()
