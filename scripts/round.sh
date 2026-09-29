#!/bin/zsh
# round.sh <project_dir> <render_root> vN [fps]
#   Renders a draft of <project_dir>/hf to <render_root>/vN.mp4 (render scratch follows --output,
#   so render_root must be outside the repo, on a disk with room), bursts it, compares against
#   <project_dir>/reference/analysis, prints the numbers. fps defaults to the reference's
#   (e.g. 30000/1001 for 29.97 — without it a 29.97 clone drifts ~1.7 frames a minute).
set -e
P=$1; R=$2; V=$3; S=${0:A:h}
FPS=${4:-$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$P/reference/ref.mp4")}
mkdir -p "$R"
( cd "$P/hf" && npx hyperframes render --strict --quality draft --fps "$FPS" --output "$R/$V.mp4" 2>&1 | grep -E "rendered in|rror" || true )
python3 "$S/burst.py" "$R/$V.mp4" "$R/$V-analysis" >/dev/null 2>&1
python3 "$S/compare.py" "$P/reference/analysis" "$R/$V-analysis" "$R/$V-compare" 2>&1 | grep -v Warning | tail -6
grep -A7 "Worst seconds" "$R/$V-compare/COMPARE.md" | tail -6
echo "$V  $(grep -E 'matched|correlation|Mean visual|Total motion' "$R/$V-compare/COMPARE.md" | tr '\n' ' ')" >> "$P/LOG-numbers.txt"
