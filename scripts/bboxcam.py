#!/usr/bin/env python3
"""bboxcam.py video.mp4 A B --lo 170 --hi 215 [--sat 18] [--out box.json]

Tracks one rigid, flat-coloured object (a window body, a card, a panel) by its bounding box:
pixels whose grey level is in [lo,hi] and whose saturation is under --sat, closed, largest
connected component. Prints x0,y0,x1,y1 per frame. Two frames' boxes give the camera between
them directly (s = width ratio, t from the top-left corner), with no chain to drift. Use it
wherever a fade or a big content change makes frame-to-frame registration unreliable.
"""
import sys, json, argparse
import cv2, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("--lo", type=int, default=170); ap.add_argument("--hi", type=int, default=215)
ap.add_argument("--sat", type=int, default=18); ap.add_argument("--close", type=int, default=9)
ap.add_argument("--out")
o = ap.parse_args()
cap = cv2.VideoCapture(o.video); i = 0; res = []
while True:
    ok, fr = cap.read()
    if not ok or i > o.b: break
    if i >= o.a:
        hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV); g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        m = ((g >= o.lo) & (g <= o.hi) & (hsv[..., 1] < o.sat)).astype(np.uint8)
        k = np.ones((o.close, o.close), np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else 0
        x, y, w, h, a = st[j]
        res.append({"f": i, "x0": int(x), "y0": int(y), "x1": int(x + w), "y1": int(y + h), "area": int(a)})
        print(i, x, y, x + w, y + h, a)
    i += 1
if o.out: json.dump(res, open(o.out, "w"))
