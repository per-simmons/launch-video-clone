#!/usr/bin/env python3
"""alive.py — find the parts of a picture that move on their own, and measure them.

  alive.py map  <video> <a> <b> <out.png>        where does it move INSIDE the frame (f a..b)?
  alive.py stat <video> <a> <b> <x,y,w,h> [...]  how much it moves there (compare ref vs clone)

`map` removes the camera move first (whole-frame shift, found by phase correlation, frame to
frame) and then shows what still changes: the living parts. Output: the middle frame with a
heat overlay (bright = moves on its own) + a text list of the hottest regions. A "still" that
lights up here is alive in the reference and needs a living-still treatment (SKILL.md).

`stat` gives, for a region (full-res pixels), the two numbers the global compare can't see:
  change%   share of pixels whose brightness changes by >4/255 frame to frame (how busy it is)
  detail    mean absolute Laplacian (how much fine texture: drops, grain, sparkle, trails)
Run it on the reference and the clone over the same frames; they should match within ~15%.
"""
import json, subprocess, sys
import numpy as np
from PIL import Image


def probe(v):
    s = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height", "-of", "json", v], capture_output=True, text=True).stdout)["streams"][0]
    return s["width"], s["height"]


def frames(v, a, b, w=None, crop=None):
    vf = f"select=between(n\\,{a}\\,{b})"
    W, H = probe(v)
    if crop:
        x, y, cw, ch = crop
        vf += f",crop={cw}:{ch}:{x}:{y}"
        W, H = cw, ch
    if w:
        h = int(round(H * w / W / 2)) * 2
        vf += f",scale={w}:{h}"
        W, H = w, h
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", vf, "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def shift(a, b):
    """Integer (dy, dx) that best aligns b onto a (phase correlation)."""
    F = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    r = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    dy, dx = np.unravel_index(np.argmax(r), r.shape)
    H, W = a.shape
    return (dy - H if dy > H // 2 else dy), (dx - W if dx > W // 2 else dx)


def cmd_map(v, a, b, out):
    fr = frames(v, a, b, w=480)
    if len(fr) < 3:
        sys.exit("need at least 3 frames")
    heat = np.zeros_like(fr[0])
    for i in range(1, len(fr)):
        dy, dx = shift(fr[i - 1], fr[i])
        al = np.roll(fr[i], (dy, dx), axis=(0, 1))
        d = np.abs(al - fr[i - 1])
        m = 8  # ignore wrapped borders
        d[:m, :] = d[-m:, :] = 0; d[:, :m] = d[:, -m:] = 0
        heat += d
    heat /= (len(fr) - 1)
    hn = np.clip(heat / max(1e-6, np.percentile(heat, 99.5)), 0, 1)
    base = np.stack([fr[len(fr) // 2]] * 3, -1) * 0.55
    over = np.zeros_like(base); over[..., 0] = 255 * hn; over[..., 1] = 180 * hn ** 2
    Image.fromarray(np.clip(base + over, 0, 255).astype(np.uint8)).save(out)
    # hottest 6x6 grid cells, in full-res coordinates
    W, H = probe(v); gh, gw = heat.shape; cy, cx = gh // 6, gw // 6
    cells = sorted(((float(heat[r*cy:(r+1)*cy, c*cx:(c+1)*cx].mean()), r, c) for r in range(6) for c in range(6)), reverse=True)
    sx, sy = W / gw, H / gh
    print(f"{out}\nhottest regions (x,y,w,h full-res : mean residual motion):")
    for val, r, c in cells[:6]:
        print(f"  {int(c*cx*sx)},{int(r*cy*sy)},{int(cx*sx)},{int(cy*sy)} : {val:.2f}")


def cmd_stat(v, a, b, region):
    x, y, w, h = [int(t) for t in region.split(",")]
    fr = frames(v, a, b, crop=(x, y, w, h))
    ch = float((np.abs(np.diff(fr, axis=0)) > 4).mean() * 100) if len(fr) > 1 else 0.0
    lap = np.abs(fr[:, 1:-1, 1:-1] * 4 - fr[:, :-2, 1:-1] - fr[:, 2:, 1:-1] - fr[:, 1:-1, :-2] - fr[:, 1:-1, 2:]).mean() / 255
    print(f"{v} f{a}-{b} region {region}: change {ch:.2f}%  detail {lap:.3f}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("map", "stat"):
        sys.exit(__doc__)
    if sys.argv[1] == "map":
        cmd_map(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    else:
        cmd_stat(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
