#!/usr/bin/env python3
"""gen_data.py: measured reference data -> hf/data.js (camera per frame, board reveal map, glyph
bitmaps, the end-card logo track). Everything the composition draws comes from here."""
import json, numpy as np
from scipy.signal import savgol_filter
P = ""  # run from the clone project root (the folder holding reference/ and hf/)
cam = json.load(open(P + "reference/cam_final.json"))
s = np.array([c["s"] for c in cam]); tx = np.array([c["tx"] for c in cam]); ty = np.array([c["ty"] for c in cam])
# smooth in log-scale and in the screen position of a world anchor (board centre), keep f0-20 static
AX, AY = 1030.0, 688.0
ls = np.log(s); X = s * AX + tx; Y = s * AY + ty
def sm(v, a=20, b=223, w=7):
    v = v.copy(); v[a:b] = savgol_filter(v[a:b], w, 2); return v
ls2, X2, Y2 = sm(ls), sm(X), sm(Y)
s2 = np.exp(ls2); tx2 = X2 - s2 * AX; ty2 = Y2 - s2 * AY
CAM = [[round(float(a), 6), round(float(b), 3), round(float(c), 3)] for a, b, c in zip(s2, tx2, ty2)]

board = json.load(open(P + "reference/board.json"))
EVENTS = [21, 41, 64, 72, 84, 90, 109, 120, 129, 133, 158, 164, 170]
fix = {-73: 64, -88: 84}
B = []
for c in board:
    rv = c["reveal"]
    if rv is None: rv = 10**6
    elif rv < 0: rv = fix.get(rv, max([e for e in EVENTS if e <= -rv], default=21))
    # cells the probe could not see at their reveal (cut by the top edge): fixed from the pair sheets
    rv = {(2, 4): 41, (2, 5): 41, (2, 7): 41}.get((c["r"], c["c"]), rv)
    B.append([c["r"], c["c"], c["g"], int(rv)])
glyphs = json.load(open(P + "reference/glyphs.json"))
G = {k: {"x": v["x"], "y": v["y"], "bm": v["bm"]} for k, v in glyphs.items()}
out = "window.DATA=" + json.dumps({"cam": CAM, "board": B, "glyphs": G}, separators=(",", ":")) + ";\n"
open(P + "hf/data.js", "w").write(out)
print("wrote data.js", len(out), "bytes; cam f0", CAM[0], "f126", CAM[126], "f222", CAM[222])
