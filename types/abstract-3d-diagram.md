# Type: Abstract 3D diagram, one take

Thin lines, rings, orbits, nodes and small monospace labels floating in 3D space, one continuous
camera move, depth of field, soft glow, usually monochrome (Linear Loops). The feature is
explained as a diagram that flies.

## What it's made of
- **three.js inside the composition**, driven by the frame: `camera.position/lookAt = f(frame)`,
  render once per `draw(f)` call. No `requestAnimationFrame`, no clock.
- **Geometry is simple; the look is post-processing.** Rings = `LineLoop`/tube with tiny radius;
  ticks = instanced short lines; nodes = small sprites with additive glow. The expensive-looking
  part is depth of field (bokeh on near and far labels), bloom on the bright arc, vignette and grain.
  Use EffectComposer (BokehPass or a custom DOF, UnrealBloomPass) and match blur amounts from the
  burst sheets: which labels are sharp in which frame tells you the focus distance over time.
- **Labels are text in 3D**, facing along the ring tangent, not the camera. Use canvas-texture
  sprites or troika-three-text; mono font, uppercase, tracked out. A label chip (inverted box
  behind one word) marks the active step.
- **The "progress" arc**: a brighter segment travelling around the ring = drawRange or a shader
  uniform on the line, eased per step. Its head carries a glowing dot.
- **Camera is one spline** through keyframes read off the burst windows. Timing lives in the
  camera; get its easing from the energy curve (one-takes have no cuts, so the curve IS the edit).

## Traps
- It's 60 fps and one shot: render at the reference fps or the camera drifts against compare.
- Line width: WebGL lines are 1px regardless of `linewidth`. Use Line2/LineMaterial (fat lines)
  or thin tubes for the hero arc.
- SwiftShader (headless) is slow for post-processing; keep bloom/DOF resolution modest in drafts.
- Distance metric stays high on dark, blurry frames even when it looks right; steer by motion
  correlation and the pairs.

## Learned from clones
(append: date, clone, one specific lesson per line)
