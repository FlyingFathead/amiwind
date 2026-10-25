# SKY-REDMOUNTAIN-BLUE-44: inside the Ghostfence at Red Mountain the sky is clear blue instead of red ash weather

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.44-dev1 at 2026-10-19 15:28 +0300: maintainer: inside and near the Ghostfence the horizon should turn mostly red, grey and brown, and the sky more red as the player approaches
- Reported with v0.0.45 at 2026-10-20 02:30 +0300: still blue in v0.0.45 (no weather table); cause: clear-weather colours only, no region weather written; fixed on branch v0.0.46-sky-pedestal, needs a world build
- Reported with v0.0.46 at 2026-10-20 21:33 +0300: maintainer, v0.0.46 playtest: inside the Ghostfence the blight sky turns blue at once (time = when the report reached the fix; the report's own time was not passed on)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | Red Mountain region inside the Ghostfence, cell 2,5 (global 20605 47338 4890, game time 15:47) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: the most important region of the game loses its look |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 20 October 2026](#status-20-october-2026)
- [Reported again with v0.0.46](#reported-again-with-v0046)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 20 October 2026

**Reported again with v0.0.46 (open, persisting).** The maintainer, in the v0.0.46 playtest: inside the Ghostfence
the blight sky turns blue while he is still inside the fence. See
[Reported again with v0.0.46](#reported-again-with-v0046) below. A fix is on branch v0.0.46-ghostfence. It is
checked in game in a fresh play copy of the v0.0.46 image with the fixed engine, but it is not gated or in a
build yet.

Earlier the same day: fixed in v0.0.46. The maintainer checked the v0.0.46-dev1 playtest on the evening of 20 October 2026: "at least the red mountain is now red". The weather itself (clouds, rain, ash) is still missing and is not part of this bug.
The text below is the state before that build.

Cause found; repaired in the source on branch v0.0.46-sky-pedestal (region weather, every region), not yet in a
build. Still present in v0.0.45 (its world has no weather table). Needs a world rebuild and an in-game look.

## Reported again with v0.0.46

Two causes, found in the game data, OpenMW and the engine:

- **The sky switched at once at every cell border.** Every exterior cell is its own CHIM frame. The default
  crossing loads the next frame as a new map: a map change, and a load that can take over 2 seconds on the
  Amiga. The weather code took both for an arrival, as after travel or a load, and put the new cell's weather
  there at once instead of changing to it over time. In game, at Ghostgate, walking south from Red Mountain
  (cell 2,5) into cell 2,4 while still inside the fence:
  - with the v0.0.46 engine, `dbg weather` said `ash` at the first look after the crossing;
  - with the fixed engine it said `blight changing to ash` 9 %, 41 %, 70 % and 98 % over the next 32 seconds,
    then `ash`.
- **Part of the fenced-in area is not Red Mountain in the game data.** The Ghostfence is not the border of the
  Red Mountain region. 22 of the 36 cells the fence runs through belong to the Ashlands region in Morrowind.esm
  (the other 14 to Red Mountain). Measured over the fence line, 9.8 % of the area inside the fence lies in Ashlands cells:
  a strip along the inside of the fence, including the north side of Ghostgate. Every one of the 37 Red Mountain
  cells is inside the fence. The original and OpenMW take the weather from the cell's own region. OpenMW 0.51
  (`apps/openmw/mwworld/weather.cpp`: `update` passes the player cell's region to `updateWeatherRegion`) does the
  same at the same place. Walking from Red Mountain into cell 2,4 at Ghostgate, its weather went from Blight to
  the Ashlands' Foggy of that day; the change was half done about 35 seconds later. So the sky inside that strip
  does change, in the original too, but slowly, not at once.

Today's Ashlands weather decides the colour it changes to: ash storm, overcast, cloudy, foggy or clear. Clear and
cloudy are blue-grey skies, together 35 % of its days.

The fix follows OpenMW's rules (read, not copied):

- A new weather starts a transition at its Transition Delta when none runs.
- While a transition runs, the next weather is queued until it ends, instead of the sky jumping back.
- A cell without a region keeps the weather it had.
- Only an arrival puts the new weather there at once: the first frame, a jump of over half a cell, or an hour or
  more of game time.

The region stays the cell's own, as in the data.

## Symptom

Inside the Ghostfence on Red Mountain the sky is a clear blue with white clouds, and the horizon fill behind the
mountain's slopes is light blue. In the original game the region under the mountain has its own weather, ash and
blight storms, with red-brown fog and sky.

## Where

Red Mountain region, cell 2,5 (global 20605 47338 4890), game time 15:47.

## How it happened

Nothing in the game chose a weather. The sky code (`engine/aga/src/r_sky.c`) built its sky, horizon and fog tables
from one fixed set of colour stops, the clear weather's (`sky_rgb_stops` / `fog_rgb_stops`, "Clear-weather RGB
stops ... No weather simulation"), and no build step wrote the regions' weather records anywhere the engine could
read them: the builder's region table (`region-names.awn`, `tools/prepare_world_ui.py`) carried only the region
names for the HUD. So every exterior cell drew the clear sky, whatever its region. Red Mountain's region record
gives blight a 100 % chance and clear 0 % (Morrowind.ini: blight sky 90,35,35, fog 128,19,19 by day).

Island-wide (v0.0.45 world, its `region-names.awn` against the region records of Morrowind.esm): every one of the
nine regions draws the clear sky all the time, while its record gives clear only part of the time:

| Region | Exterior cells | Clear in the records | Its weathers by chance |
| --- | --- | --- | --- |
| Red Mountain | 37 | 0 % | blight 100 |
| Molag Amur | 123 | 5 % | foggy 35, overcast 25, ash storm 20, cloudy 15 |
| Ashlands | 162 | 10 % | ash storm 30, overcast 25, cloudy 25, foggy 10 |
| Bitter Coast | 166 | 10 % | cloudy 60, rain 10, thunderstorm 10, foggy 10 |
| West Gash | 193 | 15 % | cloudy 30, overcast 20, foggy 15, rain 10, thunderstorm 10 |
| Sheogorad | 170 | 15 % | cloudy 40, overcast 15, rain 10, thunderstorm 10, foggy 10 |
| Azura's Coast | 379 | 25 % | cloudy 45, overcast 10, foggy 10, rain 5, thunderstorm 5 |
| Grazelands | 57 | 30 % | cloudy 40, rain 10, thunderstorm 10, overcast 5, foggy 5 |
| Ascadian Isles | 116 | 45 % | cloudy 45, rain 5, thunderstorm 5 |

## Why it was not caught

No check compares the sky and fog colour per region with the original game, and the sky work so far
([DAY_NIGHT_AND_SKY](../DAY_NIGHT_AND_SKY.md)) was the clear day and night only.

## Reproduction

Always: go inside the Ghostfence at any time of day.

## Repair

Region weather, for every region at once ([DAY_NIGHT_AND_SKY: Region weather](../DAY_NIGHT_AND_SKY.md#region-weather-20-october-2026)):

- Builder: the world UI stage writes `id1/world/region-weather.aww` (430 bytes): each region's weather chances
  from its record, in the order of `region-names.awn`, and the ten weathers' sky and fog colours, transition speed
  and glare from Morrowind.ini (or the values it ships with).
- Engine: `aw_weather.c` / `aw_weather_rules.c` pick the region's weather at the player (rules from OpenMW file
  `apps/openmw/mwworld/weather.cpp`: the roll against the summed chances, a new choice every 20 game hours, a
  transition at the weather's speed when walking into another region, at once after travel or a load); `r_sky.c`
  draws that weather's sky, horizon and fog colours at every time of day, and no sun disc or sunrise glow in a
  storm. Clear weather builds exactly the tables of before. `dbg weather` shows the weather and the region's
  chances, `dbg weather blight` forces one, `dbg weather off` (`aw_weather 0`) brings back the old clear sky.

Not in this repair: the weathers' own cloud textures (Tx_Sky_Blight and the others), ash and blight particles,
storm sounds, storm ambient light, and the [roadmap's](../ROADMAP.md) ash and red palette ramp in rings around the
mountain. The Ghostfence's own shimmering curtain, still not animated, is planned as a Quake turbulent texture with
a flickering glow ([IDEAS](../chim/IDEAS.md#the-ghostfence-as-a-quake-turbulent-surface)).

## Verification

Reported again with v0.0.46: `tests/aga_weather_rules_test.c` covers the transition, the queue, the time carried
over, a cell without a region and the arrival thresholds; `tests/test_region_weather.py` covers the wiring. In game:
the walk south across the cell border at Ghostgate, recorded with the v0.0.46 engine and with the fixed engine
(same image, same scripted route), and the same walk in OpenMW.


Done (source, 20 October 2026): `tests/test_world_ui_assets.py` (the weather table follows the region order and
chances; Red Mountain's row is blight 100; the shipped clear colours equal the engine's clear stops),
`tests/test_region_weather.py` with `tests/aga_weather_rules_test.c` (roll, 20-hour period, table shape, Red
Mountain blight in every period, the West Gash spread over 4,000 periods, the blend), the Amiga engine compiles
without warnings. On the real Morrowind.esm the builder's `region-names.awn` is byte-identical to the v0.0.45
release's and the weather table has the nine rows above.

To do: a world build with the region weather table, then stills and a short clip at the reported pose (cell 2,5,
15:47) in OpenMW and AmiWind (`dbg weather` must say blight), and a walk across the Ghostfence for the transition.

## Prevention

The builder now writes every region's weather from its record, tested against the region order; the sweep table
above is the per-region check against the original records.

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
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light
- WEATHER-AMBIENT-SUN-UNUSED-51 (no report page): Exteriors take only the sky and fog colours of the weather: its ambient and sun colours are never used, so the land under an ash or blight storm (Red Mountain) is lit neutral

Related bugs in other categories:

- [GHOSTFENCE-NO-ANIMATION-46](GHOSTFENCE-NO-ANIMATION-46.md): The Ghostfence's shimmering curtain does not move: its texture scroll is dropped by the converter

<!-- END GENERATED CATEGORY -->
