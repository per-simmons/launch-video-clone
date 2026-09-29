# Living stills: bringing a generated image to life without a video model

A generated plate is a still. The reference's picture usually isn't: rain slides, clouds drift,
screens glow, a flag ripples, light sweeps across metal. A clone that leaves those frozen reads as
"a photo with a camera move" even when every number is good. The global compare can't see it
(small moving detail barely changes distance), so this needs its own pass.

The same recipe works for anything. Never start from "what effect is this" (rain, smoke,
fireflies...). Start from **what kind of motion** it is, because there are only a few.

## 1. Find what's alive

```bash
python3 $S/alive.py map reference/ref.mp4 <a> <b> reference/alive-<shot>.png
```

It removes the camera move and shows what still changes, in orange. Coded UI that animates will
light up too; ignore it. You're looking for heat on the parts you plan to make from a still:
backgrounds, photos, product surfaces, skies. Tile every frame of those areas (sheet.py on a crop)
and describe the motion in numbers: how many things move, how big, how fast (px/frame), which
direction, what rhythm (steady, bursty, looping, random), how long anything persists.

## 2. Sort each living part into a motion kind

| Kind | Looks like | Build it in code as | Measure |
|---|---|---|---|
| **Camera** | whole plate shifts, zooms, parallax between near and far | transform on the plate; for depth, split into 2–4 layers (gpt-image edits: plate with / without foreground) or a depth map, and move layers at different speeds | pan px/frame, zoom %, layer speed ratio |
| **Flow** | continuous drift with no separate objects: clouds, fog, smoke, steam, water surface, fabric, aurora | shader warps the plate's pixels along a slow noise field (masked to that region); loops or drifts at a measured speed | drift px/frame, warp amplitude px, scale of the swirls |
| **Particles** | many small separate things: rain, snow, dust, sparks, bubbles, confetti, birds, stars | seeded particle system drawn over the plate (canvas or shader), each with measured size, speed, direction, spawn rate, lifetime | count, size, speed, spawn rate, trail length |
| **Light** | brightness changes, nothing moves: flicker, glow pulse, shimmer, glints, a highlight sweeping across metal or glass, bokeh twinkle | multiply/add a mask over the plate: pulse curves, a moving gradient band for sweeps, noise for shimmer | period (frames), peak brightness change, sweep speed |
| **Lens** | the picture bends: water drops on glass, heat haze, ripples, frosted glass | shader samples the plate with an offset (refraction), per drop or per noise field | size, distortion amount, how many |
| **Articulated** | a body or mechanism moving: a person walking, a horse galloping, hands, a machine | code can't fake this convincingly. Split the part out (gpt-image: with/without it), animate it as puppet pieces if simple; otherwise it's the one case for image-to-video | — |

Most living stills are 1–3 kinds stacked (rain on glass = particles + lens + light).

## 3. Build it the house way

- Everything is a function of the frame number and a fixed seed. No clock, no live randomness,
  so every render is identical and a fix doesn't move anything else.
- Isolate the living part with a mask so the rest of the plate stays put. If the plate needs the
  part removed or separated, make that with a gpt-image edit of the same plate ("reproduce this
  exact image with the X removed").
- Keep coded UI on top and untouched.
- Escalation ladder, cheapest first: camera → light → flow → particles → lens → puppet →
  image-to-video. Go to a video model only for articulated motion or when three code attempts
  fail the numbers below; say so in LOG.md.

## Recipes that worked

- **Moving light on a still (dappled sun, window shadows), a Light kind:** split the plate's own light
  pattern out as a log band-pass (`lightmap.py`, keep objects that must not move out of it), then in a
  shader `plate * exp(k * (bloom * M(uv + warp) - M(uv)))`: the wood grain stays put and only the
  light moves. Keep the gain grey, no warm tint. (Granola desk: change 19% vs reference 31%; push the
  warp further next time.)
- **A phone or screen inside a photoreal plate:** generate the plate with the screen switched OFF
  (black), register the plate to the reference by the screen geometry (`platefit.py`: 4 corners for an
  angled phone, the black body bbox for a top-down one), and composite the real UI in code with a
  homography (CSS `matrix3d`) onto the measured quad. Never let the image model draw the UI.
- **A person on a video call:** generated stills, the moving part (a waving hand) on its own layer,
  plus slow drift. It reads as alive at thumbnail size; it won't pass as footage up close.
- **Film grain:** measure its amplitude (std of image minus a σ2 blur in a flat region) and check with
  `alive.py stat` whether it changes frame to frame before animating it.

## 4. Check it with numbers for that region

```bash
python3 $S/alive.py stat reference/ref.mp4 <a> <b> x,y,w,h
python3 $S/alive.py stat "$R/vN.mp4"      <a> <b> x,y,w,h
```

Pick a region where the living part shows and nothing else animates. `change%` (how busy) and
`detail` (fine texture from drops, grain, sparkle) should each be within ~15% of the reference.
Too low: still dead. Too high: overdone (a common first result). Then look at the frame pairs:
the numbers say how much, your eyes say whether it looks like the same stuff.

## Examples so far
- Grok 4.5 weather shot, rain on glass = particles + lens + light: WebGL2 shader, ~200 seeded
  static drops, 30 stick-slip sliders (~7 px/f avg, bursts ~15 px/f), thin dark wiggly trails, each
  drop refracting a flipped sharper copy of the background, slight bokeh shimmer. Right margin
  f590–640: change 0.67% (still) → 1.79% (rain) vs 1.25% reference, so the first version was
  overdone: fewer or slower sliders next.
