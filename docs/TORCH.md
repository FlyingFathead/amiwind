# Carried torch

Press **F** to raise the hands, then **V** (`aw_torch`) to toggle the torch.
V can select it during the draw animation; illumination starts when the hands
are raised. V puts it away; F lowers the hands and extinguishes it. Shift+V
retains its draw-distance shortcut. Personal bindings can override V.

rc9 converts the original `torch` equipment mesh and an animated holding pose
from the owner's installation. The old independent screen-space wooden shaft
is removed. This remains temporary equipment: no inventory, fuel or durability.

## Secrets of the original torch

The base master and its NIF/animation records supply the following information;
none of the mesh, textures or animation data is redistributed in public source.

| Source | Meaning and use |
| --- | --- |
| `LIGH` object ID `torch` | Resolves `MODL` to `l\light_torch10.nif`. |
| Four visible mesh shapes | 35 + 3 + 100 + 100 = **238 triangles**, all retained. |
| `ShadowBox` | Separate helper geometry; excluded from the carried model. |
| `base_anim.1st.nif` | `torch: start` 46.0, `torch: stop` approximately 48.666668 seconds; eight sampled holding frames. |
| `Shield Bone` | Left-hand equipment attachment, beneath `Bip01 L Hand`. |
| `BoneOffset` | Authored grip translation, applied after equipment rotation. |
| `Fire Emitter` | The flame's attachment point; transformed with the same mesh pose. |
| `Smoke Emitter` | Original smoke origin, retained as a future effect reference. |
| `AttachLight` | Authored light anchor, recorded alongside the flame anchor. |

The easy-to-miss detail is that a **carried light rotates −90 degrees about its
local X axis before BoneOffset translation and the animated Shield Bone**.
Without that convention, the torch lies sideways even when its hand animation
and named attachment are correct. It is not the mirrored `Left Hand` body-part
attachment. The carried-light convention was cross-checked against OpenMW's
[ActorAnimation attachment](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwrender/actoranimation.cpp)
and [equipment transform](https://github.com/OpenMW/openmw/blob/master/components/sceneutil/attach.cpp).
AmiWind uses its own row-vector NIF assembly code; no OpenMW implementation is
bundled. The same helper transforms both geometry and emitter anchors.

The converter layers the source torch animation on the left arm over the source
unarmed idle pose. Sampling the entire skeleton at the torch timestamps also
samples unrelated right-arm animation. The right arm therefore stays on the
unarmed idle timeline. The common first-person camera transform moves the whole
assembly forward four native units for the Quake near plane; it does not change
the torch's position relative to the holding hand. NPC attachment must omit this
player-camera adaptation.

## Fire, smoke and the palette renderer

The original fire controller names `tx_firealpha10.tga` and `Fire Emitter`;
normal asset resolution also supports DDS replacements. Its source particle
array has 16 entries, emission rate 6, speed 9 with random variation 2.25, and
life 1.2 with variation about 0.3333 in the source controller's units.
The smoke controller names `tx_smokealpha00.tga` and `Smoke Emitter`; its source
array has 13 entries. These are source findings, not measured Amiga budgets.

The current adaptation draws six small animated flame billboards from a 16×16
conversion of the source fire texture. Its mask and normalized brightness feed
a warm palette ramp and ordered transparency. The flame rises from the animated
source emitter; it is not a fixed rectangle next to the fist. This is a bounded
approximation of the original effect, not a complete NetImmerse particle-system
port. Smoke remains deferred so its overdraw can be measured separately.

One keyed monochrome Quake dynamic light has radius 141–148 native units. It
stays at the safe eye position, rather than blindly placing a light through a
nearby wall at the drawn torch tip. The recorded AttachLight anchor leaves room
for a future collision-aware placement policy. The flame looks warm; surfaces
receive brightness, not orange RGB light or shadow casting. Thin walls do not
guarantee occlusion. Water rendering is unchanged.

## Conversion and runtime

`tools/prepare_torch.py` runs during image assembly, including engine/image-only
recovery. It reads the owner's master, mesh, first-person animation and textures.
The inspected base data produces 551 combined hand/torch triangles and 1,653
vertices, below the existing 2,000-vertex small-model limit. Exact counts and
checksums are recorded in the private build's `torch-conversion.json`.

| Generated file | Purpose |
| --- | --- |
| `progs/v_torch.mdl` | Original mesh/materials combined with sampled hands. |
| `gfx/torch.aws` | Matching holding frames for `--hands sprites`. |
| `gfx/torch.awt` | Bounded big-endian emitter/light anchors, duration and fire texture. |

The 716-byte AWT1 payload is checked at startup. The runtime switches only the
first-person presentation while equipped; existing F/V and QuakeC state rules
remain in use. Normal fist animation is unchanged. Torch selection survives
ordinary door/region crossings; lowering, death and new-game/save hand resets
extinguish it. Punching is suppressed while equipped. Missing metadata disables
the torch with a rebuild message. Viewmodel hiding, chase view or very wide FOV
can hide the held model while the equipped light remains active.

## rc7 crash and rc8 correction

The owner reported a crash on F then V after successful rc7 image assembly.
The old brush-lighting path treated a negative leaf root as a node-array offset.
A host address-sanitized test reproduces the segmentation fault through the
actual R_DrawBEntitiesOnList entry point. The earlier torch test exercised the
light marker directly on a synthetic tree; it missed this render integration.

rc8 marks each model's validated visible surface range. Converted mesh collision
nodes are not a render tree: some roots are negative and positive roots may
contain zero visible-face references. Simply skipping negative roots would leave
scenery unlit. Position/rotation conversion remains in use, with local model-box
and plane-distance rejection to limit lighting work. The world tree and tiled
water/sky drawing paths are unchanged.

Regression coverage includes the render entry point, negative and collision-only
roots, a separate surface array, face-zero models, rotated/translated instances,
out-of-range surface metadata, expiry, tiled-face exclusion and light slot 31.
The fix still needs the same F-then-V sequence retested on the target emulator.

## Original-model replacement and reported hand flicker

The owner reports that fists stay visible, blink completely off very briefly,
and return immediately. That brief blink repeats approximately every **1–2
seconds**. This is the interval between blinks, not a 1–2-second disappearance.
It has happened since hands were first implemented and is not a torch regression.
The cause remains **unknown and open**.

The retained idle clip lasts 2.666672 seconds. All eight baked idle frames are
nonempty. A run of the actual compiled QuakeC in the host interpreter retains
the model and valid idle state through 20,000 updates over 140 seconds. Those
checks do not reproduce the live display defect or establish the animation loop
as its cause. Renderer checks with a synthetic framebuffer also do not cover
Amiga display buffers, live protocol, camera movement and whole gameplay frames.

A separate report described F temporarily failing to raise/lower hands. Repeating
debug mode and map visits did not reproduce it; neither is a confirmed trigger.
Keep this unknown-state report separate from the regular visibility blink.
See the [bug journal](BUG_JOURNAL.md).

## Shared equipment asset and acceptance

Guards should eventually use the same original `torch` identity, mesh, materials
and emitter nodes, attached through each NPC's authored skeleton. The player
camera transform is not part of equipment identity. Night schedules, equipping,
unequipping, inventory and light budgets for multiple guards remain future work.
This checkpoint does not implement NPC torch schedules.

Source tests, original-data conversion, host rendering and native compilation
are separate from emulator acceptance. Before final release, replay F then V,
V off/on, F lowering, a door crossing, a cave wall and camera turns. Check grip,
flame alignment, absence of the old crash, cave brightness and performance.
The recurring fist blink remains open until reproduced and corrected.
