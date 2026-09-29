#!/usr/bin/env python3
"""sheet.py <video> <a> <b> <out.png> [step] [width] [x,y,w,h crop in full-res px]
Every frame from a to b (ABSOLUTE frame numbers, same numbering as burst.py), tiled 6 across and
labelled with its real frame number. Use it on the reference AND the render for any moment where
the burst sheet skips frames: a stagger, an overshoot, a transition."""
import sys, subprocess, json
import numpy as np
from PIL import Image, ImageDraw
v, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
step = int(sys.argv[5]) if len(sys.argv) > 5 else 1
w = int(sys.argv[6]) if len(sys.argv) > 6 else 384
crop = [int(t) for t in sys.argv[7].split(",")] if len(sys.argv) > 7 else None
st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "json", v], capture_output=True, text=True).stdout)["streams"][0]
sw, shh = (crop[2], crop[3]) if crop else (st["width"], st["height"])
h = int(round(w * shh / sw / 2)) * 2
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", (f"select=between(n\\,{a}\\,{b}),crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},scale={w}:{h}" if crop else f"select=between(n\\,{a}\\,{b}),scale={w}:{h}"),
                      "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
idx = list(range(0, len(fr), step)); cols = 6; rows = (len(idx) + cols - 1) // cols
sh = Image.new("RGB", (cols * (w + 4), rows * (h + 18)), (17, 17, 17)); d = ImageDraw.Draw(sh)
for k, i in enumerate(idx):
    x = (k % cols) * (w + 4); y = (k // cols) * (h + 18)
    sh.paste(Image.fromarray(np.ascontiguousarray(fr[i])), (x, y + 16)); d.text((x + 2, y + 2), f"f{a + i}", fill=(255, 220, 120))
sh.save(out)
print(out)
