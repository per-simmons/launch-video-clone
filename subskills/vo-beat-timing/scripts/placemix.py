#!/usr/bin/env python3
"""Place sounds on frames and mix them to a WAV of exactly the cut's length, safely (no hung ffmpeg), then optionally
mux onto a picture and land the loudness. One source of truth: an events file in frames, not seconds.

  placemix.py EVENTS.json --frames N [--fps 30] [--wav mix.wav] [--video picture.mp4 --out final.mp4]
              [--lufs -16] [--tp -1.5]

EVENTS.json: [{"file": "vo/L1.wav", "frame": 2, "gain_db": 0},
              {"file": "raw/clip.MOV", "frame": 427, "ss": 33.97, "dur": 18.5, "gain_db": -2, "fade_in": 0.2},
              {"file": "sfx/whoosh.wav", "frame": 382, "gain_db": -24, "anchor": "peak"}]
  frame    the global frame the sound starts on ("anchor": "peak" shifts it so its loudest moment lands on the frame)
  ss/dur   trim a source (seconds); camera-original audio (.MOV etc.) is first extracted to WAV, never mixed directly
Why the safety rules: an unbounded `apad` in a graph that also decodes camera MOV audio never reaches EOF, so ffmpeg
waits forever at 0% CPU (and an output -t did not save it). Here every input is a WAV, the pad is bounded
(apad=whole_dur), every call has -nostdin + stdin=DEVNULL + a timeout, and the mix is muxed in a separate command."""
import argparse, json, os, re, subprocess, tempfile
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("events"); ap.add_argument("--frames", type=int, required=True); ap.add_argument("--fps", type=float, default=30.0)
ap.add_argument("--wav", default="mix.wav"); ap.add_argument("--video"); ap.add_argument("--out")
ap.add_argument("--lufs", type=float, default=-16.0); ap.add_argument("--tp", type=float, default=-1.5)
a = ap.parse_args()
ev = json.load(open(a.events)); base = os.path.dirname(os.path.abspath(a.events)); tmp = tempfile.mkdtemp()
L = a.frames / a.fps

def ff(args, t=300):
    return subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + args, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=t, check=True)

def as_wav(e, k):
    src = e["file"] if os.path.isabs(e["file"]) else os.path.join(base, e["file"])
    out = os.path.join(tmp, f"in{k}.wav"); trim = []
    if "ss" in e: trim += ["-ss", str(e["ss"])]
    if "dur" in e: trim += ["-t", str(e["dur"])]
    ff(trim + ["-i", src, "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", out])
    return out

def peak_offset(path):
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True, stdin=subprocess.DEVNULL, timeout=120).stdout
    x = np.abs(np.frombuffer(p, np.int16).astype(np.float32))
    if len(x) < 80: return 0.0
    env = np.convolve(x, np.ones(80) / 80, "same")              # 10 ms envelope
    return float(np.argmax(env)) / 8000 - 0.015                  # land the peak 15 ms before the frame

inputs, chains, labels = [], [], []
for k, e in enumerate(ev):
    w = as_wav(e, k)
    t0 = e["frame"] / a.fps - (peak_offset(w) if e.get("anchor") == "peak" else 0.0)
    ms = max(0, int(round(t0 * 1000)))
    f = [f"volume={e.get('gain_db', 0)}dB"]
    if e.get("fade_in"): f.append(f"afade=t=in:d={e['fade_in']}")
    if e.get("fade_out") and e.get("dur"): f.append(f"afade=t=out:st={e['dur'] - e['fade_out']}:d={e['fade_out']}")
    f.append(f"adelay={ms}|{ms}")
    inputs += ["-i", w]; chains.append(f"[{k}:a]{','.join(f)}[s{k}]"); labels.append(f"[s{k}]")
graph = ";".join(chains) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_dur={L:.4f},atrim=0:{L:.4f}[m]"
ff(inputs + ["-filter_complex", graph, "-map", "[m]", "-c:a", "pcm_s24le", a.wav], t=300)
print("mix", a.wav, f"{L:.3f}s")

def measure(path):
    st = subprocess.run(["ffmpeg", "-nostdin", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", st)[-1]), float((re.findall(r"Peak:\s+(-?[\d.]+)", st) or ["0"])[-1])

if a.video and a.out:
    lim = 10 ** (a.tp / 20)
    I, _ = measure(a.wav); gain = a.lufs - I
    for _ in range(3):                                            # gain + limiter, re-measured on the ENCODED file
        ff(["-i", a.video, "-i", a.wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-af", f"volume={gain:.2f}dB,alimiter=limit={lim:.4f}:level=false:attack=3:release=60",
            "-c:a", "aac", "-b:a", "256k", "-shortest", a.out], t=600)
        I2, TP = measure(a.out)
        if abs(I2 - a.lufs) <= 0.5: break
        gain += a.lufs - I2
    print(f"{a.out}: {I2:.1f} LUFS, true peak {TP:.1f} dBTP")
