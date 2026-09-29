#!/usr/bin/env python3
"""sbs.py <ref.mp4> <clone.mp4> <out.mp4> [--left REAL] [--right CLONE]
16:9 1920x1080 side-by-side for review: reference left, clone right, labels above each half,
reference audio. Labels are a PIL-made transparent PNG (many ffmpeg builds have no drawtext)."""
import argparse, subprocess, tempfile, os
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("ref"); ap.add_argument("clone"); ap.add_argument("out")
ap.add_argument("--left", default="REAL"); ap.add_argument("--right", default="CLONE")
a = ap.parse_args()

fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                      "-of", "csv=p=0", a.ref], capture_output=True, text=True).stdout.strip() or "30"
im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
f = None
for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "C:/Windows/Fonts/arialbd.ttf"]:
    if os.path.exists(p):
        f = ImageFont.truetype(p, 40); break
if f is None:
    f = ImageFont.load_default()
for cx, t, c in [(480, a.left, (255, 255, 255)), (1440, a.right, (255, 80, 80))]:
    b = d.textbbox((0, 0), t, font=f); d.text((cx - (b[2] - b[0]) // 2, 215), t, font=f, fill=c)
lab = os.path.join(tempfile.mkdtemp(), "labels.png"); im.save(lab)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.ref, "-i", a.clone, "-i", lab, "-filter_complex",
                "[0:v]scale=952:-2,setsar=1[a];[1:v]scale=952:-2,setsar=1[b];[a]pad=960:ih:0:0[a2];"
                "[b]pad=960:ih:8:0[b2];[a2][b2]hstack=inputs=2,pad=1920:1080:0:(1080-ih)/2:black[s];[s][2:v]overlay=0:0[v]",
                "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-r", fps,
                "-c:a", "aac", "-shortest", a.out], check=True)
print(a.out)
