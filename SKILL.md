---
name: launch-video-clone
description: Make product-launch / motion-graphics videos in HyperFrames, in two modes. ORIGINAL (no reference): pick a category from the type files and build a launch video from scratch with the skill's motion rules. CLONE: rebuild a reference video as closely as possible — same shots, timing, easing, transitions and type — in HyperFrames, optionally re-skinned for a different brand. Opus can't watch video, so a burst-frame analyzer turns the reference into per-shot frame sequences, motion trails, easing curves and beat maps it CAN read, and a compare tool grades each render against the reference frame for frame until they match. Raster imagery comes from an image model (gpt-image or similar). Has one type file per kind of motion (UI showcase, abstract 3D diagram, 3D product, editorial collage). Use when the user says "make a launch video for <product>", "launch video for this release", "clone this launch video", "recreate this motion video", "make one like this for <brand>", "get as close to this as possible", or drops an X/YouTube link to a launch video and wants it rebuilt.
---

# Launch Video Clone

**Two modes. Pick one before anything else.**
- **Original** (no reference video): you are making a launch video for a product from scratch.
  Go to **Original mode** below. It uses the type files, `references/motion-feel.md` and steps 3-7
  of this file, and skips the cloning steps.
- **Clone** (a reference video is given): everything below, starting at *Pick the type file first*.

In clone mode, you are rebuilding a reference video, not "making something in its style". The target is a
side-by-side where a viewer has to look twice. Every decision (shot length, when a word lands,
how a shape settles) comes from the reference, measured, never from taste.

**Why this skill exists.** Out of the box, Opus 5.5 makes the generic AI motion look: sliding
text, a few safe fonts, everything eased the same way. The good ones on X all got there the same
way, by studying a real reference shot by shot and fixing timing and easing by hand over dozens
of passes (see *What the corpus says* below). This skill turns that into a loop you can run.

## Pick the type file first

Every clone uses this whole file. Then read the ONE type file that matches the reference: it
holds the build approach, the traps and what past clones learned for that kind of motion.

| Type | Looks like | File |
|---|---|---|
| Product UI showcase | App windows / UI states floating over an abstract or dark background; typing, clicks, panels morphing (Raycast, Glaze, most SaaS launches) | `types/ui-showcase.md` |
| Abstract 3D diagram, one take | Lines, rings, nodes, mono labels in 3D space; one continuous camera; depth of field and glow (Linear Loops) | `types/abstract-3d-diagram.md` |
| Photoreal 3D product | A physical product rendered in 3D: materials, studio light, close-ups, exploded views (keyboards, phones, headphones) | `types/3d-product.md` |
| Editorial collage | Paper, desk, photos, stills and UI cards composed on a surface; half the shots are footage (Kimi K3) | `types/editorial-collage.md` |
| Liquid-glass UI | Apple-style glass pills, sheets, menus, docks and widgets morphing into each other over wallpapers/photos (Bricks Dept) | `types/liquid-glass-ui.md` |
| Kinetic type into UI | The headline is built from the product's own pixels (game cells, keys, tiles), then the camera pulls back to the real app (Devin in Teams) | `types/kinetic-type-into-ui.md` |

**Also read, for every clone:** `references/motion-feel.md` (why motion looks "AI" and how to
measure and fix it; every reviewer note on a finished clone so far was about this) and, if any shot
is built from a still image, `references/living-stills.md`.

If nothing fits, use the closest one and say so in LOG.md. Every clone ends with step 7 (Teach the
skill): lessons go in the project's LESSONS.md, and the orchestrating agent merges them into the
type files and references.

## 0. Project layout

```
<project>/                       (in the repo — small files only)
  reference/ref.mp4              the video being cloned
  reference/analysis/            burst.py output for the reference
  BREAKDOWN.md                   your shot-by-shot spec (step 2) — the build contract
  assets/{fonts,brand,gen,refin} fonts, real logos, generated plates, reference frames fed to gpt-image
  hf/                            the HyperFrames project (step 4)
  LOG.md                         one row per round: what changed + the compare numbers
<RENDERS>/                       OUTSIDE THE REPO, on a disk with room, e.g. ./renders (gitignored) or an external drive
  vN.mp4, vN-analysis/, vN-compare/, vN-side-by-side.mp4
```

Renders never go in the repo. HyperFrames writes one PNG per frame as scratch **next to
`--output`**, so renders need a lot of free disk. Always render to `<RENDERS>`.

Scripts: `S="$SKILL_DIR/scripts"`, where `SKILL_DIR` is the folder this SKILL.md lives in
(e.g. `.claude/skills/launch-video-clone` in your project).
- `burst.py` analyze a video · `sheet.py` every frame of a range · `compare.py` grade a render
- `round.sh <project> <RENDERS> vN [fps]` render → analyze → compare in one go, appends to LOG-numbers.txt
- `sbs.py ref.mp4 clone.mp4 out.mp4` labeled 16:9 side-by-side for review
- `alive.py map|stat` find what moves inside a still, and measure it (see references/living-stills.md)
- `camtrack.py` (ECC, one-takes) / `camtrack_sift.py` (feature tracking, cut shots with moving content) / `gridcam.py` / `bboxcam.py` measure a camera · `rectrack.py` / `cursortrack.py` track an element / a cursor · `platefit.py` register a plate to a phone/screen shape · `lightmap.py` moving light on a still · `gradfit.py`/`gradrender.py` rebuild a blurred mesh gradient · · `framediff.py` per-frame diff + lag · `inkspan.py` text sizes · `fitplate.py` fit a gpt-image plate · `blurfit.py` · `fadecurve.py`
- `track.py` + `trackcheck.py` per-object pose (homography/similarity), validated · `export_tracks.py` · `round_mb.sh` round.sh with real motion blur · `bgfield.py`/`bgcurve.py` drifting gradient backgrounds · `colormatch.py` match a plate to the reference · `prep_refin.py` clean reference frames for gpt-image · `pair.py` · `wordtime.py` per-word typing times · `sheet.py ... x,y,w,h` crops
- `eleven.py` (ElevenLabs music + SFX, frame-exact placement) · `soundcheck.py` (grade the sound) · `listen.py` (Gemini ears)

## 1. Get the reference and make it readable

```bash
yt-dlp -o "reference/ref.%(ext)s" "<x.com or youtube url>"      # X posts work without login
python3 $S/burst.py reference/ref.mp4 reference/analysis
```

Then **read, in this order, all of it:**
1. `ANALYSIS.md`: fps, duration, shot table, BPM, how many cuts sit on an audio onset.
2. `overview.png`: the whole edit, one frame per shot.
3. For **every** shot: `burst.png` (or `burst_NN.png`, one per 2 s window on long shots),
   `cut_in.png` (every frame across the cut: this is where transitions live), `trail.png` (older
   frames fainter: direction and spacing of the main move), `curve.png` (motion energy per frame:
   its SHAPE is the easing).

Reading the curve:
- peak early, long tail → ease-out / decelerate into place (most UI and type entrances)
- peak late, sharp drop → ease-in / accelerate out (exits, whip transitions)
- symmetric hump → ease-in-out (camera moves, morphs)
- second smaller hump after the main drop → spring overshoot; count frames between humps
- flat near zero → a hold. Holds matter as much as moves; copy their length exactly
- red lines = audio onsets. If peaks sit on them, the reference animates to the beat and so must you

**Hidden cuts.** burst.py misses cuts between two similar frames (white UI to white UI, a push to a
tighter framing of the same screen). Run sheet.py across every sudden jump in scale or position and
list any hidden cuts in BREAKDOWN.md by frame (Granola: 2 of 7 cuts were white-to-white), and grade
with `compare.py ... --cut-list <all cut frames>` so they're checked too. For dark
UIs try `--spike-cuts`. If ANALYSIS.md says **CADENCE: animates on 2s**, quantize every motion
channel to the pair cadence (Granola: 25 fps motion inside a 50 fps file).

**Never describe a moment from one frame.** "Shots" are hard cuts only. Morphs, wipes and
match-moves don't register as cuts, so one shot can hold several scenes. For any moment the burst
skips over (a letter stagger, an overshoot, a transition), tile every frame of it:
`python3 $S/sheet.py reference/ref.mp4 <a> <b> out.png` (absolute frame numbers, same as burst).

**One-take zoom or pull-back? Measure the camera first.** Energy curves say when the camera moves,
not where it is. `camtrack.py` chains a scale+translate camera; refit every frame to an absolute
ruler with `gridcam.py` (grid lines, keys, tiles) or `bboxcam.py` (a rigid flat-coloured object),
because chained registration drifts (Devin: 3% scale at 12x). Write cam.json; the composition reads
it directly. For one-takes, BREAKDOWN.md can point at data tables (cam.json, fade tables) and keep
prose to the beats.

**Measure, don't eyeball, sizes.** In the Kimi clone, most look fixes in rounds 1–2 were sizes
guessed 20–40% too small. Before building, pull full-resolution reference frames
(`ffmpeg -i ref.mp4 -vf "select=eq(n\,F)" -frames:v 1 f.png`) and measure the boxes that matter
(window rects, type cap-height, pill heights, corner radii) with numpy (difference from the
background colour → bounding box). For text, `inkspan.py` measures each string's ink box in the
reference and your render: set font-size from the height ratio, tracking from the width ratio
(Devin: eyeballed sizes were 1.6–7.5% off). Write the pixel numbers into BREAKDOWN.md.

## 2. Write BREAKDOWN.md (the build contract)

Global header: resolution, **exact fps** (29.97 is `30000/1001`, not 30), total frames, BPM and
the beat grid in frames (`60fps @ 120bpm = a beat every 30f`), the colour tokens (named hexes), the
type system (family or closest free match, weight, case, tracking, measured sizes), recurring
chrome (HUD corners, counters, grain, vignette, chromatic fringe).

Then one block per shot (or per 2 s window of a one-take), frames not seconds:

```
## Shot 3 — f118–209 (92f) — "CLAUDE" wordmark on red disc     [CODED]
In:  iris wipe from shot 2, red disc grows from centre f115→f122, purple/orange fringe on the edge
Elements:
  - wordmark "CLAUDE", heavy extended grotesk, black, cap height 238px
      letters rise through a baseline mask, 1f stagger L→R, f117–f124, ease-out, no overshoot
  - hairline rule above, draws L→R f120–f126
Holds: f126–f200 static
Out: hard cut on the beat at f210
```

Tag every shot **[CODED]** (built in code: type, UI, shapes, 3D-in-code) or **[RASTER]** (needs a
generated or real image/footage: live game capture, photoreal product, photography). They get
different targets in step 5. Write "UNSURE" where you are and check those first in round 1.

## 3. Assets

**Fonts.** HyperFrames lint wants a local file for every named font. Identify the reference's
family (or the closest free match) and download TTFs into `assets/fonts/`, e.g.
`https://github.com/google/fonts/raw/main/ofl/<family>/<File>.ttf`. Declare them with `@font-face`.

**Logos and brand marks: real files only, never generated.** Sources in order: the brand's own site
first (`<site>/favicon.svg`, inline SVGs on the homepage, press kit), because icon sets lag rebrands
(lobehub still shipped Devin's old mark; the old SpaceX X came from an icon set too), then `https://unpkg.com/@lobehub/icons-static-svg/icons/<brand>.svg` (and
`<brand>-text.svg`, good for AI companies), simple-icons, or `npx hyperframes capture <url>`.

**UI components: 21st.dev.** For product UI (buttons, inputs, cards, command palettes, sidebars),
start from 21st.dev components instead of inventing UI: they're built by design engineers and
avoid the wrong-spacing, placeholder-box look. Install once in Claude Code with
`npx @21st-dev/cli@latest` (free daily allowance, needs a 21st.dev account; if it isn't set up,
say so in LOG.md and hand-build instead). Browse at 21st.dev, adapt the markup into the composition.

**Raster via an image model** (gpt-image or similar) for things code can't do: photoreal
products, photography, live game footage. Use whatever image generator you have that accepts
reference images, e.g. the OpenAI Images API edit endpoint with `gpt-image-1`:

```
<your image generator> "<prompt>" --size 1536x1024 \
  --input-image assets/refin/f0064.png [--input-image logo.png] -o assets/gen/<name>.png
```

- Feed the matching reference frame as `--input-image` to hold composition and light.
- **Clean the reference frame first.** Remove on-screen labels/chips/captions (ffmpeg `delogo`, or
  crop) or the model paints them into the plate and you'll draw them again in code.
- **Headroom for camera moves.** Plates come back 1536x1024; zooming past ~1.25x goes soft. For a
  push-in, generate the tighter framing separately.
- **Two plates beat animating one.** For something that leaves the frame (a hand, a tool), make
  the plate with it, then an edit of that plate with it removed ("reproduce this exact image but
  with the hand removed"), and animate the top layer off. Worked first try on Kimi.
- Every plate: flatten any alpha channel (an RGBA plate turned to garbage as JPEG), then colour-match
  it to its reference frame with `colormatch.py` and keep the match only if that shot's distance drops.
- If gpt-image ignores the reference framing, don't regenerate: fit the plate with `fitplate.py`
  (searches scale/offset/colour against only the reference pixels the plate shows, edge-extends so
  it can shrink). If two visible bands still disagree, split the plate at a seam the UI covers.
- If the model adds something your code also draws (a UI panel, a label), cover it in code or
  regenerate.
- It's reliable: 28/28 succeeded first try in 21–55 s. Run 4 in parallel from a small jobs script.
- Don't put hex codes or negated nouns in the prompt; the model draws them.
- **Stills are usually alive in the reference.** Run `alive.py map` on every shot you're building
  from a plate. Anything that moves on its own (rain, clouds, glow, shimmer, water, particles)
  gets the living-stills pass in `references/living-stills.md`: sort it into a motion kind
  (camera, flow, particles, light, lens, articulated), build it in code from measured numbers,
  check it with `alive.py stat`. A video model is the last rung, for articulated motion only.
- A generated still of live footage reads as a render, not a capture. Add the capture artifacts
  in code: debug HUD text, a cursor, compression softness, motion blur on the camera move.

## 4. Build in HyperFrames

Read `/hyperframes` and `/hyperframes-core` before writing anything. Match the reference fps exactly.

**Default pattern: one `index.html`, one `draw(frame)`.** It worked first try on a 29-cut clone and
kept every fix to one line:

```js
const FPS = 30000 / 1001;                 // the reference's exact fps
const SHOTS = [                           // absolute reference frame numbers from BREAKDOWN.md
  { el: "s1", a: 0,  b: 9 },
  { el: "s3", a: 64, b: 211, draw(f) { /* position everything as a pure function of f */ } },
];
function draw(t) {
  const F = Math.floor(t * FPS + 1e-6);
  for (const s of SHOTS) { const on = F >= s.a && F <= s.b; show($(s.el), on); if (on && s.draw) s.draw(F); }
  // elements that span several shots (a chat box, a label chip) get their own ranges here
}
const P = { t: 0 };
const tl = gsap.timeline({ paused: true });
tl.to(P, { t: DURATION, duration: DURATION, ease: "none", onUpdate: () => draw(P.t) }, 0);
window.addEventListener("hf-seek", (e) => draw(e.detail.time));
draw(0);
window.__timelines["main"] = tl;
```

Use sub-compositions only for a long self-contained section. Keyframe helpers (`kf(f, [[f0,v0],[f1,v1]], ease)`),
closed-form springs and seeded noise make every value a function of the frame.

Motion rules that make it look designed rather than generated:
- Everything is a pure function of the frame. No CSS transitions, no timers, no state carried
  between frames. That's what makes renders deterministic and fixes repeatable.
- Closed-form springs with small overshoot for anything that settles; if a value retargets, sum
  one spring per change. Match overshoot frame counts from the curve.
- Content enters after its container starts moving and leaves before the next move.
- If the reference has motion blur (smeared frames in the burst), render with `round_mb.sh` (fps×N,
  subframes averaged). Pick the visible shot from the integer output frame so hard cuts stay hard. Don't fake
  it with a CSS blur filter.
- Stagger, fringe, grain, HUD chrome: the small stuff separates a clone from "inspired by". It's
  in the cut_in and sheet.py sheets. Build it.
- Search `npx hyperframes catalog --query "<the move>"` before hand-writing a common move.

Audio: the reference track is for timing only while cloning. A delivered rebrand needs its own
music on the same beat grid.

## 5. Render, compare, fix. Repeat.

```bash
$S/round.sh <project> ./renders v1          # or any path outside the repo with plenty of free disk
```

Before round 1, check the look without a full render:
`npx hyperframes snapshot --at <key seconds> --against ../reference/ref.mp4 --describe false -o "$R/snap1"`.

Read `COMPARE.md`: the global numbers, then the **per-shot table** (distance, motion correlation,
peak offset in frames, motion ratio). Then `energy.png` (green reference vs red clone), then every
`pairs_*.png`, then the clone's own sheets next to the reference's for each transition.

Fix in this order, because each one moves the ones after it:
1. **Structure**: shot count and cut times, every cut within 2 frames.
2. **Timing**: per-shot peak offset → 0 (energy peaks on the same frames).
3. **Easing**: per-shot motion correlation up, motion ratio near 1.0.
4. **Look**: type, colour, scale, position (pairs + distance).
5. **Detail**: fringe, grain, blur, chrome.

**Targets differ by tag.** [CODED] shots can converge: aim for distance under ~0.05, motion corr
over ~0.8, peak offset 0–1f. [RASTER] shots can't be pixel-matched: aim only for cut timing,
framing and camera energy (motion ratio ~1), and don't spend rounds on them once those hit. Mean
distance across a video that is half raster will stall around 0.10; that's the plates, not you.

Log each round in LOG.md (what changed, the numbers). Stop when every [CODED] shot hits its
target and every [RASTER] shot hits its timing, or after 6 rounds; then report what's still off.
The last check is always looking at the pairs, never just the numbers.

**Every object that moves gets a measured pose.** `track.py` from its flat anchor frame, validated
with `trackcheck.py` before you build on it; homography only for objects with 2D texture, centre +
uniform scale for thin strips and plain plates. A quiet window with low motion correlation usually
means a missing background drift: check `bgcurve.py` before touching the foreground.

**When every window is on target, go per frame.** The 2 s windows hide the last problems (Devin:
all windows at 0.99–1.00 from round 1; the real errors were a 0.6 px board offset, a one-frame blur
step and a desktop riding the camera). Run `framediff.py ref.mp4 "$R/vN.mp4" [A B] --lag` and read the
per-frame table. A constant edge offset across zoom levels = the object is misplaced; nudge the
object, not the camera. `blurfit.py` fits a blur-to-end-card, `fadecurve.py` measures fades while
the camera moves. Compare at draft quality; the delivery encode scores ~+0.003 worse against a
compressed X upload, which is not a regression.

The side-by-side for review (quote `'0:a?'` or zsh eats it):

```bash
ffmpeg -i reference/ref.mp4 -i "$R/vN.mp4" -filter_complex \
 "[0:v]scale=952:-2,setsar=1[a];[1:v]scale=952:-2,setsar=1[b];[a]pad=960:ih:0:0[a2];[b]pad=960:ih:8:0[b2];[a2][b2]hstack=inputs=2,pad=1920:1080:0:(1080-ih)/2:black[v]" \
 -map "[v]" -map '0:a?' -c:v libx264 -crf 17 -pix_fmt yuv420p "$R/vN-side-by-side.mp4"
```

That's a 16:9 frame that drops straight into an edit. Label the halves (REAL / CLONE) by compositing a
transparent PNG made with PIL over it (`sbs.py` does this): many ffmpeg builds have no `drawtext`.

## 6. Sound (ElevenLabs makes it, the numbers grade it, Gemini listens)

A pure clone keeps the reference's audio. A rebrand, or any new visuals, needs its own music and
sound design. First real run: Grok 4.5, 2026-09-27, 4 sound rounds, every number passing
(47/47 sounds within 1 frame, -13.9 LUFS). Worked scripts from that run are in
`references/examples/grok-sound/` (project-specific numbers inside; copy the approach, not the values).

1. **Map the reference's music from the WAVEFORM, then let Gemini describe it.** Gemini's cue sheet
   got the Grok structure wrong by up to 11 s (dip at 19 s not 30 s, drop at 33 s not 5 s, 100 not
   120 BPM). Measure sections yourself (RMS per section in dB, the onsets in ANALYSIS.md, tempo from
   onset spacing), use `python3 $S/listen.py cue reference/ref.mp4` only for character (instruments,
   feel, which sounds are whooshes vs chimes), and correct SOUND.md to the waveform.
2. **Music (ElevenLabs):** `eleven.py plan "<brief>" --ms <len>`, edit the section durations to the
   measured structure, `eleven.py music --plan ...`. ElevenLabs follows the section BOUNDARIES but not
   the DYNAMICS (a "sparse" section came out 14 dB louder; no hard stop). So **shape it afterwards**
   to the reference: per-section gain to the reference's measured section level, filter the dips,
   cut hard stops with a short reverb tail (example: `shape_music.py`). If the palette or low end is
   still wrong after shaping, regenerate with a sharper brief; shaping can't fix the track itself.
3. **Sound effects (ElevenLabs), picked by taste:** 2–3 variants per sound
   (`eleven.py sfx "<concrete description>" -d 0.8 -o assets/sfx/x.mp3 -n 3`), best by
   `$S/soundcheck.py rank assets/sfx/x-*.mp3`.
   - **Typing and other repeated sounds: never one long loop.** Build them from single keystrokes
     placed on the composition's own per-character frames (example: `tracks.py`). Same for any
     series (one clack per landing card). Loops cut short can't be synced or checked.
   - Ambience beds (rain, wind, room tone) aren't events: keep them out of the sync check (beds.json).
4. **Place to the frame:** `sound/events.json` (frame from YOUR breakdown, label, sfx, anchor:
   "peak" for whooshes/swells/hits, "start" for clicks/keys) → `eleven.py place sound/events.json --fps <fps> -o sound/placed.json`.
   The loudest moment lands 15 ms before its frame (sound files start in silence; two whooshes from one
   prompt peaked 160 ms and 629 ms in).
5. **Into the composition:** write the music + every placed sound as `<audio>` elements with
   `data-start`, `data-duration`, `data-media-start`, `data-volume`, one track index per layer
   (example: `inject.py`). Starting points: music ~0.7, effects ~0.35.
6. **Grade and loop:** `$S/soundcheck.py check "$R/vN.mp4" --placed sound/placed.json --fps <fps> --ref reference/ref.mp4 --listen`
   → SOUND-CHECK.md (loudness, true peak, clipping, every sound found in the mix by waveform and
   graded ±1 frame, Audiobox taste scores clone vs reference, Gemini's critique). Fix every FAIL and
   the listener notes that the waveform confirms; max 4 rounds. The listener is advisory: it asked
   for a rocket flyby that isn't in the reference and called a -36 dB ending "silent".
7. **Loudness, last:** two-pass loudnorm to -14 LUFS, THEN a true-peak limiter; two-pass alone pushed
   the peak over -1 dBTP:
   `ffmpeg -i in.mp4 -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:linear=true,alimiter=limit=0.84" out.mp4`
   (first pass: `-af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null -`).

A human listen is the final check. `soundcheck.py` runs in the project's `.venv-sound` (see README:
`.venv-sound/bin/python $S/soundcheck.py ...`); `listen.py` uses Gemini 3.1 Pro, falling back to
3.8/3.5 Flash when Pro is out of quota; never 2.5. Both keys come from the environment only.

## 7. Teach the skill (every clone ends here)

This skill gets better only if each clone leaves behind lessons the next one can use. Before you
report, write `<project>/LESSONS.md` in exactly this shape:

```
## Lessons
- RULE: <a behaviour, "do X" / "never Y", that would help a DIFFERENT clone of a DIFFERENT video>
  EVIDENCE: <the numbers: what it was before, what it was after, which window/shot>
  GOES IN: <SKILL.md §N | types/<type>.md | references/motion-feel.md | references/living-stills.md | scripts/<name>>

## Skill feedback
- GOT IN THE WAY: <what in this skill or its scripts slowed you down or misled you>
  FIX: <the concrete change: a flag, a script, a sentence to add or delete>

## Reviewer notes
- <anything the reviewer said about this clone, verbatim, and what it turned into>
```

A lesson qualifies only if it passes three tests:
- **General:** it would help on a different video. "Raycast's rows start 2 f apart" is an incident;
  "measure per-row stagger in frames, never share a start frame" is a rule.
- **Measured:** it has a before/after number, or a frame-sheet observation behind it.
- **Behavioural:** it tells the next agent what to DO. Descriptions of what happened don't count.

Put tools you had to write in `<project>/tools/` and list them under Skill feedback, with one line
on what each one does. Don't edit the skill's own files; the orchestrating agent merges lessons
into SKILL.md, the type files and the references, so parallel clones don't collide. Reviewer notes
always get merged: every one so far became a rule (see references/motion-feel.md).

## Original mode (no reference video)

Use this when you are asked for a launch video for a product and given no video to copy. The goal
is still a launch video that doesn't look AI-made, so the motion rules are identical. What changes
is where the decisions come from: the category's type file and measured donor numbers, instead of
one reference.


**Banned in Original mode (reviewer note, 2026-09-29): the generic AI launch-video look.** No
glassmorphism or frosted-glass panels, no floating cards sliding up from below, no gradient blobs,
no default fonts, and nothing that looks like a stock HyperFrames or Remotion template. The
`liquid-glass-ui` type is for cloning a reference that is actually built that way; never pick it
for an original. Test every shot: if it could appear in any AI launch video, redo it.

1. **Pick the category.** Read the product (launch page, UI, what it does) and choose the ONE type
   file whose "Looks like" row fits best (the table in *Pick the type file first*). A model/AI launch is usually `ui-showcase`
   (the product's own interface doing a real task) or `kinetic-type-into-ui`. A physical product is
   `3d-product`, and a research or brand story is `editorial-collage` or `abstract-3d-diagram`. Say
   which and why in LOG.md. Read that type file, `references/motion-feel.md`, and
   `references/living-stills.md` if any shot starts from a still.
2. **Take numbers, not pictures, from donors.** Find 1-3 real launch videos of the same category
   (the type file names examples; `references/corpus-prompts.md` and `references/examples/` have
   more). Run step 1's analyzer (`burst.py`) on them only to measure cut rhythm, easing curves, type
   sizes relative to frame, and how long a word holds. Write those numbers into BREAKDOWN.md as
   targets. Never copy a donor's shots, layout, copy or brand.
3. **Write the script before the shots.** Use this structure: the biggest outcome in the first 3
   seconds, no logo first, show and don't explain, then problem, solution, proof, CTA (see *What
   the corpus says*). Every claim comes from the product's own launch material. Real UI, real
   numbers, real names only. Keep it to 20-45 seconds unless told otherwise.
4. **BREAKDOWN.md from scratch**, same format as step 2: one row per shot, with frame ranges,
   what moves, the easing, the type and the on-screen text. Then make **3 storyboard variants**
   (one still per shot each), pick the strongest yourself if running unattended, and record why.
5. **Build, render and self-review** with steps 3-6 (assets, HyperFrames, render, sound). There's
   no reference to diff against, so `compare.py` runs against your own storyboard stills for
   layout. Motion is graded against the donor numbers from item 2 and the checks in
   `references/motion-feel.md`: vary the easing, no everything-slides-in-from-below, holds long
   enough to read. Do a separate review pass whose only job is to find the dead moment or the
   rhythm gap, then fix it.
6. **Ship** a 1920x1080 MP4 plus the HyperFrames project, and end with step 7 (Teach the skill).

## Rebrand mode

When you want the reference's craft on a different product: keep BREAKDOWN.md's structure, timing,
easing, transitions and chrome exactly. Swap only copy, colours, type family, logo and product UI
for the target brand's real ones. Before building, show **3 storyboard variants** (one still
per scene each) and let the user pick; fixing a still is cheaper than fixing a render. Compare still
runs against the reference: cut times and energy curves should still match even though the
pictures don't, so steer by timing numbers and expect a high distance.

## What the corpus says (public X posts, collected 2026-09)

The prompts and workflows behind well-known launch/motion videos, summarised with links in
`references/corpus-prompts.md`.

- **Tim Koch (224k views, Remotion):** about a day of prompting, and the first result was poor.
  10–20 messages per scene, ~30 parallel chats, and most of the effort went into timing and easing.
  He replicated small parts of reference videos, which is what this skill does in a loop.
- **Martijn Verbove (Opus 5.5):** one canvas, one `draw(t)`, no transitions/timers, closed-form
  springs, contact sheet one frame per beat before rendering, 60fps with 6 averaged subframes.
- **Zsolt Kacso (HyperFrames, Opus 5.5):** it took a second prompt making the model inspect its own
  render for rhythm and find the gap between the brief and the result. The self-review is what makes it good.
- **Moritz Kremb (84k, Opus 5.5 + HyperFrames):** pull real assets from the internet, don't invent.
- **Rexan Wong:** reference video + HyperFrames/Remotion + 21st.dev components + brand context,
  then 3 storyboard variants, one still per scene before anything moves, then director notes.
- **Adil / Higgsfield (408k):** one shot-list document, a name per shot, fixes target one shot.
- **Eddy (60+ viral launch videos):** biggest outcome in 3 s, no logo first, show don't explain,
  hook → problem → solution → proof → CTA. Use it when writing a rebrand's copy.
