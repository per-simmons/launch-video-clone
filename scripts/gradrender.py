#!/usr/bin/env python3
"""gradrender.py <fit.json> <frame> <out.png> [ref.mp4]  render a gradfit frame at 480x270 (next to the ref frame)"""
import sys, json, subprocess, numpy as np
from PIL import Image
J = json.load(open(sys.argv[1])); f = sys.argv[2]; P = np.array(J["frames"][f])
w, h = 480, 270; yy, xx = np.mgrid[0:h, 0:w].astype(float); xx = (xx + .5) * 4; yy = (yy + .5) * 4
num = np.zeros((h, w, 3)); den = np.zeros((h, w)) + 1e-9
for cx, cy, sx, sy, th, la, r, g, b in P:
    c, s = np.cos(th), np.sin(th); dx, dy = xx - cx, yy - cy
    u, v = (c * dx + s * dy) / abs(sx), (-s * dx + c * dy) / abs(sy)
    wg = np.exp(la - 0.5 * (u * u + v * v)); num += wg[..., None] * [r, g, b]; den += wg
im = Image.fromarray(np.clip(num / den[..., None] * 255, 0, 255).astype(np.uint8))
if len(sys.argv) > 4:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[4], "-vf", f"select=eq(n\\,{f}),scale={w}:{h}", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    ref = Image.frombytes("RGB", (w, h), raw); c = Image.new("RGB", (w * 2, h)); c.paste(ref, (0, 0)); c.paste(im, (w, 0)); im = c
im.save(sys.argv[3])
