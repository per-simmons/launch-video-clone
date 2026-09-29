#!/usr/bin/env python3
"""colormatch.py <plate.png> <ref.mp4> <frame> <rows y0:y1,y0:y1> <out.jpg> [blur_px]
Matches the plate's per-channel mean/std (in Lab) to the reference frame's BACKGROUND rows (skip rows where UI sits),
optionally softens it, writes a flattened JPEG. gpt-image plates come back more saturated than the footage."""
import sys, subprocess, numpy as np, cv2
from PIL import Image, ImageFilter
plate = Image.open(sys.argv[1]); plate = plate.convert("RGBA")
a = np.asarray(plate).astype(float); rgb = a[..., :3] * a[..., 3:4] / 255.0  # flatten alpha over black
f = int(sys.argv[3]); rows = [tuple(int(v) for v in r.split(":")) for r in sys.argv[4].split(",")]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[2], "-vf", f"select=eq(n\\,{f})", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
ref = np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3)
refbg = np.concatenate([ref[y0:y1] for y0, y1 in rows]).reshape(-1, 1, 3)
lab = lambda x: cv2.cvtColor(x.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(float)
P, Rf = lab(rgb), lab(refbg)
pm, ps = P.reshape(-1, 3).mean(0), P.reshape(-1, 3).std(0); rm, rs = Rf.reshape(-1, 3).mean(0), Rf.reshape(-1, 3).std(0)
out = (P - pm) / (ps + 1e-6) * rs + rm
out = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
im = Image.fromarray(out)
if len(sys.argv) > 6 and float(sys.argv[6]) > 0: im = im.filter(ImageFilter.GaussianBlur(float(sys.argv[6])))
im.save(sys.argv[5], quality=92); print(sys.argv[5], "L a b mean", pm.round(1), "->", rm.round(1))
