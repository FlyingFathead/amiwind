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
| Eye above origin | 16.4338 (sampled Nord male camera, checkpoint-016) |
| Eye above feet | 33.0588; collision dimensions unchanged |

This replaces a footprint about 2.2 times too wide. It is a base humanoid
collision profile, not an implementation of character creation or all races.

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
