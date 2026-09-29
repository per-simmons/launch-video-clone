#!/usr/bin/env python3
"""compare.py — grade a clone against its reference, frame for frame.

Runs after burst.py has analysed BOTH videos:
  burst.py ref.mp4 analysis/ref
  burst.py render.mp4 analysis/render
  compare.py analysis/ref analysis/render out/compare [--every 0.5]

Writes:
  pairs_NN.png   reference (left) vs clone (right) at the same timestamps
  energy.png     both motion-energy curves on one timeline (timing/easing drift is visible here)
  COMPARE.md     shot-structure diff, per-second visual distance, worst moments to fix first
"""
from __future__ import annotations
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from burst import font, decode  # noqa: E402


def frame_at(path, t, width):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={width}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    if not raw:
        return None
    h = len(raw) // (width * 3)
    return np.frombuffer(raw[: h * width * 3], np.uint8).reshape(h, width, 3)


def fit(img, w, h):
    if img is None:
        return np.zeros((h, w, 3), np.uint8)
    return np.asarray(Image.fromarray(img).resize((w, h)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_analysis")
    ap.add_argument("clone_analysis")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=0.5, help="seconds between compared timestamps")
    ap.add_argument("--w", type=int, default=560)
    ap.add_argument("--cut-list", help="comma-separated reference cut frames to use instead of burst's (hidden cuts: white-to-white, dark UI)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    R = json.load(open(os.path.join(a.ref_analysis, "analysis.json")))
    C = json.load(open(os.path.join(a.clone_analysis, "analysis.json")))
    rv, cv = R["video"], C["video"]
    rfps, cfps = R["meta"]["fps"], C["meta"]["fps"]
    dur = min(R["meta"]["dur"], C["meta"]["dur"])

    # visual distance per 1/10 s at analysis size (layout + colour agreement, not pixel identity)
    rw = 96
    def small(path, meta):
        fr = decode(path, meta["w"], meta["h"], 10)
        return np.stack([np.asarray(Image.fromarray(f).resize((rw, 54))) for f in fr]).astype(np.float32)
    rs, cs = small(rv, R["meta"]), small(cv, C["meta"])
    m = min(len(rs), len(cs))
    dist = np.abs(rs[:m] - cs[:m]).mean(axis=(1, 2, 3)) / 255.0  # 0 = identical, ~0.5 = unrelated

    # side-by-side pairs
    ts = list(np.arange(0, dur, a.every))
    H = int(a.w * 9 / 16)
    per = 6
    f, ft = font(15), font(20)
    for p in range(0, len(ts), per):
        chunk = ts[p:p + per]
        im = Image.new("RGB", (2 * a.w + 30, len(chunk) * (H + 28) + 40), (18, 18, 18))
        d = ImageDraw.Draw(im)
        d.text((8, 8), "REFERENCE (left)  vs  CLONE (right)", fill=(255, 220, 90), font=ft)
        for k, t in enumerate(chunk):
            y = 40 + k * (H + 28)
            i = min(m - 1, int(t * 10))
            d.text((8, y), f"t={t:.2f}s  ref f{int(t * rfps)}  clone f{int(t * cfps)}  distance {dist[i]:.3f}",
                   fill=(220, 220, 220), font=f)
            im.paste(Image.fromarray(fit(frame_at(rv, t, a.w), a.w, H)), (8, y + 22))
            im.paste(Image.fromarray(fit(frame_at(cv, t, a.w), a.w, H)), (a.w + 22, y + 22))
        im.save(os.path.join(a.out, f"pairs_{p // per + 1:02d}.png"))

    # energy overlay on a common seconds axis
    W, Hc = 1400, 260
    im = Image.new("RGB", (W, Hc), (18, 18, 18))
    d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 40, W - 10, 24, Hc - 28
    re, ce = np.array(R["energy"]), np.array(C["energy"])
    mx = max(re[1:].max() if len(re) > 1 else 1e-6, ce[1:].max() if len(ce) > 1 else 1e-6, 1e-6)
    def line(e, fps, col):
        pts = [(x0 + (x1 - x0) * (i / fps) / dur, y1 - (y1 - y0) * min(1, v / mx)) for i, v in enumerate(e) if i / fps <= dur]
        d.line(pts, fill=col, width=2)
    for s in R["shots"]:
        x = x0 + (x1 - x0) * s["start"] / dur
        d.line([x, y0, x, y1], fill=(90, 90, 40))
    for s in C["shots"]:
        x = x0 + (x1 - x0) * s["start"] / dur
        d.line([x, y0, x, y1], fill=(40, 70, 110))
    line(re, rfps, (120, 220, 140))
    line(ce, cfps, (230, 110, 110))
    for sec in range(int(dur) + 1):
        d.text((x0 + (x1 - x0) * sec / dur - 4, y1 + 6), str(sec), fill=(150, 150, 150), font=f)
    d.text((x0, 4), "motion energy: green = reference, red = clone; vertical ticks = cuts (yellow ref, blue clone)",
           fill=(210, 210, 210), font=f)
    im.save(os.path.join(a.out, "energy.png"))

    # timing/easing numbers: clone energy resampled onto the reference's frame clock
    rt = np.arange(len(re)) / rfps
    ce_r = np.interp(rt, np.arange(len(ce)) / cfps, ce) if len(ce) > 1 else np.zeros_like(re)
    keep = rt <= dur
    def corr(x, y):
        if len(x) < 3 or x.std() < 1e-9 or y.std() < 1e-9:
            return float("nan")
        return float(np.corrcoef(x, y)[0, 1])
    g_corr = corr(re[keep][1:], ce_r[keep][1:])
    g_ratio = float(ce_r[keep][1:].sum() / max(1e-9, re[keep][1:].sum()))
    shot_rows = []
    segs = []  # reference shots, long ones split into <=2 s windows so one-takes still get rows
    win = int(round(2 * rfps))
    for s in R["shots"]:
        a0, b0 = s["start_f"], s["end_f"] + 1
        k = 0
        while a0 < b0:
            e0 = min(b0, a0 + win) if (b0 - s["start_f"]) > 1.5 * win else b0
            segs.append(dict(shot=f"{s['shot']}" + (f".{k + 1}" if e0 - a0 < b0 - s["start_f"] or k else ""),
                             start_f=a0, end_f=e0 - 1, start=a0 / rfps, dur=(e0 - a0) / rfps))
            a0, k = e0, k + 1
    for s in segs:
        a0, b0 = s["start_f"], s["end_f"] + 1
        r_seg, c_seg = re[a0:b0].copy(), ce_r[a0:b0].copy()
        if len(r_seg) > 1:
            r_seg[0], c_seg[0] = r_seg[1], c_seg[1]
        i0, i1 = int(s["start"] * 10), max(int(s["start"] * 10) + 1, int((s["start"] + s["dur"]) * 10))
        d_shot = float(dist[min(i0, m - 1):min(i1, m)].mean()) if i0 < m else float("nan")
        # static window: reference barely moves, so corr/ratio are just encoder flicker
        static = float(r_seg.mean()) < 1e-4  # reference essentially frozen (encoder flicker only)
        # peak offset from the cross-correlation lag (-6..+6 f), not argmax: plateaus fooled argmax
        off = None
        if not static and len(r_seg) > 8 and r_seg.max() > 0.003:
            best, off = -2.0, 0
            for L in range(-6, 7):
                x = r_seg[max(0, -L):len(r_seg) - max(0, L)]
                y = c_seg[max(0, L):len(c_seg) - max(0, -L)]
                if len(x) > 4 and x.std() > 1e-9 and y.std() > 1e-9:
                    cc = float(np.corrcoef(x, y)[0, 1])
                    if cc > best:
                        best, off = cc, L
        shot_rows.append((s["shot"] + (" (static)" if static else ""), a0, b0 - 1, d_shot,
                          float("nan") if static else corr(r_seg, c_seg), off,
                          float("nan") if static else float(c_seg.sum() / max(1e-9, r_seg.sum()))))

    # report
    L = ["# Compare", "", f"ref: {os.path.basename(rv)} ({R['meta']['dur']:.2f}s, {len(R['shots'])} shots)",
         f"clone: {os.path.basename(cv)} ({C['meta']['dur']:.2f}s, {len(C['shots'])} shots)", ""]
    L.append(f"Mean visual distance: {dist.mean():.3f} (0 identical, ~0.1 same layout/colours, >0.25 different picture)")
    L.append(f"Motion-curve correlation: {g_corr:.3f} (1.0 = same timing+easing everywhere)")
    L.append(f"Total motion vs reference: {g_ratio:.2f}x (under 1 = clone moves less)")
    rc = [s["start"] for s in R["shots"][1:]]
    C_cut_starts = None
    if a.cut_list:
        rc = sorted(int(x) / rfps for x in a.cut_list.split(",") if x.strip())
        # hidden cuts in the clone show up as lone per-frame energy spikes
        cfr = np.array(C["energy"])
        spikes = [i / cfps for i in range(1, len(cfr) - 1)
                  if cfr[i] > 1.5 / 255 and cfr[i] >= cfr[i - 1] and cfr[i] >= cfr[i + 1]
                  and cfr[i] > 3 * max(float(np.median(cfr[max(1, i - 15):i + 16])), 1e-6)]
        C_cut_starts = sorted(set([s["start"] for s in C["shots"][1:]] + spikes))
    cc = C_cut_starts if C_cut_starts is not None else [s["start"] for s in C["shots"][1:]]
    if rc:
        offs = [min((abs(c - r) for c in cc), default=99) for r in rc]
        hit = sum(o <= 2 / rfps for o in offs)
        L.append(f"Reference cuts matched within 2 frames: {hit}/{len(rc)}")
        bad = [(r, o) for r, o in zip(rc, offs) if o > 2 / rfps]
        if bad:
            L.append("Missed/late cuts (ref time → nearest clone cut off by): " +
                     ", ".join(f"{r:.2f}s→{o * 1000:.0f}ms" for r, o in bad[:15]))
    L += ["", "## Per shot (reference shots; long shots split into 2 s windows)", "",
          "| shot | frames | distance | motion corr | lag (f, + = clone late) | motion ratio |",
          "|---|---|---|---|---|---|"]
    for sh, a0, b0, dd, cc, off, rr in shot_rows:
        L.append(f"| {sh} | f{a0}-{b0} | {dd:.3f} | {cc:.2f} | {'' if off is None else off} | {rr:.2f} |")
    L += ["", "## Worst seconds (fix these first)", ""]
    per_sec = [(s, float(dist[s * 10:(s + 1) * 10].mean())) for s in range(int(m / 10))]
    for s, v in sorted(per_sec, key=lambda x: -x[1])[:6]:
        L.append(f"- {s}–{s + 1}s: distance {v:.3f}")
    L += ["", "Read pairs_*.png and energy.png next. Distance measures layout/colour; timing and easing",
          "live in energy.png (peaks should line up and have the same shape)."]
    open(os.path.join(a.out, "COMPARE.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:10]))


if __name__ == "__main__":
    main()
