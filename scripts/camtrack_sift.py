#!/usr/bin/env python3
"""camtrack.py <video> <a> <b> <anchor> <out.json> [--mask x,y,w,h ...] [--scale 0.5]

Measures the camera move of a shot: for every frame f in [a,b], the similarity transform
(scale, rotation, tx, ty) that maps ANCHOR-frame pixel coords to frame-f pixel coords
(full-res). SIFT features frame-to-frame, RANSAC similarity (estimateAffinePartial2D), chained
out from the anchor in both directions. --mask excludes regions (anchor coords, rough) whose
content moves on its own (a phone screen playing video, UI). Use it to drive a still plate so it
moves exactly like the reference camera, and to map composited screens into the plate.

Output: {"a":a,"b":b,"anchor":k,"frames":{f:[s,rot_deg,tx,ty,inliers]}}
Apply in CSS as: transform-origin:0 0; transform: matrix(s*cos, s*sin, -s*sin, s*cos, tx, ty)
"""
import sys, json, subprocess, argparse
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("anchor", type=int); ap.add_argument("out")
ap.add_argument("--mask", action="append", default=[])
ap.add_argument("--scale", type=float, default=0.5)
A = ap.parse_args()

W, H = 1920, 1080
w, h = int(W * A.scale), int(H * A.scale)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=between(n\\,{A.a}\\,{A.b}),scale={w}:{h}",
                      "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
sift = cv2.SIFT_create(3000)
cla = cv2.createCLAHE(2.0, (8, 8))
feats = []
for g in fr:
    k, d = sift.detectAndCompute(cla.apply(g), None)
    feats.append((np.float32([p.pt for p in k]) if k else np.zeros((0, 2), np.float32), d))
bf = cv2.BFMatcher()
masks = [tuple(float(v) * A.scale for v in m.split(",")) for m in A.mask]


def rel(i, j, M_i):
    """similarity mapping frame i coords -> frame j coords (downscaled px)."""
    (pi, di), (pj, dj) = feats[i], feats[j]
    if di is None or dj is None or len(pi) < 8 or len(pj) < 8:
        return None, 0
    m = bf.knnMatch(di, dj, k=2)
    good = [x[0] for x in m if len(x) == 2 and x[0].distance < 0.75 * x[1].distance]
    if len(good) < 8:
        return None, 0
    src = np.float32([pi[g.queryIdx] for g in good]); dst = np.float32([pj[g.trainIdx] for g in good])
    if masks:  # drop points inside masked regions (mask given in anchor coords -> map to frame i)
        inv = cv2.invertAffineTransform(M_i)
        pa = src @ inv[:, :2].T + inv[:, 2]
        keep = np.ones(len(src), bool)
        for (x, y, mw, mh) in masks:
            keep &= ~((pa[:, 0] > x) & (pa[:, 0] < x + mw) & (pa[:, 1] > y) & (pa[:, 1] < y + mh))
        src, dst = src[keep], dst[keep]
        if len(src) < 8:
            return None, 0
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=4000)
    return M, int(inl.sum()) if inl is not None else 0


def comp(M2, M1):  # apply M1 then M2
    a = np.vstack([M1, [0, 0, 1]]); b = np.vstack([M2, [0, 0, 1]])
    return (b @ a)[:2]


n = len(fr); k = A.anchor - A.a
Ms = [None] * n; inls = [0] * n
Ms[k] = np.float32([[1, 0, 0], [0, 1, 0]])
for step in (1, -1):
    i = k
    while 0 <= i + step < n:
        j = i + step
        R, c = rel(i, j, Ms[i])
        if R is None:
            R = np.float32([[1, 0, 0], [0, 1, 0]])
        Ms[j] = comp(R, Ms[i]); inls[j] = c
        i = j
out = {"a": A.a, "b": A.b, "anchor": A.anchor, "frames": {}}
for i, M in enumerate(Ms):
    s = float(np.hypot(M[0, 0], M[1, 0])); r = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    out["frames"][A.a + i] = [round(s, 5), round(r, 4), round(float(M[0, 2]) / A.scale, 2), round(float(M[1, 2]) / A.scale, 2), inls[i]]
json.dump(out, open(A.out, "w"))
fs = out["frames"]
for f in list(fs)[:: max(1, n // 12)] + [A.b]:
    print(f, fs[f])
