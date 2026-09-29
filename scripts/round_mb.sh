#!/bin/zsh
# round_mb.sh <project_dir> <render_root> vN [subframes=8] [fps=30]
#   round.sh with real motion blur: renders <project>/hf at fps*N, averages each N subframes (360-degree shutter,
#   centred on the frame via hf/mb.js), then bursts + compares like round.sh. Renders go to <render_root> (outside the repo; it needs room).
set -e
P=$1; R=$2; V=$3; N=${4:-8}; FPS=${5:-30}; S=${0:A:h}
HI=$((FPS * N))
echo "window.MB_SHIFT = $(python3 -c "print(($N-1)/2/$HI)");" > "$P/hf/mb.js"
( cd "$P/hf" && npx hyperframes render --strict --quality draft --fps $HI --output "$R/$V-raw.mp4" 2>&1 | grep -E "rendered in|rror" || true )
ffmpeg -v error -y -i "$R/$V-raw.mp4" -vf "tmix=frames=$N,select='not(mod(n+1\,$N))',setpts=N/($FPS*TB)" -r $FPS \
  -c:v libx264 -crf 16 -pix_fmt yuv420p -an "$R/$V-v.mp4"
ffmpeg -v error -y -i "$R/$V-v.mp4" -i "$P/reference/ref.mp4" -map 0:v -map '1:a?' -c copy -shortest "$R/$V.mp4"
rm -f "$R/$V-raw.mp4" "$R/$V-v.mp4"; echo "window.MB_SHIFT = 0;" > "$P/hf/mb.js"
python3 "$S/burst.py" "$R/$V.mp4" "$R/$V-analysis" >/dev/null 2>&1
python3 "$S/compare.py" "$P/reference/analysis" "$R/$V-analysis" "$R/$V-compare" 2>&1 | grep -v Warning | tail -6
grep -A7 "Worst seconds" "$R/$V-compare/COMPARE.md" | tail -6
echo "$V  $(grep -E 'matched|correlation|Mean visual|Total motion' "$R/$V-compare/COMPARE.md" | tr '\n' ' ')" >> "$P/LOG-numbers.txt"
