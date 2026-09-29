#!/usr/bin/env python3
"""gridcam.py video.mp4 cam.json out.json --calib A-B --fit A-B [--roi x,y,w,h per calib frame]

Refines a chained camera (camtrack.py) where the picture is a regular grid (tiles, cells,
keyboard keys, a calendar). A chain drifts a few % over 100 frames of big zoom; a grid gives
an absolute ruler every frame.
1. calib: in frames where the chain is trustworthy (low zoom), detect grid lines, map them to
   world (anchor) space through the chain -> world origin X0,Y0 and pitch P.
2. fit: in every frame of the fit range, detect grid lines, give each an integer index by
   predicting from the NEXT frame's fitted camera (walks backwards from the calib end, so the
   index never jumps a cell), least-squares s, tx, ty.
Writes cam json with the fitted frames replaced (other frames kept from the chain).
"""
import sys, json, argparse
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("cam"); ap.add_argument("out")
ap.add_argument("--calib", required=True); ap.add_argument("--fit", required=True)
ap.add_argument("--dark", type=float, default=150); ap.add_argument("--cover", type=float, default=0.3)
ap.add_argument("--roi", default=None, help="x,y,w,h screen rect to search for lines in calib frames")
ap.add_argument("--fwd", default=None, help="A-B: also walk FORWARD from the calib end, searching only inside the board (needs --board)")
ap.add_argument("--board", default=None, help="kx0,kx1,ky0,ky1 grid-line indices of the board edges (for --fwd ROI)")
o = ap.parse_args()
cam = {r["f"]: r for r in json.load(open(o.cam))}
ca, cb = map(int, o.calib.split("-")); fa, fb = map(int, o.fit.split("-"))

cap = cv2.VideoCapture(o.video); G = {}; i = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    if min(ca, fa) <= i <= max(cb, fb): G[i] = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    i += 1

def cluster(idx, gap=3):
    if len(idx) == 0: return np.array([])
    out, cur = [], [idx[0]]
    for v in idx[1:]:
        if v - cur[-1] <= gap: cur.append(v)
        else: out.append(np.mean(cur)); cur = [v]
    out.append(np.mean(cur)); return np.array(out)

def lines(g, roi=None):
    x0 = y0 = 0
    if roi: x0, y0, w, h = roi; g = g[y0:y0 + h, x0:x0 + w]
    d = g < o.dark
    return cluster(np.where(d.mean(0) > o.cover)[0]) + x0, cluster(np.where(d.mean(1) > o.cover)[0]) + y0

# 1. calibrate world grid
roi = tuple(map(int, o.roi.split(","))) if o.roi else None
wx, wy = [], []
for f in range(ca, cb + 1):
    c = cam[f]; lx, ly = lines(G[f], roi)
    wx.append((lx - c["tx"]) / c["s"]); wy.append((ly - c["ty"]) / c["s"])
allx = np.concatenate(wx); ally = np.concatenate(wy)
dx = np.concatenate([np.diff(w) for w in wx]); dy = np.concatenate([np.diff(w) for w in wy])
P = float(np.median(np.concatenate([dx[(dx > 5)], dy[(dy > 5)]])))
X0 = float(np.median(np.mod(allx, P))); Y0 = float(np.median(np.mod(ally, P)))
# refine pitch by lsq over index
kx = np.round((allx - X0) / P); ky = np.round((ally - Y0) / P)
A = np.concatenate([np.c_[kx, np.ones_like(kx), np.zeros_like(kx)], np.c_[ky, np.zeros_like(ky), np.ones_like(ky)]])
b = np.concatenate([allx, ally])
keep = np.abs(A @ np.array([P, X0, Y0]) - b) < 0.2 * P
P, X0, Y0 = np.linalg.lstsq(A[keep], b[keep], rcond=None)[0]
print(f"world grid: pitch {P:.3f}  X0 {X0:.2f}  Y0 {Y0:.2f}  ({keep.sum()} lines)")

# 2. fit, walking backwards from fb (then optionally forwards)
res = dict(cam)
def walk(order, prev, board=None):
  for f in order:
      # predict with the chain's relative step from prev frame
      c0, c1 = cam[f], cam[prev["f"]]
      ratio = c0["s"] / c1["s"]
      ps = prev["s"] * ratio
      # keep the chain's screen-space motion of the world point under screen centre
      cxw = (960 - c1["tx"]) / c1["s"]; cyw = (540 - c1["ty"]) / c1["s"]
      sx = c0["s"] * cxw + c0["tx"]; sy = c0["s"] * cyw + c0["ty"]
      pcx = (960 - prev["tx"]) / prev["s"]; pcy = (540 - prev["ty"]) / prev["s"]
      ptx = sx - ps * pcx; pty = sy - ps * pcy
      roi = None
      if board:
          bx0 = ps * (X0 + board[0] * P) + ptx; bx1 = ps * (X0 + board[1] * P) + ptx
          by0 = ps * (Y0 + board[2] * P) + pty; by1 = ps * (Y0 + board[3] * P) + pty
          m = 3
          roi = (max(0, int(bx0 - m)), max(0, int(by0 - m)), int(bx1 - bx0 + 2 * m), int(by1 - by0 + 2 * m))
      lx, ly = lines(G[f], roi)
      rows = []; rhs = []
      for v in lx:
          wv = (v - ptx) / ps; k = round((wv - X0) / P)
          if abs(wv - (X0 + k * P)) < 0.25 * P: rows.append([X0 + k * P, 1, 0]); rhs.append(v)
      for v in ly:
          wv = (v - pty) / ps; k = round((wv - Y0) / P)
          if abs(wv - (Y0 + k * P)) < 0.25 * P: rows.append([Y0 + k * P, 0, 1]); rhs.append(v)
      if len(rows) >= 4 and len({r[1] for r in rows}) == 2:
          A = np.array(rows); b = np.array(rhs)
          sol = np.linalg.lstsq(A, b, rcond=None)[0]
          err = np.abs(A @ sol - b); keep = err < max(3, 3 * np.median(err))
          sol = np.linalg.lstsq(A[keep], b[keep], rcond=None)[0]
          rms = float(np.sqrt(np.mean((A[keep] @ sol - b[keep]) ** 2)))
          cur = {"f": f, "s": float(sol[0]), "tx": float(sol[1]), "ty": float(sol[2]), "rot": 0, "cc": None, "grid_rms": rms, "n": int(keep.sum())}
      else:
          cur = {"f": f, "s": ps, "tx": ptx, "ty": pty, "rot": 0, "cc": None, "grid_rms": None, "n": 0}
      res[f] = cur; prev = cur
walk(range(fb, fa - 1, -1), cam[fb])
if o.fwd:
    A_, B_ = map(int, o.fwd.split("-"))
    board = list(map(int, o.board.split(",")))
    cap = cv2.VideoCapture(o.video); i = 0
    while True:
        ok, fr = cap.read()
        if not ok or i > B_: break
        if i >= A_ and i not in G: G[i] = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        i += 1
    walk(range(A_, B_ + 1), res[A_ - 1], board)
out = [res[k] for k in sorted(res)]
json.dump({"grid": {"P": P, "X0": X0, "Y0": Y0}, "cam": out}, open(o.out, "w"), indent=0)
for f in sorted(res)[::10]:
    if f > (int(o.fwd.split("-")[1]) if o.fwd else fb) or f < fa: continue
    r = res[f]; c = cam[f]
    print(f"f{f:4d} s={r['s']:8.4f} (chain {c['s']:8.4f}) tx={r['tx']:9.1f} ty={r['ty']:9.1f} rms={r.get('grid_rms')} n={r.get('n')}")
