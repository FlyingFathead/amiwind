# GUARD-TORCH-BRIGHT-31: Hlaalu guard torches over-bright at night

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev4 |
| Where | Balmora night, Hlaalu guard torches |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev4 (last seen) |
| Severity | medium: Guard torches lit whole squares brighter than the lamps after the night look changed. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | v0.0.31-dev4 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev4; repaired in source for dev5, not yet
owner-checked.

## Symptom

In Balmora at night a Hlaalu guard's torch lights the street more than the
lamps and lanterns do ("super over the top bright").

## Where

`engine/aga/src/aw_guard_torch.c` (guard torch lights) and
`engine/aga/src/aw_torch.h` (`AW_TorchLightGain`).

## How it happened

Guard torches use the player's full torch light: the torch radius and the torch
surface gain. dev4 made the light-space night the default
([DLIGHT-WALLS-31](DLIGHT-WALLS-31.md)), which stops darkening dynamic light, so
the guard torches' full reach became visible across whole squares.

## Why it was not caught

The guard torch light was accepted under the old whole-frame night look and was
not walked again at night after the night look changed.

## Reproduction

v0.0.31-dev4, Balmora at night (21:38, Hlaalu guard on the square near global
-23973 -12638): the guard's torch pool covers most of the square.

## Repair

dev5: guard torches keep the player torch's brightness at the flame and light
half as far (`aw_guard_torch_radius` 0.5; `dbg guardtorch 0.1..2.0` sets it,
`on/off/auto` as before). The surface gain is 512 x strength / radius, so the
peak at the flame stays the same and only the reach shrinks.

## Verification

Native tests (guard torch fixture) and gate 075; same-pose captures dev4 versus
dev5 (guard radius 1.0 and 0.5), headlamp off. Owner check pending.

## Prevention

Night walks through each town with guards after any change to the night look.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
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
