#!/usr/bin/env python3
"""soundcheck.py — grade a render's sound without a human. Run it with the project's sound venv
(.venv-sound: numpy, torch, audiobox_aesthetics, google-genai; see README), e.g. .venv-sound/bin/python soundcheck.py ...

  soundcheck.py check <render.mp4> [--placed sound/placed.json --fps 30] [--ref reference/ref.mp4 --listen] -o SOUND-CHECK.md
  soundcheck.py rank assets/sfx/whoosh-*.mp3        taste-score variants, best first (pick the top one)

check = one report, PASS/FAIL per line:
  1. Loudness: integrated LUFS vs YouTube's -14 (±1), true peak <= -1 dBTP, clipped samples = 0.
  2. Sync: every placed sound is located inside the mix by cross-correlating its own waveform (music
     can't fool it), then its peak is compared with its event, in frames. >1 frame off = FAIL.
  3. Taste: Meta Audiobox Aesthetics on the mix, 0-10: PQ production quality, CE enjoyment,
     CU usefulness, PC complexity. With --ref, the reference is scored too so you see the gap.
  4. --listen: runs listen.py qa (Gemini hears clone vs reference) and appends its issues.
Numbers are the gate; the listener's opinion is a second pass. A human listen is the final one.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

SR = 22050


def pcm(path, sr=SR, ch=1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    return x.reshape(-1, ch) if ch > 1 else x


def loudness(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = out[out.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    TP = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", summ)
    st = pcm(path, 48000, 2)
    clipped = int((np.abs(st) >= 0.999).sum())
    return (float(I.group(1)) if I else None, float(TP.group(1)) if TP and "inf" not in TP.group(1) else None, clipped)


def onsets(x, sr=SR):
    hop, win = 256, 1024
    if len(x) < win:
        return np.array([])
    n = 1 + (len(x) - win) // hop
    fr = np.lib.stride_tricks.as_strided(x, (n, win), (x.strides[0] * hop, x.strides[0]))
    mag = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    flux = np.concatenate([[0], np.maximum(0, np.diff(np.log1p(mag), axis=0)).sum(axis=1)])
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    k = 4
    idx = [i for i in range(k, len(flux) - k) if flux[i] > 0.8 and flux[i] == flux[i - k:i + k + 1].max()]
    return np.array(idx) * hop / sr


_pred = None


def aes(path):
    global _pred
    import torch
    from audiobox_aesthetics.infer import initialize_predictor
    if _pred is None:
        _pred = initialize_predictor()
    x = pcm(path, 16000)
    if len(x) == 0:
        return {}
    r = _pred.forward([{"path": torch.from_numpy(x.copy()).unsqueeze(0), "sample_rate": 16000}])[0]
    return {k: round(float(v), 2) for k, v in r.items()}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("render"); c.add_argument("--placed"); c.add_argument("--fps", type=float)
    c.add_argument("--ref"); c.add_argument("--listen", action="store_true"); c.add_argument("-o", "--out")
    r = sub.add_parser("rank"); r.add_argument("files", nargs="+")
    a = ap.parse_args()

    if a.cmd == "rank":
        rows = [(f, aes(f)) for f in a.files]
        rows.sort(key=lambda x: -(x[1].get("PQ", 0) + x[1].get("CU", 0)))
        for f, s in rows:
            print(f"{s.get('PQ', 0):5.2f} PQ  {s.get('CU', 0):5.2f} CU  {s.get('CE', 0):5.2f} CE  {f}")
        return

    L = [f"# Sound check: {os.path.basename(a.render)}", ""]
    fails = 0
    I, TP, clip = loudness(a.render)
    ok = I is not None and abs(I + 14) <= 1
    fails += not ok
    L.append(f"- {'PASS' if ok else 'FAIL'} loudness {I} LUFS (target -14 ±1)")
    ok = TP is not None and TP <= -1
    fails += not ok
    L.append(f"- {'PASS' if ok else 'FAIL'} true peak {TP} dBTP (max -1)")
    fails += clip > 0
    L.append(f"- {'PASS' if clip == 0 else 'FAIL'} clipped samples: {clip}")

    if a.placed:
        fps = a.fps or 30
        mix = pcm(a.render)
        on = onsets(mix)
        w = int(SR * 0.005)
        nrm = len(mix) // w
        rms = np.sqrt((mix[: nrm * w].reshape(nrm, w) ** 2).mean(axis=1)) if nrm else np.zeros(1)

        def local_peak(t, span=0.2):
            i0, i1 = max(0, int((t - span) * SR / w)), min(nrm, int((t + span) * SR / w) + 1)
            return (i0 + int(np.argmax(rms[i0:i1]))) * w / SR if i1 > i0 else None
        L += ["", "## Sync (sound peak vs its event)", "", "| event | label | expected | measured | off (frames) | |", "|---|---|---|---|---|---|"]
        for e in json.load(open(a.placed)):
            want = e["peak_s"] if e.get("anchor", "peak") == "peak" else e["start_s"]
            # Find the sound file itself inside the mix (cross-correlation): music can't fool it.
            sfx_path = e.get("sfx", "")
            cand = [sfx_path, os.path.join(os.path.dirname(os.path.abspath(a.placed)), "..", sfx_path)]
            sfx_path = next((c for c in cand if c and os.path.exists(c)), None)
            near = None
            if sfx_path:
                y = pcm(sfx_path)
                y = y[: int(SR * 1.5)]
                i0 = max(0, int((e["start_s"] - 0.25) * SR)); i1 = min(len(mix), int((e["start_s"] + 0.25) * SR) + len(y))
                seg = mix[i0:i1]
                if len(seg) > len(y) > 0:
                    n = 1 << int(np.ceil(np.log2(len(seg) + len(y))))
                    xc = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(y, n)), n)[: len(seg) - len(y) + 1]
                    found_start = (i0 + int(np.argmax(xc))) / SR
                    near = found_start + (want - e["start_s"])   # same offset inside the file
            if near is None:  # fall back to energy/onset
                near = local_peak(want) if e.get("anchor", "peak") == "peak" else (
                    float(on[np.argmin(np.abs(on - want))]) if len(on) else None)
            off = None if near is None else (near - want) * fps
            ok = off is not None and abs(off) <= 1.0
            fails += not ok
            L.append(f"| {e.get('frame', '')} | {e.get('label', '')} | {want:.3f}s | {'' if near is None else f'{near:.3f}s'} | "
                     f"{'' if off is None else f'{off:+.1f}'} | {'PASS' if ok else 'FAIL'} |")

    L += ["", "## Taste (Meta Audiobox Aesthetics, 0-10)", "", "| | PQ quality | CE enjoyment | CU usefulness | PC complexity |", "|---|---|---|---|---|"]
    s = aes(a.render)
    L.append(f"| clone | {s.get('PQ')} | {s.get('CE')} | {s.get('CU')} | {s.get('PC')} |")
    if a.ref:
        s2 = aes(a.ref)
        L.append(f"| reference | {s2.get('PQ')} | {s2.get('CE')} | {s2.get('CU')} | {s2.get('PC')} |")
        if s and s2 and s["PQ"] < s2["PQ"] - 0.5:
            L.append(f"\nProduction quality is {s2['PQ'] - s['PQ']:.1f} below the reference: check harsh/cheap SFX, mud in the low end, a thin music bed.")

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.render)), "SOUND-CHECK.md")
    if a.listen and a.ref:
        qa = os.path.splitext(out)[0] + "-listen.md"
        subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(__file__), "listen.py"), "qa", a.render, a.ref, "-o", qa])
        if os.path.exists(qa):
            L += ["", "## Listener (Gemini, clone vs reference)", "", open(qa).read()]
    L.insert(2, f"**{'PASS' if fails == 0 else f'{fails} FAIL'}** (numbers gate; listener notes below are advisory)\n")
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print(out)


if __name__ == "__main__":
    main()
