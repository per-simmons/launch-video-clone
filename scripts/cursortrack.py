#!/usr/bin/env python3
"""cursortrack.py <video> <a> <b> <out.json> [--k 15]
Finds a solid dark cursor per frame: near-black pixels, morphological opening with a k x k kernel (removes
text strokes), largest blob -> tip (top-left-most point), bbox. Prints changes. Full-res px."""
import sys, json, subprocess, numpy as np, cv2, argparse
ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("out"); ap.add_argument("--k", type=int, default=15)
A = ap.parse_args(); W, H = 1920, 1080
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=between(n\\,{A.a}\\,{A.b})", "-fps_mode",
                      "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
out = {}; prev = None
for i, g in enumerate(fr):
    m = cv2.morphologyEx((g < 45).astype(np.uint8), cv2.MORPH_OPEN, np.ones((A.k, A.k), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n < 2: continue
    k = 1 + np.argmax(st[1:, 4])
    if st[k, 4] < 200: continue
    ys, xs = np.where(lab == k); j = np.argmin(xs + ys)
    out[A.a + i] = [int(xs[j]), int(ys[j]), *[int(v) for v in st[k, :4]]]
    if out[A.a + i][:2] != prev: print(A.a + i, out[A.a + i])
    prev = out[A.a + i][:2]
json.dump(out, open(A.out, "w"))
