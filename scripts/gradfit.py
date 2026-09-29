#!/usr/bin/env python3
"""gradfit.py <video> <a> <b> <step> <out.json> [--k 7] [--mask x,y,w,h ...] [--track cam.json]

Fits a soft blurred-colour background (mesh gradient, blurred "aurora" blobs) with K Gaussian
blobs blended as a normalised RBF:  colour(p) = sum_i w_i(p) c_i / sum_i w_i(p),
w_i(p) = a_i * exp(-0.5 * rotated((p - m_i)/s_i)^2). Fits every <step> frames from a to b, each
fit warm-started from the previous one so blob identities persist and can be interpolated.
Masks exclude UI in full-res px (a window, text, a phone). Coordinates are output in full-res
pixels of the frame (or, with --track, of the camtrack anchor frame).

Output: {"k":K,"frames":{f:[[cx,cy,sx,sy,theta,a,r,g,b], ...]}, "rms":{f:err}}
The HTML side renders the same formula per pixel on a small canvas and upscales it.
"""
import json, subprocess, argparse
import numpy as np
from scipy.optimize import least_squares

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("step", type=int); ap.add_argument("out")
ap.add_argument("--k", type=int, default=7); ap.add_argument("--mask", action="append", default=[])
ap.add_argument("--init", help="json from a previous fit: warm start from its first/last frame")
A = ap.parse_args()
W, H, w, h = 1920, 1080, 96, 54
sx_, sy_ = W / w, H / h
frames = list(range(A.a, A.b + 1, A.step))
if frames[-1] != A.b: frames.append(A.b)
yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
xx = (xx + .5) * sx_; yy = (yy + .5) * sy_
mask = np.ones((h, w), bool)
for m in A.mask:
    x, y, mw, mh = [float(v) for v in m.split(",")]
    mask &= ~((xx > x) & (xx < x + mw) & (yy > y) & (yy < y + mh))


def grab(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=eq(n\\,{f}),scale={w}:{h}:flags=area",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float64) / 255


def render(P):
    P = P.reshape(-1, 9)
    num = np.zeros((h, w, 3)); den = np.zeros((h, w)) + 1e-9
    for cx, cy, sx, sy, th, la, r, g, b in P:
        c, s = np.cos(th), np.sin(th)
        dx, dy = xx - cx, yy - cy
        u, v = (c * dx + s * dy) / abs(sx), (-s * dx + c * dy) / abs(sy)
        wgt = np.exp(la) * np.exp(-0.5 * (u * u + v * v))
        num += wgt[..., None] * np.array([r, g, b]); den += wgt
    return num / den[..., None]


def init_from(img):
    K = A.k; P = []
    rng = np.random.default_rng(1)
    for i in range(K):
        cx, cy = rng.uniform(0.1, 0.9) * W, rng.uniform(0.1, 0.9) * H
        ix, iy = min(w - 1, int(cx / sx_)), min(h - 1, int(cy / sy_))
        P.append([cx, cy, 500, 350, 0, 0, *img[iy, ix]])
    return np.array(P, float).ravel()


res = {"k": A.k, "frames": {}, "rms": {}}
prev = None
if A.init:
    J = json.load(open(A.init)); fs = sorted(J["frames"], key=int)
    prev = np.array(J["frames"][fs[0] if abs(int(fs[0]) - A.a) < abs(int(fs[-1]) - A.a) else fs[-1]]).ravel()
for n, f in enumerate(frames):
    img = grab(f)
    x0 = prev if prev is not None else init_from(img)
    tries = [x0] if prev is not None else [x0] + [init_from(img) for _ in range(0)]
    best = None
    for t in tries:
        lo = np.tile([-900, -900, 140, 140, -np.pi, -8, 0, 0, 0], A.k); hi = np.tile([2800, 2000, 3000, 3000, np.pi, 8, 1, 1, 1], A.k)
        t = np.clip(t, lo + 1e-6, hi - 1e-6)
        r = least_squares(lambda P: (render(P) - img)[mask].ravel(), t, method="trf", max_nfev=400 if prev is not None else 3000,
                          x_scale="jac", bounds=(lo, hi))
        if best is None or r.cost < best.cost: best = r
    prev = best.x
    err = float(np.sqrt(np.mean(((render(best.x) - img)[mask]) ** 2)) * 255)
    res["frames"][f] = [[round(float(v), 4) for v in blob] for blob in best.x.reshape(-1, 9)]
    res["rms"][f] = round(err, 2)
    print(f, "rms %.2f/255" % err, flush=True)
json.dump(res, open(A.out, "w"))
