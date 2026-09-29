#!/usr/bin/env python3
"""fadecurve.py video.mp4 cam.json A B name:x,y,w,h[:bg] ...

Opacity-over-time of elements that FADE in while the camera moves. Each region is given in
WORLD coordinates; per frame it is mapped to the screen through cam.json (screen = s*world+t),
and the region's mean colour is expressed as alpha = |mean - bg| / |final - bg|, where bg is the
colour before the element exists (default: the region's first-frame mean) and final its value at
frame B. Prints alpha per frame and the 10%/50%/90% crossing frames, which give start, midpoint
and length of the fade.
"""
import sys, json
import cv2, numpy as np
video, camf, A, B = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
regs = []
for spec in sys.argv[5:]:
    parts = spec.split(":"); nm = parts[0]; x, y, w, h = map(float, parts[1].split(","))
    bg = np.array(list(map(float, parts[2].split(",")))) if len(parts) > 2 else None
    regs.append((nm, x, y, w, h, bg))
cam = {r["f"]: r for r in json.load(open(camf))}
cap = cv2.VideoCapture(video); i = 0; vals = {r[0]: [] for r in regs}
while True:
    ok, fr = cap.read()
    if not ok or i > B: break
    if i >= A:
        c = cam[i]
        for nm, x, y, w, h, bg in regs:
            X0, Y0 = c["s"] * x + c["tx"], c["s"] * y + c["ty"]; X1, Y1 = X0 + c["s"] * w, Y0 + c["s"] * h
            X0, Y0, X1, Y1 = max(0, int(X0)), max(0, int(Y0)), min(1920, int(X1)), min(1080, int(Y1))
            m = fr[Y0:Y1, X0:X1].reshape(-1, 3).mean(0)[::-1] if X1 > X0 and Y1 > Y0 else np.array([np.nan] * 3)
            vals[nm].append(m)
    i += 1
for nm, x, y, w, h, bg in regs:
    v = np.array(vals[nm]); b = bg if bg is not None else v[0]; fin = v[-1]
    den = np.linalg.norm(fin - b) + 1e-6
    a = np.array([np.dot(m - b, fin - b) / den ** 2 for m in v])
    fr_ = np.arange(A, A + len(a))
    cross = {}
    for q in (0.1, 0.5, 0.9):
        k = np.argmax(a >= q) if (a >= q).any() else None
        cross[q] = int(fr_[k]) if k is not None else None
    print(f"{nm}: 10%@{cross[0.1]} 50%@{cross[0.5]} 90%@{cross[0.9]}   bg={np.round(b).astype(int).tolist()} final={np.round(fin).astype(int).tolist()}")
    print("   " + " ".join(f"{f}:{x:.2f}" for f, x in zip(fr_, a)))
