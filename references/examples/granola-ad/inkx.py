#!/usr/bin/env python3
"""inkx.py <video> <a> <b> x,y,w,h [--dark|--light] [--thr 60]
Per frame: right-most and bottom-most 'ink' pixel inside a region (text typing on), relative to the region,
plus ink pixel count. Ink = darker (default) or lighter than the region's median by --thr. Reads typing
cadence without eyeballing: the right edge steps once per typed character/word."""
import sys, subprocess, numpy as np, argparse
ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int)
ap.add_argument("roi"); ap.add_argument("--light", action="store_true"); ap.add_argument("--thr", type=float, default=60)
A = ap.parse_args(); x, y, w, h = [int(v) for v in A.roi.split(",")]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A.video, "-vf", f"select=between(n\\,{A.a}\\,{A.b}),crop={w}:{h}:{x}:{y}",
                      "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(float)
prev = None
for i, g in enumerate(fr):
    med = np.median(g); ink = (g > med + A.thr) if A.light else (g < med - A.thr)
    cols = np.where(ink.sum(0) > 1)[0]; rows = np.where(ink.sum(1) > 1)[0]
    r = (int(cols.max()) if len(cols) else -1, int(rows.max()) if len(rows) else -1, int(ink.sum()))
    if r != prev: print(A.a + i, "right", r[0], "bottom", r[1], "ink", r[2])
    prev = r
