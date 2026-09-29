#!/bin/zsh
# sound/sround.sh vN — render, loudness-fix to -14 LUFS / -1.5 dBTP, grade with soundcheck (+ Gemini listen)
set -e
P=${0:A:h:h}; R=${RENDERS:-$P/renders}; S=${S:?set S to the skill scripts dir}; V=$1
( cd $P/hf && npx --yes hyperframes@0.8.77 render --quality draft --fps 30 --output "$R/$V-raw.mp4" 2>&1 | grep -E "rendered in|rror" | grep -v "attribute width" || true )
J=$(ffmpeg -hide_banner -i "$R/$V-raw.mp4" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$J" | python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -v error -y -i "$R/$V-raw.mp4" -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,alimiter=limit=0.79:level=false:attack=1:release=60" -ar 48000 -c:a aac -b:a 256k "$R/$V.mp4"
$S/soundcheck.py check "$R/$V.mp4" --placed $P/sound/placed.json --fps 30 --ref $P/reference/ref.mp4 --listen -o $P/sound/SOUND-CHECK-$V.md 2>&1 | tail -3
