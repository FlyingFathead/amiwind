# NIGHT-RUST-31: night tint rounds dark colours to rust-red speckle

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in an unknown version |
| Where | Night remap tables (engine R_SkyNearest), dark walls and ground |
| Reproduction | always |
| Duplicate of | no |
| Persists in | unknown |
| Severity | medium: Rust-red speckle on dark surfaces at night. |
| Family | Lighting, lamps and night (`lighting-night`) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Repair in source (engine `R_SkyNearest`), checked by a native test; not
yet packaged or seen in game.

## Symptom

At night, dark walls and ground show scattered dark rust-red speckles on
near-black, a hue the textures do not have ("this very peculiar hue", owner,
Balmora).

## Where

`engine/aga/src/r_sky.c`, `R_SkyNearest` and the day/night fog tables it fills;
applied to the finished frame by `aw_fog.c`.

## How it happened

The night remap scales each palette colour and then finds the nearest palette
entry through a 16 x 16 x 16 grid: each channel is rounded to steps of 17.
Near black, one channel can round up while the others round down. Palette 211
(23, 17, 13), a common dark wall and ground colour, becomes (9, 8, 8) at deep
night; red rounds up to 17, green and blue round down to 0, and the grid cell
(17, 0, 0) maps to palette 215 (23, 7, 3), dark rust. Measured on one Balmora
wall texture at night: 132 of 1,024 texels rust; on one terrain texture 292 of
1,024 (28.5 %). An exact nearest-colour search sends 211 to a dark grey.

## Why it was not caught

The grid lookup was chosen for speed; its error is invisible in bright colours
and only shows near black, and night frames were not checked texel by texel.

## Reproduction

Any exterior at deep night (`dbg set time 2300`), dark walls and ground.

## Repair

`R_SkyNearest` keeps the fast grid lookup, but a dark colour (all channels
below 64) whose grid answer is clearly more saturated than the colour itself
(spread more than 12 above the source's) is searched exactly over the palette.
On the shipped palette that is 6 of 256 colours at deep night, once per table
build, never per pixel; palette 211 and 214 then map to a near-black grey
(9, 9, 6) instead of rust (23, 7, 3). A full exact search of every table level
was rejected: about a million comparisons per table build on the 68040.

## Verification

Native test `--night-rust` (day/night test): a palette holding the measured
trap, rust nearest the grid point and a grey nearest the colour; the grey must
win and bright colours keep the grid answer. In-game check pending.

## Prevention

A check that the night tables never map a near-neutral colour to a colour of
noticeably different hue.

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
- [NPC-LIGHT-COHERENCE-32](NPC-LIGHT-COHERENCE-32.md): Characters are lit by the floor below them, not by the light where they stand
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
