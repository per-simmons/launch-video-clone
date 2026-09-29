#!/usr/bin/env python3
"""bgfield.py <ref.mp4> <out.js> — measured drifting-gradient backgrounds.
For each listed range, samples a 4x3 grid of 160x120 probes (median colour) every STEP frames from the reference and
writes window.BGF = {name: {a, b, step, k: [[12 x [r,g,b]] ...]}}. Probes that sit on UI in that range are listed in
SKIP and filled from the nearest valid probe in the same row (then column). The composition upsamples the 4x3 grid
bilinearly and blurs it: a colour field, not the picture."""
import sys, json, subprocess, numpy as np
XS, YS, STEP = [20, 620, 1140, 1740], [20, 480, 940], 3
# EDIT THESE for your reference: the values below are from one worked clone, as an example.
RANGES = {  # name: (a, b, probes to skip as (col,row))
    "s1": (0, 142, [(1, 1), (2, 1)]),
    "s2": (186, 315, [(1, 1), (2, 1)]),
    "lav7": (579, 631, [(1, 0), (2, 0), (1, 1), (2, 1), (1, 2), (2, 2)]),
    "lav8": (632, 694, [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]),
    "lav9": (695, 792, [(1, 1), (2, 1)]),
    "s10": (793, 832, [(1, 1), (2, 1)]),
}
def frames(v, a, b):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select=between(n\\,{a}\\,{b})", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920, 3)
out = {}
for name, (a, b, skip) in RANGES.items():
    F = frames(sys.argv[1], a, b); keys = []
    for i in range(0, len(F), STEP):
        g = np.zeros((3, 4, 3)); ok = np.ones((3, 4), bool)
        for c, x in enumerate(XS):
            for r, y in enumerate(YS):
                g[r, c] = np.median(F[i, y:y + 120, x:x + 160].reshape(-1, 3), 0); ok[r, c] = (c, r) not in skip
        for r in range(3):
            for c in range(4):
                if not ok[r, c]:
                    cands = [(abs(c2 - c), g[r, c2]) for c2 in range(4) if ok[r, c2]] or [(abs(r2 - r), g[r2, c]) for r2 in range(3) if ok[r2, c]]
                    g[r, c] = min(cands, key=lambda t: t[0])[1] if cands else g[r, c]
        keys.append([[int(v) for v in g[r, c]] for r in range(3) for c in range(4)])
    out[name] = dict(a=a, b=b, step=STEP, k=keys)
open(sys.argv[2], "w").write("window.BGF=" + json.dumps(out, separators=(",", ":")) + ";\n"); print(sys.argv[2], {k: len(v["k"]) for k, v in out.items()})
