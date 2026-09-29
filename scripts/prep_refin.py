"""Cut cleaned reference frames into assets/refin/ for gpt-image: UI regions become flat black holes.
prep_refin.py <ref-frames dir> <out dir>   (ref-frames/fNNNN.png = frame NNNN-1, 1080p)"""
import os, sys
from PIL import Image, ImageDraw
K, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
def fr(f): return Image.open(f"{K}/f{f + 1:04d}.png").convert("RGB")
# EDIT THESE for your reference: the jobs below are from one worked clone, as an example.
# name: (frame, [holes x0,y0,x1,y1], crop or None)
jobs = {
    "bg_swirl":  (322, [(520, 480, 1800, 600)], None),
    "bg_dock":   (406, [(0, 430, 1920, 780), (805, 260, 1160, 380)], None),
    "bg_dune_a": (424, [(560, 180, 1360, 720)], None),
    "bg_dune_b": (486, [(530, 0, 1390, 1080)], None),
    "bg_bigsur": (520, [(130, 420, 1790, 660), (760, 0, 1165, 305)], None),
    "bg_rocks":  (566, [(0, 320, 1195, 755)], None),
    "wall_phone": (616, [(505, 330, 1415, 705), (580, 730, 730, 875), (1195, 730, 1345, 875), (800, 955, 1120, 985)], (495, 0, 1425, 870)),
    "avatar":    (90, [], (1410, 478, 1590, 658)),
}
for name, (f, holes, crop) in jobs.items():
    im = fr(f); d = ImageDraw.Draw(im)
    for h in holes: d.rectangle(h, fill=(0, 0, 0))
    if crop: im = im.crop(crop)
    im.save(f"{OUT}/{name}.png")
print("ok", len(jobs))
