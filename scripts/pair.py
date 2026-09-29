#!/usr/bin/env python3
"""pair.py <ref.mp4> <clone.mp4> <out.png> f1 [f2 ...] — ref (left) / clone (right) at 960 px per frame, one row per frame."""
import sys, subprocess, numpy as np
from PIL import Image, ImageDraw
def grab(v, f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select=eq(n\\,{f}),scale=960:540", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(540, 960, 3))
fs = [int(x) for x in sys.argv[4:]]; out = Image.new("RGB", (1924, 558 * len(fs)), (17, 17, 17)); d = ImageDraw.Draw(out)
for i, f in enumerate(fs):
    out.paste(grab(sys.argv[1], f), (0, 558 * i + 18)); out.paste(grab(sys.argv[2], f), (964, 558 * i + 18)); d.text((4, 558 * i + 3), f"f{f}  REF | CLONE", fill=(255, 220, 120))
out.save(sys.argv[3]); print(sys.argv[3])
