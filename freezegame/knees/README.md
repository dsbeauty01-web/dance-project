# freezegame/knees — the freeze pose clips at the Ditto body's framing

These are the four pose clips cut to the SAME crop box as the knees-up Ditto body
(`628:1126:218:257` of a 1076x1924 frame → 1080x1920, zoom ~1.71x). Frame rate is
unchanged at 24 fps: these are page-side `PoseClip` overlays, not a Ditto source, so
nothing here is resampled or re-timed.

**This set is NOT approved.** Measured on the exact frame the page holds, 3 of the 4 poses
lose the landmarks that make them: star loses both hands, bear loses a raised paw and the
top of the pose, frog loses both knees. Only flamingo survives. See `manifest.json` for the
per-pose numbers and `../../docs/nova-ditto/freeze-crop-check.jpg` for the picture.

They are kept here so the crop can be judged by eye, and so the wiring has something real to
point at once the poses are re-generated at knees-up framing. `beta/freeze.html` reads
`manifest.json`: while `set_verdict` is not `OK`, `?face=ditto` banners and `PoseClip.show()`
refuses — a kid never sees a chopped pose.
