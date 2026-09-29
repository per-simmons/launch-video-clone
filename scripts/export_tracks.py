"""export_tracks.py <trackH dir> <out.js> — every track as TRK[name] = {roi, anchor, a, H:[[9]...]} for the composition."""
import json, glob, os, sys
out = {}
for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    d = json.load(open(p)); R = d["rows"]
    out[os.path.basename(p)[:-5]] = dict(roi=d["roi"], anchor=d["anchor"], a=R[0]["f"],
                                          H=[[round(v, 7) for v in r["H"]] for r in R])
open(sys.argv[2], "w").write("window.TRK=" + json.dumps(out, separators=(",", ":")) + ";\n")
print(sys.argv[2], {k: (v["a"], v["a"] + len(v["H"]) - 1) for k, v in out.items()})
