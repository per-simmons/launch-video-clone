#!/usr/bin/env python3
"""Prove a UI overlay doesn't jump: per-frame bounding box of the visible UI in a folder of RGBA PNG frames, and the
largest frame-to-frame move of each edge. Optionally checks that text already on screen never moves (needs the
per-frame word rects your renderer reports, e.g. rects.json {"frames": {"458": {"card": [x,y,w,h], "words": [[x,y,w,h], ...]}}};
words are measured relative to the card, so the card entering or sliding as a whole is not counted as drift).

  uibbox.py FRAMES_DIR [--glob "*.png"] [--alpha 24] [--rects rects.json] [--max 4] [--settle 8]

--alpha   alpha threshold (0-255) for "visible": set it above soft glows/shadows so they don't count as the card
--max     pass/fail limit in px per frame for any edge (an eased grow at sane speed stays under ~4 px/frame at 1080p)
Prints the worst frames per edge and the max placed-word drift; exit 1 on failure."""
import argparse, glob, json, os, sys
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("--glob", default="*.png"); ap.add_argument("--alpha", type=int, default=24)
ap.add_argument("--rects"); ap.add_argument("--max", type=float, default=4.0)
ap.add_argument("--settle", type=int, default=8, help="frames a new word may animate in before it counts as placed")
a = ap.parse_args()
files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
if not files: raise SystemExit("no frames")
boxes = []
for f in files:
    al = np.asarray(Image.open(f).convert("RGBA"))[..., 3]
    ys, xs = np.where(al > a.alpha)
    boxes.append(None if len(xs) == 0 else (xs.min(), ys.min(), xs.max(), ys.max()))
worst = {e: (0, None) for e in ("left", "top", "right", "bottom")}
for i in range(1, len(boxes)):
    if boxes[i] is None or boxes[i - 1] is None: continue
    for k, e in enumerate(("left", "top", "right", "bottom")):
        dlt = abs(int(boxes[i][k]) - int(boxes[i - 1][k]))
        if dlt > worst[e][0]: worst[e] = (dlt, os.path.basename(files[i]))
ok = all(v[0] <= a.max for v in worst.values())
print("max edge move px/frame:", {e: v for e, v in worst.items()})
if a.rects:
    R = json.load(open(a.rects))["frames"]; keys = sorted(R, key=int); drift = (0.0, None)
    first = {}                                                       # frame each word index first appears
    for k in keys:
        for i in range(len(R[k].get("words", []))): first.setdefault(i, int(k))
    for k0, k1 in zip(keys, keys[1:]):
        w0, w1 = R[k0].get("words", []), R[k1].get("words", [])
        c0, c1 = R[k0].get("card", [0, 0]), R[k1].get("card", [0, 0])   # measure words relative to their card, so a
        for i, (r0, r1) in enumerate(zip(w0, w1)):                      # whole-card entry or slide isn't "drift"
            if int(k0) - first[i] < a.settle: continue                  # still animating in
            dd = max(abs((r0[0] - c0[0]) - (r1[0] - c1[0])), abs((r0[1] - c0[1]) - (r1[1] - c1[1])))
            if dd > drift[0]: drift = (dd, k1)
    print("max placed-word drift px:", drift)
    ok = ok and drift[0] <= 1.0
print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
