---
name: word-synced-ui
description: Product UI overlays that type, send and respond in sync with a speaker's real words - a prompt box, chat, search or command bar composited beside the person on camera, each word appearing on the frame it is spoken, then the product's real working states (thinking, building, result) over continuing B-roll. Built in HTML/CSS as a pure function of the frame, rendered to RGBA in headless Chrome, and checked so nothing jumps. Use when a creator says a prompt out loud on camera, or any UI must follow live speech.
---

# Word-synced UI over footage

The person on camera says the prompt; a small, real-looking UI types it as they say it, sends it, and
the product visibly works while the video carries on. Every rule below came from a real build, and
`scripts/` sits next to this file.

## 1. Words and timing come from the take

- Run Whisper with word timestamps (`mlx_whisper … --word-timestamps True`, or openai-whisper) on the
  **exact audio that's in the cut**. Each word appears on its start frame. Put the word list in a
  config file (`[{w, f}]`) and leave the timing out of code.
- Typing text is what the person actually said, including their filler, unless the brief says to
  clean it. A prompt that doesn't match the voice reads as fake.

## 2. Look

- **Small, flat and straight-on, beside the speaker.** Not a tilted phone mockup, and not oversized.
  Both were rejected; a ~580 px card on a 1920 frame passed. Keep the speaker clear: put the card on
  the opposite side and check against a person track (Vision humans/faces, or SAM) on every frame.
- **The product's real UI:**
  - its font (woff2 from its site)
  - its colours and controls
  - its current wording for each state
  Research its current UI (docs, changelog, recent demo videos) and copy the state names and order.
  Don't invent features. Anything guessed (a file name, a label) gets listed in the report.
- A soft brand glow behind the card ties it to the footage. Keep it below the alpha threshold your QA
  uses, so it isn't measured as the card.

## 3. Layout that cannot jump (the main lesson)

A version pinned to its bottom edge pushed every typed line up 30 px whenever a word wrapped. A
reviewer saw it immediately as "an aggressive jump". The fix is structural:

- **Anchor the edge that must not move.** While typing, the top is fixed and the card grows downward,
  so placed words never move. After send, the bottom (the composer) is fixed and the thread stacks
  upward above it.
- **Lay the whole prompt out once, up front,** to know which word wraps to which line and on which
  frame. Then the height is a function of the frame, not of the DOM each frame.
- **Open each new line early and eased:** sine ease over ~12 frames, starting ~6 frames before the
  wrapping word appears.
- **Word entrance:** ≤ 5-6 px rise, ~6-frame smoothstep fade, a touch of blur. A 9 px out-cubic
  entrance read as punchy.
- After send:
  - the prompt lifts out of the box into a bubble
  - thinking (shimmer) → "thought for Ns" → work rows (editing → edited) → a result card
  - each item's slot eases open, so the items above glide instead of popping

Build it as one HTML page whose `setFrame(g)` positions everything as a pure function of the frame
(no CSS transitions, no timers). Render with Playwright/Chrome, `omitBackground: true` → RGBA PNGs,
after `document.fonts.ready`. Have `setFrame` **return rects** (card, words, thumbnails) so QA and the
compositor can find things.

## 4. Keep the story moving under the UI

When the speaker's read ends, don't freeze on them. Cut on the send tap to B-roll from the same
place, continuing the action (walking on, crossing back), while the UI thinks and builds:

- Pick a stretch where nobody blocks the lens. Measure it: the largest other person stays under ~15%
  of the frame, and the subject is tracked in 100% of frames.
- If the subject is talking in that stretch (another take), mute it. Lay room tone from the same take
  under it.
- 3-4 s covers thinking → result at a readable pace.

## 5. QA (numbers before eyes, then eyes)

- `scripts/uibbox.py FRAMES --alpha 200 --rects rects.json`:
  - every edge of the card moves ≤ 4 px per frame
  - settled words drift ≤ 1 px relative to the card
  - the jumpy version measured 123 px in one frame; the fixed one 4 px and 0.2 px
- Watch the overlay composited in context at full speed. Check the frame where each line wraps and
  the send.

## 6. Out of the UI

Hand off to the payoff with a transition from `../footage-transitions` (match-cut the result card's
thumbnail onto the real screen, a whip, a material wipe, a graphic bridge). Don't morph the card into
a physical object in the footage. That was rejected as "not good".

## Scripts
- `scripts/uibbox.py`: per-frame bbox of the overlay + settled-word drift; pass/fail.
