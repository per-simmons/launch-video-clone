# launch-video-clone

A Claude Code skill for making product launch videos in [HyperFrames](https://www.npmjs.com/package/hyperframes)
that don't look AI-made.

Out of the box, a model makes the generic "AI motion" look: sliding text, safe fonts, the same
ease on everything. The launch videos that look designed got there by studying a real reference
shot by shot and fixing timing and easing over many passes. This skill turns that into a loop an
agent can run, with scripts that measure motion instead of guessing it.

## Two modes

- **Original** (no reference video): pick the category that fits the product (UI showcase,
  abstract 3D diagram, photoreal 3D product, editorial collage, liquid-glass UI, kinetic type
  into UI), take cut rhythm and easing numbers from 1-3 donor videos of that category, write the
  script and a shot-by-shot breakdown, build it in HyperFrames and self-review it against the
  motion rules.
- **Clone** (a reference video is given): rebuild the reference as closely as possible (same
  shots, timing, easing, transitions and type), optionally re-skinned for another brand. The model
  can't watch video, so `scripts/burst.py` turns the reference into per-shot frame sheets, motion
  trails, easing curves and beat maps it can read, and `scripts/compare.py` grades every render
  against the reference frame for frame until they match.

Both modes end by writing a `LESSONS.md` so the skill improves with each video.

## Layout

```
SKILL.md              the workflow (start here)
types/                one file per kind of motion: build approach, traps, lessons
references/           motion-feel rules, living-stills recipes, the corpus of public techniques,
                      and worked example code from past clones (examples/)
scripts/              analysis, tracking, comparison and sound tools
```

## Install

Copy this folder to either location:

```bash
# for all your projects
cp -R launch-video-clone ~/.claude/skills/launch-video-clone
# or for one project
cp -R launch-video-clone <project>/.claude/skills/launch-video-clone
```

Then ask Claude Code for "a launch video for <product>" or "clone this launch video: <url>".
In the skill, `$SKILL_DIR` means the folder you copied it to; set `S="$SKILL_DIR/scripts"`.

## Requirements

- **HyperFrames CLI** (`npx hyperframes ...`, Node 18+)
- **ffmpeg / ffprobe** on PATH
- **python3** with: `numpy pillow opencv-python scipy matplotlib`
  ```bash
  pip install numpy pillow opencv-python scipy matplotlib
  ```
- **yt-dlp** to download a reference video (optional)
- **Blender** for photoreal 3D product shots (optional)

Sound (optional):
- `ELEVENLABS_API_KEY` for `scripts/eleven.py` (music and sound effects)
- `GEMINI_API_KEY` for `scripts/listen.py` (a model that listens to the audio)
- A separate venv for `scripts/soundcheck.py`, in your project:
  ```bash
  python3 -m venv .venv-sound
  .venv-sound/bin/pip install numpy torch audiobox_aesthetics google-genai
  .venv-sound/bin/python "$S/soundcheck.py" check renders/v1.mp4 ...
  ```

API keys are read from environment variables only. Nothing reads `.env` files for you:
export them in your shell (`export ELEVENLABS_API_KEY=...`).

Images (optional): an image generator that accepts reference images (gpt-image or similar), for
photoreal plates. UI, type and logos are always built in code or taken from real files.

Renders are large (HyperFrames writes one PNG per frame as scratch), so render outside the repo,
e.g. `./renders` (gitignored here) or an external drive.

## License

MIT. See [LICENSE](LICENSE).
