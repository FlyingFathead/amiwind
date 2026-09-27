# Filled terrain and fog

Checkpoint-002 adds a 97x97 heightfield over the nine exported Seyda Neen cells.
The 68000 samples 80 screen columns, four pixels wide, from near to far. Each
column retains its highest filled pixel; terrain below that boundary is hidden.
This is a heightfield renderer, separate from the 33x33 wireframe comparison.

The host bakes colours from 19 original base-game terrain textures, using four
averaged samples per material tile, slope lighting and three land palette slots.
Water, fog, sky and text use the remaining slots. The result is a coarse colour
map tied to the original land material IDs, not runtime UV texture mapping or a
reproduction of OpenMW's texture blending. Original and baked pixels stay private.

| Key | Fog starts, original world units | Fully opaque | Sampled depth slices |
| --- | ---: | ---: | ---: |
| 1, default | 1,024 | 1,536 | 10 |
| 2 | 1,536 | 2,304 | 16 |
| 3 | 2,560 | 3,840 | 28 |

Fully fogged terrain is the same colour as the sky and is never sampled. The
band uses discrete OCS palette steps. These distances are forward camera depth,
not a circular world radius. Pitch shifts the horizon; this is an approximation
to a fully pitched perspective camera. The eye follows the nearest height sample.

## Work split and timing

- The PC extracts heights, samples original DDS textures, reduces the palette,
  and makes exact integer projection lookup tables for the bounded height range.
- The CPU traverses rays, handles occlusion and input, and draws short spans.
- The blitter copies the HUD/clears three-plane buffers and draws long masked
  vertical spans. Projection can overlap an outstanding span; pixel writes wait
  for it before touching the destination. Paula independently plays the PCM.

The supplied region needs 21,784 bytes for height projection tables. Row-offset
tables and register-resident ray coordinates remove more inner-loop arithmetic.
The build gates Chip hunks at 352 KiB and all hunks at 400 KiB. OS/stack and
filesystem overhead are excluded from those executable counts; emulator boot
with exactly 512 KiB Chip + 512 KiB slow RAM remains a separate check.

Escape prints solid/wire frame counts, elapsed vertical-event ticks and mean
presented-frame rates. PAL uses 50 ticks/second. Counts include input and frame
presentation waits, cap each mode's sample at 60,000 ticks, and aggregate all fog
presets used in that mode. Restart and keep one preset for comparable figures.
The reported decimal truncates to one place. See OPENING_VALIDATION.md for results.

## Objects and next scene work

LAND heights do not contain the town's meshes. CELL references place buildings,
trees and other objects separately; the host export already records those.
Candidate representation: masked baked sprites for trees and distant objects,
simple geometry for nearby buildings, and several baked viewing angles where
rotation exposes a single billboard. The blitter can composite a masked image;
scaling, viewpoint selection and visibility still require preparation or CPU work.

Objects must respect terrain occlusion. One option is to insert billboard strips
into the same near-to-far depth traversal. Test one tree and one building before
increasing counts. OpenMW actor assembly/baking and animation remain separate
host-tool tasks. This checkpoint establishes the filled terrain path first.

## Streaming interaction

Checkpoint-004 also polls async audio at terrain depth and wireframe row
boundaries when at least four PAL ticks have elapsed. This prevents long render
passes from postponing all read completions to the next frame. Renderer registers
are preserved, and the in-flight blitter still has exclusive access to its
unfinished destination span. Geometry, palette and drawing algorithms are
otherwise unchanged. See PROFILING.md for the audio/frame-pacing trade-off.
