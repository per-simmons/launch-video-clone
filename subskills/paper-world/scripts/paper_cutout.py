#!/usr/bin/env python3
"""Turn a photo + subject mask into a realistic paper cut-out (the After Effects recipe: Roughen Edges on the scissor
line, an off-white paper border with fibre texture, a darker bevelled outer edge for paper thickness). Output: RGBA PNG
cropped to the cut, plus its box in the source frame (so you can place it back exactly where it was).

  paper_cutout.py IMAGE MASK OUT.png [--border 14] [--rough 5] [--seed 3] [--texture paper.jpg] [--paper 242,236,226]

IMAGE  the frame (any size). MASK  white = subject (same size; SAM / Apple Vision / rembg output).
--border   paper margin around the subject in px (scale it with the subject: ~1-2% of its height)
--rough    how far the scissor line wanders in px (slow, large-scale noise: a hand cut, not a jagged tear)
--texture  optional paper scan; without one a procedural fibre texture is used
The cut never eats into the subject (it is unioned with a dilated mask)."""
import argparse
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument("image"); ap.add_argument("mask"); ap.add_argument("out")
ap.add_argument("--border", type=float, default=14); ap.add_argument("--rough", type=float, default=5)
ap.add_argument("--seed", type=int, default=3); ap.add_argument("--texture")
ap.add_argument("--paper", default="242,236,226", help="paper colour, R,G,B")
a = ap.parse_args()

img = cv2.imread(a.image, cv2.IMREAD_COLOR)
m = (cv2.imread(a.mask, cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
if img is None or m is None: raise SystemExit("could not read image or mask")
if m.shape != img.shape[:2]: m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
H, W = m.shape
rng = np.random.default_rng(a.seed)

def fractal(scales, amps):
    n = np.zeros((H, W), np.float32)
    for s, amp in zip(scales, amps):
        g = rng.standard_normal((H // s + 2, W // s + 2)).astype(np.float32)
        n += amp * cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
    return n / sum(amps)

# scissor line: distance from the subject, pushed in and out by slow noise
dist = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
cut = dist < (a.border + a.rough * fractal((90, 34), (1.0, 0.35)))
cut = cv2.morphologyEx(cut.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
cut |= cv2.dilate(m, np.ones((5, 5), np.uint8)) > 0                 # never cut into the subject

# paper texture: a scan if given, otherwise fibre noise (fine streaks + blotches)
if a.texture:
    t = cv2.imread(a.texture, cv2.IMREAD_GRAYSCALE)
    t = cv2.resize(t, (W, H)).astype(np.float32) / 255
    fib = np.clip((t - t.mean()) * 0.45, -0.05, 0.05)
else:
    streak = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), sigmaX=6, sigmaY=0.8)
    fib = np.clip(0.02 * streak / (streak.std() + 1e-6) + 0.015 * fractal((24, 8), (1, .5)), -0.05, 0.05)
r, g, b = (float(v) for v in a.paper.split(","))
paper = np.dstack([np.full((H, W), v, np.float32) for v in (b, g, r)]) * (1 + fib)[..., None]

# bevel: darker toward the cut edge (paper thickness), a soft highlight just inside it
d_edge = cv2.distanceTransform(cut.astype(np.uint8), cv2.DIST_L2, 5)
paper *= (1 - 0.22 * np.exp(-d_edge / 1.4) + 0.05 * np.exp(-((d_edge - 3.5) ** 2) / 3))[..., None]
photo = img.astype(np.float32) * (1 + 0.06 * fib)[..., None]          # the print picks up the fibre too
rgb = np.where((m > 0)[..., None], photo, paper)
alpha = cv2.GaussianBlur(cut.astype(np.float32), (3, 3), 0.7) * 255

x, y, w, h = cv2.boundingRect(cut.astype(np.uint8)); P = 4
out = np.zeros((h + 2 * P, w + 2 * P, 4), np.uint8)
out[P:-P, P:-P, :3] = np.clip(rgb[y:y + h, x:x + w], 0, 255)
out[P:-P, P:-P, 3] = alpha[y:y + h, x:x + w]
cv2.imwrite(a.out, out)
print(f"{a.out}: box {x - P},{y - P},{w + 2 * P},{h + 2 * P}")
