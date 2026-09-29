#!/usr/bin/env python3
"""Shape the ElevenLabs bed to the reference's MEASURED dynamics (the model ignores the plan's dynamics):
per-section gain to the reference's section RMS, high-passed dip, two breaks, hard stop at 47.0 s + reverb tail."""
import subprocess, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "assets/music/bed.mp3", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64).copy()
T = np.arange(len(x)) / SR
# (start, end, target dB) — reference section RMS from the waveform (SOUND.md corrections)
SEC = [(0, .6, -14), (.6, 5.25, -21), (5.25, 12.72, -19.9), (12.72, 13.42, -33), (13.42, 19.0, -20.3), (19.0, 33.25, -23.9),
       (33.25, 40.72, -8.5), (40.72, 41.27, -20), (41.27, 47.0, -8.8)]
def rms(a): return 10 * np.log10((a ** 2).mean() + 1e-12)
g = np.zeros(len(x))
for a, b, tdb in SEC:
    i, j = int(a * SR), int(b * SR); g[i:j] = tdb - rms(x[i:j])
# after the stop: very quiet pad at -36
g[int(47.0 * SR):] = -36 - rms(x[int(49 * SR):int(55 * SR)])
# 60 ms ramps between sections (hard stop stays hard)
k = int(.06 * SR); gs = np.convolve(g, np.ones(k) / k, "same"); s0 = int(47.0 * SR); gs[s0 - 200:] = g[s0 - 200:]
y = x * (10 ** (gs / 20))[:, None]
# dip: high-pass 250 Hz with 0.3 s crossfades
hp = sosfilt(butter(4, 250, "hp", fs=SR, output="sos"), y, axis=0)
w = np.clip(np.minimum((T - 19.0) / .3, (33.25 - T) / .3), 0, 1)[:, None]
y = y * (1 - w) + hp * w * 2.2
# hard stop: 25 ms fade of the dry signal at 47.0, then a reverb tail built from the last half second
tail_src = y[s0 - int(.5 * SR):s0].copy()
fade = np.clip((47.025 - T) / .025, 0, 1)
pad = y * (T >= 47.2)[:, None] * np.clip((T - 47.2) / 1.5, 0, 1)[:, None]
y = y * fade[:, None]
rng = np.random.default_rng(3); L = int(1.4 * SR)
ir = rng.standard_normal((L, 2)) * np.exp(-np.arange(L) / (0.28 * SR))[:, None]
ir = sosfilt(butter(2, [300, 6000], "bp", fs=SR, output="sos"), ir, axis=0)
tail = np.stack([fftconvolve(tail_src[:, c], ir[:, c]) for c in range(2)], 1)
tail *= 10 ** ((-16 - rms(tail[:int(.3 * SR)])) / 20)
e = s0 + len(tail); y[s0:min(e, len(y))] += tail[:len(y) - s0]
y += pad
y *= 0.9 / np.abs(y).max()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", "-", "assets/music/bed-edit.wav"], input=y.astype(np.float64).tobytes(), check=True)
for a, b, tdb in SEC + [(47.2, 48, 0), (49, 55, -36)]:
    print(f"{a:6.2f}-{b:5.2f}  target {tdb:6.1f}  got {rms(y[int(a*SR):int(b*SR)]):6.1f}")
