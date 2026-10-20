# groove-1080: Kling v2.1 pro image-to-video sources (2026-10-20)

- Reference: frame t=1.0 s of freezegame/idle_sway.mp4 (1076×1924), used as image_url AND tail_image_url (start = end → seamless loop).
- Model fal-ai/kling-video/v2.1/pro/image-to-video, duration 10, cfg_scale 0.5, negative "camera movement, zoom, cuts, extra people, text, blur, morphing, distorted hands, face changes".
  (This endpoint has no aspect_ratio input; 9:16 comes from the reference.)
- Prompts: A talk groove (head steady, mouth closed) · B big groove (arms up, side sways) · C half-time sway (head steady).
- analysis.json: seam = mean abs pixel diff first vs last frame (0–255, 270×480 grey; lower = better).
  head_px_s = face-patch template-track path length per second at full res (lower = steadier).
- preview/contact-sheet.png (first/mid/last per clip) · preview/preview-6tile.mp4 (top A1 A2 B1, bottom B2 C1 C2).
- Fal output URLs: gen.json.
