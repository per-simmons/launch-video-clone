#!/usr/bin/env python3
"""wordtime.py <video> <a> <b> <camtrack.json> <out.json> --line y1,y2,... [--x0 600 --x1 1600]

Per-word typing timing for text that types on while the camera moves. Each frame is warped back into
the camtrack's anchor coordinates (inverse similarity), then for every text line (band y-34..y+10
around the given anchor baseline) it records, per frame:
  any  = right-most x with any ink (grey or black, gray < 215)  -> when a word appears
  dark = right-most x with near-final ink (gray < 90)            -> when it has finished fading in
Output {line_y: {frame: [any, dark]}}. Compare two videos with --vs other.json: prints, per line and per
40 px step of x, the frame each video first reaches it for any/dark, and the mean offsets."""
import sys, json, subprocess, argparse
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("track"); ap.add_argument("out")
ap.add_argument("--line", required=True); ap.add_argument("--x0", type=int, default=600); ap.add_argument("--x1", type=int, default=1640)
ap.add_argument("--vs")
A = ap.parse_args()
lines = [float(v) for v in A.line.split(",")]
T = json.load(open(A.track))["frames"]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=between(n\\,{A.a}\\,{A.b})", "-fps_mode", "passthrough",
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920)
out = {str(y): {} for y in lines}
for i, g in enumerate(fr):
    f = A.a + i; s, r, tx, ty, _ = T[str(f)]; th = np.radians(r)
    M = np.array([[s * np.cos(th), -s * np.sin(th), tx], [s * np.sin(th), s * np.cos(th), ty]])
    w = cv2.warpAffine(g, cv2.invertAffineTransform(M), (1920, 1400), flags=cv2.INTER_LINEAR, borderValue=248)
    for y in lines:
        band = w[int(y - 26):int(y + 14), A.x0:A.x1]
        anyc = np.where((band < 215).sum(0) > 1)[0]; dk = np.where((band < 90).sum(0) > 1)[0]
        out[str(y)][f] = [int(anyc.max() + A.x0) if len(anyc) else -1, int(dk.max() + A.x0) if len(dk) else -1]
json.dump(out, open(A.out, "w"))
if A.vs:
    B = json.load(open(A.vs)); da, dd = [], []
    for y in lines:
        ra, rb = out[str(y)], B[str(y)]
        def first(D, k, x):
            for f in sorted(D, key=int):
                if D[f][k] >= x: return int(f)
            return None
        xs = range(A.x0 + 40, A.x1, 40); row = []
        for x in xs:
            a_any, b_any, a_dk, b_dk = first(ra, 0, x), first(rb, 0, x), first(ra, 1, x), first(rb, 1, x)
            if a_any is None or b_any is None: continue
            row.append((x, a_any, b_any, a_dk, b_dk))
            da.append(a_any - b_any)
            if a_dk is not None and b_dk is not None: dd.append((a_dk - a_any) - (b_dk - b_any))
        print(f"line {y}: " + " ".join(f"x{x}:{p}/{q}" for x, p, q, _, _ in row[:12]))
    print(f"appear offset (this - other): mean {np.mean(da):+.2f} f  median {np.median(da):+.1f} f  n={len(da)}")
    print(f"fade length difference (this - other): mean {np.mean(dd):+.2f} f  median {np.median(dd):+.1f} f")
