# Type: Editorial collage

Paper, desk surface, photos, drafting tools, stills and UI cards composed on a surface, with
footage or screenshots dropped in (Kimi K3). Half coded, half raster.

## What it's made of
- **Desk plates from gpt-image**, fed the reference frame: one plate per composition, plus
  edited variants for anything that leaves (the hand-with-pencil plate + the same plate with the
  hand removed; animate the top layer off).
- **Coded on top**: the type, UI (chat box, model picker, send button), label chips, code tokens.
- **Footage shots** (games, apps) = generated stills + camera move in code + capture artifacts
  (HUD text, cursor, compression, motion blur). They can't pixel-match: tag [RASTER].
- **Camera**: a slow push/pan on a wrapper over the whole desk, with jitter on anything handheld.

## Learned from clones
- 2026-09-25 Kimi K3: 28/28 cuts within 2f, motion corr 0.82 after 6 rounds; worst seconds were
  all generated game plates (they read as cinematic renders, not captures).
- 2026-09-25 Kimi K3: shots that look like one clip in the overview were 5 hard cuts (f332–372);
  check the cut list before building a "shot" as one element.
- 2026-09-25 Kimi K3: paper tearing via particle erosion looked grainy; torn-edge masks (an SVG
  path with a noise edge) are closer.
- 2026-09-25 Kimi K3: layout sizes guessed from 192px analysis were 20–40% small; measure at full res.
