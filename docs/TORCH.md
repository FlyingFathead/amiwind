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

The current guard-torch work reuses this original equipment identity through
each NPC's authored skeleton. Its controls, source rules and bounded lighting
policy are described below. The player camera transform is not part of NPC
equipment. Image015 passed bounded native guard-admission, boundary and visible-particle checks. The 2 MiB safety-reference comparison remains a reserve warning.

Source tests, original-data conversion, host rendering and native compilation
are separate from emulator acceptance. Before final release, replay F then V,
V off/on, F lowering, a door crossing, a cave wall and camera turns. Check grip,
flame alignment, absence of the old crash, cave brightness and performance.
The recurring fist blink remains open until reproduced and corrected.


## Guard torches and the clock — scoped native verification passed

The current runtime adds clock-driven torches to the converted Imperial guards
in Seyda Neen and Hlaalu guards in Balmora. It identifies the original `Guard` and
`Ordinator Guard` classes, never guesses from a displayed name, and reuses the
original carried-light mesh, third-person left-hand pose and flame texture.

| Control | Default | Effect |
| --- | --- | --- |
| `guards_torch_cycle true` | true | Enable automatic guard torch use; archived in configuration |
| `guards_torch_cycle false` | — | Disable automatic use while retaining the explicit debug override |
| `dbg guardtorch on` | — | Force torches on for all supported, eligible guard render records, including those without a source inventory torch |
| `dbg guardtorch off` | — | Force guard torches off |
| `dbg guardtorch auto` | auto | Clear the session override and resume the configured automatic policy |

The setting and on/off forms also accept `1/0` and `true/false`. The debug
override is a session diagnostic, not saved inventory. It affects guard types,
not arbitrary NPCs, and still requires valid converted companion assets.

Automatic use reads the actual saved world clock: **before 06:00 or after
20:00**, with exactly 06:00 and 20:00 excluded. It requires a validated exterior,
an original carryable inventory light using `l/light_torch10.nif` (including
`torch_infinite_time`), and no active enemy/combat field. No interior ambient or
regional weather state is guessed. Manual `on` bypasses the clock, inventory
and exterior requirements; corpse/dead and swimming exclusions still apply.
Ordinary NPCs with a default health value of zero are not mistaken for corpses.
Waiting, setting time and restoring a save use the same clock. The sky gallery's
presentation clock does not advance this equipment schedule.

### Original pose and bounded runtime cost

The converter samples the third-person `base_anim` torch interval
97.2–99.8667 seconds on the left-clavicle descendants while retaining the actor's
idle/talk/blink/walk frames and female animation override. Attachment follows
Shield Bone, the carried-light −90-degree X rotation and BoneOffset. It omits
the player's four-unit camera offset. Separate held-body and held-torch models
preserve the base NPC model, map geometry and collision bytes.

`gfx/guard-torches.awg` is the bounded AWG1 registry, with at most 32 source/model
records, companion paths, original frame layout, inventory eligibility and
per-frame flame anchors. Content-addressed `progs/gt_b_<hash>.mdl` and
`progs/gt_t_<hash>.mdl` contain the companions; `gfx/guard-torches.json` records
conversion provenance. These generated game assets remain private.

The current original-data conversion contains nine referenced source/model
records, eight distinct held-body companions and five shared torch models.
Three town guard identities have automatic inventory eligibility; the six
opening-sequence records are available through the explicit override. One is
the captain, whose original class is `Ordinator Guard`. Converted payloads total
2,813,448 bytes excluding the JSON provenance manifest; the registry is 4,148
bytes. These are disk figures, not resident RAM: companions load on demand.
Eight focused converter tests passed. The combined source subsequently passed
the full Windows and Linux Docker gates, including the Linux native guard fixture.
Those host checks do not establish native Amiga appearance or cache cost. Image014 exposed the cold alias-cache failure. The model-cache correction passed focused host tests and finalization011 gates. Its fixture changed from 41 alias loads / 40 evictions to 2 loads / 1 eviction while the actor, body and held item remained resident. The estimator now case-folds source IDs but preserves model paths. One mixed-case Imperial map counts five placements instead of two (+352,144 B); the checked Hlaalu map is unchanged. Five focused ledger tests and the Linux Docker target-ABI gate passed. Image015 passed cold admission and boundary checks for both guard factions, with three eligible actors admitted and no skips or evictions.

The runtime limits are 32 visible torch-bearing guards and the nearest
two dynamic lights within 384 native units, with a clear emitter-to-camera trace.
Flames use the normal depth test. Light is the existing monochrome surface
illumination, not coloured global lighting or full shadow casting. Fixed runtime
arrays avoid per-frame allocation, but first-use model-cache loading has a real
memory cost. Conversion and focused source tests are separate from final native
equipping, grip, transition, occlusion, frame-cost and cache-pressure acceptance;
those combined checks remain pending.

### Primary-source use rules

[OpenMW weather.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwworld/weather.cpp)
uses a strict time comparison: before sunrise or after sunset plus its duration,
and no precipitation. With the original settings of sunrise 06:00, sunset 18:00
and two-hour sunset duration, this is before 06:00 or after 20:00. Exactly 06:00
and 20:00 are outside that interval. Ash storm is excluded from precipitation
by that implementation. AmiWind currently has no regional precipitation system;
the present exterior scope follows those original clear-weather times.

[OpenMW actors.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwmechanics/actors.cpp)
selects an equippable inventory light. Outside combat it takes precedence in the
left slot; during combat a preferred shield wins. Daytime puts the light away
and restores a preferred shield. Swimming extinguishes/removes a held light.
The player's remaining light lifetime is decremented; NPC lifetime is not.

[OpenMW worldimp.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/mwworld/worldimp.cpp)
uses a separate interior policy: no-sleep cells suppress automatic use, and
otherwise the ambient RGB sum must be at most 201. That interior policy requires
authored data; a dark screenshot is not sufficient evidence. The new exterior
guard feature must not claim full inventory, combat, weather or interior parity.
