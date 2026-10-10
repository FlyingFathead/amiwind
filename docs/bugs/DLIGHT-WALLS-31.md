# DLIGHT-WALLS-31: torches barely light town walls at night

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev3 |
| Where | Balmora at night, outdoor night remap (aw_fog.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.31-dev4 |
| Severity | medium: Torch light on town walls was halved by the night remap; visible but limited. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | v0.0.31-dev3 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Cause found and measured; repaired in source for v0.0.31-dev4 (light-space
night made the default), awaiting the owner's in-game check.

## Symptom

At night in Balmora the player's torch and the guards' torches seemed to light
the ground but not the buildings (owner). The same carried light lights walls
inside the prison ship.

## Where

`engine/aga/src/aw_fog.c` (`AW_FogDraw`, the whole-frame night remap through
`sky_fog`) and its tables in `engine/aga/src/r_sky.c`.

## How it happened

Not a light-marking problem: a native run of the real engine code on the
shipped Balmora map's faces shows placed walls get the full dynamic light
(264 of 266 faces at 32 to 64 units reach full light). Outdoors, after all
lighting, the night remap rewrote every geometry pixel through a table that
scales the palette by the night ambient (about 0.43, 0.52, 0.66 at deep night),
so it also halved the torch's own light; interiors skip that step. Walls
across a street are 100 to 200 units away against the torch's 192-unit reach,
so their remaining light was faint and easy to miss.

Measured in game (v0.0.31-dev3, Balmora, 22:21, one switch at a time): the
headlamp lifts the facade from 13.5 to 24.8 mean luma with the remap, and from
13.7 to 41.7 with light-space night (`aw_night_light 1`), the night being
equally dark without the headlamp.

## Why it was not caught

The native light tests run without the night remap; town walls at night were
not compared with and without a torch in game.

## Reproduction

Balmora at night, `dbg headlamp on` and off next to a facade, with
`dbg night light 0` and `1`.

## Repair

`aw_night_light` defaults to 1: the night's brightness goes into the light
(ambient and baked light), dynamic lights are added after it unscaled, and the
end-of-frame table keeps only the hue. The cvar is saved, so a configuration
that stored 0 keeps 0 until changed.

## Verification

In-game A/B above; owner check of dev4 pending.

## Prevention

A town headlamp pair at night in the regular capture set.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [LAMPS-FLICKER-31](LAMPS-FLICKER-31.md): Night lamps switch on and off while turning or walking
- [LAMPS-RANGE-31](LAMPS-RANGE-31.md): Only the nearest lamps light up at night
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

<!-- END GENERATED CATEGORY -->
