# Motion feel: why a clone looks "AI" even when everything is in the right place

Read this for EVERY clone, whatever the type. Reviewer notes on finished clones are almost never about
layout. They're about motion that doesn't feel natural: UI that "comes in a little too fast"
(Raycast, 2026-09-27), a product whose float "does not look natural" (MarkKnd keyboard, 2026-09-27).
Both come from the same few mistakes, so the rules below are about motion in general, not about
UI or 3D.

## The mistakes

1. **Stopping between keys (the most common one).** Easing every keyframe in and out makes the thing decelerate to zero
   and restart at every key. Real motion (a camera operator, a floating product, a settling window)
   keeps moving through the middle and only eases at the very start and end of the move.
2. **Everything moving in lockstep.** Separate things (windows in a cascade, parts of an exploded
   product, cards) all start, peak and stop on the same frames. Real motion gives each object its
   own timing: one arrives late, one counter-rotates, one settles slower. (Measure first: a SINGLE
   floating product in MarkKnd moved all its own axes together, in phase. The offsets were between
   objects, not between one object's axes.)
3. **Settling too fast.** The move lands in ~20 frames and stops dead. Premium motion has a long,
   soft tail (Raycast: 30–33 f at 30 fps) and the last 5% of the travel takes a third of the time.
4. **Linear scale.** Scaling 8x → 1x linearly spends most of its time big, then lurches. Big scale
   changes interpolate in log space: `s = S0 ** ((1 - t) ** 4)`.
5. **One start frame for many things.** A group that all begins on the same frame reads as
   mechanical. Stagger by measured frames (Raycast rows: 2–2.5 f).
6. **Easing in at the start of a shot.** Shots usually cut in ON motion, already moving fast
   (MarkKnd: speed on the cut 4–10x the average). An ease-in from zero at a cut looks staged.
7. **Putting everything inside the camera.** Only the thing that zooms or moves belongs in the
   camera transform. Track one fixed feature of each layer (a wallpaper edge, a taskbar) across the
   move first; if it holds still, it sits outside the camera. (Devin: desktop inside the camera =
   taskbar energy 45 vs the reference's 0.58, window motion ratio 1.16 → 0.98 once moved out.)
8. **Crossfading solid shapes of the same colour.** Opacity on black over black reads as a grey
   flash. Morph with solid layers (reveal the real mark underneath) instead.
9. **Stepping into a blur.** blur(0) → blur(1px) is a one-frame jump. Start ramps at ~0.3 px and fit
   the curve to the reference (blurfit.py).
10. **Smooth motion where the reference animates on 2s.** Some motion designers animate at half the
    frame rate (25 fps inside 50). Smooth 50 fps motion next to it reads floaty. ANALYSIS.md flags the
    cadence; quantize to it.
11. **Guessing instead of measuring.** Every one of these was invisible until someone measured the
   reference per frame.

## The method (works on anything that moves)

1. **Measure the reference per channel, per frame.** Not "the shot's energy": the actual
   position x/y, rotation, scale (and opacity) of the moving thing, frame by frame, from full-res
   frames (bounding box / corners / tracked points with numpy; sheet.py to see it). Plot each channel.
2. **Read the curves:** where is velocity zero (only at the ends?), how long is the settle, is
   there overshoot (a second hump), are channels out of phase and by how many frames, is there
   secondary motion (a small lag or wobble after a direction change).
3. **Build each channel as its own smooth curve** that reproduces the measured one: a spline with
   long handles, a sum of slow sines, or the log-scale ease above. Offset phases between channels as
   measured. No velocity zeros mid-move unless the reference has them.
4. **Check it in the numbers for that moment**: motion correlation ≥ 0.95, motion ratio ~1.0, peak
   offset 0 f (compare.py per-window table, or a per-moment range). A ratio well under 1 = too fast
   and settles too soon; a ratio over 1 = too busy.
5. **Then watch it at normal speed** next to the reference. The numbers say where; the eye says
   whether it breathes.

## Measured examples

- **Raycast / Glaze, 0:24 window cascade (UI):** depth cascade, each element 7–9x → 1x scaling about
  the frame centre, log-scale quartic ease-out over 30–33 f, no overshoot, rows 2–2.5 f apart,
  containers ~1 f before their content, chrome last and entering smaller (3x). Went from motion corr
  0.79, ratio 0.25, peak +12 f ("comes in too fast") → 0.96, 1.06, 0 f. Row start frames mattered
  more than curve power (1 f off = −0.02 corr).
- **MarkKnd keyboard, floating product (3D):** every floating channel fits one curve,
  `p(t) = A(1 − e^(−t/τ)) + B·t` (about half quick ease-out, half steady drift), τ = 6 f on the hero
  float, 8.5–17 f on the exploded stack. Shots cut in ON motion (speed on the cut 4–10x the average,
  no ease-in) and never reach zero speed mid-shot. One product moves all its channels together; the
  out-of-phase motion is BETWEEN objects (box, keyboard, tray each with their own τ; the tray
  counter-rotates −12° against the box's +11° and arrives late). An exploded view is the parts
  separating, not a camera push. Ours eased to a stop mid-shot, then went linear: replacing the
  per-key eases with one drift curve per channel took motion corr 0.73 → 0.98 (shot 3) and 0.78 → 0.91
  (shot 8). Measure object motion with optical flow inside a box per object (OpenCV LK flow +
  estimateAffine2D → x/y/rotation/scale per frame), then fit the curve.
