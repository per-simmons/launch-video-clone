#!/usr/bin/env python3
"""mkdata.py — turns the measured tracks in reference/track/ into hf/data.js (window.DATA), per-frame arrays
the composition reads directly. Camera tracks are smoothed with a short Savitzky-Golay filter on the 25 fps
samples (the reference moves in frame pairs), then held per pair so the clone steps like the reference."""
import json, numpy as np
from scipy.signal import savgol_filter
T = "reference/track/"
L = lambda n: json.load(open(T + n))


def cam(name, win=7):
    J = L(name); fs = sorted(int(k) for k in J["frames"])
    a = np.array([J["frames"][str(f)][:4] for f in fs], float)
    if len(fs) > win:
        a[:, 0] = savgol_filter(a[:, 0], win, 2); a[:, 2] = savgol_filter(a[:, 2], win, 2); a[:, 3] = savgol_filter(a[:, 3], win, 2)
        a[:, 1] = savgol_filter(a[:, 1], win, 1)
    return {"a": fs[0], "v": [[round(x, 5) for x in r] for r in a]}


D = {}
D["s1"] = cam("s1.json"); D["s3"] = cam("s3.json"); D["s5a"] = cam("s5a.json", 5); D["s5b"] = cam("s5b.json")
D["s2b"] = cam("s2b.json")
# shot 2 early camera from the teal screen width/centre (screen2.json), in f262 coords: s = width/358
S2 = L("screen2.json")
D["s2teal"] = {k: v for k, v in S2.items()}
# call window rect per frame (frame space)
W = {}
for n in ("win2.json", "win2b.json"):
    for k, v in L(n).items():
        k = int(k)
        if v[2] < 900 and (k <= 162 or 170 <= k <= 191): W[k] = v
fs = sorted(W); allf = range(94, 263)
arr = np.array([W[f] for f in fs], float)
D["win"] = {"a": 94, "v": [[round(float(np.interp(f, fs, arr[:, i])), 2) for i in range(4)] for f in allf]}
for g in ("grad2.json", "grad4.json", "grad5c.json"):
    try:
        J = L(g); ks = sorted(int(k) for k in J["frames"])
        A = np.array([J["frames"][str(k)] for k in ks], float)            # (T, K, 9)
        from scipy.ndimage import gaussian_filter1d
        # the fits jitter frame to frame (independent least-squares solves); the reference drifts slowly
        # (no temporal smoothing: blob parameters are non-linear, averaging them broke the picture, error 0.017 -> 0.19;
        #  the raw warm-started fits already step like the reference: 0.0053 vs 0.0050 per 4 f)
        D[g[:-5]] = {k: [[round(float(x), 4) for x in b] for b in A[i]] for i, k in enumerate(ks)}
    except FileNotFoundError:
        pass
D["screen1"] = L("screen1.json")["shot1_screen_f0"]
C = L("cursor.json"); fs = sorted(int(k) for k in C); a = np.array([C[str(f)] for f in fs], float)
D["cursor"] = {"a": 440, "v": [[round(float(np.interp(f, fs, a[:, i])), 1) for i in (0, 1, 4, 5)] for f in range(440, 601)]}
D["profile2"] = L("screen2-profile.json")
open("hf/data.js", "w").write("window.DATA=" + json.dumps(D, separators=(",", ":")) + ";\n")
print("hf/data.js", sum(len(json.dumps(v)) for v in D.values()), "bytes;", list(D))
