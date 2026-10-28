---
name: paper-world
description: Turn a frame of real footage into a dimensional paper-collage world and back - freeze on a word, cut the subject out as real paper, let the background fall away like a stage flat, climb through a parallax paper city and paper clouds (Blender headless), stage a literal stat or a brand reveal, then return to footage through a cloud. Use for collage / paper-craft / cut-out beats inside a live-action video (stat visualisations, metaphors, logo reveals), or any shot where footage becomes an illustrated 3D world.
---

# Paper world: footage → paper collage → footage

A hybrid beat inside a live-action video. The viewer should feel the real frame turn into paper,
not cut to an animation. Everything here is a general rule learned on a real build, with the numbers
behind it. `scripts/` sits next to this file.

## The shape of the beat

```
real footage ─► freeze on the stressed word ─► subject lifts off as paper ─► background falls back
  ─► camera move through a layered paper world (the stat / metaphor, shown literally)
  ─► brand or payoff assembles from the world ─► the world closes over it ─► opens onto footage again
```

Write the beat into the timing sheet first (see `vo-beat-timing`): which word freezes the frame,
which word the payoff lands on, and which word hands back to footage.

## 1. Freeze and cut out (real pixels, real paper)

- **Freeze on the stressed word** of the line (the number, the noun), and pick the freeze frame where
  the subject is sharp and still. Use the graded frame (`scripts/log_lut.py` builds a shared
  Log→Rec.709 film LUT so footage and renders match).
- **Segment:**
  - SAM / SAM 2 for objects.
  - For small people in a wide shot, run a foreground-instance mask on a 2-3× crop. Whole-frame
    person segmentation returned an empty mask on a figure ~8% of frame height. Apple Vision
    `VNGenerateForegroundInstanceMaskRequest` on a 3× crop worked first try.
  - Thin structures (poles, cables, scaffold tubes) get SAM point prompts along their length, or are
    drawn from the frame by hand.
  - Check every mask at 300% before you build on it: a clipped head or a missing pole is visible at
    full size.
- **Clean plate:** inpaint what the cut-outs leave behind (LaMa big-lama TorchScript works without its
  pip wrapper). The plate becomes the background flat.
- **Paper treatment:** `scripts/paper_cutout.py IMAGE MASK OUT.png --border <~1-2% of subject height>`.
  It gives a scissor line with a slow wander, an off-white fibre border, a darker bevelled edge, and a
  cut that never eats into the subject.
  - Thin perfect white outlines read as "fake digital lines". Reject them.
  - Per-frame wobble "on 2s" (stop-motion boil) read as glitchy at review. Use smooth eased motion
    instead.
- **Textures come from real photos, never procedural drawing.** In one build, scaffolding drawn as grey
  diagonals and flat colour bars was rejected at the texture preview. Scaffolding tiled from a real
  cut-out of the footage passed. Sources, in order: your own footage, then real photography, then
  generated imagery (last resort).

## 2. The lift and the fall (the subject stays, the world moves)

- The subject cut-outs lift a few pixels (soft shadow grows, eased), and the **background plate falls
  back on a hinge like a theatre flat** (eased in-out, soft landing, a little dust), while the
  subject stays in place. A swipe or slide of the whole frame was called lazy. The fall sells "this
  was paper all along".
- Bridge real → 3D with a 3-4 frame crossfade from the real freeze to a render whose camera is
  photo-matched to that frame (same focal length and horizon; place the plate where it projects back
  onto itself). Check the seam frames' diff (`../footage-transitions/scripts/spikecheck.py`).

## 3. The world (Blender headless)

- **Paper cards at many depths.** Image planes with a paper material (emission + some diffuse, fibre
  texture, haze with distance), so parallax does the 3D work. Vary the building types (row houses,
  lofts, towers, warehouses). One repeated facade reads as clip art.
- **Hero pieces are solids:** extrude and bevel 2D polygons (logo pieces, clouds, key buildings), so
  edges catch light.
- **Real landmarks at real relative positions** when the place is real. A wrong skyline gets noticed.
- **Clouds = 2-3 extruded, bevelled cloud silhouettes stacked in depth**, each smaller, whiter and
  offset. Rules:
  - Silhouettes must be puffy all round. A flat bottom or a straight end means the card bounds are
    clipping the shape, and it reads as fake. Check edges on a full-res frame.
  - Foreground clouds sit at the frame edges, defocused, covering ≤ ~20% of the frame combined. One
    test had a defocused cloud over the whole left third.
  - Background clouds go behind the subject, with a clear corridor around it.
  - Any full-frame white (flying through a cloud) lasts ≤ ~10 frames. Twenty frames reads as a
    blank card.
- **Literal stats.** If the line says "N of X", show the X, and make them the subject:
  - centred
  - ~15-20% of frame width on the stressed word
  - growing out of the thing the camera has been following, not standing beside it
  In one build, a stack placed small at the frame edge failed review; the same stack centred and
  scaled passed.
- **Brand from the world:**
  - Use the real logo (press kit / logo service), built as extruded paper pieces.
  - Assemble it over ≥ ~1.5 s with eased moves. Faster was called "a little too fast".
  - Hold it readable for ≥ ~0.7 s.
  - Let the world part to frame it (clouds open), rather than cutting to a logo card.

## 4. Camera

One continuous keyframed path, smoothed (Hann window over the keys), exported to `cam.json`.
Then **assert the numbers**:

- A climb never reverses: height is non-decreasing frame to frame.
  - One version dipped from 167 to 5 units and turned 13° mid-climb; that was the first note.
  - Roll is 0, yaw change ≈ 0, and pitch change totals only a few degrees.
  - "No rotation, no flying around" is a hard rule unless the story is the rotation.
- **Slow down where the subject must read.** On the stressed word, ease the speed down to where
  motion blur doesn't smear detail. 0.3 units/frame read sharp at a camera ~100 units away; 1.3
  units/frame smeared the windows. Then ease back up.
- Motion blur on (shutter ~0.5). It's what made the stack landings feel physical ("nice motion
  blur, well done").

## 5. Back to footage

- **Close the world over the payoff in SCREEN space, not world units.** One build closed four cloud
  pieces with an ease in world units while the camera pushed ~4 units/frame. Their edges sat just
  off-frame, so the entire close reached the screen in one frame (diff 9.6× the local median). It's a
  pop, and the previous version had it too. Fix:
  - Drive each piece by where its edge lands on screen.
  - Pace the uncovered area so it falls at an even rate: coverage ∝ (1 − trapezoid(t))^0.6.
  - Run it over ≥ 10-12 frames, front layer first.
  - That brought the worst ratio to 1.7×.
- **Open onto the footage through the same material:** an RGBA cloud pass composited over the next
  shot. It thins in layers, a hole opens on the face first, and focus racks onto the subject. No
  black, no hard cut.

## 6. Process that kept it on track

- **Test renders are cheap; full renders are not.** Use a LITE mode (25% res, 8 samples, every 6th-10th
  frame) for camera-path sheets, then one full-res frame on each key beat. If LITE hides anything
  (fill rows, far buildings), print that on the sheet. One review lost a round to a LITE sheet that
  showed an empty grey floor.
- **Review gates before the full render:**
  1. A preview of any new texture or hero asset.
  2. Full-res frames on the stressed words.
  3. A sheet of the whole move.
  Each gate caught something the acceptance numbers didn't: drawn-line scaffolding, clipped clouds,
  a subject too small, a 20-frame white-out.
- **Acceptance checks for an agent building this:**
  - camera assertions (monotonic, roll/yaw/pitch)
  - no isolated frame-diff spike > 2.5× local median (`spikecheck.py`)
  - no near-black frames
  - key words land within ±3 frames of their beats on the final mix (`vo-beat-timing/scripts/beatcheck.py`)
  - a contact sheet the agent has actually looked at
- Re-render only the frame range you changed, keep the old frames, then recompose and re-check.

## Scripts
- `scripts/paper_cutout.py`: photo + mask → paper cut-out RGBA (+ its box in the frame).
- `scripts/log_lut.py`: Apple Log → filmic Rec.709 .cube (`--exposure`, `--film` 0-1). Swap the decode for
  other log curves.
- Shared: `../footage-transitions/scripts/spikecheck.py`, `../vo-beat-timing/scripts/beatcheck.py`.
