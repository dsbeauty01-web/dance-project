#!/usr/bin/env python3
"""
ot_avatars.py — register Maya's gesture avatars in OpenTalking from the Kling clips (QuickTalk = template video, no bake).
Layout discovered on the pod (GATE 1): <OT_AVATAR_DIR>/<avatar_id>/manifest.json with model_type "quicktalk" + source_video.
  python ot_avatars.py --clips /workspace/maya-ops/bake/src1080 --dry     # show what would be created
  python ot_avatars.py --clips /workspace/maya-ops/bake/src1080           # create manifests + copy videos
Then set in ~/.maya/host.env:  OT_AVATAR_SHOW=maya_show  OT_AVATAR_POINT=maya_point  OT_AVATAR_LISTEN=maya_listen  OT_AVATAR_WAVE=maya_wave  OT_AVATAR_IDLE=maya_idle
maya_ot.py switches avatars per intent IF the OpenTalking build exposes a session avatar-switch route; otherwise it stays on the main template (logged once).
"""
import argparse, json, os, shutil, glob

MAP = {"maya_show": ["*show*", "*present*", "*holding*"], "maya_point": ["*point*", "*cta*"], "maya_listen": ["*listen*", "*examine*"],
       "maya_wave": ["*wave*", "*invite*"], "maya_idle": ["*idle*"]}


def find(clips, patterns):
    for p in patterns:
        hits = sorted(glob.glob(os.path.join(clips, p + ".mp4")))
        if hits:
            return hits[0]
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--clips", required=True); ap.add_argument("--dir", default=os.environ.get("OT_AVATAR_DIR", "/workspace/opentalking/data/avatars"))
    ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    for aid, pats in MAP.items():
        src = find(a.clips, pats)
        if not src:
            print(f"skip {aid}: no clip matching {pats} in {a.clips}"); continue
        d = os.path.join(a.dir, aid); dst = os.path.join(d, "source.mp4")
        manifest = {"avatar_id": aid, "name": aid.replace("_", " ").title(), "model_type": "quicktalk", "source_video": "source.mp4", "description": f"Maya gesture: {aid}"}
        print(f"{'DRY ' if a.dry else ''}{aid} ← {os.path.basename(src)} → {d}")
        if a.dry:
            continue
        os.makedirs(d, exist_ok=True); shutil.copy2(src, dst)
        json.dump(manifest, open(os.path.join(d, "manifest.json"), "w"), indent=2)
    print("done. Verify with the OpenTalking WebUI avatar list (or GET /avatars) — adjust manifest keys if the build differs.")


if __name__ == "__main__":
    main()
