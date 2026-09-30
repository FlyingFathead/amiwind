# Balmora and opening regression investigation

Development correction, 30 September 2026. The released v0.0.24-dev1 archives
remain unchanged. Focused acceptance results and unresolved limits follow.

## Missing Balmora facades: reproduced and isolated

Owner views:

| Local position | Yaw | Pitch | Observation |
| --- | --- | --- | --- |
| -669, -768, 142 | 65 | -6 | Buildings have missing walls and roof sections |
| -544, -784, 142 | 2 | -11 | Sign and roof decoration remain in front of an absent facade |
| -1109, -98, 256 | 180 | -15 | Further missing facades and floating decoration |

The original building geometry is present in the owned meshes and private
converted scenery archive. The generic reduction in `prepare_balmora.py`
assigned buildings a 200-triangle target. Reducing individual open material
components this aggressively collapses their boundaries and deletes large
portions of architectural shells. Independent placed signs, doors and other
decoration survive, producing the appearance of floating objects.

The isolated reference 6867 uses `meshes/x/ex_hlaalu_b_07.nif`, at local
(-360.62890625, -798.182861328125, 168.55099487304688). Source: 738 triangles;
dev1 reduction: 309 triangles across 60 material components. The effective
triangle count exceeds the nominal target because small components are retained.
Total source triangle area falls from about 3,599,937 to 2,744,951 source square
units. More importantly, the isolated native view visibly loses the facade.
Converting the same reference without reduction restores it. Both probes use
the same engine, terrain, placement, texture size and collision source.

Restoring the architecture throughout the original bm019 region repairs both
reported views in the native renderer. The two-view check recorded no surface
or edge overflow, with 5,975 peak surface fragments and 11,320 peak edges.
This is a focused visual comparison, not an inspection of every building.

The correction retains original architecture and manufactured-object geometry;
organic prop reductions remain separately bounded. Region overlap is
reduced from 1024 to 896 while preserving the 540-unit viewing range, 96-unit
hysteresis and diagonal coverage requirement. The purpose is to recover memory
headroom for the restored geometry. All 64 regions rebuilt with all 1,488 selected references covered and no lost
IDs. The maximum resident count is 654. All three reported facade views were
recaptured and inspected in the final converted scene: walls/roofs are restored,
with 3,656 peak surface fragments, 6,783 edges and no overflow. This remains
focused validation, not every building or crossing.

An additional diagnostic with far culling disabled exceeded the 12,288-surface
pool. That is a separate renderer limit; the single-building comparison proves
that overflow is not the cause of the facade destruction.

The earlier dev1 visual validation was insufficient. Counting retained reference
IDs and validating collision coverage did not establish intact visible geometry.

## Boat performance

The v0.0.23 and dev1 ship BSP, Jiub model, default settings and emulator preset
are byte-identical. A sequential matched FS-UAE test used the same stationary
ship viewpoint, default settings, 68040/FPU/JIT, 2 MiB Chip and 16 MiB Z3 RAM.
The audio device was a null sink. This host is not the owner's machine.

| Build | Measured frames | Elapsed milliseconds | Average FPS |
| --- | --- | --- | --- |
| v0.0.23 | 219 | 19,537 | 11.21 |
| v0.0.24-dev1 | 219 | 19,694 | 11.12 |

This test finds no meaningful new slowdown at that viewpoint. It does not
compare against the original PC Morrowind renderer or certify the entire opening.
The map command bypasses the natural New Game script sequence.

Additional instrumentation measured significant server collision work and UI
target-query work as well as rendering. In a separate 169-frame ship run:
world rendering 6,885 ms, server work 5,968 ms, UI work 2,836 ms. These timings
are diagnostic, with host load differing from the matched comparison; nested
render/screen timings must not be added twice. No blanket performance fix is
claimed. The ship view reaches about 8,987 surface fragments, illustrating why
a smaller interior can be more expensive than some restored Balmora views.

## Dock guard circling

Reproduced with the original exterior, authored route and standing collision.
Near the Census steps the guard steered toward the final auxiliary grid point,
circling around (342, -185, 30) for over five seconds. The requested destination
is (330, -200.25, 31.5), not that grid point.

The candidate follows a clear nearby final approach to the actual destination
once on the last graph leg. A standing-hull sweep checks the approach; movement,
floor support and actor avoidance still apply. A native retest reaches about
(334, -202, 28) inside the existing arrival tolerance, without the circling phase.
This focused route test uses diagnostic setup, not a complete natural opening.

## Interaction prompts

Travel activation and the displayed Talk hint used different conditions.
Darvame/Selvil's travel menu could be available while the generic greeting
cooldown hid the hint. One driver target query now serves activation and prompt.
Ordinary NPC activation accepted a nearby, clear, facing candidate, but the hint
also required an exact ray hit on the shorter collision box. The hint now uses
the same candidate rule. Intro actors and voiceless actors are excluded before
expensive line-of-sight traces in both the native hint and QC greeting selector.

Native tests show Fargoth's `(E: Talk)` and record his manual response counter
rising from 0 to 1 after E. A grounded Darvame test shows the prompt and opens
the travel menu. Host checks cover both drivers, cooldown, blocked sightlines,
ordinary facing with a missed exact ray, and intro-actor exclusion. Speech panels
still take priority over the lower hint area while dialogue is displayed.

## Underpasses and player dimensions

The cause/fix history is maintained in
[Mesh tips and tricks](MESH_TIPS_AND_TRICKS.md#balmora-underpasses-and-global-player-height-v0024-dev2),
including both coordinates, source meshes, old/new collision and source triangle
checks. The original shared physical box is 14.64 x 14.24 x 33.25 after the same
quarter scaling as the world. A native body/point-sweep calibration independently
measures these effective dimensions and finds no doubled height or origin offset.
Both source passages fit that box; the converted convex unions obstructed them.

Native ordinary walking, with noclip used only to set the initial test positions,
advances the bridge from (-455,-22,142) to (-455,109,139), beyond its old y=10
obstruction. The temple advances from (-419,722,210) to about (-418,987,210),
beyond its old y=816 obstruction and up to the labelled Temple entrance.
Diagnostic forward input is reissued after regional loads. These are bounded
route checks, not citywide stair/door coverage or a full natural opening.

The global eye-height report identified another real issue: dev1 applies the
Nord eye to every character. Dev2 exports the ordinary first-person Camera pose
and original race/sex height fields. Pre-creation uses the source Dark Elf Player;
confirmed creation choices, scene changes and restored saves use the selected
height. Native logs report eye above feet 31.176 and FOV 90. Host checks cover
legacy/truncated catalogues, selection, cancellation/confirmation and unchanged
physical bounds. The full male/female source table is in
[player movement](PLAYER_MOVEMENT.md#original-race-based-heights).

The physical box is retained; the eye changes to the chosen proportions. This
is not a claim that the owner's overall height concern is closed without their
playtest, or that animated original-game camera parity is established. Quake
90-degree FOV and bob are kept. An optional slider is a performance-gated roadmap
item, not a substitute for correcting scale.

## Native memory and build checks

The largest rebuilt BSP is bm036, 5,335,048 packaged bytes (5,328,760 before
resident entity insertion), with 37,817 clipnodes and 159
unique inline models. A native visit reaches 10,122,880 hunk bytes within the
unchanged 11 MiB game heap, on 2 MiB Chip + 16 MiB Z3. The combined final route /
region check records 3,313 peak surfaces, 6,987 edges and no overflow. These are
accelerated FS-UAE functional tests, with a null host audio sink; controlled
simulation timing in route tests must not be presented as a performance benchmark.

All 278 host tests pass, including native C fixtures. The native 68040/FPU build
retains the established optimization/toolchain settings. Complete warning text,
source path and warning class compare 85 baseline to 82 candidate, with no new
diagnostic and three old aw_nav indentation warnings removed. The 82 remaining
warnings are retained in the private build logs; this is not a warning-clean build.
The missing ED_FindGlobal prototype was also supplied for correct host pointer
handling in the newly exercised hint path.

## Remaining work

- Optimize the ship after profiling; no general frame-rate fix is claimed here.
- Owner playtest of proportions at 90-degree FOV and the corrected race/sex eye.
- Full natural opening/guard/menu flow and wider walking, stair and corner checks.
- Balmora interiors, other Strider routes, richer NPC behavior and background
  streaming remain unfinished. Region loads still pause synchronously.
- Rebuilt content has a new save fingerprint; dev1 saves are not compatible with
  this geometry/catalogue change. Start a new game or Demo Game in this package.
