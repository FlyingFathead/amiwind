# Checkpoint-017: ship structure repair and debug scene picker

Runtime **v0.0.15-dev2**, source **0.12.0.dev2**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

<!-- contents start -->
## Contents

- [Delivered scope](#delivered-scope)
- [Diagnosis and host validation](#diagnosis-and-host-validation)
- [Native acceptance by build](#native-acceptance-by-build)
- [Exact environment and artifacts](#exact-environment-and-artifacts)
- [Remaining reports](#remaining-reports)
- [Live visibility trial and final control acceptance](#live-visibility-trial-and-final-control-acceptance)
- [Ship contribution diagnostic](#ship-contribution-diagnostic)

<!-- contents end -->

## Delivered scope

Restore selected structural interior surfaces and their source UVs; retain
reduction for other detail and keep collision unchanged. `dbg scene change`
opens the two-scene menu, also through `debug` and `amiwind debug`; arrows/Enter,
mouse and Escape/Cancel work through the existing menu path. Missing BSP files
are disabled. Direct ship/town commands and E hatch use remain.

Add a live Options → Graphics fog-distance slider and exact debug aliases.
Default stays 700 local units. Left/Right steps by 10; Shift steps by 1; reset
restores 700. The same setting controls fog and forward-depth culling. Existing
32 KiB fog-table storage remains; rebuilding now uses 15 integer divisions and
band fills rather than 32,767 floating-point divisions. Add default-off `dbg fps`
using the existing profiler time sample and a roughly one-second average.

This is an opening-location preview, not the original opening quest. No new
native NPCs, container interactions, daylight cycle, water feedback or audio
scheduler changes are included. Those requests are preserved in
SEYDA_NEEN_NEXT_STEPS.md and the roadmap. The new private vicinity audit lists
15 exterior and 28 directly linked interior NPC references, with separate cast,
door/container metadata and conditioned voice candidates. It does not spawn them.

## Diagnosis and host validation

The source mesh and transforms render a curved lower hold; reducing the entire
shell at .08 ratio flattens it through the furniture. Independent host raster
comparisons and owner native screenshots agree on this failure. Host renders
are diagnostic source projections, not OpenMW screenshots or exact lighting parity.
The fix retains named lower-hull, floor, wall, ceiling, stair and plank groups.
A synthetic curved-mesh test checks exact retained triangles/UVs and rejects
invalid preserved-material requests. Missing requested source prefixes fail conversion.

97 host tests passed with AMIWIND_RUNTIME_SOURCE set to the actual dev2 r6 tree:
no skipped native tests. Menu checks exercise both scene choices, cancellation
and missing files. Fog tests compare all 32,768 depth entries against the numeric
profile at five distances, test culling after adjustment and reject invalid
values; HUD tests cover default-off FPS and overlay suppression. Four new vicinity tests cover exterior/interior separation,
door metadata, conditioned packages, deletions, unresolved links and duplicate
cells. The first vicinity fixture caught incorrect CELL deletion when a placed
reference had DELE; the corrected header-only cell check preserves other refs.

Amiga engine r1 failed compilation because the scene-picker drawing branch was
misplaced; r2 fixes it. Later r3/r4 add live controls and fine steps; r5 adds FPS. Native
options testing caught a numeric-readout ABI issue (slider moved correctly but
text showed zero); r6 uses the explicit long formats already used by other
Amiga HUD values. Final image r5 reads every
payload back from the RDB/FFS image and checks legacy root metadata. Existing
compiler warnings remain. Fresh full-game guided conversion was not rerun:
source exterior/NPC/hand outputs are retained, interior extraction was rebuilt,
then its cached export was recompiled with additional stair/plank preservation.
Public prepare_interior.py contains the final matching recipe.

## Native acceptance by build

Geometry/menu route: `interior017-native-r1`, fresh writable copy of candidate
image r1, engine r2, 3D hands. It predates the live fog/FPS additions.
Boot, a short startup walk, three lower-hold report views, all three scene-picker
prefixes, cancel-to-console, town/ship selections, both controlled E hatch
transitions and clean Exit to DOS passed. No ERROR.TXT; the existing harmless
`aw_hull is not a field` warning remains. Screenshots confirm restored curved
hull space and a recognizable ramp at the reported locations. Network angle
quantization means displayed DEG/P can differ by roughly 1–2 degrees from the
requested command pose. Exact original-game visual parity is not claimed.

The E tests first place diagnostic cameras and then disable noclip. They do
not certify a continuous unassisted lower-to-upper stair route. That remains
an explicit acceptance item. Hatch open/closed geometry and persistence are
still TODO; the current link loads another scene with a static hatch mesh.
The owner's exterior formation at (211,447,47), requested yaw4/pitch0, is
reproduced and remains unfixed; its identity is not proven by the screenshot.

Four scene leave/enter pairs retain the same music track and increasing played
frames. Map-ready times were 290, 234, 285 and 222 ms on this accelerated emulator.
Zero music file errors; clicks/underruns remain open. This route does not finish
a full song and does not replace prior playlist/full-track validation.

| Geometry/menu route counter (r1) | Value |
| --- | ---: |
| Frames | 2754 |
| Elapsed ms | 150376 |
| Surface overflow frames | 0 |
| Edge overflow frames | 0 |
| Maximum surfaces | 6757 |
| Maximum edges | 12774 |
| Hunk bytes at exit | 7997088 |
| Free Chip bytes | 1796432 |
| Free Fast bytes | 5046960 |
| World ms | 88615 |
| Entities ms | 248 |
| C2P ms | 370 |
| Hands ms | 17 |
| Audio late updates | 2 |
| Missed audio frames | 8655 |
| Warmup missed frames | 3534 |
| Worst frame us | 1003939 |

Interior BSP is 3,538,308 bytes, +54,428 over dev1; 26,572 faces (+499),
19,304 vertices (+302), same 14,566 nodes and 23,487 clipnodes. Shell reduced
triangles: 8,257, previously 7,404. Existing authored collision remains unchanged.
Exterior BSP is byte-identical, SHA-256:
`c376306a581cb2f9fdad92e646ad3ed0d5a8bafdcf499091e69d37b57b2f3dac`.
The heap reservation remains 9 MiB in the same 16 MiB Fast configuration.
Source retains both 3D and experimental sprite-hand paths; only the default
3D HDF is rebuilt/distributed in this hotfix. The prior dev1 sprite image remains
an immutable separate experiment, not a dev2 build.

## Exact environment and artifacts

FS-UAE **3.1.66**, A1200/AGA/PAL, **68040-NOMMU**, internal 68040 FPU, JIT/max
(resolved cache 8192), 2 MiB Chip + 16 MiB Z3 Fast, 24-bit addressing disabled,
keyboard joystick off. No Workbench desktop. WinUAE preset is guidance, not a
local WinUAE test. No physical-Amiga or stock-A1200 performance claim.
ROM: Kickstart 3.1 A1200 **40.68**, 524,288 bytes, SHA-256:
`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`.
FS-UAE executable SHA-256:
`b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.
AmigaPorts GCC 16.2-rc11 / 16.2.0b20260825082934, 68040/FPU.
AmiQuake commit `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`;
archive SHA-256 `43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c`.

HDF: 134,250,496 bytes, 128 MiB FFS partition in RDB, 18 music tracks.

| Artifact | SHA-256 |
| --- | --- |
| HDF | `d481b67d304a70758983d87b6c6dc610224038cee32de5863954e38d9bdef0fe` |
| Executable | `d796e4a3403a93ce2f2bc87f24fdf9354e3ba1499afb60c3bd98badc2088d74d` |
| 68000 preflight | `4eb7a089dce45963d4442a49ee69e2ea06ddd9b852fb5b8320b97f6b1972c54a` |

## Remaining reports

Owner visual acceptance pending. Exterior formation/Silt Strider coverage,
ship deck/bow gaps, disappearing house, underwater warm tint, audio clicks and
reported WinUAE slowdown remain tracked. Opening scripts and NPCs, Census
interior, hatch state, containers, dialogue, save/load, sky and torches are not
implemented by this hotfix. See the roadmap and follow-up register.

## Live visibility trial and final control acceptance

`interior017-native-r2` uses image r3/engine r4. It verifies both scene directions
and live fog changes with zero edge/surface overflow and zero music read errors;
its numeric menu text was faulty, so it is not the final UI acceptance. At the
owner's requested camera (-44,259,75), yaw328/pitch-14 (quantized to 327.65/-12.66),
stationary windows inside the recorded screenshot brackets gave:

| Fog/cull distance | Measured frames / time | Effective FPS | Median sampled frame |
| --- | --- | ---: | ---: |
| 700 | 80 / 6.981 s | 11.46 | 86.13 ms |
| 400 | 130 / 7.552 s | 17.21 | 58.10 ms |

Same run, machine, camera, hidden hands and overlay; no native memory increase.
Frame intervals span the full selected windows; median values sample every tenth
frame. This is one short stationary comparison with no confidence interval, not
a stock-hardware benchmark or proof of the cause of the owner's regression.
The nearer cutoff visibly changes what can be seen. Do not count missing source
geometry as an optimization. The broader ship/no-ship and overhang/material A/B
comparisons remain TODO; WinUAE 1440p output is another owner-reported variable.

An earlier three-checkpoint comparison was interrupted during its third run.
The older checkpoint also has a different eye height. Those captures are kept
as incomplete diagnostic evidence, not used to claim a regression or speedup.

Final `interior017-native-r3` uses **image r5, engine r6**, the packaged default
3D build. Fresh boot, `dbg fps on`, scene picker to town, exact distance675,
slider675→665→664→700, Escape/back, overlay off/on, individual FPS off and clean
Exit all pass. Native screenshots verify actual numeric values and an FPS value
consistent with the slow-view profiler. Default-off behavior is preserved.
No ERROR.TXT; zero surface/edge overflow. This final supplemental route does
not re-run the long hatch route; r2 above exercised that unchanged code.

Final supplemental route: 1237 frames / 102574 ms; max surfaces9717 / edges17783;
hunk7677200 bytes, free Chip1796432 / Fast5045136; 3 audio late updates,
8640 missed frames (3164 at warm-up). Audio remains an open problem.
97 host tests pass against final r6 source with no skips.

## Ship contribution diagnostic

`ship017-native-ab` uses the final engine with a separate private map candidate.
Only exterior hull submodel15's visible surface count changes from3931 to0.
Collision, existing arrays/texture allocation and separate ship attachments
remain. At the same town camera and fog700, selected stationary windows give
**10.52 FPS with hull surfaces vs 12.44 FPS suppressed**. No render overflow
or music read error; the on-screen town view is otherwise unchanged.
This suggests some hull rendering cost at that camera, but it does not explain
all of the low frame rate or establish the original regression's cause. It is
one short run, not a statistically controlled benchmark. Keep testing the
building/overhang and cache paths. The normal playable image retains the ship;
the suppression candidate is diagnostic evidence only, not a shipped gameplay
mode or a geometry optimization. It does not measure the potential memory
saving from removing the entire ship assembly after the opening.
