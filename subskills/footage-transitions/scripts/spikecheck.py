#!/usr/bin/env python3
"""Find the frames a viewer will feel as a jump: single-frame changes much bigger than their neighbours (a pop, a
one-frame transition, a seam between two renders), plus near-black frames and container problems.

  spikecheck.py VIDEO [--cuts 120,431] [--range A B] [--ratio 2.5] [--min 4] [--win 8] [--black 18] [--out DIR]

Per frame: mean absolute difference to the previous frame on a 320x180 grey proxy (0-255). A frame is HOT when its
diff > --min AND > --ratio x the median of the --win frames on each side. An isolated hot frame (both neighbours
under 60% of it) is a SPIKE: a one-frame pop, the thing viewers feel. Consecutive hot frames are a BURST: a fast
move (whip, iris, push) that should be checked on a sheet but is usually intended. Intended hard cuts go in --cuts.
Also reports: darkest frame (mean luma, flags frames under --black), frame count, duration, audio vs video length.
Writes DIR/spikes.json and DIR/diff.png (red = spikes, blue = listed cuts). Exit code 1 if any spike or black frame.
Grain and noise raise every diff equally, so a clean spike stands out even on a grainy encode; for the strictest read
run it on a pre-grain render."""
import argparse, json, os, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--cuts", default=""); ap.add_argument("--range", nargs=2, type=int)
ap.add_argument("--ratio", type=float, default=2.5); ap.add_argument("--min", type=float, default=4.0)
ap.add_argument("--win", type=int, default=8); ap.add_argument("--black", type=float, default=18.0)
ap.add_argument("--out", default=None)
a = ap.parse_args()
out = a.out or os.path.splitext(a.video)[0] + "_spikecheck"; os.makedirs(out, exist_ok=True)
cuts = {int(c) for c in a.cuts.split(",") if c.strip()}
W, H = 320, 180

def run(cmd, t=900):
    return subprocess.run(["perl", "-e", f"alarm {t}; exec @ARGV"] + cmd, capture_output=True, stdin=subprocess.DEVNULL)

p = run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"])
fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W).astype(np.float32)
n = len(fr)
diff = np.zeros(n, np.float32); diff[1:] = np.abs(fr[1:] - fr[:-1]).mean((1, 2))
luma = fr.mean((1, 2)) * (219 / 255) + 16                     # approx. limited-range Y like signalstats YAVG
A, B = (a.range if a.range else (1, n - 1))
hot = {}
for g in range(max(1, A), min(n, B + 1)):
    if g in cuts: continue
    nb = np.concatenate([diff[max(1, g - a.win):g], diff[g + 1:g + 1 + a.win]])
    if len(nb) == 0: continue
    med = float(np.median(nb))
    if diff[g] > a.min and diff[g] > a.ratio * max(med, 0.5):
        hot[g] = {"frame": g, "diff": round(float(diff[g]), 2), "local_median": round(med, 2),
                  "ratio": round(float(diff[g]) / max(med, 0.5), 2)}
spikes, bursts = [], []
for g, h in sorted(hot.items()):
    lo, hi = diff[g - 1] if g > 0 else 0, diff[g + 1] if g + 1 < n else 0
    if lo < 0.6 * diff[g] and hi < 0.6 * diff[g]: spikes.append(h)
    elif bursts and bursts[-1]["end"] >= g - 1: bursts[-1]["end"] = g; bursts[-1]["max_ratio"] = max(bursts[-1]["max_ratio"], h["ratio"])
    else: bursts.append({"start": g, "end": g, "max_ratio": h["ratio"]})
black = [int(i) for i in np.where(luma < a.black)[0]]

pr = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration", "-of", "json", a.video])
info = json.loads(pr.stdout or b"{}")
dur = {s["codec_type"]: float(s.get("duration", 0) or 0) for s in info.get("streams", [])}
rate = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", a.video]).stdout.decode().strip()
fps = eval(rate) if rate else 30.0
rep = {"frames": n, "fps": round(fps, 3), "video_s": dur.get("video"), "audio_s": dur.get("audio"),
       "av_gap_frames": round((dur["audio"] - dur["video"]) * fps, 2) if "audio" in dur and "video" in dur else None,
       "spikes": spikes, "bursts": bursts, "max_ratio": max([s["ratio"] for s in spikes], default=None),
       "darkest_frame": int(np.argmin(luma)), "darkest_luma": round(float(luma.min()), 1), "black_frames": black[:50]}
json.dump(rep, open(f"{out}/spikes.json", "w"), indent=1)
try:
    from PIL import Image, ImageDraw
    sx = max(1, 2000 // max(n, 1)); top = max(20.0, float(diff.max()))
    im = Image.new("RGB", (n * sx, 320), (250, 250, 250)); d = ImageDraw.Draw(im)
    for c in cuts: d.line((c * sx, 0, c * sx, 300), fill=(120, 160, 230))
    for s in spikes: d.line((s["frame"] * sx, 0, s["frame"] * sx, 300), fill=(230, 60, 60))
    for g in range(1, n): d.line(((g - 1) * sx, 300 - diff[g - 1] / top * 290, g * sx, 300 - diff[g] / top * 290), fill=(30, 30, 30))
    im.save(f"{out}/diff.png")
except ImportError:
    pass
print(json.dumps({k: v for k, v in rep.items() if k not in ("spikes", "bursts")}, indent=1))
for s in spikes[:30]: print("SPIKE", s)
for b in bursts[:30]: print("burst (check on a sheet)", b)
sys.exit(1 if spikes or black else 0)
