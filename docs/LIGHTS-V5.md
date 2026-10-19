# LIGHTS-V5 — the polish pass (read .claude/skills/game-vfx-juice/SKILL.md FIRST, then apply its polish list to the LIGHTS-FINAL engine)

Analysis of v4 (founder + architect): the language is right; the execution is still "drawn," not "alive." Fix, in this order:
1. WAVE comet → tapered RIBBON trail (Catmull-Rom over the chain; width 0.22×sw head → 0.04×sw tail; alpha 1→0), head bloom via offscreen blur, overshoot the fingertip 0.15×sw then dissolve. CAP the head radius at 0.22×sw — the resting arm must never turn into a ball (v4 frame 3 bug).
2. HOOP → flatter perspective (ry = 0.28·rx), eased travel (easeOutCubic over the lead), 60ms hit-stop at arrival then one pulse; the anchor hoop breathes ±3%.
3. ICE → add a 1-2px bright rim on the silhouette edge (mask minus eroded mask); deepen with easeInQuad; FROZEN = one 120ms rim pulse only.
4. SNAP → line brightens easeIn as hands close; star scale 1.3→1 easeOutExpo over 250ms; 40ms white micro-flash on both hands.
5. ORB → squash/stretch on hit (1.25 → 0.9 → 1 over 200ms); closing ring easeOutQuad; PERFECT gets the 60ms hit-stop.
6. LABELS → easeOutCubic rise, 8° tilt on PERFECT, 3px dark outline + 24px glow; never two at once.
7. PARTICLES → Gaussian scatter, 400-700ms lifetimes, gravity only on bursts.
8. SOUND → every tick/snap/ding within 30ms of its visual; pitch scales with quality.
Global: all light additive; offscreen-blur bloom (not single gradients); all sizes from sw; nothing linear; nothing over the face; nothing red.
Record v5 on the same clip → Downloads lights-demo-v5 + 3 beeps. Tag beta-b0.18. Hold.
