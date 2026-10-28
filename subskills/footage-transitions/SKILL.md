---
name: footage-transitions
description: Transitions between live-action footage and motion graphics (or between two footage shots through graphics) that never go to black and never pop - iris and dot holds on the right person, in-scene transitions (clouds, paper, light), motion-blurred push-ins on a word, match cuts onto real screens, whip pans and material wipes, each landed on a steady destination frame with the audio J-cut under it. Includes how to present options (4 in-context variants on one review page) and a frame-diff spike check. Use whenever a hybrid video changes shot through an effect, or when asked "what other transition options do we have".
---

# Footage ↔ graphics transitions

A transition in a hybrid video has two jobs: carry the viewer's eye to the next thing, and never
break the illusion with a pop, a black frame or a wrong target. `scripts/` sits next to this file.

## Rules (each one from a rejected version)

- **Never go to black.** An iris that closed to black was rejected twice. Keep picture alive through
  the change: a dot that holds on the subject, a cloud, a light leak, a paper sheet.
- **Live inside the scene.** The camera climbs into the same sky the logo hangs in; the cloud that
  hid the logo opens on the face. A crumple, a page-turn or a cut to a new card reads as a template.
- **The right target.** An iris centred on frame centre landed on a stranger. Track the person (face
  or head) per frame, smoothed, and centre every iris, push and dot on the track.
- **Iris:**
  - soft feather (40-60 px at 1080p)
  - eased 16-22 frames (a 10-frame iris was "too fast")
  - when the subject is small in a crowd, close to a dot on their head and hold it a beat before
    opening
  - dissolve dot-to-dot between shots
- **Push-in on a word:** the scale peaks on the stressed word, with real motion blur (average 8+
  sub-frame renders across the shutter). A CSS or Gaussian blur doesn't read as camera motion.
- **Land on a steady frame.** Find where the destination shot settles: the hand stops, the phone is up,
  the camera stops moving. Enter there, even if it's later in the clip, and J-cut the destination's
  audio under the transition so the line still starts on time. In one build, entering at 15.5 s
  landed on a phone still moving; entering at 17.8 s landed clean.
- **Match cut on content beats morphing objects.** Let a UI result card's thumbnail settle exactly
  onto the real phone screen showing the same content, then dissolve. Morphing the card into the
  phone's shape was rejected.
- **Seams between renders or sources** (footage → render, render A → render B): check the diff at the
  seam. If it spikes, crossfade 3-4 frames, or photo-match the render's camera to the frame.

## When asked for options

Render **four, different in kind**, never four flavours of one idea. For example:
1. a match cut through content (UI preview → the real screen)
2. a graphic bridge (dots/particles that become the destination's content, kept clear of the subject)
3. a camera move (an eased whip pan with real motion blur)
4. a material wipe (a torn paper print of the destination's content sliding across)

Each is a ~5-6 s clip **in context**: ~2.5 s before, the transition, ~2.5 s after. It's graded like the
cut and has soft sound. Put them on one review page with a one-line description each, viewable from a
phone (publish the page; don't hand over a file path). Reviewers pick from motion, not descriptions.

## QA

- `scripts/spikecheck.py VIDEO --cuts <intended hard cuts>`:
  - **isolated spikes:** single frames > 2.5× the local median frame diff. These are the pops viewers
    feel. Must be zero.
  - **bursts:** a few consecutive hot frames (a whip, an iris). Check them on a full every-frame sheet.
  - **darkest frame:** flag mean luma under 18 unless black is intended.
  - **A/V length gap.**
- It caught a known one-frame pop (7.2×) in an earlier version and passes the fix. Grain raises every
  diff equally, so it works on the final encode.
- Then look at every frame of each transition on a sheet (`sheet.py` in the parent skill's
  `scripts/`).

## Scripts
- `scripts/spikecheck.py`: per-frame diff curve, isolated spikes vs bursts, near-black frames,
  container check.
