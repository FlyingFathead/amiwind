# LIGHT-STYLES-UNDEFINED-33: The flicker and pulse lightstyles of the light design are never defined, and styles below 32 dim with daylight

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | worldspawn sets only style 0; R_BuildLightMap dims styles below 32; light_sources.quake_style |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Nothing bakes Morrowind lights yet; once wired, flickering lights would burn steady and every light source would dim at night. |
| Family | Lighting, lamps and night (`lighting-night`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 05ee452, engine 05ee452, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 05ee452, world format unknown |
| Unknown because | found in source while designing; no world built for it |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found in source while designing the CHIM light bake ([CHIM lighting](../chim/LIGHTING.md)). Nothing shows it
yet, because no Morrowind light is baked (LIGHT-ENTITIES-UNWIRED-33).

## Symptom

`tools/light_sources.py` gives animated lights id's lightstyle numbers: 1 for flicker, 6 for slow flicker, 5 for
pulse and 11 for slow pulse. Once those lights are baked:

- they would burn steady, because no lightstyle string is ever set for those styles;
- every steady light source baked in style 0 would dim with the daylight at night, although the original's lights
  never switch off.

## Where

- `engine/aga/qc/world.qc` `worldspawn`: sets only `lightstyle(0, "m")`. An unset style reads as a steady 256 in
  `R_AnimateLight`.
- `engine/aga/src/r_surf.c` `R_BuildLightMap`: styles below `AW_LAMP_STYLE` (32) are scaled by `r_daylight`.
- `tools/light_sources.py` `quake_style`.

## How it happened

The style mapping took id's numbering from Quake's own worldspawn, but AmiWind's QuakeC never had the strings.
Night dimming came later and was written for the sun and ambient light of style 0.

## Why it was not caught

No converter writes light entities, so no face has ever carried these styles. No test checks that a style the
mapping uses is defined.

## Reproduction

Always: read `worldspawn` and `quake_style`.

## Repair

To do, with the CHIM light bake:

- steady light sources in style 32 (never dimmed by daylight; `r_lamps 0` still switches them off for A/B);
- animated sources in styles 33-36, with strings generated from the original's flicker and pulse rates and set in
  `worldspawn`;
- the sun and ambient stay in style 0.

## Verification

Pending: a test that every style the mapping emits has a string, and frames at night with a flickering source.

## Prevention

A unit test over `quake_style` and the QuakeC style table.

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
