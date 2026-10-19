# DETECTION-MIGRATE — MoveNet → MediaPipe Pose Landmarker (fresh CLI · one bounded session · Freeze beta first)

## CODE NAMES (the founder's vocabulary — use them in reports)
BODY = the page's HTML/CSS · LIGHTS = joint lights · CUES = what the kid must do (windows, score, success) · DETECTION = the pose code · BRAIN = her talking/encouraging.

## THE JOB (DETECTION only — touch nothing else)
1. Read `.claude/skills/movement-tracking/SKILL.md` §1-§2.
2. Create `shared/pose-adapter.js` EXACTLY as in skill §2 (toNova, MP, MOVENET maps).
3. Add `shared/pose-engine.js`: loads MediaPipe Pose Landmarker (`@mediapipe/tasks-vision`, model `pose_landmarker_lite.task` self-hosted under `/models/`, delegate GPU → CPU fallback → MoveNet fallback), runningMode VIDEO, numPoses 1, `outputSegmentationMasks:false` for now. Emits `onPose(toNova(result, engine))` per frame. Logs `[POSE] engine=<mediapipe|movenet> fps=<n>` every 5s.
4. Wire it into `beta/freeze.html` ONLY. The stillness detector reads named joints via toNova (no raw indices remain — grep-proof). Visibility gate 0.5 for MediaPipe, min 8 visible joints.
5. Recalibrate: the stillness threshold via the harness (values may shift 10-20%). Run MACHINE-CERTIFY graders on beta/freeze: 3× clean EN + 3× HE.
6. Tag `beta-b0.10`, CHANGELOG line "DETECTION: MediaPipe engine + adapter on Freeze beta".

## EVIDENCE (then HOLD)
- `[POSE] engine=mediapipe` lines + fps · the adapter file · grep showing zero raw keypoint indices in beta/freeze.html · harness results table · one screenshot of the pose overlay (debug `?pose=1`) on a real camera frame.
- Pod self-stops. Nothing merged to main.
