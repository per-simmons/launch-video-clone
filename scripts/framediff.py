#!/usr/bin/env python3
"""framediff.py ref.mp4 clone.mp4 [A B] [--lag]

Per-FRAME numbers where compare.py gives 2 s windows: visual distance (mean abs diff, 0..1,
on 480x270 grey), motion energy of each video (mean abs frame-to-frame diff) and their ratio.
--lag also reports, per 15-frame block, the frame shift (-3..+3) that best aligns the clone's
energy curve to the reference's: + means the clone is late.
"""
import sys, cv2, numpy as np
a = sys.argv[1:]; lag = "--lag" in a; a = [x for x in a if x != "--lag"]
ref, clo = a[0], a[1]; A = int(a[2]) if len(a) > 2 else 0; B = int(a[3]) if len(a) > 3 else 10**9
def load(v):
    cap = cv2.VideoCapture(v); out = []; i = 0
    while True:
        ok, f = cap.read()
        if not ok or i > B + 1: break
        out.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32) / 255)
        i += 1
    return out
R, C = load(ref), load(clo); n = min(len(R), len(C))
eR = np.array([0] + [np.abs(R[i] - R[i - 1]).mean() for i in range(1, n)])
eC = np.array([0] + [np.abs(C[i] - C[i - 1]).mean() for i in range(1, n)])
for i in range(max(A, 0), min(B + 1, n)):
    d = np.abs(R[i] - C[i]).mean()
    print(f"f{i:4d} dist {d:.4f}  eRef {eR[i]*1000:7.2f}  eClone {eC[i]*1000:7.2f}  ratio {eC[i]/max(eR[i],1e-5):5.2f}")
if lag:
    print("\nlag per 15f block (+ = clone late):")
    for s in range(max(A, 3), min(B, n - 3), 15):
        e = min(s + 15, n - 3); best = min(range(-3, 4), key=lambda k: np.sum((eR[s:e] - eC[s + k:e + k]) ** 2))
        print(f"  f{s}-{e - 1}: {best:+d}")
