# Type: Liquid-glass UI

Apple-style "liquid glass" interface pieces morphing into each other over wallpapers and photos:
notification pills, sheets, menus, tab bars, docks, widgets, camera controls, player cards, message
bubbles. The motion is the product; there's usually no app story. Example: Bricks Dept's YouTube
intro. Use ui-showcase.md for window/typing software launches instead.

## What it's made of
- **Glass in code:** `backdrop-filter` blur + an SDF edge-refraction `feDisplacementMap` (see
  `references/examples/bricks-glass/lib.js`, `lensMap`) + inset rim highlights. Test-render the glass
  once before building ten of them. Keep displacement ≤ ~50 over busy photos (110 turned a camera
  lens into orange soup).
- **Every morph = a tracked pose + measured box keys.** Run `track.py` on each object from its flat
  anchor frame (full homography for objects with 2D texture; centre + uniform scale only for thin
  strips like search bars, docks, tab bars, and for featureless plates, or they shear into
  trapezoids). Validate every track with `trackcheck.py` before building on it (Bricks: 19/21 tracks
  within ~10 px with no hand keys). `export_tracks.py` writes hf/tracks.js.
- **Backgrounds:** soft drifting gradients = `bgfield.py` (median-colour probes, 4x3 grid every 3 f,
  skipping probes that sit on UI, rendered as a blurred bilinear field); photos = gpt-image plates
  from `prep_refin.py` frames (UI blacked out), colour-matched with `colormatch.py` (Lab over
  background-only rows; keep only if that shot's distance drops). Check every plate for an alpha
  channel and flatten it (an RGBA plate turned to garbage as JPEG).
- **Motion blur is real:** `round_mb.sh` renders at fps×N and averages subframes. Choose the visible
  shot from the INTEGER output frame and only shift time for the motion, or hard cuts blend
  (7/9 cuts, corr 0.637 without it).
- **Camera dives through several states** (tilted card → top-down → spin): ONE virtual camera with
  separate keyed channels (anchor path, log-scale zoom, tilt weight, scroll, rotation). Key zoom from
  a feature whose world size is fixed (road width, window chrome), never from an icon that scales.
- **Voice-over over typing UI:** word times from a local Whisper pass (mlx_whisper large-v3-turbo,
  word timestamps), confirmed on a cropped every-frame sheet; mid-sentence words land 3–5 f before
  Whisper's onset.

## Traps
- A quiet window with low motion correlation usually means the reference has a background-drift
  floor your clone lacks: print both energy curves (`bgcurve.py`) before touching the foreground.
- Gooey stretch morphs (a tab bar stretching into a floating bar) don't come from box keyframes;
  hand-keyed box morphs scored corr 0.58 there. Needs an SDF/metaball blend (open problem).

## Learned from clones
- 2026-09-28 Bricks Dept intro: distance 0.047, motion corr 0.954, motion 0.99x, 9/9 cuts on frame.
  Coded shots under 0.05; plate shots 0.063–0.088 with timing on target. App icons were code
  stand-ins (only After Effects and Discord real); 21st.dev not used (all Apple system UI).
