# FLAME-RANGE-NEAREST-32: A hearth fire shows only up close when many candles are nearer

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Census and Excise Office hearth (static flame budget) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.50 |
| Severity | medium: The hearth fire is not drawn until the player is close, because nearer candles take the flame slots. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 8 October 2026

Open: repaired in source (v0.0.32-fire-range), not yet in a built image. Reported by the maintainer
on v0.0.32-dev1. Present since static flames got their per-frame budget (v0.0.30-dev5), so
v0.0.31 behaves the same; not a v0.0.32 regression.

## Symptom

Seyda Neen, Census and Excise Office (local -25 -20 64, heading south, pitch 10, 10:40): the
fireplace a few metres ahead shows no fire. The fire appears only when the player walks right up
to it.

## Where

`engine/aga/src/aw_guard_torch.c`, `AW_StaticFlamesDraw`: the flames of placed fires, candles and
lanterns (`aw_flame` entities written by the scene converter), drawn as flame particles plus Quake
particle embers (`pt_awember`, `r_part.c`).

## How it happened

Each frame the engine draws at most 12 static flames (`STATIC_FLAME_DRAW`) within 640 units, and
chose the 12 nearest in any direction, without looking at the view or the flame size. The Census
office has 51 `aw_flame` entities: one hearth (size 8) and 50 candles (size 0.8), most of them in
fours on chandeliers. At the maintainer's pose 14 flames are nearer than the hearth (about 100 units
away), 10 of them behind the camera, so the hearth ranked 15th and was never drawn. Closer to the
fireplace it got into the nearest 12, which matches the report. The map's `aw_flame` entities are
identical in v0.0.31 and dev1, and the selection code is unchanged since v0.0.31.

## Why it was not caught

The flame budget was checked in rooms with few flames; no room with more than 12 nearer flames,
most of them behind the camera, was in the capture set.

## Reproduction

Census and Excise Office: `noclip`, `aw_view -25 -20 64 277 10`; the fireplace has no flame.
`aw_static_flames_nearest 1` restores the earlier rule in a fixed engine.

## Repair

Engine only (`AW_StaticFlamesPick`), the same budget of 12 flames:

- Default rule (`aw_static_flames_nearest 0`): only flames whose particles can reach the view
  rectangle (same projection as the flame particles, with their size, spread and rise as margin)
  compete for the budget, ranked by drawn size over distance, so a hearth outranks far candles and
  flames behind the camera never take a slot.
- The earlier rule (nearest within range, in any direction) is kept and selectable:
  `aw_static_flames_nearest 1`.

## Verification

- `tests/aga_static_flame_select_test.c` (native, `test_aga_native_source.py`): a room modelled on
  the Census office; the earlier rule leaves the hearth out (12 nearest, checked against an
  independent distance oracle), the default rule draws it first and only flames in front; turning
  around gives its slot away; never more than 12; nothing beyond the range.
- Pending: the Census office pose in FS-UAE with the next image.

## Prevention

The native test pins both rules and the budget; rooms with many candles (Census office) are in
the interior capture set.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-EXTERIOR-FLAMES-MISSING-48](CHIM-EXTERIOR-FLAMES-MISSING-48.md): CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- CHIM-ROOM-LIGHT-FLAT-48 (no report page): CHIM rooms light each placement at one level: Temple arch trims and Rithleen walls look flat and brighter than the room maps baked light
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- ENGINE-FLAME-LIGHT-KEY-WARNING-51 (no report page): Every Seyda Neen load prints "aw_flame_light is not a field" ten times: the fire rows key no QuakeC field
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
