#!/usr/bin/env python3
"""burst.py — turn a reference video into something a model can "watch".

Opus can't play video. It can read stills. Single keyframes lose what makes
motion design good: timing, easing, overshoot, how a transition actually
travels. This script decodes EVERY frame and writes:

  overview.png            one labelled frame per shot (the whole edit at a glance)
  shots/NN/burst.png      consecutive frames through the shot, frame-numbered
                          (shots > 4 s: burst_01.png, burst_02.png ... one per 2 s window)
  shots/NN/cut_in.png     every frame across the cut INTO this shot (transition anatomy)
  shots/NN/trail.png      motion trail: frames of the busiest moment, older = fainter
  shots/NN/curve.png      motion-energy per frame (the easing curve), beats marked
  analysis.json           shots, motion events + easing hints, palette, beats
  ANALYSIS.md             the same, readable

Usage: burst.py <video> <out_dir> [--cut 0.32] [--sheet-w 480]
Deps: ffmpeg/ffprobe on PATH, numpy, Pillow.
"""
from __future__ import annotations
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

AW = 192  # analysis width


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                          "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                                     "-show_entries", "stream=index", "-of", "csv=p=0", path],
                                    capture_output=True, text=True).stdout.strip())
    return dict(w=int(s["width"]), h=int(s["height"]), fps=fps,
                dur=float(j["format"]["duration"]), audio=has_audio)


def decode(path, w, h, fps):
    """All frames at analysis size, RGB uint8, shape (n, ah, AW, 3)."""
    ah = max(2, int(round(h * AW / w / 2)) * 2)
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={AW}:{ah}:flags=area",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (AW * ah * 3)
    return np.frombuffer(raw[: n * AW * ah * 3], np.uint8).reshape(n, ah, AW, 3)


def hist(f):
    q = (f // 32).astype(np.int32)  # 8 levels per channel
    idx = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    hgm = np.bincount(idx.ravel(), minlength=512).astype(np.float64)
    return hgm / hgm.sum()


def detect_cuts(fr, thresh, spike_cuts=False):
    n = len(fr)
    g = fr.astype(np.float32).mean(axis=3)
    energy = np.zeros(n)
    energy[1:] = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)) / 255.0
    hs = np.array([hist(f) for f in fr])
    hd = np.zeros(n)
    hd[1:] = 0.5 * np.abs(np.diff(hs, axis=0)).sum(axis=1)  # total variation, 0..1
    score = 0.6 * hd + 0.4 * np.clip(energy * 4, 0, 1)
    cuts = [0]
    for i in range(1, n):
        lo, hi = max(1, i - 3), min(n, i + 4)
        # --spike-cuts: dark UI cuts barely move the histogram, so also accept a lone per-frame diff
        # spike (>1.5/255, >3x local median). Raycast: 3 found vs 18 real without it. It also fires on
        # fast moves (Raycast 26, Kimi 66 vs 28), so check each extra cut on its cut_in.png sheet.
        med = float(np.median(energy[max(1, i - 15):min(n, i + 16)]))
        spike = spike_cuts and energy[i] > 1.5 / 255 and energy[i] > 3 * max(med, 1e-6) and energy[i] == energy[lo:hi].max()
        if ((score[i] >= thresh and score[i] == score[lo:hi].max()) or spike) and i - cuts[-1] >= 3:
            cuts.append(i)
    return cuts, energy, score


def audio_beats(path, dur):
    sr = 22050
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < sr:
        return None
    hop, win = 512, 1024
    nfr = 1 + (len(x) - win) // hop
    frames = np.lib.stride_tricks.as_strided(x, (nfr, win), (x.strides[0] * hop, x.strides[0]))
    mag = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(mag), axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    t = np.arange(len(flux)) * hop / sr
    # onsets: local maxima above adaptive threshold
    ons = []
    k = 6
    for i in range(k, len(flux) - k):
        if flux[i] > 1.0 and flux[i] == flux[i - k:i + k + 1].max() and flux[i] > np.median(flux[i - k * 4:i + k * 4 + 1]) + 0.8:
            ons.append(round(float(t[i]), 3))
    # tempo via autocorrelation of flux, 70..180 bpm
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    fps_a = sr / hop
    lags = np.arange(len(ac)) / fps_a
    ok = (lags > 60 / 180) & (lags < 60 / 70)
    bpm = None
    if ok.any():
        lag = lags[ok][np.argmax(ac[ok])]
        bpm = round(60 / lag, 1)
    rms = float(np.sqrt((x ** 2).mean()))
    return dict(bpm=bpm, onsets=ons, silent=rms < 1e-3)


def palette(img, k=6):
    q = Image.fromarray(img).quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: k * 3]
    counts = sorted(q.getcolors(), reverse=True)
    out = []
    for c, i in counts[:k]:
        r, g, b = pal[i * 3: i * 3 + 3]
        out.append(dict(hex=f"#{r:02x}{g:02x}{b:02x}", share=round(c / (img.shape[0] * img.shape[1]), 3)))
    return out


def motion_events(e, s, t, fps):
    """Contiguous runs of motion inside a shot, with an easing hint from the shape."""
    seg = e[s:t].copy()
    if len(seg) < 3:
        return []
    seg[0] = seg[1] if len(seg) > 1 else 0  # the cut frame itself is not motion
    base = np.percentile(seg, 20)
    thr = base + max(0.004, (seg.max() - base) * 0.25)
    on = seg > thr
    ev, i = [], 0
    while i < len(seg):
        if on[i]:
            j = i
            while j + 1 < len(seg) and (on[j + 1] or (j + 2 < len(seg) and on[j + 2])):
                j += 1
            run = seg[i:j + 1]
            if j - i + 1 >= 3:
                pk = int(np.argmax(run))
                rel = pk / max(1, len(run) - 1)
                # secondary bump after the main decay => spring / overshoot
                tail = run[pk:]
                bump = False
                if len(tail) > 4:
                    d = np.diff(tail)
                    rises = np.where((d[:-1] < 0) & (d[1:] > 0))[0]
                    bump = any(tail[r + 2:].max() > tail[r + 1] + 0.25 * (run.max() - tail[r + 1]) for r in rises if r + 2 < len(tail))
                hint = ("ease-out (fast start, long settle)" if rel < 0.3 else
                        "ease-in (slow start, hard stop)" if rel > 0.7 else "ease-in-out")
                if bump:
                    hint += " + overshoot/spring"
                ev.append(dict(start_f=s + i, end_f=s + j, frames=j - i + 1,
                               ms=round((j - i + 1) / fps * 1000), peak_f=s + i + pk,
                               peak_energy=round(float(run.max()), 4), hint=hint))
            i = j + 1
        else:
            i += 1
    return ev


def font(sz):
    for p in ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf",
              "/Library/Fonts/Arial.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def grab(path, idxs, fps, width):
    """Full-quality frames by index, resized to `width`."""
    idxs = sorted(set(int(i) for i in idxs))
    out = {}
    B = 60
    for k in range(0, len(idxs), B):
        chunk = idxs[k:k + B]
        sel = "+".join(f"eq(n\\,{i})" for i in chunk)
        tmp = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                              f"fps={fps},select={sel},scale={width}:-2", "-fps_mode", "passthrough",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        if not tmp:
            continue
        arr = np.frombuffer(tmp, np.uint8)
        per = len(arr) // len(chunk)
        h = per // (width * 3)
        for n, i in enumerate(chunk):
            out[i] = arr[n * per:(n + 1) * per].reshape(h, width, 3)
    return out


def sheet(frames, labels, cols, title=None):
    if not frames:
        return None
    fh, fw = frames[0].shape[:2]
    pad, lab, top = 6, 22, (34 if title else 0)
    rows = math.ceil(len(frames) / cols)
    W = cols * (fw + pad) + pad
    H = top + rows * (fh + lab + pad) + pad
    im = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(im)
    f, ft = font(15), font(20)
    if title:
        d.text((pad, 7), title, fill=(255, 220, 90), font=ft)
    for n, (fr, lb) in enumerate(zip(frames, labels)):
        r, c = divmod(n, cols)
        x, y = pad + c * (fw + pad), top + pad + r * (fh + lab + pad)
        d.text((x, y + 2), lb, fill=(230, 230, 230), font=f)
        im.paste(Image.fromarray(fr), (x, y + lab))
    return im


def trail(frames):
    """Older frames fainter, newest on top: reads as direction + spacing of motion."""
    acc = frames[0].astype(np.float32) * 0.35
    n = len(frames)
    for i, f in enumerate(frames[1:], 1):
        a = 0.25 + 0.75 * i / (n - 1)
        acc = acc * (1 - a * 0.5) + f.astype(np.float32) * (a * 0.5)
    return np.clip(acc, 0, 255).astype(np.uint8)


def curve_png(e, s, t, fps, events, beats, path, W=900, H=220):
    im = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(im)
    f = font(13)
    seg = e[s:t]
    if len(seg) < 2:
        im.save(path)
        return
    seg = seg.copy()
    seg[0] = seg[1]
    mx = max(1e-6, seg.max())
    x0, y0, x1, y1 = 40, 20, W - 10, H - 30
    X = lambda i: x0 + (x1 - x0) * i / max(1, len(seg) - 1)
    Y = lambda v: y1 - (y1 - y0) * v / mx
    for ev in events:
        d.rectangle([X(ev["start_f"] - s), y0, X(ev["end_f"] - s), y1], fill=(40, 48, 70))
    for b in beats or []:
        bf = b * fps
        if s <= bf < t:
            d.line([X(bf - s), y0, X(bf - s), y1], fill=(200, 80, 80), width=1)
    pts = [(X(i), Y(v)) for i, v in enumerate(seg)]
    d.line(pts, fill=(120, 220, 140), width=2)
    for i in range(0, len(seg), max(1, len(seg) // 12)):
        d.text((X(i) - 6, y1 + 6), str(s + i), fill=(160, 160, 160), font=f)
    d.text((x0, 2), f"motion energy per frame (f{s}-{t - 1}); blue = motion event, red = audio onset",
           fill=(200, 200, 200), font=f)
    im.save(path)


def tc(i, fps):
    s = i / fps
    return f"{int(s // 60)}:{s % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--cut", type=float, default=0.32, help="cut-detection threshold (lower = more cuts)")
    ap.add_argument("--sheet-w", type=int, default=480, help="tile width in burst sheets")
    ap.add_argument("--max-burst", type=int, default=24, help="max tiles per shot burst")
    ap.add_argument("--spike-cuts", action="store_true", help="also detect cuts between dark/similar UI frames (over-detects on fast motion)")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    meta = probe(a.video)
    fps = meta["fps"]
    fr = decode(a.video, meta["w"], meta["h"], fps)
    n = len(fr)
    cuts, energy, score = detect_cuts(fr, a.cut, a.spike_cuts)
    bounds = cuts + [n]
    shots = [(bounds[i], bounds[i + 1]) for i in range(len(cuts))]
    beats = audio_beats(a.video, meta["dur"]) if meta["audio"] else None
    onsets = beats["onsets"] if beats else []

    # which full-res frames we need
    need = set()
    plan = []
    for k, (s, t) in enumerate(shots):
        L = t - s
        # long shots (one-takes) get one burst sheet per 2 s window so sampling stays dense
        win = int(round(2 * fps)) if L > 4 * fps else L
        bursts = []
        for w0 in range(s, t, win):
            w1 = min(t, w0 + win)
            step = max(1, math.ceil((w1 - w0) / a.max_burst))
            bb = list(range(w0, w1, step))
            if bb[-1] != w1 - 1:
                bb.append(w1 - 1)
            bursts.append(bb)
        burst = [i for bb in bursts for i in bb]
        cut_in = list(range(max(0, s - 4), min(n, s + 8))) if k > 0 else []
        ev = motion_events(energy, s, t, fps)
        busiest = max(ev, key=lambda e: e["peak_energy"]) if ev else None
        tr = list(range(busiest["start_f"], busiest["end_f"] + 1)) if busiest else []
        if len(tr) > 12:
            tr = tr[:: math.ceil(len(tr) / 12)]
        plan.append((k, s, t, bursts, cut_in, ev, tr))
        need.update(burst, cut_in, tr, [s + L // 2])
    full = grab(a.video, need, fps, a.sheet_w)

    shots_out = []
    ov_frames, ov_labels = [], []
    for k, s, t, bursts, cut_in, ev, tr in plan:
        dname = os.path.join(a.out, "shots", f"{k + 1:02d}")
        os.makedirs(dname, exist_ok=True)
        mid = full.get(s + (t - s) // 2)
        if mid is not None:
            ov_frames.append(mid)
            ov_labels.append(f"#{k + 1} {tc(s, fps)} {t - s}f")
        for wi, burst in enumerate(bursts):
            tag = "" if len(bursts) == 1 else f" window {wi + 1}/{len(bursts)} f{burst[0]}-{burst[-1]}"
            im = sheet([full[i] for i in burst if i in full],
                       [f"f{i} {tc(i, fps)}" for i in burst if i in full], 4,
                       f"shot {k + 1}: f{s}-{t - 1} ({t - s} frames, {(t - s) / fps:.2f}s){tag} every {burst[1] - burst[0] if len(burst) > 1 else 1} frame(s)")
            if im:
                im.save(os.path.join(dname, "burst.png" if len(bursts) == 1 else f"burst_{wi + 1:02d}.png"))
        if cut_in:
            im = sheet([full[i] for i in cut_in if i in full],
                       [("CUT " if i == s else "") + f"f{i}" for i in cut_in if i in full], 6,
                       f"cut into shot {k + 1}: every frame, f{cut_in[0]}-{cut_in[-1]}")
            if im:
                im.save(os.path.join(dname, "cut_in.png"))
        if tr and all(i in full for i in tr):
            Image.fromarray(trail([full[i] for i in tr])).save(os.path.join(dname, "trail.png"))
        curve_png(energy, s, t, fps, ev, onsets, os.path.join(dname, "curve.png"))
        pal = palette(fr[s + (t - s) // 2])
        near = None
        if onsets:
            ct = s / fps
            j = min(onsets, key=lambda o: abs(o - ct))
            near = round((j - ct) * 1000)
        shots_out.append(dict(shot=k + 1, start_f=s, end_f=t - 1, frames=t - s,
                              start=round(s / fps, 3), dur=round((t - s) / fps, 3),
                              cut_score=round(float(score[s]), 3) if k else None,
                              nearest_onset_ms=near if k else None,
                              palette=pal, motion_events=ev,
                              files=sorted(os.listdir(dname))))
    im = sheet(ov_frames, ov_labels, 5, f"{os.path.basename(a.video)} — {len(shots)} shots, {meta['dur']:.1f}s @ {fps:g}fps")
    if im:
        im.save(os.path.join(a.out, "overview.png"))

    res = dict(video=os.path.abspath(a.video), meta=meta, frames=n, audio=beats,
               energy=[round(float(x), 5) for x in energy], shots=shots_out)
    json.dump(res, open(os.path.join(a.out, "analysis.json"), "w"), indent=1)

    L = [f"# Analysis: {os.path.basename(a.video)}", "",
         f"{meta['w']}x{meta['h']}, {fps:g} fps, {meta['dur']:.2f}s, {n} frames, {len(shots)} shots, "
         f"avg shot {meta['dur'] / max(1, len(shots)):.2f}s"]
    # animating on 2s? per 40 f window: one parity of frame diffs near zero = every other frame holds
    on2 = []
    for w0 in range(1, n - 40, 40):
        seg = energy[w0:w0 + 40]
        ev, od = seg[0::2], seg[1::2]
        m_ = min(len(ev), len(od))
        lo, hi = sorted([float(ev[:m_].mean()), float(od[:m_].mean())])
        if hi > 0.002 and lo / hi < 0.3:
            on2.append(w0)
    if on2:
        rng = ", ".join(f"f{w}-{w + 39}" for w in on2[:12]) + (" ..." if len(on2) > 12 else "")
        L.append(f"CADENCE: animates on 2s in {len(on2)} window(s) ({rng}): every other frame holds. Quantize motion there to the pair cadence.")
    if beats:
        L.append(f"Audio: ~{beats['bpm']} BPM, {len(beats['onsets'])} onsets" + (" (near-silent)" if beats["silent"] else ""))
    else:
        L.append("Audio: none")
    aligned = [x for x in shots_out if x["nearest_onset_ms"] is not None and abs(x["nearest_onset_ms"]) <= 50]
    if beats and len(shots_out) > 1:
        L.append(f"Cuts within 50 ms of an audio onset: {len(aligned)}/{len(shots_out) - 1}")
    L += ["", "| # | start | frames | dur s | onset Δms | motion events (frames, hint) | palette |", "|---|---|---|---|---|---|---|"]
    for x in shots_out:
        evs = "; ".join(f"f{e['start_f']}-{e['end_f']} {e['frames']}f {e['hint']}" for e in x["motion_events"]) or "hold"
        L.append(f"| {x['shot']} | {tc(x['start_f'], fps)} | {x['frames']} | {x['dur']} | "
                 f"{x['nearest_onset_ms'] if x['nearest_onset_ms'] is not None else ''} | {evs} | "
                 + " ".join(p["hex"] for p in x["palette"][:4]) + " |")
    L += ["", "Per shot: shots/NN/burst.png (consecutive frames), cut_in.png (every frame across the cut),",
          "trail.png (busiest motion, older frames fainter), curve.png (energy = speed; its shape is the easing)."]
    open(os.path.join(a.out, "ANALYSIS.md"), "w").write("\n".join(L) + "\n")
    print(f"{len(shots)} shots, {n} frames -> {a.out}")


if __name__ == "__main__":
    main()
