"""sitecustomize.py -- installs the full-body shim into ditto_wide before ditto_server imports it.

ditto_server.py does `sys.path.insert(0, BENCH); import ditto_wide as DW` at module import and only
later calls `DW.patch_first_frame_crop(lm)` inside Engine.load(). Importing ditto_wide HERE, at
interpreter start, puts the module in sys.modules first, so ditto_server reuses the patched one and
not a single line of maya-lt is edited.

Fail-soft on purpose: this file is on PYTHONPATH for every python in the venv, including the
`python -c "import site; ..."` calls ditto_up.sh makes while the venv is still being built. It must
never raise and never write to stdout (ditto_up.sh captures stdout of those calls).
"""
import os
import sys

if os.environ.get("DITTO_FB_ON") == "1":
    try:
        for p in (os.environ.get("DITTO_FB_SHIM", ""), os.environ.get("DITTO_FB_BENCH", "")):
            if p and p not in sys.path:
                sys.path.insert(0, p)
        import ditto_wide            # noqa: F401  -- lands in sys.modules, patched below
        import ditto_fullbody
        ditto_fullbody.install()     # reads DITTO_FB_BOX / DITTO_FB_UP
    except Exception as e:           # noqa: BLE001
        print(f"[sitecustomize] full-body shim NOT installed: {type(e).__name__}: {e}", file=sys.stderr)
