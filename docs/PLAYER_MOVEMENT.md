# Player scale, collision and camera motion

The owner reported blocked stairs, excessive resistance on mild slopes and
idle downhill sliding in checkpoint-011. The old standing player used Quake's
32 x 32 x 56 box although the imported Morrowind world is scaled by 0.25.

## Verified base dimensions

The owner's `meshes/base_anim.nif` Bounding Box gives half extents approximately
29.28 x 28.48 x 66.5 and centre z=66.5. OpenMW reads that collision box in
`mwphysics/actor.cpp`. `Npc::adjustScale(..., false)` in `mwclass/npc.cpp` does
not apply race height/weight to collision; those proportions affect rendering.
An individual reference scale still applies. This prototype uses reference
scale 1 and a centred player hull:

| Quantity | AmiWind world units |
| --- | --- |
| Minimum | -7.32, -7.12, -16.625 |
| Maximum | 7.32, 7.12, 16.625 |
| Full body dimensions | 14.64 x 14.24 x 33.25 |
| Eye above origin | Selected eye above feet minus 16.625; dev2 pre-creation 14.551 |
| Eye above feet | Race/sex Camera-bone sample; dev2 pre-creation 31.176 |

This replaces a footprint about 2.2 times too wide. It is a base humanoid
collision profile. The dev2 eye-height selection is independent of this box.

## Physical recheck, v0.0.24-dev2

The owner reports being too tall relative to both Seyda Neen and Balmora. A live
Amiga calibration room compares body and point sweeps against known flat walls,
floor and ceiling. This tests the effective baked collision, not just constants:

| Axis | Negative body / point stop | Positive body / point stop | Measured full size |
| --- | --- | --- | --- |
| X | -56.64875 / -63.96875 | 56.64875 / 63.96875 | 14.640 |
| Y | -56.84875 / -63.96875 | 56.84875 / 63.96875 | 14.240 |
| Z | 16.65625 / 0.03125 | 43.34375 / 59.96875 | 33.250 |

The common trace epsilon cancels in each difference. No hidden doubled height or
vertical hull-origin shift is present. The original full collision dimensions
are 58.56 x 56.96 x 133; scenery, terrain and player all use the same 0.25 scale.
The two reported Balmora passages also fit this body against original triangles;
their converted concave collision was obstructing the routes. Source triangle
tests include larger-body positive controls. See the full symptom/cause/fix
record in [mesh notes](MESH_TIPS_AND_TRICKS.md#balmora-underpasses-and-global-player-height-v0024-dev2).

Dev1 nevertheless applies the Nord eye fixture to every character. Dev2 exports
the ordinary idle Camera bone (124.7052 source units) and each race/sex height
into an optional AWE1 catalogue trailer. It uses the source Player race before
creation, applies confirmed choices immediately, and reapplies the selected eye
after scene/save restoration. Dark Elf/Imperial eyes are 31.176 units above feet,
Nord 33.047, High Elf 34.294, Breton female 29.617 and Wood Elf male 28.059.
Legacy catalogues retain their baked eye fallback. Physical collision is unchanged.
Host checks cover catalogue bounds, legacy data, pre-creation selection,
confirmation/cancellation and unchanged physical bounds. The native rebuilt
catalogue reports 31.176 before creation.

Keep **90-degree horizontal FOV** and the existing Quake bob. The optional slider
in the roadmap must pass a performance comparison and is not a world-scale fix.
These measurements do not establish original-game animated camera parity or
close the owner's broader assessment of player proportions.

## Original race-based heights

Read directly from the owned base `Morrowind.esm` playable RACE records, RADT
male/female height fields (30 September 2026). These are relative height
multipliers, not metres and not the separate weight fields.

| Race | Male height | Female height |
| --- | --- | --- |
| Argonian | 1.03 | 1.00 |
| Breton | 1.00 | 0.95 |
| Dark Elf | 1.00 | 1.00 |
| High Elf | 1.10 | 1.10 |
| Imperial | 1.00 | 1.00 |
| Khajiit | 1.00 | 0.95 |
| Nord | 1.06 | 1.06 |
| Orc | 1.05 | 1.05 |
| Redguard | 1.02 | 1.00 |
| Wood Elf | 0.90 | 1.00 |

Nords are taller than the 1.00 baseline; High Elves are taller still. This is
source-defined character stature, not an AmiWind invention. Dev2 uses these
values for `eye above feet = sampled first-person Camera height * 0.25 * race/sex
height`. It does not multiply the base collision box by race height. The earlier
fixed Nord camera incorrectly applied the 1.06 proportion to all choices.

References inspected at OpenMW revision
`46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:
[actor.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwphysics/actor.cpp),
[npc.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwclass/npc.cpp),
[movement constants](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/misc/constants.hpp),
[physics constants](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwphysics/constants.hpp).
No OpenMW implementation is incorporated into the runtime.

## Matching the baked map

Changing the player box alone is insufficient: Quake standing collision is
pre-expanded into a BSP hull. The converter compiles an anisotropically scaled
copy of the world with external unmodified qbsp, then transforms the standing
clip planes back, including the vertical origin offset. It grafts only that
standing hull into the visible world and expands architectural proxies using
the same profile. The image builder rejects a scene without the matching
`tes3-humanoid-v1` marker. Old compiled scenes must be rebuilt.

Visible surfaces, point traces and visibility data remain separate. Building
proxies remain approximate convex unions. Yaw-rotated proxies also rotate the
pre-expanded player footprint; they are not exact arbitrary-orientation AABB
sweeps. This limitation still needs targeted corner/stair tests.

## Ground support and feel

Step-up height is 8.5 units (OpenMW's 34 at scale 0.25). Downward support
is deliberately limited to 8.75 units in this prototype, rather than copying
OpenMW's larger 62-unit descent allowance. Slightly tilted riser planes can
request the same step test as an exactly vertical riser.

A confirmed walkable support suppresses gravity-driven downhill creep and
follows the uphill tangent without reducing the commanded horizontal speed.
Supported walking can follow a bounded downward step. A jumping, falling,
swimming or noclip player must not be glued to nearby ground. The native
step-down code must test the hit object's solidity, not the player's solidity,
before restoring grounded state.

Keep the owner's preferred Quake camera motion: `cl_bob 0.02`,
`cl_bobcycle 0.6`, `cl_bobup 0.5`. These defaults and the view code are unchanged.
Collision fixes must not remove bob or replace it with a motionless camera.

See checkpoint-012 validation for native evidence and remaining limitations.

## Checkpoint-013 architectural ghost volumes

The owner reported an invisible square obstruction after slopes/stairs improved.
Expanding only a convex piece's facet planes creates large solid spikes at acute
corners. Add six axial support limits before expanding each piece by the standing
player box. Point traces retain their original hull: the extra limits are only
needed for the expanded standing hull, saving memory and visibility-trace work.

A host grid found 246 old solid hits outside expanded model bounds and zero after
the change. Native comparison reproduced a false-solid point at (0,136,90): old
code refused to leave noclip, while the corrected image grounded the player and
walked across the square. This is a reproduced local defect, not proof that it is
the exact spot in the owner's screenshot or that all collision is now exact.
Use `aw_pos` and `aw_blockers` to report any remaining location.

## Eye-height audit, checkpoint-016 development

The owner's low-camera report is credible: the existing `view_ofs.z=13.3`
places the nominal eye 29.925 runtime units above the feet (119.7 source units),
before bob and network quantization. That value was a prototype choice, not
verified first-person parity.

The already-converted first-person skeleton's Camera bone is at 31.187569
runtime units above the source origin in the sampled unarmed pose. The owned
Nord race record gives male height 1.05999994: applying that scale gives about
33.0588 runtime units (132.235 source units). This is roughly 10.5% higher than
the old nominal eye. Verify reference origin, animated camera motion and race
transform against an original/OpenMW view before declaring exact parity.

At the pinned OpenMW revision, first-person camera tracking uses the animation's
Camera node (Head fallback), not the constructor's 124-unit third-person height.
Reference: [camera.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwrender/camera.cpp),
`calculateTrackedPosition` and `processViewChange`. This is a behaviour audit;
no implementation is copied. The collision footprint should not be widened to
correct an eye-height discrepancy.

Checkpoint-016 now bakes this calibrated eye offset into `aw_eye_height` in both
worlds. Local first-person rendering reads the exact server value to avoid the
legacy signed-byte network view-height quantization. Quake walk bob remains.
`dbg eyeheight` prints the current values; an optional 4..24 offset permits A/B
comparison. This corrects the documented prototype value, not a claim of exact
animated camera parity for every race/equipment combination.

## Dev1 regression comparison, 28 September 2026

Owner reported that guards seemed smaller or the player taller. Recompiled the
owner's v0.0.17 snapshot and compared it with v0.0.18-dev1 on the same HDF,
scene, spawn and emulator configuration. Both native logs report eye offset
16.434 / eye above feet 33.059, player origin (16,44,60), and identical placed
NPC coordinates. Fargoth/guard MDLs and both BSP files are byte-identical to
the pre-UI scene. The matched native screenshots show the nearest guard at
roughly 89 pixels in both builds.

The UI reserves 48 bottom rows: the 3D viewport is now 320x152, compared with
320x200 when the previous debug strip was off. Horizontal FOV, pixel aspect,
projection scale, collision hull and eye offset are unchanged. The visual centre
moves upward by 24 pixels. FS-UAE scaling is another presentation variable;
these captures held it fixed. Do not rescale actors to compensate for framing.

Original-data caveat: free exploration still uses the calibrated Nord male
first-person fixture. The base master's pre-creation Player record is Dark Elf.
Creation must choose race/sex eye proportions explicitly; existing calibration
is not proof of every original in-game camera or character appearance.


## dev4 Balmora stair entrance

The Nord report at XYZ925,-290,62 identifies `ex_hlaalu_b_17`, reference 32631.
Its convex collision approximation seals the authored stair opening. Preserve
the authored surfaces as thin collision shells for both placements, 32631 and
32644. Native walking reaches XYZ1078,-292,144 through the previously blocked
entrance. Physical dimensions, selected race/sex eye height, step/slope rules,
bob and 90-degree FOV remain unchanged. The later deformed stair report at
XYZ613,-125,59 is a different asset and remains open; see the dev4 investigation.
