# SKY-REDMOUNTAIN-BLUE-44: inside the Ghostfence at Red Mountain the sky is clear blue instead of red ash weather

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | Red Mountain region inside the Ghostfence, cell 2,5 (global 20605 47338 4890, game time 15:47) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | medium: the most important region of the game loses its look |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 19 October 2026

Reported by the maintainer; not fixed yet.

## Symptom

Inside the Ghostfence on Red Mountain the sky is a clear blue with white clouds, and the horizon fill behind the
mountain's slopes is light blue. In the original game the region under the mountain has its own weather, ash and
blight storms, with red-brown fog and sky.

## Where

Red Mountain region, cell 2,5 (global 20605 47338 4890), game time 15:47.

## How it happened

The sky, fog and horizon colours do not yet follow the region's weather: every region gets the same clear sky.

## Why it was not caught

No check compares the sky and fog colour per region with the original game.

## Reproduction

Always: go inside the Ghostfence at any time of day.

## Repair

To do: read the Red Mountain region's weather from the game data, compare with OpenMW at the same place and time,
then give the sky, fog and horizon their colours per region. The [roadmap's colour plan](../ROADMAP.md) adds an ash
and red palette ramp that grows in rings around the mountain, so the sky shades toward red as the player gets close. The Ghostfence's own shimmering curtain, still not animated,
is planned with it as a Quake turbulent texture with a flickering glow
([IDEAS](../chim/IDEAS.md#the-ghostfence-as-a-quake-turbulent-surface)).

## Verification

To do: stills and a short clip at the same pose in OpenMW and AmiWind.

## Prevention

To do: a per-region sky and fog colour check against the original weather records.

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
- [GUARD-TORCH-CHIM-FRAMES-44](GUARD-TORCH-CHIM-FRAMES-44.md): Outdoor guards carry no torch at night: the torch step never read the CHIM frame maps
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
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
