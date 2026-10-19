---
name: game-vfx-juice
description: Use this skill whenever polishing, tuning, or building visual feedback effects for Nova's games (the light engine — orbs, comets, hoops, ice, snaps, labels, particles) or judging whether an effect "feels alive." Encodes the game-feel/juice canon (Juice It or Lose It, The Art of Screenshake, Disney's animation principles, Steve Swink's Game Feel) and canvas-2D VFX technique (offscreen bloom, tapered ribbon trails, easing, additive blending, lifetimes) — so every effect has anticipation, impact, and follow-through, sized and timed like a real game.
---

# Game VFX Juice — why an effect feels alive (and why ours don't yet)

## The canon (what the best games do)
- **Juice It or Lose It** (Jonasson & Purho): a functional prototype becomes alive by stacking small feedbacks on every event — squash/stretch, particles, trails, flashes, sound, easing. Feedback must fire ON the event, instantly, proportionally.
- **The Art of Screenshake** (Vlambeer): impact = a chain of tiny hits landing within ~100ms — flash, particles, a kick, a sound. One big effect < five small ones together.
- **Disney's principles** that apply to light: **anticipation** (something small happens BEFORE the event — the cue), **squash & stretch** (the effect deforms with energy), **follow-through** (it doesn't stop dead — it overshoots, settles, fades), **timing/easing** (nothing moves linearly; ease-out on arrival, ease-in on departure), **secondary action** (sparks, a ring, a label — small companions to the main effect).
- **Game Feel** (Swink): the loop is input → immediate response → readable result. Delay or ambiguity kills it. Every effect answers "what did I just do?" within one frame.
- The counter-warning (Folmer Kelly): juice that ignores the material breaks immersion — light must behave like light (blooms, trails, fades), never like UI (hard circles, flat lines).

## Canvas-2D technique (the professional way)
1. **Bloom = offscreen blur composite:** draw the glow source to an offscreen canvas, blur it (`ctx.filter='blur(px)'` or a downscaled copy), composite with `globalCompositeOperation='lighter'`, then draw the sharp core on top. Three layers (wide/mid/core) read as light; one radial gradient reads as a sticker.
2. **Trails = tapered ribbons, not dots:** store the last N positions of the moving thing; draw a polygon whose width tapers from head to tail with alpha fading; smooth the points (Catmull-Rom) so low frame rates don't look jagged. Dots-in-a-row is the amateur tell.
3. **Additive blending** for all light; `source-over` only for anchors (dashed rings, labels' dark outline).
4. **Easing everything:** cue arrival = easeOutCubic; hit burst = easeOutExpo (fast start, long tail); fades = easeInQuad; nothing linear.
5. **Lifetimes:** hits 250-450ms, rings 300-500ms, labels 700ms rise, cues live exactly lead+window. Anything longer lingers; anything shorter isn't seen.
6. **Scale by body:** every size derives from the live shoulder-width; a 4-year-old far from the camera and an adult up close get the same proportions.
7. **Hit-stop for light:** on a PERFECT, freeze the cue's ring for ~60ms at max brightness before it bursts — the eye reads the moment.
8. **Sound is half the effect:** the tick/snap/ding lands within 30ms of the visual; pitch or volume scales with quality/streak.
9. **Never cover the face; never red.** Labels above the head; warnings warm, not red.

## The polish list for Nova's five effects (apply on top of LIGHTS-FINAL)
- **Comet (wave):** replace the dot-tail with a **tapered ribbon** (Catmull-Rom over the chain, width head 0.22×sw → tail 0.04×sw, alpha 1→0), head bloom via offscreen blur; the hit comet overshoots the fingertip by ~0.15×sw and dissolves (follow-through). Cap head radius so a resting arm never becomes a ball.
- **Hoop (ribs/hips):** perspective ratio ry/rx = 0.28 (flatter = more 3D), the moving hoop **eases** to the target (easeOutCubic over the lead), a 60ms hit-stop at arrival, then a single bright pulse; the hip hoop breathes (±3%) so it reads alive but anchored.
- **Ice (freeze):** keep subtle; add a 1-2px brighter rim on the silhouette edge (edge = mask minus eroded mask) so the ice has a surface; deepen with easeInQuad over the hold; the FROZEN moment = one 120ms brightness pulse of the whole rim, nothing else.
- **Snap (clap):** anticipation = the thin line brightens with easeIn as the hands close; contact = star for 250ms with easeOutExpo scale (1.3 → 1), ring 300ms; add a 40ms white micro-flash on both hands.
- **Orb (moves):** squash/stretch on hit (scale 1.25 then 0.9 then 1 over 200ms), the closing ring uses easeOutQuad so it "arrives," PERFECT gets the 60ms hit-stop.
- **Labels:** rise with easeOutCubic, 8° tilt on PERFECT, dark outline 3px, glow 24px; never two labels at once.
- **Particles:** Gaussian scatter (not uniform), 400-700ms lifetimes, gravity only on burst particles, none on ice.

## Anti-patterns
Dots-in-a-row trails · single radial gradients as "glow" · linear motion · effects that stop dead · giant torso-sized rings · anything red · labels on the face · two cues in one beat · effects longer than 700ms (except cues and ice).
