# THE GESTURE LIBRARY — the 9 Kling clips that unlock "natural" (your only manual job)

Why: every behavior skill says the same thing — gestures must fire BY MEANING, with ≥2 variants each or the
repeat shows within minutes; and "human noise" every 20–40s is what killed the robot feel on the $7.6M Baidu host.
presence.py already emits the right gesture + gaze cue per line (SHOW / POINT / WAVE / LISTEN / IDLE). It has
nothing to play until these exist.

RULES FOR EVERY CLIP (non-negotiable — they're why the last attempt flickered)
· Source image: Maya holding the bottle, warm room. Same outfit, same light, same framing in ALL clips.
· WAIST-UP (face large — lips read, gestures still visible). 1080p, 16:9, 25fps, audio OFF.
· Start AND end in the same neutral pose (bottle at waist, hands relaxed) → crossfades/switches are invisible.
· Mouth CLOSED the whole time. Negative prompt: talking, moving lips, open mouth, deformed hands, extra fingers.
· ONE continuous motion per clip — never stitch inside a clip.

THE NINE (Kling 3.0, Image-to-Video, Pro)
IDLE ×2 (15s each, first frame = last frame)
 1. "She stands relaxed holding the bottle at waist level, breathing subtly, blinks softly, tiny weight shift,
     calm warm presence. Mouth stays closed."
 2. "She stands naturally, glances briefly down at the bottle and back to camera, small smile, slight shift of
     weight. Mouth stays closed."   ← this one doubles as the 'human noise' beat
LISTEN ×2 (8s)
 3. "She tilts her head slightly and nods gently twice as if listening to a customer, attentive warm expression,
     then returns to neutral. Mouth stays closed."
 4. "She looks slightly off-camera as if reading messages on a screen, raises her eyebrows with interest, returns
     to camera. Mouth stays closed."
SHOW ×2 (8s)
 5. "She raises the bottle to chest height and tilts it toward the camera to show it, then lowers it back to
     waist. Warm proud smile. Mouth stays closed."
 6. "She turns the bottle slowly in her fingers while looking at it, then looks back at the camera. Mouth stays
     closed."
POINT ×2 (6s)
 7. "She lifts her free hand and points down toward the bottom of the frame twice, confident casual smile, then
     relaxes. Mouth stays closed."
 8. "She opens her palm toward the camera in a warm inviting gesture, then relaxes. Mouth stays closed."
WAVE ×1 (5s)
 9. "She raises her hand and gives a warm friendly wave toward the camera, smiling, then lowers it. Mouth stays
     closed."

FILE NAMES (the tooling matches on these): maya_idle_1.mp4, maya_idle_2.mp4, maya_listen_1.mp4, maya_listen_2.mp4,
maya_show_1.mp4, maya_show_2.mp4, maya_point_1.mp4, maya_point_2.mp4, maya_wave_1.mp4 → drop in $CLIPS_DIR.

WHAT HAPPENS THEN (no pod needed to prepare)
· register_avatar.py validates each (single take, 1080p, no jumps) and registers it.
· maya_ot.py switches by the gesture presence.py emits — IF the engine exposes avatar switching; if it doesn't,
  the clips still serve the director layer (PiP/cutaway) and a future managed avatar.
· COST: 9 clips ≈ one Kling session. This is the cheapest "natural" upgrade available on our own stack.
