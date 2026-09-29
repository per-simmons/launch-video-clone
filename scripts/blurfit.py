#!/usr/bin/env python3
"""blurfit.py video.mp4 sharp_frame A B [--mask x,y,w,h]
Per frame A..B, finds the Gaussian sigma (and a linear gain/offset, for a white wash) that best
turns the sharp frame into that frame. Gives the blur ramp of a "blur to end card" as numbers."""
import sys, cv2, numpy as np
v, sf, A, B = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
mask = None
if len(sys.argv) > 6 and sys.argv[5] == "--mask": mask = tuple(map(int, sys.argv[6].split(",")))
cap = cv2.VideoCapture(v); fr = {}; i = 0
while True:
    ok, f = cap.read()
    if not ok or i > B: break
    if i == sf or A <= i <= B: fr[i] = cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32)
    i += 1
S = fr[sf]; M = np.ones(S.shape[:2], bool)
if mask: x, y, w, h = [int(q / 4) for q in mask]; M[y:y + h, x:x + w] = False
for f in range(A, B + 1):
    best = None
    for sg in np.arange(0, 40.01, 0.5):
        Bl = cv2.GaussianBlur(S, (0, 0), sg / 4) if sg > 0 else S   # sigma in full-res px
        x = Bl[M].reshape(-1); y = fr[f][M].reshape(-1)
        a, b = np.polyfit(x, y, 1); e = np.mean((a * x + b - y) ** 2)
        if best is None or e < best[0]: best = (e, sg, a, b)
    print(f"f{f} sigma={best[1]:.2f}px gain={best[2]:.3f} offset={best[3]:.1f} rmse={np.sqrt(best[0]):.2f}")
