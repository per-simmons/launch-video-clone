#!/usr/bin/env python3
"""trackcheck.py <video> <track.json> [every]
Warps the anchor frame by each tracked H and reports mean abs error inside the object's quad vs the
real frame (0-255), next to the error with no motion applied. err << still means the track holds."""
import sys, json, cv2, numpy as np
v, tj = sys.argv[1], json.load(open(sys.argv[2])); every = int(sys.argv[3]) if len(sys.argv) > 3 else 5
x, y, w, h = tj["roi"]; rows = {r["f"]: r for r in tj["rows"]}; A = tj["anchor"]
cap = cv2.VideoCapture(v); fr = {}; i = 0
while True:
    ok, im = cap.read()
    if not ok or i > max(rows): break
    if i in rows: fr[i] = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    i += 1
a = fr[A]; out = []
for f in sorted(rows)[::every]:
    Hm = np.array(rows[f]["H"]).reshape(3, 3)
    wa = cv2.warpPerspective(a, Hm, (a.shape[1], a.shape[0]))
    m = np.zeros(a.shape, np.uint8); cv2.fillConvexPoly(m, np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], np.int32), 1)
    m = cv2.warpPerspective(m, Hm, (a.shape[1], a.shape[0])) > 0
    m = cv2.erode(m.astype(np.uint8), np.ones((15, 15))) > 0
    if m.sum() < 500: continue
    out.append(f"f{f}:{np.abs(wa - fr[f])[m].mean():.1f}/{np.abs(a - fr[f])[m].mean():.1f}")
print(sys.argv[2].split("/")[-1][:-5].ljust(7), " ".join(out))
