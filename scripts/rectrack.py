#!/usr/bin/env python3
"""rectrack.py <video> <a> <b> <out.json> --rule <name> [--roi x,y,w,h | --roitrack track.json:x,y,w,h]
Bounding box per frame of a UI element found by a colour rule, full-res px. Rules:
  notteal   pixels that are not teal (G-R<20) : a photo/window floating on a teal gradient
  white     near-white pixels (all channels > 235)
  dark      near-black (all < 40)
ROI restricts the search; --roitrack maps the ROI (given in a camtrack anchor's coords) through
that track per frame. Prints and writes {f:[x,y,w,h]} using the largest connected component."""
import sys, json, subprocess, argparse
import numpy as np, cv2
ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int); ap.add_argument("out")
ap.add_argument("--rule", default="notteal"); ap.add_argument("--roi"); ap.add_argument("--roitrack")
ap.add_argument("--minarea", type=int, default=2000)
A = ap.parse_args()
W, H = 1920, 1080
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=between(n\\,{A.a}\\,{A.b})",
                      "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
trk = None
if A.roitrack:
    p, r = A.roitrack.split(":"); trk = json.load(open(p))["frames"]; roi0 = [float(v) for v in r.split(",")]
out = {}
for i, im in enumerate(fr):
    f = A.a + i
    x0, y0, x1, y1 = 0, 0, W, H
    if A.roi:
        x, y, w, h = [int(v) for v in A.roi.split(",")]; x0, y0, x1, y1 = x, y, x + w, y + h
    if trk and str(f) in trk:
        s, r, tx, ty, _ = trk[str(f)]
        x0, y0 = int(roi0[0] * s + tx), int(roi0[1] * s + ty); x1, y1 = int((roi0[0] + roi0[2]) * s + tx), int((roi0[1] + roi0[3]) * s + ty)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    c = im[y0:y1, x0:x1].astype(int); R, G, B = c[..., 0], c[..., 1], c[..., 2]
    if A.rule == "notteal": m = (G - R) < 20
    elif A.rule == "white": m = (R > 235) & (G > 235) & (B > 235)
    else: m = (R < 40) & (G < 40) & (B < 40)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2: continue
    k = 1 + np.argmax(st[1:, 4])
    if st[k, 4] < A.minarea: continue
    x, y, w, h = st[k, :4]
    out[f] = [int(x + x0), int(y + y0), int(w), int(h)]
json.dump(out, open(A.out, "w"))
for f in list(out)[::max(1, len(out) // 20)]: print(f, out[f])
