#!/usr/bin/env python3
"""track.py <video> <a> <b> <anchor> <x,y,w,h> <out.json> [--scale 0.5] [--plot out.png]

Per-frame 2D affine of ONE object (a UI card, a window, a photo plate) inside a shot, measured
with masked ECC between consecutive frames and chained outward from the anchor frame. The ROI
(anchor-frame px) is the object's box; the mask follows the object as it moves.

--mode homography also tracks perspective (tilts): use H (row-major 3x3, anchor px -> screen px) as
CSS matrix3d(h00,h10,0,h20, h01,h11,0,h21, 0,0,1,0, h02,h12,0,h22) with transform-origin 0 0.
Output per frame f: M = [a, b, c, d, e, f] with  screen = [[a c e],[b d f]] @ [x_anchor, y_anchor, 1]
plus s (uniform scale), r (rotation deg), cx, cy (where the ROI centre lands), cc (ECC score).
In CSS: lay the object out at its anchor-frame pixel position inside a 1920x1080 layer, then
transform: matrix(a,b,c,d,e,f) with transform-origin 0 0.
"""
import sys, json, argparse, math
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("anchor", type=int); ap.add_argument("roi"); ap.add_argument("out")
ap.add_argument("--scale", type=float, default=0.5)
ap.add_argument("--mode", default="affine", choices=["affine", "similarity", "translation", "homography"])
ap.add_argument("--plot")
o = ap.parse_args()
x, y, w, h = [float(v) for v in o.roi.split(",")]
S = o.scale
cap = cv2.VideoCapture(o.video); fr = {}; i = 0
while True:
    ok, im = cap.read()
    if not ok or i > o.b: break
    if i >= o.a:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
        fr[i] = cv2.GaussianBlur(g, (5, 5), 0).astype(np.float32)
    i += 1
H, W = next(iter(fr.values())).shape
mode = {"affine": cv2.MOTION_AFFINE, "similarity": cv2.MOTION_EUCLIDEAN, "translation": cv2.MOTION_TRANSLATION, "homography": cv2.MOTION_HOMOGRAPHY}[o.mode]
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
H3 = lambda M: np.vstack([M, [0, 0, 1]])
Sm = np.diag([S, S, 1.0]); Si = np.linalg.inv(Sm)

def mask_for(M):  # M: anchor(full px) -> frame(full px) 3x3; returns mask in scaled px
    pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float64)
    q = (M @ np.c_[pts, np.ones(4)].T).T; q = q[:, :2] / q[:, 2:3] * S
    m = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(m, q.astype(np.int32), 255); return m

def step(src, dst, M_src):
    """transform mapping frame src -> frame dst (full px), estimated inside the object's mask on src"""
    Wm = np.eye(3, 3, dtype=np.float32) if mode == cv2.MOTION_HOMOGRAPHY else np.eye(2, 3, dtype=np.float32)
    try:
        c, Wm = cv2.findTransformECC(fr[dst], fr[src], Wm, mode, crit, mask_for(M_src), 5)
    except cv2.error:
        return np.eye(3), -1.0
    # ECC: fr[src](Wm x) ~ fr[dst](x)  -> Wm maps dst->src; we want src->dst
    Wf = Wm.astype(np.float64); Wf = Wf if Wf.shape[0] == 3 else H3(Wf)
    return Si @ np.linalg.inv(Wf) @ Sm, float(c)

M = {o.anchor: np.eye(3)}; C = {o.anchor: 1.0}
for f in range(o.anchor + 1, o.b + 1):
    T, c = step(f - 1, f, M[f - 1]); M[f] = T @ M[f - 1]; C[f] = c
for f in range(o.anchor - 1, o.a - 1, -1):
    T, c = step(f + 1, f, M[f + 1]); M[f] = T @ M[f + 1]; C[f] = c
rows = []
cxa, cya = x + w / 2, y + h / 2
for f in sorted(M):
    m = M[f] / M[f][2, 2]; a, b, c, d, e, ff = m[0, 0], m[1, 0], m[0, 1], m[1, 1], m[0, 2], m[1, 2]
    s = math.sqrt(abs(a * d - b * c)); r = math.degrees(math.atan2(b, a))
    q = m @ [cxa, cya, 1]; cx, cy = q[:2] / q[2]
    rows.append(dict(f=f, M=[round(v, 5) for v in (a, b, c, d, e, ff)], H=[round(float(v), 8) for v in m.flatten()], s=round(s, 5), r=round(r, 3),
                     cx=round(cx, 2), cy=round(cy, 2), cc=round(C[f], 3)))
json.dump(dict(roi=[x, y, w, h], anchor=o.anchor, rows=rows), open(o.out, "w"))
bad = [r["f"] for r in rows if r["cc"] < 0.5]
print(f"{o.out}: {len(rows)} frames, low-confidence frames: {bad[:30]}{'...' if len(bad) > 30 else ''}")
if o.plot:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    F = [r["f"] for r in rows]; fig, ax = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    ax[0].plot(F, [r["cx"] for r in rows]); ax[0].set_ylabel("cx")
    ax[1].plot(F, [r["cy"] for r in rows]); ax[1].set_ylabel("cy")
    ax[2].plot(F, [r["s"] for r in rows]); ax[2].set_ylabel("scale")
    ax[3].plot(F, [r["r"] for r in rows]); ax[3].set_ylabel("rot deg")
    for a_ in ax: a_.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(o.plot, dpi=70)
