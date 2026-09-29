#!/usr/bin/env python3
"""fitplate.py plate.png ref_frame.png out.png --mask x0,y0,x1,y1 [--mask ...] [--smin 0.8 --smax 2.2]

gpt-image rarely keeps the reference's framing (it re-crops to its own taste). Instead of
regenerating, fit the plate: brute-force scale + offset (+ per-channel gain) so the plate matches
the reference only where the reference shows the plate (masks = rects covered by UI, excluded).
Writes the plate resampled to the reference's size and prints scale, offset and the residual.
"""
import argparse, cv2, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("plate"); ap.add_argument("ref"); ap.add_argument("out")
ap.add_argument("--mask", action="append", default=[])
ap.add_argument("--pad", type=int, default=0, help="extra px kept on every side (edge-replicated if the plate runs out)")
ap.add_argument("--smin", type=float, default=0.8); ap.add_argument("--smax", type=float, default=2.4)
o = ap.parse_args()
P = cv2.imread(o.plate).astype(np.float32); R = cv2.imread(o.ref).astype(np.float32)
# let the plate shrink below "cover" scale: extend its (usually plain) edges first
P = cv2.copyMakeBorder(P, P.shape[0] // 3, P.shape[0] // 3, P.shape[1] // 3, P.shape[1] // 3, cv2.BORDER_REPLICATE)
H, W = R.shape[:2]; d = 8                     # search at 1/8 resolution
Rs = cv2.resize(R, (W // d, H // d), interpolation=cv2.INTER_AREA)
M = np.ones(Rs.shape[:2], bool)
for m in o.mask:
    x0, y0, x1, y1 = [int(v) // d for v in m.split(",")]; M[y0:y1 + 1, x0:x1 + 1] = False
best = None
for s in np.exp(np.linspace(np.log(o.smin), np.log(o.smax), 40)):
    pw, ph = int(P.shape[1] * s / d), int(P.shape[0] * s / d)
    if pw < Rs.shape[1] or ph < Rs.shape[0]: continue
    Ps = cv2.resize(P, (pw, ph), interpolation=cv2.INTER_AREA)
    for oy in range(0, ph - Rs.shape[0] + 1, 1):
        for ox in range(0, pw - Rs.shape[1] + 1, 2):
            c = Ps[oy:oy + Rs.shape[0], ox:ox + Rs.shape[1]]
            e = np.mean((c[M] - Rs[M]) ** 2)
            if best is None or e < best[0]: best = (e, s, ox, oy)
e, s, ox, oy = best
# refine offset at full res around the coarse hit
full = cv2.resize(P, (int(P.shape[1] * s), int(P.shape[0] * s)), interpolation=cv2.INTER_CUBIC)
Mf = cv2.resize(M.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
bx, by, be = ox * d, oy * d, None
for dy in range(-d, d + 1, 2):
    for dx in range(-d, d + 1, 2):
        X, Y = ox * d + dx, oy * d + dy
        if X < 0 or Y < 0 or X + W > full.shape[1] or Y + H > full.shape[0]: continue
        c = full[Y:Y + H:4, X:X + W:4]; ee = np.mean((c[Mf[::4, ::4]] - R[::4, ::4][Mf[::4, ::4]]) ** 2)
        if be is None or ee < be: be, bx, by = ee, X, Y
pd = o.pad
fullp = cv2.copyMakeBorder(full, pd, pd, pd, pd, cv2.BORDER_REPLICATE)
crop = fullp[by:by + H + 2 * pd, bx:bx + W + 2 * pd].copy()
inner = crop[pd:pd + H, pd:pd + W]
# per-channel gain/offset to the reference's colours in the visible area
for ch in range(3):
    a, b = np.polyfit(inner[..., ch][Mf].ravel(), R[..., ch][Mf].ravel(), 1)
    crop[..., ch] = a * crop[..., ch] + b
cv2.imwrite(o.out, np.clip(crop, 0, 255).astype(np.uint8))
print(f"scale {s:.3f} offset {bx},{by}  rmse {np.sqrt(be):.1f} (coarse {np.sqrt(e):.1f})")
