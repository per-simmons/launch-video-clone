#!/usr/bin/env python3
"""camtrack.py video.mp4 out.json [--anchor F] [--a A --b B] [--scale 0.5]

Measures a continuous camera (zoom + pan) across a one-take video. Frame-to-frame ECC
(affine, on a downscaled grey copy), chained so every frame is expressed against one
anchor frame. Output per frame: s (screen px per anchor px) and tx, ty, so that
  screen = s * anchor + (tx, ty)
Use the anchor frame's layout as your world coordinates; the camera for frame f is then
transform: translate(tx,ty) scale(s) with transform-origin 0 0.
"""
import sys, json, argparse
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--anchor", type=int, default=0)
ap.add_argument("--a", type=int, default=0); ap.add_argument("--b", type=int, default=10**9)
ap.add_argument("--scale", type=float, default=0.5)
ap.add_argument("--mask", action="append", default=[], help="A-B:x,y,w,h full-res rect to ignore in frames A..B (e.g. a logo drawn over the world)")
ap.add_argument("--mincc", type=float, default=0.97, help="steps below this ECC score are replaced by their neighbours' mean (content changes, not camera)")
o = ap.parse_args()

cap = cv2.VideoCapture(o.video)
frames = []
masks = []
i = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    if o.a <= i <= o.b:
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=o.scale, fy=o.scale, interpolation=cv2.INTER_AREA)
        frames.append(cv2.GaussianBlur(g, (5, 5), 0).astype(np.float32))
        m = np.ones_like(g, dtype=np.uint8)
        for spec in o.mask:
            rng, rect = spec.split(":"); A, B = map(int, rng.split("-")); x, y, w, h = map(int, rect.split(","))
            if A <= i <= B: m[int(y*o.scale):int((y+h)*o.scale), int(x*o.scale):int((x+w)*o.scale)] = 0
        masks.append(m)
    i += 1
n = len(frames); a0 = o.a
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)

def H(W): return np.vstack([W, [0, 0, 1]])
steps = []   # steps[k]: maps frame k coords -> frame k+1 coords (full-res)
cc = []
for k in range(n - 1):
    W = np.eye(2, 3, dtype=np.float32)
    try:
        c, W = cv2.findTransformECC(frames[k], frames[k + 1], W, cv2.MOTION_AFFINE, crit, masks[k] & masks[k + 1], 5)
    except cv2.error:
        c = -1
    # ECC: frames[k+1](W x) ~ frames[k](x)  => W maps k -> k+1
    M = H(W.astype(np.float64))
    S = np.diag([o.scale, o.scale, 1.0])
    M = np.linalg.inv(S) @ M @ S
    sc = float(np.sqrt(abs(np.linalg.det(M[:2, :2]))))   # project to scale + translate, no rotation/shear
    steps.append(np.array([[sc, 0, M[0, 2]], [0, sc, M[1, 2]], [0, 0, 1.0]]))
    cc.append(float(c))
bad = [k for k in range(len(steps)) if cc[k] < o.mincc]
good = [k for k in range(len(steps)) if cc[k] >= o.mincc]
for k in bad:
    lo = max([g for g in good if g < k], default=None); hi = min([g for g in good if g > k], default=None)
    nb = [steps[g] for g in (lo, hi) if g is not None and abs(g - k) <= 3]
    if nb: steps[k] = sum(nb) / len(nb)
print("replaced steps:", bad, file=sys.stderr)

anc = o.anchor - a0
# T[k]: maps anchor coords -> frame k coords
T = [None] * n
T[anc] = np.eye(3)
for k in range(anc + 1, n): T[k] = steps[k - 1] @ T[k - 1]
for k in range(anc - 1, -1, -1): T[k] = np.linalg.inv(steps[k]) @ T[k + 1]
out = []
for k in range(n):
    M = T[k]
    s = float(np.sqrt(abs(np.linalg.det(M[:2, :2]))))
    out.append({"f": k + a0, "s": s, "tx": float(M[0, 2]), "ty": float(M[1, 2]),
                "rot": float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))),
                "cc": cc[k] if k < len(cc) else None})
json.dump(out, open(o.out, "w"), indent=0)
for r in out[::10]:
    print(f"f{r['f']:4d} s={r['s']:8.4f} tx={r['tx']:9.1f} ty={r['ty']:9.1f} rot={r['rot']:+.3f} cc={r['cc']}")
