# Type: Kinetic type into UI

The headline is made out of the product's own pixels (cells of a game board, keys, tiles, list rows,
a grid of app icons), then the camera pulls back to reveal the real app, usually in one take.
Example: Cognition's "Devin is now in Teams" (Minesweeper cells spell the line, pull back 12x into
a Minesweeper window, then Teams). Route here when the burst shows type built from UI elements.

## What it's made of
- **The UI itself, in code, at world size.** Build the board/keyboard/grid once at its final
  on-screen size (the anchor frame) and let the camera do the zoom. Never build a separate
  "zoomed" version.
- **Measured camera, not guessed.** One-take zooms are the whole piece. Run `camtrack.py` to chain
  a scale+translate camera, then refit every frame to an absolute ruler with `gridcam.py` (grid
  lines) or `bboxcam.py` (a rigid flat-coloured object). Write cam.json; the composition reads it.
- **Pixel fonts extracted, never substituted.** For game/LCD/retro type, find the pixel unit from
  stroke-edge runs on the sharpest frame and sample every glyph as a bitmap. A "similar" pixel font
  is visibly wrong.
- **Cell states probed per frame.** Probe every cell through the measured camera (raised / open /
  pressed / ink) to get its reveal frame (examples/devin-teams/cellmap.py, boardmap.py).
- **Only the zooming object is in the camera.** Things that hold still (desktop, wallpaper,
  taskbar) sit outside it (see motion-feel.md).

## Traps
- Chained frame-to-frame registration drifts (Devin: 3% scale at 12x, 1.5° creep with free affine).
  Always refit to a ruler.
- A cell cut by the frame edge at its change frame gets dated to when it first comes fully into
  view. Check the frame-edge cells on the pair sheets and override.
- A constant edge offset in world px across zoom levels means the object is misplaced, not the
  camera. Nudge the object.
- Logo morphs between solid same-colour shapes: never crossfade (grey flash). Use solid layers.

## Learned from clones
- 2026-09-28 Devin in Teams: 5 rounds, distance 0.014 (draft) / 0.017 (delivery encode), motion
  corr 0.997, every window corr 0.99–1.00, lag 0 f. The camera tooling and per-frame diffs did it.
