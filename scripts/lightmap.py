#!/usr/bin/env python3
"""lightmap.py <plate.jpg> <out.png> [--fine 10] [--coarse 90]
Splits a lit plate's light pattern (dapples, window shadows) from its texture: M = log(blur_fine(L)) -
log(blur_coarse(L)), stored as 8-bit (128 + 64*M). A shader re-lights the plate with plate*exp(M(uv+warp) - M(uv)):
zero warp returns the plate exactly, a slow warp makes the light move while wood grain stays put."""
import sys, numpy as np, cv2, argparse
ap = argparse.ArgumentParser(); ap.add_argument("plate"); ap.add_argument("out")
ap.add_argument("--fine", type=float, default=10); ap.add_argument("--coarse", type=float, default=90)
A = ap.parse_args()
im = cv2.imread(A.plate).astype(np.float32) / 255
Lm = (0.3 * im[..., 2] + 0.59 * im[..., 1] + 0.11 * im[..., 0]) + 0.02
# objects that must not move (phone, keys, laptop): dark or low-saturation pixels, dilated; excluded with a
# normalised convolution so they neither carry light pattern nor leak darkness into it
hsv = cv2.cvtColor((im * 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
obj = ((im.max(2) < 0.25) | (hsv[..., 1] < 50)).astype(np.uint8)
obj = cv2.dilate(cv2.morphologyEx(obj, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)), np.ones((31, 31), np.uint8))
w = 1.0 - obj.astype(np.float32)
nb = lambda x, s: np.maximum(cv2.GaussianBlur(x * w, (0, 0), s) / (cv2.GaussianBlur(w, (0, 0), s) + 1e-4), 1e-3)
M = (np.log(nb(Lm, A.fine)) - np.log(nb(Lm, A.coarse))) * cv2.GaussianBlur(w, (0, 0), 8)
M[cv2.GaussianBlur(w, (0, 0), A.fine) < 0.05] = 0
print("M range", M.min().round(3), M.max().round(3), "std", M.std().round(3))
cv2.imwrite(A.out, np.clip(128 + 64 * M, 0, 255).astype(np.uint8))
