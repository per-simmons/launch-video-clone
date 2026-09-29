#!/usr/bin/env python3
"""bgcurve.py <ref.mp4> <clone.mp4> <a> <b> [step] — mean luminance of 6 background probe boxes (corners + edge
middles, 160x120) per frame, ref/clone side by side. Fit drifting gradient backgrounds to these, not to the eye."""
import sys, subprocess, numpy as np
P = [(20, 20), (880, 20), (1740, 20), (20, 940), (880, 940), (1740, 940)]
def lum(v, a, b):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select=between(n\\,{a}\\,{b}),format=gray", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920).astype(float)
    return np.array([[f[y:y + 120, x:x + 160].mean() for x, y in P] for f in fr])
a, b = int(sys.argv[3]), int(sys.argv[4]); st = int(sys.argv[5]) if len(sys.argv) > 5 else 5
R, C = lum(sys.argv[1], a, b), lum(sys.argv[2], a, b)
print("frame  " + "  ".join(f"{n:>9}" for n in ["TL", "TM", "TR", "BL", "BM", "BR"]) + "   (ref/clone)")
for i in range(0, len(R), st): print(f"f{a + i:<5} " + "  ".join(f"{R[i, k]:4.0f}/{C[i, k]:<4.0f}" for k in range(6)))
print("mean |ref-clone| per probe:", " ".join(f"{v:.1f}" for v in np.abs(R - C).mean(0)))
