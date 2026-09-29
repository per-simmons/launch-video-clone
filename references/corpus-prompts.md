# Corpus: how other people made launch / motion videos with AI

Public X posts collected in September 2026. Each entry is the author, a link to the original post,
and a short paraphrase of the technique. Read the originals for the full prompts; they are not
reproduced here.

## Moritz Kremb (@moritzkremb): SaaS launch video from one prompt
https://x.com/moritzkremb/status/2103066071838466494

One prompt in HyperFrames: pick a well-known SaaS product, pull its real assets and images from the
web, and cut a motion-graphics launch video that shows features and benefits. The lesson is to use
real assets rather than invented ones.

## Zsolt Kacso (@kaolti): Cosmos.so launch in HyperFrames, two prompts
https://x.com/kaolti/status/2103481296018092204

Prompt 1 asks the agent to research the product, find its value proposition and build a launch video
that feels unmistakably like the brand. Prompt 2 makes the agent watch its own render, critique the
rhythm and pacing, and produce a faster, more inventive v2. The self-review pass is what made it good.

## Martijn Verbove (@verbove): MakerMap, one shape morphing through the product
https://x.com/verbove/status/2103483957266268381

A structured prompt (inputs, rules, structure, motion, export): one HTML file with one `draw(t)`,
no CSS transitions or timers, one shape that morphs through every UI state on a 120 BPM grid,
closed-form springs with small overshoot, a contact sheet of one frame per beat before rendering,
then a 60 fps render with averaged subframes for motion blur.

## Stephan Livera (@stephanlivera): a 15-second "showreel"
https://x.com/stephanlivera/status/2103315922098470926

A single short open-ended prompt asking the model for a showreel-style motion piece, run at max
effort in stock Claude Code for about 40 minutes. Shows how far one prompt goes with no reference.

## TechHalla (@techhalla): kinetic risograph title sequence as a JSON prompt
https://x.com/techhalla/status/2092885302066979166

A text-to-video prompt written as structured JSON: concept, locked camera, music-synced beats,
an allowed word list, a two-ink palette with deliberate misregistration that snaps into register
on the kick, and a per-beat storyboard. Useful as a template for writing a beat-by-beat brief.

## Adil (@adilinthewild, Higgsfield): AI commercial, full workflow thread
https://x.com/adilinthewild/status/2070561738433712369

Three stages: build reference sheets for every asset (product angles, character sheets on a plain
grey background, 3/4-angle locations, props), have Claude turn the script into one named shot-list
document with a shared style prefix, then generate scenes and fix them by naming the one shot that
is wrong. Other tips: spell out actions move by move, give the model a layout map instead of prose,
make a second reference sheet when a character changes mid-scene, and iterate fast.

## Tim Koch (@timkochjar): Remotion product demo video, notes from his replies
https://x.com/timkochjar/status/2092278549679886507

All visuals made with Claude Code in one Remotion timeline, hooked up to the real component
library so the UI is 1:1. Sound effects and music were added in post. It took a day or two:
roughly 10-20 messages per scene across many parallel chats, replicating shots from reference
videos, and most of the effort went into timing and easing.

## Eddy (@Motionsbyeddy): what 60+ viral startup launch videos have in common
https://x.com/Motionsbyeddy/status/2071694912597479912

Show the biggest outcome in the first 3 seconds (no intro, no logo first), sell the change rather
than the features, show instead of explaining, cut any shot that doesn't earn the next second,
follow hook, problem, solution, proof, CTA, leave people wanting more, and prefer real proof
over polish.
