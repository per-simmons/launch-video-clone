#!/usr/bin/env python3
"""eleven.py — sound design with ElevenLabs, placed to the frame.

  eleven.py sfx "<description>" -d 0.8 -o assets/sfx/whoosh.mp3 [-n 3]
      Text-to-sound-effect. -n makes variants (…-1.mp3, -2.mp3) to pick from with soundcheck.py rank.
  eleven.py plan "<music brief>" --ms 56000 -o sound/music-plan.json
      Get a composition plan (sections with durations + styles). EDIT IT so section boundaries land on
      the reference's structure (intro / drop / dip / hard stop from reference/SOUND.md + ANALYSIS.md).
  eleven.py music --plan sound/music-plan.json -o assets/music/bed.mp3
  eleven.py music "<brief>" --ms 30000 -o assets/music/bed.mp3
  eleven.py place sound/events.json --fps 30 -o sound/placed.json
      For every event, finds the sound's own loudest moment and sets its START so that peak lands
      LEAD ms (default 15) before the event frame. This is the step no tool does for you: a whoosh
      file starts in silence and peaks later, so placing its start on the frame makes it late.

events.json: [{"frame": 712, "label": "windows land", "sfx": "assets/sfx/whoosh-2.mp3",
               "anchor": "peak"|"start", "gain": 0.35, "lead_ms": 15}, ...]
  anchor "start" for typing ticks and clicks (the attack IS the start), "peak" for whooshes/risers/hits.
placed.json adds "start_s" and "peak_s" for each; the composition reads it and puts an <audio> at start_s.

Key: ELEVENLABS_API_KEY, read from the environment only (export it before running).
"""
import argparse, json, os, subprocess, sys, time, urllib.request, urllib.error
import numpy as np

API = "https://api.elevenlabs.io/v1"


def key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        sys.exit("ELEVENLABS_API_KEY is not set. Export it first:  export ELEVENLABS_API_KEY=...")
    return k


def post(path, body, binary=True, tries=4):
    for i in range(tries):
        req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")[:300]
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(5 * (i + 1)); continue
            sys.exit(f"ElevenLabs {path} HTTP {e.code}: {msg}")


def pcm(path, sr=22050):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32), sr


def peak_s(path):
    """Time of the sound's loudest 10 ms (RMS), in seconds from file start."""
    x, sr = pcm(path)
    if len(x) == 0:
        return 0.0
    w = int(sr * 0.01)
    n = len(x) // w
    rms = np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(axis=1)) if n else np.array([0])
    return float(np.argmax(rms) * w / sr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sfx"); s.add_argument("text"); s.add_argument("-d", "--dur", type=float)
    s.add_argument("-o", "--out", required=True); s.add_argument("-n", type=int, default=1)
    s.add_argument("--influence", type=float, default=0.5)
    p = sub.add_parser("plan"); p.add_argument("text"); p.add_argument("--ms", type=int, required=True)
    p.add_argument("-o", "--out", required=True)
    m = sub.add_parser("music"); m.add_argument("text", nargs="?"); m.add_argument("--ms", type=int)
    m.add_argument("--plan"); m.add_argument("-o", "--out", required=True)
    pl = sub.add_parser("place"); pl.add_argument("events"); pl.add_argument("--fps", type=float, required=True)
    pl.add_argument("-o", "--out", required=True); pl.add_argument("--lead-ms", type=float, default=15)
    a = ap.parse_args()

    if a.cmd == "sfx":
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        root, ext = os.path.splitext(a.out)
        for i in range(a.n):
            body = {"text": a.text, "prompt_influence": a.influence}
            if a.dur:
                body["duration_seconds"] = a.dur
            out = a.out if a.n == 1 else f"{root}-{i + 1}{ext}"
            open(out, "wb").write(post("/sound-generation", body))
            print(f"{out}  peak at {peak_s(out) * 1000:.0f} ms")
    elif a.cmd == "plan":
        plan = post("/music/plan", {"prompt": a.text, "music_length_ms": a.ms}, binary=False)
        json.dump(plan, open(a.out, "w"), indent=1)
        for sct in plan.get("sections", []):
            print(f"{sct['section_name']}: {sct['duration_ms']} ms  {', '.join(sct.get('positive_local_styles', [])[:3])}")
        print(a.out)
    elif a.cmd == "music":
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        if a.plan:
            body = {"composition_plan": json.load(open(a.plan))}
        elif a.text and a.ms:
            body = {"prompt": a.text, "music_length_ms": a.ms}
        else:
            sys.exit("music needs --plan, or a brief with --ms")
        open(a.out, "wb").write(post("/music", body))
        print(a.out)
    elif a.cmd == "place":
        ev = json.load(open(a.events))
        base = os.path.dirname(os.path.abspath(a.events))
        out = []
        for e in ev:
            t = e["frame"] / a.fps if "frame" in e else float(e["t"])
            path = e["sfx"] if os.path.isabs(e["sfx"]) else os.path.join(base, "..", e["sfx"])
            pk = peak_s(path) if e.get("anchor", "peak") == "peak" else 0.0
            lead = e.get("lead_ms", a.lead_ms) / 1000.0 if e.get("anchor", "peak") == "peak" else 0.0
            start = max(0.0, t - pk - lead)
            out.append({**e, "event_s": round(t, 4), "sfx_peak_in_file_s": round(pk, 4),
                        "start_s": round(start, 4), "peak_s": round(start + pk, 4)})
        json.dump(out, open(a.out, "w"), indent=1)
        print(f"{len(out)} sounds placed -> {a.out}")


if __name__ == "__main__":
    main()
