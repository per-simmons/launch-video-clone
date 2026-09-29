#!/usr/bin/env python3
"""listen.py — Gemini listens so Opus doesn't have to. Opus can't hear; Gemini 3.1 Pro takes video
WITH its audio track natively.

  listen.py cue  <ref.mp4>                  [-o SOUND.md]   sound cue sheet of the reference
  listen.py qa   <clone.mp4> <ref.mp4>      [-o SOUND-QA.md] critique the clone's audio against the reference
  listen.py qa   <clone.mp4> --cues SOUND.md                 (reference not re-uploaded)

`cue` = what a sound designer would write down: music (genre, BPM, structure, where it drops/
builds/stops), then every sound effect with a timestamp (m:ss.xx), what it sounds like
(whoosh, click, riser, impact, UI blip, typing...) and which on-screen event it's attached to.

`qa` = what's missing, late/early (in ms), wrong in character, too loud/quiet, and whether the
music fits, each tied to a timestamp. It's an ear, not a meter: pair it with compare.py's
numbers, and trust it for character ("too harsh", "no low end on the hit") more than for
millisecond precision.

Key: GEMINI_API_KEY, read from the environment only (export it before running).
Model: gemini-3.1-pro-preview, falling back to gemini-3.8-flash on quota errors (never 2.5). Override with GEMINI_MODEL.
"""
import argparse, os, subprocess, sys, tempfile, time

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
FALLBACKS = ["gemini-3.8-flash", "gemini-3.5-flash"]  # used when the Pro model is out of quota or busy

CUE_PROMPT = """You are a senior sound designer. Watch AND listen to this product launch video
closely (it is short; take it in fully). Write a sound cue sheet another designer could rebuild
the audio from, in markdown:

## Music
Genre/feel in plain words, instrumentation, approximate BPM, key moments with timestamps
(intro, builds, drops, hits, stops/silence, the ending), and how the edit follows it.

## Sound effects
A table: | time (m:ss.xx) | sound (what it is: whoosh, riser, impact, click, UI blip, typing,
glitch, swell, reverse cymbal...) | character (pitch, length, weight, dry/reverbed) | attached to
(the on-screen event it lands on) |
List EVERY distinct effect you can hear, in order. If sounds are layered, list each layer.

## Mix
Relative levels of music vs effects vs any voice, where the music ducks, stereo movement,
anything notable (sidechain pumping, filtered sections, silence used as a beat).

Be precise with timestamps. If unsure of a timestamp, say so. No preamble."""

QA_PROMPT = """You are a senior sound designer doing QA. {what}
Compare the CLONE's audio against the reference and report, in markdown:

## Verdict
Two sentences: how close the clone sounds overall, and the single biggest problem.

## Issues (most important first)
| time (m:ss.xx) | problem (missing / late by ~N ms / early / wrong sound / too loud / too quiet / clashes) | what the reference does there | fix |

## Music
Does the clone's music match the reference's feel, tempo and structure? Where do its builds,
drops and stops miss the edit?

## Mix
Levels, ducking, harshness, low end, anything that makes it sound cheap.

Be specific and tie every point to a timestamp. No preamble."""


def key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        sys.exit("GEMINI_API_KEY is not set. Export it first:  export GEMINI_API_KEY=...")
    return k


def small(path):
    """480p copy with full audio: faster upload, same sound."""
    out = os.path.join(tempfile.mkdtemp(), os.path.basename(path))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", "scale=-2:480", "-c:v", "libx264",
                    "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", out], check=True)
    return out


def upload(client, path, types):
    f = client.files.upload(file=small(path), config=types.UploadFileConfig(mime_type="video/mp4"))
    t0 = time.time()
    while True:
        cur = client.files.get(name=f.name)
        if cur.state.name == "ACTIVE":
            return cur
        if cur.state.name == "FAILED" or time.time() - t0 > 600:
            sys.exit(f"upload failed: {cur.state.name}")
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["cue", "qa"])
    ap.add_argument("video")
    ap.add_argument("ref", nargs="?")
    ap.add_argument("--cues", help="reference cue sheet (qa mode, instead of uploading the reference)")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key())
    files = []
    try:
        if a.mode == "cue":
            files = [upload(client, a.video, types)]
            contents = [files[0], CUE_PROMPT]
            out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "SOUND.md")
        else:
            clone = upload(client, a.video, types)
            files = [clone]
            if a.ref:
                ref = upload(client, a.ref, types)
                files.append(ref)
                contents = ["REFERENCE video:", ref, "CLONE video:", clone,
                            QA_PROMPT.format(what="You get two videos: the REFERENCE and a CLONE of it.")]
            elif a.cues:
                contents = ["CLONE video:", clone, "REFERENCE sound cue sheet:\n" + open(a.cues).read(),
                            QA_PROMPT.format(what="You get a CLONE video and the reference's sound cue sheet.")]
            else:
                sys.exit("qa needs a reference video or --cues")
            out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "SOUND-QA.md")
        used, resp = None, None
        for attempt in range(5):
            for m in [MODEL] + [x for x in FALLBACKS if x != MODEL]:
                try:
                    resp = client.models.generate_content(model=m, contents=contents)
                    used = m
                    break
                except Exception as e:
                    msg = str(e)
                    if not any(c in msg for c in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500")):
                        raise
                    print(f"  {m}: {msg[:60]}... trying next", file=sys.stderr)
            if resp is not None:
                break
            time.sleep(20 * (attempt + 1))
        if resp is None:
            sys.exit("all Gemini models busy or out of quota; try again in a few minutes")
        open(out, "w").write(f"<!-- listened by {used} -->\n" + (resp.text or "(empty)"))
        print(out)
    finally:
        for f in files:
            try:
                client.files.delete(name=f.name)
            except Exception:
                pass


if __name__ == "__main__":
    main()
