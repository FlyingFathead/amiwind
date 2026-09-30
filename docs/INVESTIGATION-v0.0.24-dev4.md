# Seyda Neen subdivision and Balmora follow-up

30 September 2026. Delivered dev3 artifacts remain unchanged. This record
separates reported symptoms, inspected causes, corrections and remaining limits.

## Accepted dev3 behavior

The owner reports that Balmora regions/sub-cells work surprisingly well and are
a promising foundation for streaming the wider game without disruptive scene
breaks. Keep the frozen last frame with a small top Loading... box as the default;
retain the black-screen option. Loading still replaces one BSP synchronously.
The owner explicitly accepts the Balmora Silt Strider: do not change its dev3
geometry/profile. Its earlier broken-appearance report is superseded.

## Seyda Neen residency

**Symptom:** even the first pier scene and enclosed ring courtyard are expensive,
while many larger Balmora views feel faster. The existing intro variant hid
scenery and leaf marks but retained unused geometry inside the loaded BSP.

**Correction:** add 30 regular overlapping Seyda regions, the compact arrival
area `intro_seyda_neen_subcell_pier` (file `intro_docks.bsp`) and separate
`sncourt.bsp`. Select complete intersecting models using transformed bounds;
the intro uses a conservative eight-sided footprint guided by the owner's map.
Keep the Strider, driver, ship/plank/pier and nearby Census buildings.

The compactor removes unused models and their referenced geometry, textures,
collision nodes and planes. It remaps indices without simplifying retained
meshes. World faces outside retained marks are removed; source inner terrain
collision and PVS remain, with outer coverage collision planes. Region core size
is 768 with merged partial edge cores, overlap 896 and hysteresis 96. Both region
exteriors cap effective draw distance at 540; a larger stored request is preserved
for other scenes. This cap is a coverage requirement, not a claimed FPS cure.

| BSP | Dev3 bytes | Dev4 bytes | Dev4 models | Dev4 faces |
| --- | ---: | ---: | ---: | ---: |
| Intro pier | 5,567,884 | 3,938,380 | 54 | 17,923 |
| Ring courtyard | Full Seyda: 5,606,204 | 3,651,132 | 40 | 15,470 |

Native diagnostic visits reach 7,710,896 hunk bytes at the intro pier and
7,188,288 at the courtyard, within the existing 11 MiB reservation. These are
specific scene/setup measurements, not a guarantee of the same FPS gain on the
owner's machine. Static source reference 227023 (Strider) and actor 270748 (driver)
remain in the intro payload. Complete placements avoid repeating facade loss.

## Distance-1000 observation

The owner repeatedly reports that the opening pier becomes faster at 1000.
A native sweep on unchanged dev3 dock geometry used the same camera position
(590,-353,56), three headings and actual uncapped 450/540/1000 distances. The
new profiler records effective distance, world render time and BSP identity.

| Heading | 450 median world ms | 540 median world ms | 1000 median world ms |
| --- | ---: | ---: | ---: |
| About149 degrees | 85.4 | 94.5 | 125.0 |
| About335 degrees | 23.9 | 22.0 | 21.0 |
| About87 degrees | 45.7 | 51.3 | 101.7 |

One view exhibits a modest reversal; others get substantially slower. These are
small diagnostic samples (roughly 5 per distance, with settling samples in some
groups), not repeated randomized benchmarks. They do not yet explain the owner's
large gain. Occlusion/draw ordering and host variability remain hypotheses.
Do not label the report fixed or infer a general benefit from increasing distance.
Prison-ship interior cost is separate and unchanged by exterior subdivision.

## Teleport arrival correction

Cross-town shortcuts now read the destination catalogue. Native visual review
also caught Census selecting the first catalogue entry (reference474482), whose
arrival landed below the room despite the local floor check. Debug teleport now
prefers the inspected pier-side registration entrance, reference113893. This
corrects the shortcut; it does not certify the separate alternate doorway.

## Opening restrictions and character UI

The source barriers do not fully contain the long pier. A player-only supplement
follows its two sides and shore end while the dock stage remains active, leaving
the ship/plank connection open. Existing authored barriers and NPC navigation
remain. Native walking tests stop sideward attempts around (596,-347,39) and
(570,-378,39), while a forward approach reaches(379,-208,39), movement type 3.
These are focused checks, not full natural-opening acceptance.

Census door reference 119513 back to the pier is locked during registration.
Continue through the courtyard. Host checks cover restriction and later release.
Choose is highlighted in confirmation dialogs; review has a centered page counter.
Native captures confirm the review title and Choose highlight.

Shift+V cycles 450/540/1000 requested distance. Startup removes only exact old
generated distance bindings on 1/2/3, preserving unrelated custom bindings.
The numeric keys are available for the planned keymap.

## Balmora stairs: one corrected opening, wider defects still open

| Reported camera | Placed asset | Finding / status |
| --- | --- | --- |
| 925,-290,62; yaw1, pitch-18 | `ex_hlaalu_b_17`, ref 32631 | Convex collider seals the authored stair opening; corrected |
| 613,-125,59; yaw22, pitch-5 | `ex_hlaalu_dsteps_03`, ref 41159, beside `ex_hlaalu_b_04`, ref 22548 | Visible broken/jagged treads reproduced; source/conversion cause and traversal remain open |
| 1182,-141,119; yaw91, pitch-12 | `ex_hlaalu_dsteps_03`, ref41134, beside `ex_hlaalu_b_04`, ref22539 | Another blocked stair instance; owner report, open |
| -883,126,300; yaw346, pitch-14 | `ex_hlaalu_b_13`, ref 24020 | Narrow stairs cannot be climbed; owner report, open |
| 962,119,64; yaw18, pitch-8 | `ex_hlaalu_b_15`, ref 41379 | Owner reports jagged treads and blocked ascent; recurring defect, not covered by b17 correction |

For b17, preserve authored collision surfaces as thin shells for both references
32631 and 32644. Rebuild nineteen affected regions. Visible vertices, UVs, edges
and textures remain byte-identical to dev3; the accepted Strider stays intact.
Native ordinary walking advances from (924,-290,62) to (1078,-292,144), beyond
the old blockage and up the stairs. Player dimensions, selected race/sex eye,
step/slope rules, bob and 90-degree FOV remain unchanged.

The second camera reproduces the visual issue on unchanged dev3 geometry.
Trying to leave noclip at that exact point reports inside-solid, so the subsequent
free-flight path is **not** walking evidence. Do not claim traversal from it.
See ROADMAP.md's **FIXES NEEDED IN BALMORA** for a reusable stair conversion and
standing-hull ascent/descent validation algorithm, plus memory-cost acceptance.

## Jagged door arches

Owner screenshots show irregular dark strips around many upper doorway arches:
(1218,-792,120), yaw352/pitch-7; (1269,-788,133), yaw343/pitch-18; and
(-1012,-939,142), yaw204/pitch-5. These remain open visual defects.
Inspect source triangles, wall/door overlap, merging and depth ordering. A baked
flat surface/bitmap is a candidate to compare against corrected geometry, with
near/oblique views, interaction, collision and measured rendering cost retained.
This is linked to J021's concealed door/wall geometry work, not silently marked
implemented. The whole-map polygon-density study is next-version roadmap only.

## Missing street texture

Owner report: XYZ455,-699,61, yaw3/pitch17 (screenshot HUD yaw1/pitch16).
The image shows a broad flat untextured patch by a lightpost and two doorways.
Restore continuity with the usual paving after checking source placement,
materials and converted UV/texture references. Geometry loss versus texture
mapping is not yet isolated. This remains an open TODO, with floor collision
and seam checks required.

## Hlaalu guard chest armor

Owner screenshot: XYZ862,-502,58, yaw290/pitch13, v0.0.24-dev3. The torso/chest
plate is visibly absent or transparent. Material conversion is the owner's
hypothesis, not a confirmed cause. Inspect equipped armor/body slots, missing
submeshes, triangle retention/winding and material/alpha conversion separately.
This is an open actor-conversion defect, distinct from the static architecture.

## Validation and limits

283 host tests pass, including compactor remapping/pruned world collision,
region/courtyard selection, intro restrictions, confirmation defaults and key
migration. Native GCC diagnostics compare 82 to 82 with no added or removed
warnings; full text is retained privately. Existing warnings remain work.
The native profile remains 68040/FPU/JIT, 2 MiB Chip, 16 MiB Z3 and an 11 MiB heap.
Tests use an offscreen emulator/null host audio sink; deterministic walking runs
are not FPS benchmarks. Full opening/citywide walking and owner acceptance remain
open. New geometry changes the save fingerprint; dev3 saves are incompatible.


Final packaged-HDF check: all 706 payload files read back with matching hashes.
The final executable boots from a diagnostic copy, opens the teleport menu,
visits Balmora/Census/Seyda Neen/prison, crosses four Seyda boundaries with
freeze/black/freeze choices, and walks the corrected b17 stair. Census now
arrives at approximately (3,-33,64) inside the registration room. The full route
records no surface/edge overflow, a peak sampled hunk of 10,219,920 bytes and
Seyda region replacements of 258–460 ms on this host. Packaged HDF bytes remain
unchanged by the diagnostic run. Citywide and natural-opening acceptance remain
separate; this route does not certify the newly reported Balmora defects.
