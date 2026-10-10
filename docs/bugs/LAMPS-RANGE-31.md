# LAMPS-RANGE-31: only the nearest lamps light up at night

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev4 |
| Where | Balmora night lamps (engine lamp module) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev4 (last seen) |
| Severity | medium: Only the nearest lamps get a light at night; distant lamps stay dark until approached. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | v0.0.31-dev4 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open (limit of the v0.0.31-dev4 night lamps). Owner report; cause known.

## Symptom

Walking through Balmora at night, distant lamps, including those in the next
sub-cell, stay dark and light up only as the player comes close ("can't see
shit", then "oh, there's light after all").

## Where

`engine/aga/src/aw_lamps.c`: night lamps are dynamic lights for the nearest
`aw_lamp_lights` (default 2) lamps within 512 local units of the player.

## How it happened

Dynamic lights cost time every frame, so only a few nearby lamps can be lit at
once; all other lamps have no light at all, because the exterior maps carry no
baked lamp light ([BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md)).

## Why it was not caught

The night lamps were first built as a stopgap and not walked across a whole
town at night before packaging.

## Reproduction

v0.0.31-dev4, Balmora at night: look along a street toward lamps more than a
few houses away.

## Repair

Not done. The lamp data is not lost between sub-cells: every lamp in the 3 x 3
cells around the player is read and known to be lit. Only the nearest lamps get
one of the few dynamic lights, so a step can hand a slot from the lamp ahead to
one behind ("like walking into motion detector lights", owner).

dev5 mitigation: lamps ahead of the view win the slots (a lamp behind counts
three times as far), a newly chosen lamp grows to full radius over 0.4 s instead
of popping on, the lamp radius is the torch radius (owner choice from 1.0/1.5/2.0 captures) (`dbg outdoorlantern`), and
lantern glass and windows glow at night at any distance (no per-frame cost).

Full repair (Quake's switchable lights): every lamp baked into the map
lightmaps on a night lightstyle (32 or above), switched on at dusk: all lamps
in view lit at any distance, no per-frame cost, one surface-cache rebuild at
dusk and dawn. Cost is lightmap memory, measured on the bm019 prototype at
about 0.96 MB of heap headroom; each map is to be checked by a lights gate.

## Verification

Pending.

## Prevention

Night walks across each town in the capture set.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [LAMPS-FLICKER-31](LAMPS-FLICKER-31.md): Night lamps switch on and off while turning or walking
- [LIGHT-ENTITIES-UNWIRED-33](LIGHT-ENTITIES-UNWIRED-33.md): Morrowind lights are never turned into Quake light entities, so the light compiler bakes nothing
- LIGHT-EXTERIOR-JUMP-29 (no report page): Brightness discontinuity at the reported Seyda Neen shack
- [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md): Interior lights stop dead at their radius
- LIGHT-GRADIENT-29 (no report page): Unsigned light gradients overflow during surface interpolation
- [LIGHT-NEGATIVE-31](LIGHT-NEGATIVE-31.md): Negative (darkening) lights bake as bright white light
- [LIGHT-OFF-31](LIGHT-OFF-31.md): Lights flagged Off by default would bake as lit
- [LIGHT-STYLES-UNDEFINED-33](LIGHT-STYLES-UNDEFINED-33.md): The flicker and pulse lightstyles of the light design are never defined, and styles below 32 dim with daylight
- LIGHT-UV-DISTANCE-29 (no report page): Texture scale changes dynamic-light reach on surfaces
- [NIGHT-0400-DARK-31](NIGHT-0400-DARK-31.md): Exterior suddenly much darker around 04:00
- [NIGHT-RUST-31](NIGHT-RUST-31.md): Night tint rounds dark colours to rust-red speckle
- [NPC-LIGHT-COHERENCE-32](NPC-LIGHT-COHERENCE-32.md): Characters are lit by the floor below them, not by the light where they stand
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

Related bugs in other categories:

- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables

<!-- END GENERATED CATEGORY -->
