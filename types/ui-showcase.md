# Type: Product UI showcase

App windows, panels, inputs and UI states moving over a plain or abstract background. Typing,
clicks, a prompt turning into a built thing, panels morphing into each other. Most SaaS and AI
launches (Raycast/Glaze, Grok 4.5, Devin, Linear feature drops).

## What it's made of
- **Real UI, rebuilt in code.** Every window, button and card is HTML/CSS at the reference's exact
  pixel sizes. Never a generated image of UI (it comes back stretched and fake). For the product's
  own screens, capture them (`npx hyperframes capture <url>`) or rebuild them from screenshots;
  for generic components start from 21st.dev.
- **One background system** (a gradient, a dark liquid/chrome texture, flat white with faint grid).
  If it's a moving texture (Raycast's black liquid chrome), it's either a looping shader in code
  or a generated plate with slow drift. Check the burst sheets: if it moves on its own, it's a shader.
- **Typing is the heartbeat.** Prompts type in at a steady per-character rate, often with a
  blinking caret. Measure chars-per-frame from sheet.py, don't guess. Send-button press = the cut.
- **Windows travel as one piece**: scale + translate with a soft shadow, eased out, often with a
  slight 3D tilt (perspective + rotateX/rotateY) on the way in. Measure start/end rects.
- **Cursor**: real macOS arrow, moves on eased paths, clicks with a 2–3 frame scale dip.
- **Macro/micro rhythm**: wide establishing frame → push into one detail (the model picker, a
  button) → pull back. Those pushes are scale on a wrapper; get the origin right.

## Easing rule (reviewer note, 2026-09-27: "Raycast does a really good job of really nice, natural easing")
Premium UI launches never snap. Things settle over a long, soft tail with no overshoot, and many
things that look like they "fly in" are actually scaling down from near the camera.
- **Measure the settle, don't pick a preset.** Tile every frame of each entrance (sheet.py) and read
  the energy curve: count frames from first motion to fully still. Raycast's is ~30f at 30fps.
  If you can't measure it, err long: a 24f near-linear move with a 4f fade read as "snapping in".
- **Log-scale for scale moves.** Anything growing or shrinking by a big factor interpolates in log
  space: `s = S0 ** ((1 - t) ** 4)` over the settle (quartic ease-out). Linear scale from 8x to 1x
  looks like it lurches, then stops dead.
- **Scale about the frame centre** when the reference's elements sweep outward as they shrink.
  Per-element centres make them collapse in place instead.
- **Stagger in frames, measured**: Raycast staggers rows 2–2.5f, containers ~1f ahead of their
  content, chrome (header, banner) last. A shared start for everything reads mechanical.
- **Check it:** that window's motion ratio should be ~1.0 and peak offset 0. A ratio well under 1
  (0.25 here) means the clone moves too fast and settles too soon.

## Traps
- System fonts: macOS UI is SF Pro (not on Google Fonts). Use Inter at matched metrics, and say so.
- Blur-behind panels need `backdrop-filter`, which HyperFrames renders. Check it in a draft render
  before building ten of them.
- App content (movie posters, album art, avatars) inside windows is raster: gpt-image or real
  images, composited into the coded window, never part of a UI plate.

## Learned from clones
(append: date, clone, one specific lesson per line)
- 2026-09-27 Raycast/Glaze: 0:24 window stack-in was a depth cascade (7–9x → 1x about frame centre, log-scale quartic ease-out over 30f, 2–2.5f row stagger). Fix took that window from motion corr 0.79 / ratio 0.25 / peak +12f to 0.91 / 1.04 / 0f.
- 2026-09-27 Grok 4.5: 0.031 distance, 0.93 motion corr after 8 rounds. Logos from icon sets can be outdated (old SpaceX X): crop-compare against the reference. A full-screen layer hid the chat pill for 60f and the numbers barely moved; only the frame pairs caught it.
- 2026-09-27 Grok 4.5: the weather background was a live plate (rain on glass). Built in code, no video model: WebGL2 shader over the still, seeded static drops + stick-slip sliders (~7 px/f avg, bursts ~15 px/f) with thin dark wiggly trails, each drop refracting a flipped sharper copy of the background, frame-driven. Margin pixel-change 0.17% still → 0.41% vs ref 0.38%. The global distance number can't see small moving drops: measure a strip where the UI holds still.
- 2026-09-27 Raycast/Glaze (approved in review, v9): 18/18 cuts on the exact frame, motion corr 0.93, distance 0.031. burst.py found 3 of 18 cuts between dark UI frames: run it with --spike-cuts on dark UIs and confirm each cut on its cut_in sheet.
- 2026-09-27 Raycast: the "static" liquid-chrome background was footage (constant motion, one held frame every 10 f). One gpt-image plate per scene ("black rectangles are holes, continue the ribbons") + per-scene drift gain fitted to the reference's baseline motion lifted every quiet UI window (corr −0.2 → 0.3–0.56). One global drift value overshot (end card ratio 2.8).
- 2026-09-27 Raycast: gpt-image refuses "reproduce this exact movie poster"; "make a portrait film poster with this same composition" works, but it renames titles. Composite real titles in code when they matter.
- 2026-09-27 Raycast: panels passing under a glass sidebar: backdrop-filter renders fine in HyperFrames; don't clip the strip at the content edge.
- 2026-09-27 Raycast: entry opacity on big near-camera layers ≤2 f (a long fade dims the frames where the layer is biggest), except full-height panels, which need ~10 f or they spike energy before the reference moves.
- 2026-09-28 Devin/Teams: content inside a container (a video in a card, a screenshot in a window): measure container and content separately; containers often settle on their own (card 1.04 → 1.0 around a fixed video). Drawing the card at final size showed its edge 3 f early.
- 2026-09-28 Devin/Teams: measure a UI group's fade at its top AND bottom element; if they differ, drive a gradient alpha mask between the two curves, not one opacity (top row 50% at f193, bottom at f197; f195 distance 0.038 → 0.018).
- 2026-09-28 Granola ad: blurred mesh-gradient backgrounds rebuild well as K fitted Gaussian blobs per 4 f (gradfit.py / gradrender.py) on a small canvas upscaled with blur; blend neighbouring keys in PIXEL space, never interpolate the blob parameters.
- 2026-09-28 Granola ad: a reveal's white bbox tracks a soft fade tail that runs up to 30 f past the move. Time moves to the energy curve and track the element rect separately (rectrack.py). Measures on a display:none scene return 0: measure after the scene is visible and fonts have loaded.
- 2026-09-28 Granola ad: 8 rounds, 5/5 detected cuts on frame, motion corr 0.959, distance 0.033. Real 2025 wordmark came from the Wayback Machine (the current site shows a newer mark than the ad): match the logo to the reference's date.
- 2026-09-28 Granola ad: typed/written text (an email writing itself, a prompt typing) gets per-word timing measured from the reference, never a chars-per-second guess: `wordtime.py` warps frames into the camera anchor and tracks each line's leading ink edge. Words appeared almost fully black (first ink → black ≤ 1 pair); an 8 f fade read as late. Rebuilding all 70 word frames took that window corr 0.63 → 0.98.
- 2026-09-28 Granola ad: when a reference animates on 2s, the pair PHASE (odd/even frames) can flip mid-scene: measure it per window and match it, or motion lands a frame off.

