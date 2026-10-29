# CENSUS-OFFICE-BRIGHT-32: the Census and Excise Office walls are about twice as bright as the original

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | Census office baked light (tools/prepare_census.py, tools/interior_lighting.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | low: Walls about twice as bright as the original at the arrival pose; no gameplay effect. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 64f9df5 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.51 (25 October 2026)._

## Status: 25 October 2026

Open. Interiors were baked without their cell sunlight
([INTERIOR-SUNLIGHT-UNBAKED-51](INTERIOR-SUNLIGHT-UNBAKED-51.md)). The OpenMW numbers below already include the
office's sunlight, so the extra brightness here comes from the bake itself: linear falloff and no facing term.
The office's cell holds ambient 55, 45, 45 (luma 48) and sunlight 87, 58, 13 (luma 61.5), so the sunlight is a
real part of its light. v0.0.51-dev3 adds it at bake time and lowers the interior luma default from 1.2 to 1.0 at
run time, a sixth less. The
maintainer says the office was already too bright, so dev3 is measured at the arrival pose before anything else.
The repair is a judged `CELL_PROFILES` entry, as for the ship.

## Status: 9 October 2026

Open. Measured while checking character light (NPC-LIGHT-COHERENCE-32); no repair yet.

## Symptom

At the office's arrival pose the candle-lit walls are about twice as bright as in the original;
the whole view is 1.23 times as bright.

## Where

The office map's baked light (`tools/prepare_census.py` through the shared bake in
`tools/interior_lighting.py`) and the interior luma setting (default 1.2).

## How it happened

FS-UAE, v0.0.32 image, `dbg tp census`, `aw_aim 0 15`, clock 12:00, headlamp off, against OpenMW
at the same pose (Seyda Neen, Census and Excise Office, MW 16 -136, heading 90, pitch 14): view
mean luma 21.5 against 17.9; the wall left of the tapestry 38.6 against 19.8. The office bakes
with the first-pass light: linear falloff, no facing term, times the interior luma 1.2 at run time,
the same causes the prison ship had ([OPENING-BRIGHT-31](OPENING-BRIGHT-31.md)).

## Why it was not caught

Interiors other than the ship have not been compared with the original light by light.

## Reproduction

`dbg tp census`, `aw_aim 0 15`, headlamp off; OpenMW at the same pose and time.

## Repair

Not done. Candidate: a `CELL_PROFILES` entry for the office (original falloff, facing term),
judged against OpenMW at the same poses, as for the ship.

## Verification

Pending.

## Prevention

The office's arrival pose in the original-versus-AmiWind capture set.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CHIM-EXTERIOR-FLAMES-MISSING-48](CHIM-EXTERIOR-FLAMES-MISSING-48.md): CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- CHIM-ROOM-LIGHT-FLAT-48 (no report page): CHIM rooms light each placement at one level: Temple arch trims and Rithleen walls look flat and brighter than the room maps baked light
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- ENGINE-FLAME-LIGHT-KEY-WARNING-51 (no report page): Every Seyda Neen load prints "aw_flame_light is not a field" ten times: the fire rows key no QuakeC field
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-ALDRUHN-CYCLE-56](GUARD-TORCH-ALDRUHN-CYCLE-56.md): Ald'ruhn's guards do not carry torches by the day and night cycle (beside the temple at least)
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- [GUARD-TORCH-CHIM-FRAMES-44](GUARD-TORCH-CHIM-FRAMES-44.md): Outdoor guards carry no torch at night: the torch step never read the CHIM frame maps
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- INTERIOR-FOG-UNUSED-51 (no report page): Interiors have no fog: the cell's fog colour and density are never used, so misty caves and tinted rooms show none
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [INTERIOR-SUNLIGHT-COLOUR-51](INTERIOR-SUNLIGHT-COLOUR-51.md): The cell sunlight is baked as brightness only: Akulakhan's Chamber is lit grey where the original lights it red
- [INTERIOR-SUNLIGHT-UNBAKED-51](INTERIOR-SUNLIGHT-UNBAKED-51.md): Interiors are baked without their cell sunlight: Akulakhan's Chamber is nearly black where the original is lit red
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
- RED-MOUNTAIN-MENACE-54 (no report page): Requested: the Red Mountain region, near and inside the Ghostfence, darker, redder and more menacing, from the game's own region and weather data
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light
- WEATHER-AMBIENT-SUN-UNUSED-51 (no report page): Exteriors take only the sky and fog colours of the weather: its ambient and sun colours are never used, so the land under an ash or blight storm (Red Mountain) is lit neutral

<!-- END GENERATED CATEGORY -->
