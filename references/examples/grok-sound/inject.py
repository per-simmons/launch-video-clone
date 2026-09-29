#!/usr/bin/env python3
"""Write the music + every placed SFX into hf/index.html as <audio> elements (between SOUND markers).
Copies the sound files into hf/assets/sound. Run after eleven.py place."""
import json, os, shutil, re
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_GAIN = float(os.environ.get("MUSIC_GAIN", "0.7")); SFX_SCALE = float(os.environ.get("SFX_SCALE", "1.0"))
dst = os.path.join(P, "hf/assets/sound"); os.makedirs(dst, exist_ok=True)
shutil.copy(os.path.join(P, "assets/music/bed-edit.wav"), dst)
rows = [f'<audio id="music" src="assets/sound/bed-edit.wav" data-start="0" data-duration="55.8333" data-track-index="20" data-volume="{MUSIC_GAIN}"></audio>']
for i, d in enumerate(json.load(open(os.path.join(P, "sound/placed.json")))):
    f = os.path.basename(d["sfx"]); shutil.copy(os.path.join(P, d["sfx"]), dst)
    st = max(0.0, d["start_s"]); ms = max(0.0, -d["start_s"])
    dur = d.get("dur_s") or 6.0
    dur = min(dur, 55.8333 - st)
    rows.append(f'<audio id="sfx{i:02d}" src="assets/sound/{f}" data-start="{st:.3f}" data-duration="{dur:.3f}" data-media-start="{ms:.3f}" '
                f'data-track-index="{21 + i % 8}" data-volume="{d["gain"] * SFX_SCALE:.3f}"></audio>')
for j, b in enumerate(json.load(open(os.path.join(P, "sound/beds.json")))):
    f = os.path.basename(b["sfx"]); shutil.copy(os.path.join(P, b["sfx"]), dst)
    rows.append(f'<audio id="bed{j}" src="assets/sound/{f}" data-start="{b["start_s"]:.3f}" data-duration="{b["dur_s"]:.3f}" data-track-index="30" data-volume="{b["gain"]}"></audio>')
h = open(os.path.join(P, "hf/index.html")).read()
block = "<!-- SOUND -->\n  " + "\n  ".join(rows) + "\n  <!-- /SOUND -->"
if "<!-- SOUND -->" in h:
    h = re.sub(r"<!-- SOUND -->.*?<!-- /SOUND -->", lambda m: block, h, flags=re.S)
else:
    h = h.replace('<div id="bg"></div>', block + '\n  <div id="bg"></div>', 1)
open(os.path.join(P, "hf/index.html"), "w").write(h); print(len(rows), "audio elements")
