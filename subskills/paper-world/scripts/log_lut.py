#!/usr/bin/env python3
"""Build a .cube LUT that takes Apple Log (iPhone ProRes Log) footage to a filmic Rec.709 look, so live footage and
rendered/collage shots share one grade. Pipeline: Apple Log decode -> linear Rec.2020 -> Rec.709 -> exposure ->
Hable filmic tone curve -> saturation -> gamma -> optional print-film look (cool shadows, warm highlights, gentle
S-curve, lifted black, rolled-off white).

  log_lut.py OUT.cube [--exposure 1.6] [--film 1.0] [--sat 0.25] [--size 33]
  ffmpeg -i clip.MOV -vf "lut3d=file=OUT.cube" ...

--exposure  linear gain before the tone curve (1.6 suits normally exposed daylight Apple Log; raise for underexposure)
--film      0 = neutral filmic, 1 = full print look. Make a few (e.g. 0 and 1 at two exposures) and pick on stills.
For other log curves (S-Log3, V-Log, LogC) swap decode() for that camera's published formula."""
import argparse
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--exposure", type=float, default=1.6); ap.add_argument("--film", type=float, default=1.0)
ap.add_argument("--sat", type=float, default=0.25); ap.add_argument("--size", type=int, default=33)
a = ap.parse_args()

def decode(P):                      # Apple Log -> scene-linear (Apple's published constants)
    R0, Rt, c, b, gm, d = -0.05641088, 0.01, 47.28711236, 0.00964052, 0.08550479, 0.69336945
    Pt = c * (Rt - R0) ** 2
    return np.where(P >= Pt, 2 ** ((P - d) / gm) - b, np.sqrt(np.clip(P, 0, None) / c) + R0)

def hable(v):
    A, B, C, D, E, F = 0.15, 0.50, 0.10, 0.20, 0.02, 0.30
    return ((v * (A * v + C * B) + D * E) / (v * (A * v + B) + D * F)) - E / F

N = a.size; g = np.linspace(0, 1, N)
Bc, Gc, Rc = np.meshgrid(g, g, g, indexing="ij")            # .cube order: R fastest
P = np.stack([Rc, Gc, Bc], -1).reshape(-1, 3)
M2020_709 = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
x = np.clip(decode(P) @ M2020_709.T, 0, None) * a.exposure
x = hable(x) / hable(11.2)
lum = (x * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
x = lum + (x - lum) * (1 + a.sat * a.film)
y = np.clip(x, 0, 1) ** (1 / 2.4)
s = a.film
if s:
    L = (y * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    sh = np.clip(1 - L * 2.0, 0, 1) ** 1.2; hi = np.clip(L * 1.6 - 0.6, 0, 1)
    y = y + s * (sh * np.array([-0.035, 0.010, 0.030]) + hi * np.array([0.045, 0.012, -0.045]))   # split tone
    y = y + s * 0.10 * (y - 0.5) * np.sin(np.pi * np.clip(y, 0, 1))                              # S-curve
    y = 0.025 * s + y * (1 - 0.045 * s)                                                          # print black/white
with open(a.out, "w") as fh:
    fh.write(f"LUT_3D_SIZE {N}\n")
    for r, gg, bb in np.clip(y, 0, 1): fh.write(f"{r:.6f} {gg:.6f} {bb:.6f}\n")
print(a.out)
