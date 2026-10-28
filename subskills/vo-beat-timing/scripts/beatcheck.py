#!/usr/bin/env python3
"""Check that spoken words land on their picture beats, on the FINAL mix (not on the VO files you placed).

  beatcheck.py VIDEO BEATS.json [--fps 30] [--tol 3] [--model mlx-community/whisper-large-v3-turbo]

BEATS.json: {"freeze": {"word": "thousand", "frame": 37}, "logo": {"word": "lovely", "frame": 315}, ...}
  - "word" is matched case- and punctuation-insensitively (as a substring of Whisper's token, so "eyesores" matches
    "eyesores."); numbers Whisper writes as digits ("7,000") are also matched by their spoken words where possible
  - when a word occurs more than once, the occurrence nearest the target frame is used
Transcribes with mlx_whisper (Apple silicon) or openai-whisper, word timestamps on. Prints got/want/delta per beat and
exits 1 if any |delta| > --tol frames or a word is missing. Whisper word starts carry ~1-2 frames of noise; a delta that
is stable across builds at 4-5 frames on a number token is usually tokenisation, not drift: say so, don't chase it."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("beats"); ap.add_argument("--fps", type=float, default=30.0)
ap.add_argument("--tol", type=float, default=3.0); ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
a = ap.parse_args()
beats = json.load(open(a.beats))
tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, "a.wav")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", a.video, "-ac", "1", "-ar", "16000", wav],
               check=True, stdin=subprocess.DEVNULL, timeout=600)
words = []
if shutil.which("mlx_whisper"):
    subprocess.run(["mlx_whisper", wav, "--word-timestamps", "True", "--output-format", "json", "--output-dir", tmp,
                    "--language", "en", "--model", a.model], capture_output=True, stdin=subprocess.DEVNULL, timeout=1800)
    js = json.load(open(os.path.join(tmp, "a.json")))
    words = [(w["word"], w["start"]) for s in js["segments"] for w in s.get("words", [])]
else:
    import whisper                                            # pip install openai-whisper
    r = whisper.load_model("small").transcribe(wav, word_timestamps=True, language="en")
    words = [(w["word"], w["start"]) for s in r["segments"] for w in s.get("words", [])]
NUM = {"000": "thousand", "00": "hundred"}
def norm(s):
    s = s.lower()
    for k, v in NUM.items(): s = s.replace("," + k, v)
    return re.sub(r"[^a-z0-9]", "", s)
bad = 0
for label, b in beats.items():
    key = norm(b["word"]); target = float(b["frame"])
    cand = [(w, t) for w, t in words if key in norm(w)]
    if not cand: print(f"{label:16s} '{b['word']}' MISSING"); bad += 1; continue
    w, t = min(cand, key=lambda c: abs(c[1] * a.fps - target))
    d = t * a.fps - target; flag = "OK" if abs(d) <= a.tol else "OFF"
    bad += flag != "OK"
    print(f"{label:16s} '{b['word']}' got f{t * a.fps:7.1f} want f{target:7.1f}  delta {d:+5.1f}  {flag}")
print("transcript:", " ".join(w.strip() for w, _ in words)[:300])
sys.exit(1 if bad else 0)
