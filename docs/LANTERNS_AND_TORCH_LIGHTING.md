# Study lanterns and torch lighting more

## Why this study is part of v0.0.29

The 4 October 2026 post-release playtest reports three distinct failures or
gaps: F/V can fail to produce a visible player torch, carried guard torches do
not convincingly illuminate nearby night surfaces, and interiors look bleak.
A visible flame and a working local light are different results. Fixing input
does not prove surface illumination, and making a flame brighter does not light
a wall. Keep [TORCH-INPUT-29](journals/BUG_JOURNAL-v0.0.29.md#torch-input-29-f-cannot-raise-hands-and-v-only-reports-torch-state-open),
[TORCH-LIGHT-29](journals/BUG_JOURNAL-v0.0.29.md#torch-light-29-guard-torches-do-not-illuminate-nearby-night-surfaces-open)
and [INTERIOR-LIGHT-29](journals/BUG_JOURNAL-v0.0.29.md#interior-light-29-interiors-lack-convincing-local-light-open)
separate until each has its own evidence.

This document is a study and acceptance plan. The existing converted torch and
bounded dynamic-light paths are described in [TORCH.md](TORCH.md). It does not
claim new lantern conversion, interior lighting, coloured lights or shadows.

## Read the source placements before choosing a renderer

Build a reproducible census from the user's own original installation. Start
with placed CELL references and resolve their base records, including `LIGH`,
their model, radius, colour, flags and scripts where present. Preserve original
reference identity, interior/exterior cell, position, rotation, scale and load
order. A fixture-shaped static or activator model is not automatically a light;
record its associated light reference or controller only when the source proves
one. Identify missing/unresolved links instead of inventing emitters.

Inspect wall-mounted torches, hanging and standing lanterns, other authored
indoor light fixtures, the player torch and guard equipment separately. For
each representative source object, distinguish these components:

| Component | Question the source audit must answer |
| --- | --- |
| Visible housing or torch mesh | Which authored model and transform place it? Does a wall mount or fixture already exist in the room conversion? |
| Flame, glow or emissive material | Which texture/controller animates it? Does it draw bright pixels without affecting other surfaces? |
| Scene light | Which record/controller supplies radius, colour, intensity and flags? Which source placement or node determines its world origin? |
| Carried attachment | Which hand/bone, equipment transform and animated anchor place the item and its light? |
| Enable/state policy | Is it always on, scripted, carryable, extinguished or condition-dependent? Does time of day actually control it? |

The existing torch conversion records `Fire Emitter`, `Smoke Emitter` and
`AttachLight`, as documented in TORCH.md. Do not assume every lantern uses the
same node names, first-person camera offset or third-person attachment.
Keep light position separate from the brightest texture pixel. Compare source
scale to converted native units before choosing radius or falloff.

Original models, textures, animations, game records and generated inspection
media remain outside public source. Publish converter logic, schemas, synthetic
fixtures and technical conclusions; do not embed proprietary source extracts.

## OpenMW and original-game behavior to examine

Use a pinned OpenMW revision and record the exact functions studied. Start at
[ActorAnimation](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwrender/actoranimation.cpp)
for equipment attachment and trace the related scene-light creation/update
path. Follow placed-light object handling separately from carried equipment.
Inspect visibility, attachment updates, light flags/radius/falloff, scripts and
interior ambient/fog interaction. A scene graph light is not a direct drop-in
implementation for an indexed software renderer.

Confirm original-game behavior with controlled owned-data scenes: fixed camera,
identical time, the same nearby wall/floor, and one light enabled/disabled.
Record wall-mounted placement, shadows or their absence, flicker, colour and
script transitions separately. Do not infer original behavior from a modded
screenshot or assume all indoor fixtures follow night. The automatic guard
cycle remains tied to the saved world clock; a sky gallery preview does not
change NPC equipment time.

## Quake and AmiQuake pipeline to examine

Trace the existing engine's complete light path: keyed light allocation and
expiry, `R_PushDlights` surface marking, world and transformed brush-model
contributions, `R_BuildLightMap` and the final palette lookup. Check what alias
models receive separately. These stages need diagnosis, not an assumption that
the current defect is missing light creation.

For a failing fixture, record whether a light is admitted, where it is placed,
its radius/lifetime, affected surfaces, cache invalidation and final pixel
contrast. Check contents/trace rejection, source versus local transforms,
fullbright paths, ambient/static-light saturation and night palette treatment.
Retain the historical negative/collision-only brush-root crash coverage.
Do not alter global ambient brightness merely to hide an unproven local-light
failure, or describe a monochrome intensity path as coloured surface lighting.

## Bounded prototype options

Evaluate stationary authored lights and carried lights as separate budgets.
Static baked contributions may suit fixed interior fixtures if the conversion
and runtime lightmap contract supports them; dynamic lights may suit moving
hands and guards. Neither choice is accepted before a working bounded prototype.
An animated flame can remain a small sprite while its illumination has a slower
measured update cadence. Do not add a light to every emissive texture by guess.

For dynamic lighting, use a capped nearby-light selection with deterministic
priority and stable transitions. Measure rather than promise the benefit of
visibility rejection, distance limits or lower update cadence. Avoid per-frame
allocation, repeated whole-cell scans and unbounded light/surface combinations.
Preserve reference memory headroom and measure dense indoor rooms and both
guard factions at night. A disabled/low-cost fallback must retain readable rooms
without pretending that the local-light fidelity target is met.

## Required evidence before calling it fixed

1. Bind input/conversion/build identity, source-reference scope and exact camera.
   Test the player F/V chain independently using the matrix in TORCH.md.
2. Show same-camera light-off/on stills for a wall-mounted torch, a lantern,
   player torch and Imperial/Hlaalu guard torch. Inspect walls, floor, nearby
   scenery and moving actors separately; state unsupported contributions.
3. Demonstrate radius/falloff, movement/rotation, expiry and transitions, including
   indoor door entry/exit and guard day/night boundaries. Check stale lights,
   light leaks and hidden emitter policies explicitly.
4. Run real renderer/VM fixtures, conversion validation and matching target
   gameplay. Parsing a command, registering a light or showing flame sprites is
   insufficient closure evidence.
5. Record frame-time distribution/worst frame, light/surface counts, memory and
   loading cost in representative and dense scenes. Compare identical settings
   against the baseline and retain the existing reserve requirement.

Keep open questions, attempted approaches, failures and measured results in the
bug journal. The [v0.0.29 immediate plan](PLAN-v0.0.29.md) tracks this study and
the specific control, guard-light and interior-light fixes without merging them.

## First end-to-end surface fixture result, v0.0.29-dev1

The real guard-to-world/rotated-brush surface-cache fixture found and reproduced
an unsigned-gradient interpolation overflow. The narrow renderer repair passes
sanitizers and verifies brighter final pixels plus complete light-off restoration
at representative ambient/static levels across all four mip resolutions. See
[LIGHT-GRADIENT-29](journals/BUG_JOURNAL-v0.0.29.md#light-gradient-29-unsigned-surface-light-interpolation-overflow).

This rejects a universal failure to create or rasterize guard lights under those
conditions. It does not close the observed in-game report. Next, bind the exact
guard/location, compare light eligibility and emitter-to-camera visibility,
surface type/radius and the final night palette at a controlled native camera.
Keep missing lightdata, fullbright and saturation as explicit negative controls.

## Source study: light attachments and lava are separate contracts

OpenMW 0.51.0 separates a light record from its visible model: the light class
honors its off-by-default state and carry flag; NPC animation attaches the held
model and adds the scene light separately. This is a data/behavior reference,
not an implementation to transplant into the indexed software renderer. See
[`light.cpp`](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwclass/light.cpp),
[`npcanimation.cpp`](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwrender/npcanimation.cpp)
and [`actoranimation.cpp`](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwrender/actoranimation.cpp).

The Quake/AmiQuake software path marks affected surfaces, adds local intensity
to static samples and shades through a colormap. Fullbright or missing world
lightdata bypasses this path. Actual world/rotated-brush final-pixel checks are
therefore required; visible flame art alone is insufficient. Reference:
[`r_surf.c`](https://github.com/id-Software/Quake/blob/master/WinQuake/r_surf.c).

The current fork retains `CONTENTS_LAVA`, lava view tint and turbulent textures,
but turbulent surfaces bypass ordinary lightmaps. Emissive-looking lava does
not automatically light neighbouring walls. Original Quake's `WaterMove` applies
periodic lava damage; the fork's `PF_WaterMove` is under `QUAKE2`, which the
production build does not enable, and current AmiWind QuakeC has no lava damage
loop. These retained constants/renderers do not establish working lava gameplay.
Reference: [`client.qc`](https://github.com/id-Software/Quake/blob/master/QW/progs/client.qc).

Before adding lava, survey owned activator placements, scripts, transforms,
materials, animation and collision. OpenMW's generic activator does not make
every activator a lava volume. Derive any Vvardenfell debug-map lava overlay from
verified placements, with separate contact/damage and bounded illumination
tests; never infer lava from red terrain or guessed map dots. Reference:
[`activator.cpp`](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwclass/activator.cpp).

## NPC illumination remains a separate acceptance gate

The dev4 playtest reports torch-lit walls/floors but dark nearby NPCs.
Track [TORCH-NPC-LIGHT-29](journals/BUG_JOURNAL-v0.0.29.md#torch-npc-light-29-nearby-npcs-do-not-respond-to-torchlight-open)
independently of surface coverage, emitter visibility and light radius. An
emitter or illuminated floor does not establish actor lighting. Verify the
actor's rendering branch, base light, dynamic-light clamp and final night
palette with a fixed-time off/on/off comparison before marking it resolved.

## Self-lit materials (emissive), 7 October 2026

Morrowind marks glowing parts of a mesh (lantern glass, lava, Dwemer lights,
Bitter Coast mushrooms) with an emissive colour in the NIF material. The scene
converter used to read only the diffuse colour, so those parts got the same
lightmap as the wood or stone around them.

- **Converter:** each material records a glow level from 0 to 9, taken from
  its brightest emissive channel. Textures of glowing materials are named
  `emitN_...` instead of `surfaceN`. `AMIWIND_NO_EMISSIVE=1` converts without
  the marking and reproduces the previous maps byte for byte.
- **Engine:** when a lightmap is built, a surface whose texture is `emitN...`
  gets at least N/9 of full light. Dynamic light still adds on top.
  `aw_emissive` (saved setting, default 1) and `dbg emissive 0/1` switch it;
  changing it rebuilds the cached surfaces at once.
- **Measured in the Balmora Temple:** rebuilt with the marking, the map
  differs from the previous one only in the texture lump (one texture, the
  Dunmer lantern's glass). In FS-UAE, switching `aw_emissive` changes only
  the lantern panes (about 2,600 to 2,900 pixels, average brightness 93 to
  100), and switching back restores the exact previous image.

The prison ship lanterns and all candles have **no** emissive material: their
glow comes from a particle flame. They need the static-flame work, not this.
Placed emissive meshes in the game: 86 meshes, about 12,500 placements.

## NPC static light from brush floors, 7 October 2026

Actors take their static light from `R_LightPoint`, which traced straight
down through the world BSP only. In converted interiors the world is mostly
the sealing box and the floors are brush objects, so the trace found nothing
and actors got ambient light only: dark, "anti-lit" NPCs.

The lookup now also tests the brush objects below the actor. AmiWind keeps no
render node tree for inline models (only collision nodes), so their surfaces
are tested directly: upward-facing surfaces below the point, the point
projected onto each surface's plane, the highest hit inside the surface's
lightmap extents, then the normal lightmap sample. Results are cached per
position, so actors are re-sampled only after they move. `aw_actor_brush_light`
(saved setting, default 1) switches it; 0 restores the world-only trace.

Measured in the Census office (FS-UAE, same camera): Socucius Ergalla's
figure goes from average brightness 9.5 to 16.4 and now matches the floor
light where he stands; nothing else in the frame changes. A first version
that traced the inline models' node trees crashed the emulator, because those
nodes are not resident; it was replaced before any build left the workspace.
