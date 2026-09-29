#!/usr/bin/env python3
"""inkspan.py ref.png clone.png name:x0,y0,x1,y1[:thresh] ...
Text/ink extent inside a rect in both frames (pixels darker than the rect's median by > thresh):
left, right, top, bottom and the width ratio clone/ref. Use it to set font-size (height ratio) and
letter-spacing (width ratio after size) of every UI string from numbers instead of eyeballing."""
import sys, cv2, numpy as np
R = cv2.imread(sys.argv[1], 0).astype(int); C = cv2.imread(sys.argv[2], 0).astype(int)
for spec in sys.argv[3:]:
    p = spec.split(":"); nm = p[0]; x0, y0, x1, y1 = map(int, p[1].split(",")); th = int(p[2]) if len(p) > 2 else 60
    out = []
    for im in (R, C):
        a = im[y0:y1, x0:x1]; m = a < np.median(a) - th
        ys, xs = np.where(m)
        out.append((xs.min() + x0, xs.max() + x0, ys.min() + y0, ys.max() + y0) if len(xs) else None)
    r, c = out
    if r and c:
        print(f"{nm:14s} ref x{r[0]}-{r[1]} y{r[2]}-{r[3]} (w{r[1]-r[0]+1} h{r[3]-r[2]+1})  clone x{c[0]}-{c[1]} y{c[2]}-{c[3]} (w{c[1]-c[0]+1} h{c[3]-c[2]+1})  w-ratio {(c[1]-c[0]+1)/(r[1]-r[0]+1):.3f} dx{c[0]-r[0]:+d} dy{c[2]-r[2]:+d}")
    else: print(nm, out)
