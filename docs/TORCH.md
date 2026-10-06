# Carried torch

## v0.0.29 open owner reports

On 4 October 2026, post-release v0.0.28 playtesting again found **F unable to
raise hands in debug play; V prints torch on/off but no hands or working torch
appear**. Treat [TORCH-INPUT-29](BUG_JOURNAL.md#torch-input-29-f-cannot-raise-hands-and-v-only-reports-torch-state-open)
as a high-priority recurring regression. Missing converted-world hand metadata
is a confirmed defect; the exact older owner-session cause and debug/map
involvement remain unverified. Existing control descriptions below state the contract,
not proof that this reported runtime state works. Keep the older fist blink
and previous torch crash separate.

Guard torches also fail to produce convincing surrounding night illumination
in the owner's view, and interiors lack convincing lantern/torch lighting.
[TORCH-LIGHT-29](BUG_JOURNAL.md#torch-light-29-guard-torches-do-not-illuminate-nearby-night-surfaces-open)
and [INTERIOR-LIGHT-29](BUG_JOURNAL.md#interior-light-29-interiors-lack-convincing-local-light-open)
need matched-camera surface comparisons, not just flame/admission tests.
Study original owned light records, OpenMW semantics and Quake/AmiQuake light
paths; audit conversion, final lightmap/palette contribution, radius, rejection
and ambient saturation before changing brightness. Use bounded light counts
and measure frame time/memory, especially indoors. No new RGB/shadow or FPS
claim is made by this work list.

## v0.0.29 required hands and light acceptance matrix

This is a mandatory regression gate for future input, debug/map, hand-state,
viewmodel, scene-transition or torch changes. Test the full chain; a console
"torch on" message or nonempty model is insufficient. Retain the failing state
and link any new recurrence to its source test and target replay before closure.

| Scenario | Required observable result |
| --- | --- |
| F from lowered hands in normal and debug gameplay | Binding reaches the hand-state transition; hands visibly draw and remain raised. |
| V during draw and after raised hands | Selection survives draw; correct held model, animated flame and local light appear when ready. |
| V off/on, then F lowering | Visible equipment/flame/light follow actual state; lowering extinguishes without leaving a stale light. |
| Debug on/off, normal/noclip, map and F10 return | Legitimate gameplay input remains usable; HUD visibility cannot silently disable hands. Capture intended modal/story refusal explicitly. |
| Default and personal bindings; Shift+V | F/V command semantics remain bindable; intentional user overrides and draw-distance shortcut are preserved. |
| Model and sprite hands; normal camera | Both supported presentations show valid poses. Viewmodel hiding/chase/FOV exceptions are explicit and tested separately. |
| Ordinary doors/regions; permitted save/load | Preserve intended raised/lowered and equipped goals; death/new-game/reset behavior remains deliberate. |
| Player torch against a cave wall/floor | Same-camera off/on changes actual lit surface pixels with bounded falloff and no crash. |
| Imperial and Hlaalu guards at night | Confirm automatic schedule/override, held item/flame and nearby surface illumination independently, including cold entry. |
| Representative indoor lanterns/torches | Source-derived position/light policy produces visible local contrast; report coverage gaps and measured frame/memory cost. |

Run relevant source/VM/renderer fixtures and actual native replay. Include
negative/collision-only brush roots, transformed instances and light expiry from
the historical crash coverage. Do not clear the new report because an older
isolated fixture passes; the exact owner state and final display still matter.

### Scoped v0.0.29-dev1 native F/V replay

A native replay observed F visibly raising the hands and V equipping the held
torch in Seyda Neen. After a checked catalogue transition to one world-region
destination, F lowered and raised the hands and V equipped the held torch again.
Diagnostics showed hands state 2, hand goal 1 and torch goal 1 on both equipped
views.

A subsequent Hlaalu Council interior replay shows F raising hands and V
equipping the torch; toggling V off darkens the surrounding view again. In
lossless engine-generated off/on/off frames, 24,728 viewport pixels stable
between the off captures change with the torch, including 16,624 above the
lower hand/torch band. Visible wall/floor changes and this broad response extend
beyond the held sprite. Without a separate interior depth mask, the count is
not an exact world-surface count.

At a second Balmora Hlaalu guard view, forced torch-on produces a visible
pavement pool. Two selected pavement strips beside the guard, excluding the
central actor/flame strip, contain 1,680 pixels: 841 brighten with the torch.
The off-state restore is exact within those strips, and automatic night lighting
matches forced-on there exactly. These are screen regions selected from the
visible pavement, not a general depth classification. Other pixels differ,
so no full-frame identity is claimed. Both checks use the default night palette path.

The earlier attempted Balmora guard view remains unresolved: its off/on frames
are byte-identical and the guard is not recognizable. Registry/proxy admission
does not prove allocation of the actual surface light. Diagnose that view
separately; the successful second pose cannot close it.

A later controlled save/door replay uses the same Hlaalu Council interior.
Quicksave records a test character at 25 health with the torch equipped. After
setting health to 5, quickload restores the prior 25-health bar; the captured
frame matches the earlier 25-health frame byte-for-byte. Hands initially return
lowered, consistent with the documented save hand reset; F then V visibly
re-equips the torch and restores the sampled interior light. This demonstrates
re-equipping after load, not preservation of equipped appearance across load.

Ordinary E-door use then crosses Council to Balmora and returns through the
Council door with the torch still visibly equipped. F lowers/redraws the hands
and V equips the torch afterward; diagnostics finish at hand state 2, hand goal
1 and torch goal 1. This is one roundtrip and one save/load sequence, not all
maps, saves, story states or personal bindings. Controlled health settings do
not test gameplay damage, healing or god mode.

Together these results establish bounded equipment, re-equipping, door-travel
and local-light samples. Exact owner-state replay, other actors/maps/save states,
authored static lanterns and target performance remain open. No fixed release
is claimed.

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

The dedicated [Study lanterns and torch lighting more](LANTERNS_AND_TORCH_LIGHTING.md)
covers wall-mounted torches, lantern fixtures and carried lights; authored
placements/attachments; indoor static/dynamic lighting; the guard day/night
cycle; and measured local illumination rather than flame sprites alone.

## Hand-state timing investigation

**Historical initial lead (superseded by the completed census and source tests):** the inspected released
`vf1340` worldspawn lacks the hand draw/idle/lower/punch timing fields. The
QuakeC path can remain in drawing state 1 when duration is nonpositive and
clear the weapon model. V accepts that state and reports its goal toggle, while
the equipped-light path requires raised state 2. This mechanism matches the
reported no-hands/no-light symptoms, but the affected conversion/map census and
actual owner-state/native reproduction remain pending. Do not close the report
or claim a repaired image from this inspection alone.

## Confirmed converted-world hand metadata defect, 4 October 2026

The released-map audit found missing hand draw/idle/lower/punch timing and eye
height metadata in **all 2,532 checked world-region BSPs**. All **190 checked
town/interior maps** contain the required metadata; the character gallery also
lacks it. This establishes a conversion coverage defect, not a personal-binding
diagnosis. No runtime restoration supplies the absent values.

The failure chain explains the reported behavior: missing/nonpositive draw
duration can leave QuakeC in drawing state 1 with the weapon model cleared.
V still accepts that state and prints its selected on/off goal, but actual
torch equipment requires raised state 2. Consequently the console can report
on while no hands, held model or equipped light appear. The exact owner-session
replay still needs acceptance, distinct from this source/payload diagnosis.

The v0.0.29-dev1 source candidate now stamps validated authored hand-conversion
metadata into staged worldspawn before optimization/fingerprinting and verifies
hand-model topology/frame provenance. Non-entity lumps and unrelated entity
bytes remain unchanged. Invalid metadata causes explicit safe QuakeC refusal
and clear state rather than invented fallback timing or repeated console spam.

Seven metadata tests pass on Windows and Linux. The actual compiled QuakeC plus
runtime torch fixture reproduces the missing-timing failure and passes corrected
draw/idle/model/light, lower, punch and death transitions under sanitizers. The
Amiga target compiles.

The corrected hand fields have now been stamped into all **2,532 staged
world-region BSPs**, with complete staged-image file readback and independent
metadata preservation checks passing. Sampled native F/V checks pass in Seyda
Neen and after a town-to-world transition into `vf1463`: hands lower/redraw,
the held torch appears, and equipped-state diagnostics agree. A subsequent
Hlaalu Council interior replay also shows F raising hands and V toggling the
held torch, with a broad response in the scoped native lighting checks. These samples
now include a normal Hlaalu Council/Balmora door roundtrip with the torch
preserved, plus successful F/V re-equipping after a quickload that initially
lowered the hands. They do not establish the full owner-state matrix, every map,
all save/load states or general lighting acceptance. **Fixed: N; first verified
fixed release: none.**

## LIGHT-GRADIENT-29: unsigned surface-light interpolation overflow

During the v0.0.29 guard-light investigation, a synthetic fixture using the
actual guard allocator, surface marking, rotated-brush transform, surface cache
and palette lookup triggered signed overflow in `R_DrawSurfaceBlock8_mip0`.
The surface light samples are unsigned. Subtracting them before the shift made
negative slopes wrap into huge positive steps and overflow during interpolation.
This is an inherited renderer arithmetic defect; its introducing revision is
not established. It is not yet proven to explain the owner's entire guard-light
report.

The v0.0.29-dev1 candidate converts the bounded samples before subtraction and
uses explicit floor rounding for negative steps in all four active 8-bit mip
paths. The unchanged 16-bit path already loads signed endpoints before doing
its differences. No light count, radius or global brightness was increased.

Before repair, the final-pixel fixture failed under undefined-behavior checking.
After repair, all four mip levels brighten world and translated/rotated brush
pixels at representative ambient/static levels (0/12, 128/12 and 128/50);
extinguishing restores every original pixel. Missing-lightdata, fullbright and
saturation controls correctly show no change. Existing player-torch and brush
fixtures also pass, and the Amiga target compiles. The fixture is
[`aga_guard_light_surface_test.c`](../tests/aga_guard_light_surface_test.c).

This establishes the arithmetic repair and a working synthetic surface-light
path. The bounded native interior and guard checks documented above add visible
view/pavement responses, but do not isolate this arithmetic change as the cause
of those results or establish general appearance/frame cost. **Source repair
tested; Fixed: N pending complete matching native acceptance. First verified
fixed release: none.** TORCH-LIGHT-29 and INTERIOR-LIGHT-29 remain open for
scene-specific diagnosis.

## TRANSITION-EQUIPMENT-29: carried torch blinks out during cell handoff (OPEN)

Owner reports 5 October 2026 in Seyda Neen automatic cell/sub-cell travel: hands
remain visible, but an equipped torch disappears briefly on arrival. Reproduce
with F-raised hands plus V torch, cross a boundary without toggling either, and
inspect the first visible arrival frames. Compare unarmed, fists, fists+torch,
raising/lowering and attack phases. Future weapons plus torch must use the same
complete state-transfer contract, not a fists-only presence check.

Source diagnosis: the current load path carries aw_hand_goal and aw_torch but
not aw_hand_state, animation timer age, attack latch or ready weapon presentation.
The newly spawned player begins in state0; game rules restart drawing. Torch
rendering/lighting requires ready state2, so the saved torch bit alone cannot
prevent the blink. Transfer field-by-field values and timer age across the new
server clock, rebind new-world model names instead of carrying VM pointers, and
restore before the first visible client state. Native acceptance remains pending.
**Fixed: N.** The separate owner observation that player torch lights surfaces
does not establish transfer continuity.

## TORCH-HAND-SEPARATION-29: grip appears to break during idle animation (OPEN)

Owner supplied two frames on 5 October 2026 showing the torch-side hand/grip
changing/separating while standing. He associates it with breathing/idle motion;
this is a reproduction hypothesis, not a confirmed geometry or skinning cause.
Visible HUD: global -14208,-66080,170; local -736,1399,42; heading282/pitch0;
game times22:24 and22:25. Exact animation phase and active streamed chunk still
need capture. Compare the owned torch model's successive frames, grip/hand
topology, interpolation, clipping and shared pose transforms at a fixed camera.
Keep distinct from the map-handoff blink until evidence links them. **Fixed: N.**

### 5 October torch-light acceptance follow-up

Owner confirms the held/player torch now visibly illuminates surroundings.
He separately reports the guard torches still appear to illuminate little or
nothing. A nighttime guard screenshot records global -11281,-70292,315;
local -4,346,78; heading330/pitch13; game time21:12. Reproduce there, distinguish
visible flame proxies from admitted point lights, and measure actual surface
pixels. The guard-light path is capped at two admitted lights; visible flames
alone do not prove a corresponding light was selected. Root cause of this
specific screenshot remains unverified; retain the guard-light bug as open.

The source candidate now implements saved aw_torch_radius (default 192,
clamped to 32–288) for the player torch and admitted guard torches, plus
dbg torch radius X. The prior radius was 144. Flame style uses saved
aw_torch_flame_style: 1 is classic (default), 2 is brightbase (near-white base,
warm above), selectable with dbg torch flame classic/brightbase. These controls
are in the newer source candidate only; the current post-reboot dev1-based
target has not been updated or natively accepted. Verify player and guard
surface response independently, including the ground directly beneath the
player. Measure bounded falloff, frame/memory cost and save/config behavior.
Keep the surface radius separate from flame appearance and urgent equipment
handoff.

### Later 5 October owner refinement

The newer source candidate implements universal player and admitted-guard
radius control: saved aw_torch_radius default 192, bounds 32–288, and console
command dbg torch radius X. The prior default was 144. It also implements
saved aw_torch_flame_style (1 classic default, 2 brightbase) and
dbg torch flame classic/brightbase. The Amiga build passed. The initial integration run passed 78/79 checks;
the remaining old-radius assertion was corrected and its real-QC fixture
passed separately. A fresh combined validation follows the map/stride changes.
These controls are not deployed to current development playtest or natively accepted. Preserve
separate player/guard surface checks; radius does not replace
TRANSITION-EQUIPMENT-29 priority.

For TORCH-HAND-SEPARATION-29, study first-person part visibility and geometry
against OpenMW and OG behavior as requested. This is an investigation request,
not an established root cause or parity requirement.

### Near-field and movement acceptance update, 5 October

The owner identifies dim ground directly beneath the player as the main torch
illumination problem. Compare torch OFF/ON at the same nighttime position while
looking down from a normal holding pose, inspecting ground immediately beneath
the player. Test held-player and guard torches independently; a successful
farther-wall response or guard pavement sample does not close the other case.

The owner reports the hand/torso glitch most strongly during SHIFT+RUN, with
left-side geometry appearing and disappearing. Treat this as stronger
reproduction evidence for TORCH-HAND-SEPARATION-29, not a confirmed part-
visibility/mesh cause. Study OpenMW and OG first-person part visibility as
requested. The later traversal screenshot strengthens the SHIFT+RUN reproduction case.


## Source-candidate torch controls, 5 October

The controls described above are source-only pending delivery to current development playtest.
Amiga compilation passed; integration/native acceptance is not established
by compilation. Do not raise or lower the default without owner direction.


The principal player-light acceptance gap remains ground directly beneath the
player at night. Compare OFF/ON at the same position while looking down from a
normal torch pose. Test player and guard lights separately.


### Running torch arm: tested source mitigation, target acceptance pending

The current first-person model contains arm parts and the torch, with no torso.
Inspection and projection comparisons identify forward stride bob exposing
near-clipped arm geometry as a reproducible running contribution. The source
adds saved `aw_torch_depth_bob 0`: torch-equipped depth remains stable while
camera and lateral/vertical motion continue; `1` restores the legacy behavior.
A fixture using the actual camera and alias-transform routines passes 324
stride/speed/pitch/yaw combinations with sanitizers; restoring the old depth
behavior causes the relevant assertion to fail. This is a tested source
mitigation, not native acceptance or a claim that all grip fragmentation is
resolved. Standing/idle fragmentation remains OPEN.


### Combined source validation, 5 October 2026

A fresh combined offline Docker run passed all 80 native-source test methods
and the Amiga 68040 build. It includes the UI V2/scene shortcut, full equipment
handoff, radius/flame controls, running-torch depth correction, and map marker/
debug selection changes. Native acceptance and delivery of these changes remain
pending. The smaller idle-grip defect and scene-specific light/geometry reports
remain open.

### 5 October: texture-density-dependent surface light, next development candidate

A bounded test of the actual surface-light accumulator found a units mismatch:
radius and height above the surface were world distances, while lateral falloff
used raw texture coordinates. Imported scenery uses arbitrary source UV scales
and skew. With radius 192 and a light 25 units above a floor, the same sample
16 world units away received a contribution of 38,656 at unit UV scale and zero
at UV scale 16. At scale 0.125 it received 42,240 instead. These are synthetic
lightmap accumulator values, not measured screen brightness.

The next development source converts UV deltas into an orthonormal basis on the
surface before the existing approximate distance calculation. Basis setup runs
once per lit surface, with no square root per lightmap sample. Singular mappings
retain the legacy fallback. Radius, flicker, light counts and guard admission
policy remain unchanged. This corrects a reproduced material-density defect;
it does not establish the cause of the owner's specific dim-underfoot or guard
view. Sparse lightmap samples, palette saturation and guard rejection remain
separate possible limits.

`dbg guardtorch` now reports active light slots as well as visible proxies,
last-frame selected lights, range/contents/trace rejections and untested/budget
candidates. Rejection counts describe distinct guards; a visible flame still
does not imply that a point light was admitted. An eviction can clear active
slots after selection, so both current and last-frame counts are shown.

Six focused Linux Docker methods passed with sanitizers on 5 October 2026:
85 same-point UV comparisons, near-foot/range/singular controls, guard diagnostic
controls, existing player/guard admission and flame cases, brush-root handling,
and final world/rotated-brush surface pixels at all four mip levels. The new
distance regression fails the unchanged renderer. See
[`aga_torch_light_distance_test.c`](../tests/aga_torch_light_distance_test.c)
and [`aga_guard_light_diagnostic_test.c`](../tests/aga_guard_light_diagnostic_test.c).
No native Amiga appearance or frame-cost acceptance is claimed. The sealed dev2
artifacts are unchanged; the guard-light and direct-underfoot reports remain OPEN.


The same candidate also passes finite tiny-scale, near-singular and extreme-UV
offset controls under float-cast-overflow sanitization. Out-of-range or
non-finite distances are rejected before integer conversion. Target 68040
compilation of both changed C files passed in Linux Docker. Compilation reported
four maybe-uninitialized warnings in the existing 16-bit surface-block routine
and two misleading-indentation warnings in existing guard statements; this
check does not certify those paths or establish native visual acceptance.


## Subsequent development candidate: proximal arm visibility

The smaller idle fragments remain part of OPEN TORCH-HAND-SEPARATION-29.
An owned-source comparison isolates thin disconnected pieces near the left
grip to the proximal upper-arm fallback, including before mesh reduction.
They cross the five-unit near plane after the shared four-unit view offset.
This is separate from an entire hand presentation blinking during crossings.

The torch converter now defaults to `--upper-arms hidden`, selecting hands,
wrists and forearms while omitting both proximal upper arms from this equipped
first-person model. `--upper-arms legacy` retains the former selection; Python
callers can pass `upper_arms='legacy'` to `prepare`. Ordinary unarmed hands,
world actors, animation timelines, torch attachment and the runtime
`aw_torch_depth_bob` setting are unchanged. Reconvert the torch files together
for a future image; changing this source does not alter an existing playtest.

Synthetic part-preservation checks and a private owned-data conversion pass
in offline Docker. With the inspected base data, hidden produces 531 triangles
and 1,593 vertices; legacy reproduces the previous 551-triangle model byte for
byte. Both profiles retain all 238 torch triangles and identical emitted flame/
light metadata. Independent projections of all eight poses remove the isolated
proximal pieces. These projections are not the Amiga rasterizer: standing,
walking, running, looking up/down, draw/lower and cell-crossing target acceptance
remain pending. This candidate is not part of the sealed dev2 playtest.

## Dev4 follow-up: accepted dev3 light and optional sparks

The player torch's dev3 surface lighting has owner acceptance. The next request
is more visible upward and sideways reach, independently of small white-hot and
yellow flame sparks. The dev4 source adds an optional `sparks` flame style while
retaining classic as default. See [Torch particles and light reach](TORCH_PARTICLES.md)
for pinned AmiQuake source findings, commands and exact validation limits.
Earlier source-only statements above describe their original checkpoints;
they do not retract the later dev3 owner acceptance.
