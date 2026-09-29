#!/usr/bin/env python3
"""Build frame-exact typing tracks (one soft tick per typed/erased character, at the same frames the
composition's Typer uses) and the book-landing clack track. Output: assets/sfx/trk-*.wav + sound/tracks.json."""
import json, subprocess, numpy as np
SR, FPS = 48000, 30
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()
def cuts(x, n, dur=0.07):
    e = np.convolve(np.abs(x), np.ones(96) / 96, "same"); thr = e.max() * 0.35; out = []; i = 0
    while i < len(x) and len(out) < n:
        if e[i] > thr:
            s = max(0, i - 48); seg = x[s:s + int(dur * SR)].copy(); seg *= np.hanning(len(seg) * 2)[len(seg):] ** .5
            out.append(seg / (np.abs(seg).max() + 1e-9)); i += int(0.09 * SR)
        else: i += 1
    return out
tick = load("assets/sfx/tick-2.mp3"); keys = cuts(load("assets/sfx/type-short-3.mp3"), 12) + cuts(tick, 1, 0.06)
# light, digital: high-pass the keyboard hits
from numpy.fft import rfft, irfft
def hp(s, fc=900):
    S = rfft(s, len(s) * 2); f = np.fft.rfftfreq(len(s) * 2, 1 / SR); S *= np.clip((f / fc) ** 2, 0, 1); return irfft(S)[: len(s)]
keys = [hp(k) for k in keys]; keys = [k / (np.abs(k).max() + 1e-9) for k in keys]
rng = np.random.default_rng(7)
def schedule(ops):
    t = []
    for op in ops:
        f0, f1, n = op[1], op[2], (len(op[3]) if op[0] == "t" else op[3])
        for k in range(n): t.append((round(f0 + (k * (f1 - f0) / (n - 1) if n > 1 else 0)), op[0]))
    return t
PROMPTS = {
 "intro": [("t", 0, 27, "Introducing Grok 4.5")],
 "headline": [("t", 62, 78, "delivers"), ("t", 73, 76, "frontier"), ("t", 80, 82, "-level"), ("t", 88, 111, "intelligence")],
 "science": [("t", 899, 899, "B"), ("t", 901, 901, "f"), ("t", 903, 903, "s"), ("t", 906, 906, "m"), ("t", 908, 908, "a"), ("t", 910, 910, "e")],
 "weather": [("t", 402, 414, "Build"), ("t", 419, 420, " a"), ("t", 424, 425, " w"), ("t", 427, 441, "eather"), ("t", 445, 453, " app")],
 "books": [("t", 651, 688, "Build a site for my book reviews")],
 "finance": [("d", 706, 729, 32), ("t", 730, 753, "Build a dashboard from our latest financials")],
 "city": [("d", 790, 802, 9), ("t", 805, 815, "Build a 3D city i can walk through")],
 "canvas": [("t", 842, 856, "Build an infinite design canvas")],
 "booster": [("d", 983, 1009, 27), ("t", 1011, 1040, "Build me a 3D model of the booster")],
 "everyday": [("t", 1105, 1126, "And everyday"), ("t", 1131, 1139, " work,"), ("t", 1143, 1147, " too")],
 "roadmap": [("t", 1166, 1204, "Turn these notes into a quarterly roadmap")],
 "deck": [("t", 1293, 1330, "Build the Q2 sales deck")],
}
out = []
for name, ops in PROMPTS.items():
    sch = schedule(ops); f0 = min(f for f, _ in sch); L = (max(f for f, _ in sch) - f0) / FPS + 0.2
    y = np.zeros(int(L * SR))
    for f, kind in sch:
        k = keys[rng.integers(len(keys))] * (0.55 if kind == "d" else 1.0) * rng.uniform(.75, 1.0)
        i = int((f - f0) / FPS * SR) + int(rng.uniform(0, 0.012) * SR)
        y[i:i + len(k)] += k[: len(y) - i]
    y *= 0.8 / (np.abs(y).max() + 1e-9)
    p = f"assets/sfx/trk-type-{name}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", p], input=y.astype(np.float32).tobytes())
    out.append({"frame": f0, "label": f"typing: {name}", "sfx": p, "anchor": "start", "gain": 0.3, "dur_s": round(L, 3)})
# books: one clack per book landing (drop starts 702 + j*4.6, lands 7 f later)
clacks = cuts(load("assets/sfx/books-1.mp3"), 6, 0.12)
land = [round(702 + j * 4.6 + 7) for j in range(10)]; y = np.zeros(int(((land[-1] - land[0]) / FPS + 0.3) * SR))
for j, f in enumerate(land):
    c = clacks[j % len(clacks)] * rng.uniform(.7, 1); i = int((f - land[0]) / FPS * SR); y[i:i + len(c)] += c[: len(y) - i]
y *= 0.8 / np.abs(y).max()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "assets/sfx/trk-books.wav"], input=y.astype(np.float32).tobytes())
out.append({"frame": land[0], "label": "books land on shelf (10 clacks)", "sfx": "assets/sfx/trk-books.wav", "anchor": "start", "gain": 0.35})
json.dump(out, open("sound/tracks.json", "w"), indent=1); print(len(keys), "key samples;", len(out), "tracks")
