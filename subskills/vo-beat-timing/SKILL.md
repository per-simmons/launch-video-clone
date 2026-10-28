---
name: vo-beat-timing
description: Lock narration and on-camera speech to picture - a frame-numbered timing sheet before anything is built, temp TTS voice-over with word timestamps, picture events pinned to stressed words, J/L-cuts and room tone for real takes, soft sound design placed on frames, and verification on the FINAL mix with Whisper (±3 frames). Includes a safe audio mix pipeline (no hung ffmpeg) and loudness landing. Use for any video where voice drives the edit - hybrid footage + graphics pieces, sponsor reads, explainers, launch videos with VO.
---

# Voice-over and beat timing

Most notes on hybrid edits are timing notes: a pause that drags, an effect a beat late, a reveal
before its word. Fix that with one source of truth in frames, then verify on the mix. `scripts/` sits
next to this file.

## 1. The timing sheet comes first

Before building anything, write `TIMING.md`: one row per beat with **frames | picture | sound / VO**.
Pin every VO line's start frame and the frame of each stressed word inside it. Then hang picture
events on those words:
- freeze on the number
- the reveal on the brand name
- the push-in on the adjective
- the stat on its noun

Code reads its constants from this sheet. When a section grows, shift every downstream constant by a
single offset in code (`S = 19`) instead of retyping numbers, and re-verify.

## 2. Temp voice-over

- Use TTS with timestamps (e.g. ElevenLabs `with-timestamps`), so word frames are known before the real
  record. Keep one voice per piece.
- **Lines run back to back:** ≤ ~0.25 s from one line's speech end to the next line's start, unless a
  pause is a deliberate beat. Dead air between lines was the most repeated note.
- When the creator records the real lines, swap them in and re-run the word timing. The sheet stays,
  and only the frames move.

## 3. Real takes

- **J-cut / L-cut** the speaker's audio across transitions, so speech starts on time while the picture
  is still changing.
- Under B-roll from a take where they're talking about something else, mute it and lay **room tone
  from the same take**. Room tone from elsewhere sounds pasted.
- Speech that drives an on-screen UI (`word-synced-ui`) gets its word frames from the same audio that's
  in the cut.

## 4. Sound design

- Soft and low: foley (paper, cloth, taps, a soft thud on a landing) 20-34 dB under the voice. Stingers
  and loud whooshes were called aggressive.
- Every effect sits on a frame from the sheet. Whooshes and hits anchor on their **peak** (land the
  peak ~15 ms before the frame); clicks and taps anchor on their start.

## 5. Mixing without hangs

A final mix sat at 0% CPU for an hour; later mixes hit their alarms. The same graph ran in 0.1 s by
hand. The cause: an unbounded `apad` in a graph that also decoded camera-original MOV audio never
reaches EOF, and an output `-t` did not save it. `scripts/placemix.py` encodes the safe pattern:

- extract every source (camera MOVs included) to WAV first
- bound the pad (`apad=whole_dur=<length>`)
- run every ffmpeg call with `-nostdin`, `stdin=DEVNULL` and a timeout
- mix to WAV, then mux onto the picture in a **separate** command (`-map 0:v -map 1:a -c:v copy`)
- land loudness on the **encoded** file: gain + true-peak limiter, re-measured, typically 1-2 passes

Targets: −16 LUFS / −1.5 dBTP for creator video, or the parent skill's −14 LUFS for launch pieces.

In shell wait loops, never `pgrep -f <pattern>` for a pattern that appears in the loop's own command
line. It matches itself and the loop never ends.

## 6. Verify on the final mix

`scripts/beatcheck.py FINAL.mp4 beats.json --tol 3` runs Whisper on the delivered file and prints
got/want/delta per beat.
- **Pass:** every stressed word within ±3 frames.
- Whisper has ~1-2 frames of noise. A stable 4-5 frame offset on a number token ("7,000") is
  tokenisation, so note it rather than chase it.
- Check after every recompose, not just at the end.

## Scripts
- `scripts/placemix.py`: events in frames → exact-length WAV → mux → loudness, with the hang-proof rules.
- `scripts/beatcheck.py`: Whisper word timing on the final mix vs the sheet.
