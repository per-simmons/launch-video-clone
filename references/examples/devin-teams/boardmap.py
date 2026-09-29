#!/usr/bin/env python3
"""boardmap.py: per-cell reveal frame for the Minesweeper board, combining the transcribed
final content (glyph cells) with a per-frame bevel probe (blank cells). Glyph cells reveal on
the first frame their ink colour is present and stays; blank cells on the first frame the raised
bevel is gone and stays gone. Writes reference/board.json."""
import json, cv2, numpy as np
CONTENT = {  # (row, col): glyph — transcribed from f126/f150/f185 crops
 (2,4):'2',(2,5):'1',(2,6):'2',(2,7):'1',(2,9):'1',(2,10):'2',(2,12):'2',(2,13):'1',
 (3,3):'2',(3,4):'1',
 (4,2):'D',(4,3):'E',(4,4):'V',(4,5):'I',(4,6):'N',(4,8):'I',(4,9):'S',(4,11):'N',(4,12):'O',(4,13):'W',(4,15):'1',
 (5,1):'2',(5,2):'1',
 (6,1):'2',(6,4):'I',(6,5):'N',(6,7):'T',(6,8):'E',(6,9):'A',(6,10):'M',(6,11):'S',(6,13):'1',
 (7,1):'2',(7,2):'1',(7,3):'1',(7,4):'1',(7,14):'2',
 (8,4):'2',(8,5):'1',(8,7):'2',(8,8):'1',(8,9):'1',(8,10):'1',(8,11):'1',(8,12):'1',(8,14):'1',
 (9,5):'1',(9,6):'1',(9,7):'2',
}
d = json.load(open('reference/cam_grid.json')); cam = {r['f']: r for r in d['cam']}
P, X0, Y0 = d['grid']['P'], d['grid']['X0'], d['grid']['Y0']
cap = cv2.VideoCapture('reference/ref.mp4'); i = 0
obs = {}  # (r,c) -> list of (f, open?)
while True:
    ok, fr = cap.read()
    if not ok or i > 190: break
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(float); c = cam[i]; s = c['s']; p = P * s
    for r in range(11):
        for cc in range(17):
            x0 = s * (X0 + (54 + cc) * P) + c['tx']; y0 = s * (Y0 + (36 + r) * P) + c['ty']
            if x0 < 0 or y0 < 0 or x0 + p > 1919 or y0 + p > 1079 or p < 12: continue
            if (r, cc) in CONTENT:
                pt = fr[int(y0 + p * .2):int(y0 + p * .8), int(x0 + p * .2):int(x0 + p * .8)].reshape(-1, 3).astype(int)
                b, gg, rr = pt[:, 0], pt[:, 1], pt[:, 2]
                ink = ((b > 140) & (rr < 110) & (gg < 110)) | ((gg > 90) & (rr < 90) & (b < 90)) | ((rr < 70) & (gg < 70) & (b < 70))
                op = ink.mean() > 0.03
            else:
                tb = g[int(y0 + 1):int(y0 + p * .12), int(x0 + p * .25):int(x0 + p * .75)]
                lb = g[int(y0 + p * .25):int(y0 + p * .75), int(x0 + 1):int(x0 + p * .12)]
                hi = min(tb.max(axis=1).max(), lb.max(axis=0).max())
                ctr = np.median(g[int(y0 + p * .35):int(y0 + p * .65), int(x0 + p * .35):int(x0 + p * .65)])
                op = hi - ctr <= 35
            obs.setdefault((r, cc), []).append((i, op))
    i += 1
out = []
for r in range(11):
    line = []
    for cc in range(17):
        seq = obs.get((r, cc), [])
        rev = None
        if seq:
            v = np.array([o for _, o in seq]); fs = [f for f, _ in seq]
            # first index k such that >=85% of the remaining readings are open
            for k in range(len(v)):
                if v[k] and v[k:].mean() >= 0.85: rev = fs[k]; break
            if rev is not None and rev == fs[0] and fs[0] > 0: rev = -fs[0]   # already open when first seen
        out.append({"r": r, "c": cc, "g": CONTENT.get((r, cc), ""), "reveal": rev})
        line.append(f"{CONTENT.get((r, cc), '.') }{'' if rev is None else rev:>4}")
    print(" ".join(x.ljust(6) for x in line))
json.dump(out, open('reference/board.json', 'w'), indent=0)
