#!/usr/bin/env python3
"""platefit.py <plate.png> <ref_frame.png> <out.jpg> [--margin 0.08] [--mask x,y,w,h ...] [--affine]

gpt-image returns a plate that is close to the reference frame but shifted/scaled (and 3:2, not 16:9).
This registers the plate onto the reference frame (SIFT + RANSAC homography, or --affine for a
similarity), then warps it into the reference's pixel grid with a margin on every side so a
camera track can zoom out a little. Output size = (1920, 1080) * (1 + 2*margin); the reference
frame's (0,0) sits at (margin*1920, margin*1080) in the output. Masks (ref coords) exclude
regions from matching (a lit screen, UI). Prints inlier count and the reprojection error.
"""
import argparse, numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument("plate"); ap.add_argument("ref"); ap.add_argument("out")
ap.add_argument("--margin", type=float, default=0.08); ap.add_argument("--mask", action="append", default=[])
ap.add_argument("--affine", action="store_true")
ap.add_argument("--target", help="x,y,w,h: map the plate's black-screen bbox onto this measured rect (non-uniform scale)")
ap.add_argument("--grade", action="store_true", help="match the plate's colour to the reference (LAB mean/std on non-dark pixels)")
ap.add_argument("--screen", choices=["quad", "rect"], help="register on the black phone screen instead of features: "
                "quad = 4-corner homography (angled phone), rect = scale+translate from its left/right/top edges")
A = ap.parse_args()
P = cv2.imread(A.plate); R = cv2.imread(A.ref)
g = lambda im: cv2.createCLAHE(2.0, (8, 8)).apply(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
sift = cv2.SIFT_create(6000)
mR = np.full(R.shape[:2], 255, np.uint8)
for m in A.mask:
    x, y, w, h = [int(v) for v in m.split(",")]; mR[y:y + h, x:x + w] = 0
def screen_quad(im):
    """black screen: largest near-black component -> 4 corners (tl,tr,br,bl) via polygon approx of its hull."""
    m = (im.max(axis=2) < 40).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + np.argmax(st[1:, 4]); comp = (lab == k).astype(np.uint8)
    cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(cs[0])
    eps = 0.01 * cv2.arcLength(hull, True)
    for _ in range(60):
        ap_ = cv2.approxPolyDP(hull, eps, True)
        if len(ap_) <= 4: break
        eps *= 1.15
    q = ap_.reshape(-1, 2).astype(np.float32)
    c = q.mean(0); ang = np.arctan2(q[:, 1] - c[1], q[:, 0] - c[0]); q = q[np.argsort(ang)]  # clockwise from -pi
    q = np.roll(q, -int(np.argmin(q.sum(1))), axis=0)  # start at top-left
    return q, st[k, :4]


if A.screen:
    qp, bp = screen_quad(P); qr, br = screen_quad(R)
    print("plate screen", qp.round(1).tolist(), "\nref screen", qr.round(1).tolist())
    if A.target:
        x, y, w, h = [float(v) for v in A.target.split(",")]
        sx_ = w / bp[2]; sy_ = h / bp[3] if h > 0 else sx_; H = np.array([[sx_, 0, x - sx_ * bp[0]], [0, sy_, y - sy_ * bp[1]], [0, 0, 1]], float)
        print("target fit: sx %.4f sy %.4f" % (sx_, sy_))
    elif A.screen == "quad":
        H = cv2.getPerspectiveTransform(qp, qr)
    else:
        s_ = br[2] / bp[2]; H = np.array([[s_, 0, br[0] - s_ * bp[0]], [0, s_, br[1] - s_ * bp[1]], [0, 0, 1]], float)
    mx, my = int(1920 * A.margin), int(1080 * A.margin)
    T = np.array([[1, 0, mx], [0, 1, my], [0, 0, 1]], float)
    out = cv2.warpPerspective(P, T @ H, (1920 + 2 * mx, 1080 + 2 * my), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if A.grade:
        o = out[my:my + 1080, mx:mx + 1920]
        m = (o.max(2) > 70) & (R.max(2) > 70)
        lo, lr = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(np.float32), cv2.cvtColor(R, cv2.COLOR_BGR2LAB).astype(np.float32)
        so = lo[my:my + 1080, mx:mx + 1920][m]; sr = lr[m]
        lo = (lo - so.mean(0)) / (so.std(0) + 1e-6) * sr.std(0) + sr.mean(0)
        out = cv2.cvtColor(np.clip(lo, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
        print("graded: LAB mean", so.mean(0).round(1), "->", sr.mean(0).round(1))
    cv2.imwrite(A.out, out, [cv2.IMWRITE_JPEG_QUALITY, 94])
    print("scale", np.sqrt(abs(np.linalg.det(H[:2, :2]))), "->", A.out, "offset", mx, my)
    raise SystemExit
kp, dp = sift.detectAndCompute(g(P), None); kr, dr = sift.detectAndCompute(g(R), mR)
mt = cv2.BFMatcher().knnMatch(dp, dr, k=2)
good = [a for a, b in mt if a.distance < 0.8 * b.distance]
src = np.float32([kp[m.queryIdx].pt for m in good]); dst = np.float32([kr[m.trainIdx].pt for m in good])
if A.affine:
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4)
    H = np.vstack([M, [0, 0, 1]])
else:
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
inl = inl.ravel().astype(bool)
err = np.linalg.norm(cv2.perspectiveTransform(src[inl][None], H)[0] - dst[inl], axis=1)
print(f"matches {len(good)} inliers {inl.sum()} reproj err median {np.median(err):.2f}px")
mx, my = int(1920 * A.margin), int(1080 * A.margin)
T = np.array([[1, 0, mx], [0, 1, my], [0, 0, 1]], float)
out = cv2.warpPerspective(P, T @ H, (1920 + 2 * mx, 1080 + 2 * my), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
cv2.imwrite(A.out, out, [cv2.IMWRITE_JPEG_QUALITY, 94])
print("scale", np.sqrt(abs(np.linalg.det(H[:2, :2]))), "->", A.out, out.shape[1], "x", out.shape[0], "offset", mx, my)
