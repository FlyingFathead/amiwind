# INTERIOR-SUNLIGHT-UNBAKED-51: interiors are baked without their cell sunlight

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 25 October 2026, in v0.0.51-dev1 |
| Where | tools/interior_lighting.py (the room bake: ambient and placed lights only) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.51-dev1 (last seen) |
| Severity | high: The final chamber of the main quest is almost black; 322 of 1,335 interior cells light mostly by their sunlight |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | 2026_10_25_v0.0.51-dev1_dev1_ec96c86d |
| From commit | source ec96c86, engine ec96c86, CHIM world ec96c86 |
| CHIM engine version | CHIM 0.2.2, engine ec96c86, world format 0.11 |
| Platform or emulator | FS-UAE, JIT, A1200 profile, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.51 (25 October 2026)._

<!-- contents start -->
## Contents

- [Status: 25 October 2026](#status-25-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [What it affected](#what-it-affected)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 25 October 2026

Fixed in source on v0.0.51-dev, built in v0.0.51-dev3. Every interior is baked again with its cell sunlight. The
interior luma default goes back from 1.2 to 1.0.

## Symptom

Akulakhan's Chamber, the last room of the main quest, is nearly black in the v0.0.51-dev1 screenshots (FS-UAE,
32 MB). The original lights it red. The maintainer: it is lit properly in the original game. Many other interiors
have looked dimmer than the original since the first converted interiors, and nobody knew why.

## Where

`tools/interior_lighting.py`, the room bake. Every interior cell's AMBI record holds three things: the ambient
colour, the sunlight colour and the fog. The bake used the ambient and the placed lights, never the sunlight.
The original engine applies an interior's sunlight as a directional light from one fixed direction (OpenMW
`interiorSunPos`).

## How it happened

The first interior bake took "ambient" as the whole of the cell's own light. The sunlight bytes sit next to the
ambient bytes in the same record and were never read. For most rooms that only made them dimmer, so the
difference read as "interiors look bleak" and was tuned with a brightness knob, not traced to an input.

## What it affected

- **How many rooms.** Of 1,335 interior cells in the three masters, 322 have sunlight luma at least twice their
  ambient luma, 85 have four times and 29 have eight times. Those rooms were baked mostly or almost wholly without
  their main light.
- **Akulakhan's Chamber.** Ambient 20, 30, 30 (luma 27) and sunlight 255, 140, 140 (luma 174), with 7 placed lights
  in a large room. Without the sunlight, all that is left is the dim ambient and a few lamps far apart.
- **The interior luma default of 1.2.** It was set in v0.0.29-rc2 for
  [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md) ("interiors lack convincing local illumination"). Looking back, it was
  a correction for the missing sunlight: it lifted every room the same amount, so rooms with a lot of sunlight
  stayed too dark and rooms with little sunlight got too bright. Once the sunlight is baked in, the default goes
  back to 1.0. The `aw_interiorluma` control stays in the options and the debug console for players who want to
  adjust brightness. At 1.0 it costs nothing; at 1.2 it cost about 1.2% of frame time on the surface cache.
- **Characters in rooms.** Actors and placed models take their light level from the bake at their centre, so they
  missed the sunlight too. INTERIOR-NPC-LIGHT-29 (Census Office characters too dark)
  is probably partly this; it is checked again on dev3.
- **CHIM rooms.** CHIM rooms bake no lightmaps. Each placed model gets one light level at its centre, so the
  sunlight adds half the sun's luma to every model in the room. In the chamber that is about +87 on a base of 27.
  How flat that looks is tracked in CHIM-ROOM-LIGHT-FLAT-48.
- **Lightmapped rooms** (the BSP room maps) get the full cosine term on each face.
- **The prison ship.** Its look was judged against OpenMW without the sunlight
  ([OPENING-BRIGHT-31](OPENING-BRIGHT-31.md)). Its sunlight is lower than its ambient anyway, and its profile now
  says `sunlight_term: False`, so its judged look stays as it was.
- **The Census and Excise Office.** At v0.0.32 its walls were already about twice as bright as OpenMW
  ([CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md)). The OpenMW reference already includes the sunlight, so
  the extra brightness has another cause (the first-pass falloff and no facing term). The sunlight adds light at
  bake time and the 1.0 default takes away a sixth at run time; dev3 is measured to see the net change.
- **Not affected.** Exteriors use the sky and weather sunlight, not this field. Interior light is static: it does
  not follow the game clock, except for cells that behave like exteriors (Mournhold, Solstheim), which come later.

## Why it was not caught

Interiors were compared with the original room by room and adjusted with a global multiplier and per-cell
profiles. No one listed every light input in the cell record and checked that the bake used each one.

## Reproduction

v0.0.51-dev1 or earlier: `dbg tp heartchamber`, look along +y from the arrival point. The original and OpenMW at
the same place for comparison.

## Repair

`tools/interior_lighting.py`: `sun_light()` adds the cell sunlight as a directional light from OpenMW's interior
direction (-1, 45°, 45°): its luma times the cosine toward each face; actors and placed models get half of it
(`SUN_ACTOR_SHARE`). A judged cell profile can leave it out (`sunlight_term: False`, the prison ship). The interior
luma default is 1.0 in `engine/aga/src/r_light.c`, `config/game.cfg` and the debug catalogue. Tests:
`tests/test_ship_light.py` (InteriorSunlightTests) and the luma tests.

## Verification

Pending on v0.0.51-dev3: Akulakhan's Chamber at 32 MB from the arrival point, four directions; each room map's
average light before and after; the census office and the prison ship at their arrival poses.

## Prevention

Before any lighting change or new brightness profile, list every light input the original data holds for the
place (ambient, sunlight, fog, placed lights, glowing surfaces) and check that the bake uses each one. A per-cell
profile records which inputs it was judged with.

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
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- [GUARD-TORCH-CHIM-FRAMES-44](GUARD-TORCH-CHIM-FRAMES-44.md): Outdoor guards carry no torch at night: the torch step never read the CHIM frame maps
- GUARD-TORCH-CYCLE-29 (no report page): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- INTERIOR-FOG-UNUSED-51 (no report page): Interiors have no fog: the cell's fog colour and density are never used, so misty caves and tinted rooms show none
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- INTERIOR-NPC-LIGHT-29 (no report page): Census Office characters appear too dark under room lighting
- [INTERIOR-SUNLIGHT-COLOUR-51](INTERIOR-SUNLIGHT-COLOUR-51.md): The cell sunlight is baked as brightness only: Akulakhan's Chamber is lit grey where the original lights it red
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

Related bugs in other categories:

- [BUILD-CUTOFF-WHOLE-ANCESTOR-51](BUILD-CUTOFF-WHOLE-ANCESTOR-51.md): An interior light change reran exterior stages: the reuse cutoff refuses a stage when any earlier stage's whole output differs, not the files it reads

<!-- END GENERATED CATEGORY -->
