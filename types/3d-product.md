# Type: Photoreal 3D product

A physical product (keyboard, phone, headphones) rendered in 3D: studio or lifestyle light,
material close-ups, slow orbits, exploded views, product floating with ribbons. Made in
C4D/Blender by hand (MarkKnd says no AI prompts were used).

## Two routes (decide per shot, write it in BREAKDOWN.md)
1. **Blender (preferred for hero orbits and exploded views).** Needs Blender on PATH
   (headless: `blender -b -P script.py`). Model the product
   procedurally in Python (bmesh; keycaps are instanced rounded boxes), PBR materials, HDRI or
   area-light studio, Cycles or EEVEE. Animate the camera/parts from keyframes read off the burst
   windows, render an image sequence at the reference fps, bring it into HyperFrames as video.
   Match lens: estimate focal length from perspective in the reference frames.
2. **gpt-image plates + camera move in code** for static close-ups and lifestyle shots (desk
   scene, macro of a keycap). Feed the reference frame, then push/pan in code. Won't hold for
   parts that move.

## What sells it
- Materials: brushed aluminium anisotropy, soft-touch plastic, keycap legends, a lit screen with
  real UI on it (the screen content is coded UI rendered to a texture, never generated).
- Light: big soft key, rim light, gentle bounce; colour grade from the palette.
- Motion: slow, heavy, eased; dolly and orbit with slight parallax; depth of field on macros.
- Overlaid UI callouts (the keyboard's "Screen" chip) are coded HTML on top of the render.

## Traps
- Cycles on CPU is slow: use EEVEE or low samples + denoise for drafts, final at higher samples.
- Render output and frame scratch go outside the repo, on a disk with room (it's thousands of PNGs).
- A procedural model won't match an original CAD model's proportions by eye; measure ratios
  (width:depth:height, key pitch) off the reference and write them down first.

## Learned from clones
(append: date, clone, one specific lesson per line)
- 2026-09-27 MarkKnd keyboard: distance 0.20 (vs ~0.03 on coded UI clones) after 6 rounds: timing held (8/8 cuts, motion corr 0.87), materials didn't (matte keycaps vs glossy soft-touch with dished tops; flat ribbons with no refraction). Budget rounds for materials, not just motion.
- 2026-09-27 MarkKnd: float motion fix = see references/motion-feel.md (one drift curve per channel, cut in on motion, objects out of phase with each other). The reviewer's note was "the way it floats doesn't look natural".
- 2026-09-27 MarkKnd: Blender traps: the default AgX view transform greys flat backgrounds (use Standard for flat-colour grounds); EEVEE needs raytracing + denoise or white keycaps go grainy. round.sh doesn't run Blender: render the Blender pass first, then the HyperFrames overlay.
- 2026-09-27 MarkKnd: the distance score is dominated by background colour; a structurally closer shot scored worse because the wall was darker. Judge product shots on the pairs and the per-object tracking, not distance alone.

