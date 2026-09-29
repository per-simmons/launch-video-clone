#!/usr/bin/env python3
"""cellmap.py video.mp4 cam_grid.json out.json --board kx0,kx1,ky0,ky1 [--a 0 --b 222]

For a grid whose cells change state over time (Minesweeper reveals, a calendar filling,
tiles flipping), samples every cell through the measured camera in every frame and reports,
per cell: first frame it reads as revealed, frames it reads as pressed, and its content
(colour class of the glyph) from the sharpest frame after the reveal.
"""
import json, argparse
import cv2, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("cam"); ap.add_argument("out")
ap.add_argument("--board", required=True); ap.add_argument("--a", type=int, default=0); ap.add_argument("--b", type=int, default=222)
o = ap.parse_args()
d = json.load(open(o.cam)); cam = {r["f"]: r for r in d["cam"]}; P, X0, Y0 = d["grid"]["P"], d["grid"]["X0"], d["grid"]["Y0"]
kx0, kx1, ky0, ky1 = map(int, o.board.split(","))
C, R = kx1 - kx0, ky1 - ky0
cap = cv2.VideoCapture(o.video); i = 0
state = {}   # (c,r) -> list of (f, cls, pitch)
def classify(patch):
    # patch: BGR cell interior (edges trimmed). returns state + glyph class
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(int); bgr = patch.reshape(-1, 3).astype(int)
    b, g, r = bgr[:, 0], bgr[:, 1], bgr[:, 2]
    blue = ((b > 150) & (r < 100) & (g < 100)).mean(); green = ((g > 90) & (r < 80) & (b < 80)).mean()
    red = ((r > 150) & (g < 90) & (b < 90)).mean(); black = ((r < 60) & (g < 60) & (b < 60)).mean()
    grey = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    glyph = max([(blue, "1"), (green, "2"), (red, "3"), (black, "L")])
    return glyph, float(np.median(grey))
while True:
    ok, fr = cap.read()
    if not ok or i > o.b: break
    if i >= o.a and i in cam:
        c = cam[i]; s = c["s"]; pitch = P * s
        if pitch >= 9:
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            for cc in range(C):
                for rr in range(R):
                    x0 = s * (X0 + (kx0 + cc) * P) + c["tx"]; y0 = s * (Y0 + (ky0 + rr) * P) + c["ty"]
                    if x0 < 0 or y0 < 0 or x0 + pitch > 1919 or y0 + pitch > 1079: continue
                    # highlight probe: 2 px band just inside the top edge, middle third
                    hy = int(y0 + max(1, pitch * 0.07)); hx0 = int(x0 + pitch * 0.35); hx1 = int(x0 + pitch * 0.65)
                    hl = float(gray[hy, hx0:hx1].mean())
                    m = int(pitch * 0.22)
                    patch = fr[int(y0) + m:int(y0 + pitch) - m, int(x0) + m:int(x0 + pitch) - m]
                    if patch.size == 0: continue
                    (gv, gcls), med = classify(patch)
                    st = "up" if hl > 225 else ("pressed" if med < 170 else "open")
                    state.setdefault((cc, rr), []).append((i, st, gcls if gv > 0.03 else "", round(pitch, 1)))
    i += 1
out = []
for (cc, rr), obs in sorted(state.items()):
    opened = [f for f, st, g, p in obs if st == "open"]
    pressed = [f for f, st, g, p in obs if st == "pressed"]
    # first frame of a run of >= 2 consecutive "open" readings
    rf = None
    for k in range(len(obs) - 1):
        if obs[k][1] == "open" and obs[k + 1][1] == "open": rf = obs[k][0]; break
    # content: from the open observation with the biggest pitch
    op = [x for x in obs if x[1] == "open"]
    cont = max(op, key=lambda x: x[3])[2] if op else ""
    out.append({"c": cc, "r": rr, "reveal": rf, "pressed": pressed[:6], "content": cont,
                "seen": [obs[0][0], obs[-1][0]]})
json.dump(out, open(o.out, "w"), indent=0)
# print a map of reveal frames and content
grid = {(x["c"], x["r"]): x for x in out}
for rr in range(R):
    print(" ".join(f"{(grid.get((cc, rr), {}).get('content') or '.'):>1}{(grid.get((cc, rr), {}).get('reveal') or 0):>4}" for cc in range(C)))
print("pressed:", [(x["c"], x["r"], x["pressed"]) for x in out if x["pressed"]])
