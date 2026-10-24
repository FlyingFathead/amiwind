# GUARD-TORCH-CHIM-FRAMES-44: outdoor guards carry no torch at night: the torch step never read the CHIM frame maps

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | tools/prepare_guard_torches.py guard scan (*.bsp only) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | high: Regression: guards walking the streets at night lost the torch light the game had since v0.0.28 |
| Family | Lighting, lamps and night (`lighting-night`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | unknown (maintainer playtest screenshot; emulator not stated) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 19 October 2026

Fixed in the builder; the next image rebuilds the guard torches with every outdoor guard. In-game night check
pending.

## Symptom

At night the guards in the streets of Balmora (the Hlaalu guard outside, at 21:38) walk without their torch and
without its light. Guards inside buildings still carry one. Guards with lit torches on their night duty were a
feature since v0.0.28, so this is a regression.

## Where

Every town and region on CHIM: Balmora, Seyda Neen, Vivec, the intro docks and every other outdoor guard.

## How it happened

The image step's torch tool finds the guards by reading the entities of every map. Two things kept the outdoor
guards out of it. It listed only `maps/*.bsp`, while since v0.0.36 the CHIM town and region frames are written as
`maps/<name>.chim`. And it ran before the image step writes those frame maps at all: the towns and regions on CHIM
take their residents straight from the game data into the frame maps, so at the time of the scan no map held an
outdoor guard. Only the 13 guard types placed in interiors got a torch companion; the engine draws a torch only for
a guard model in that table.

## Why it was not caught

The frame map extension change had a test against hand-made frame-map paths, but not against tools that list maps
with their own `*.bsp` pattern, nor against steps that run before the frame maps exist. The torch receipt only
records what it found, and no check compares that with the guards actually placed in the world. The first repair
was checked on a finished image's files, where the frame maps already exist; a check of the image step's order
found that it would still have found 13.

## Reproduction

Always: stand in a Balmora street after dusk and look at a passing Hlaalu guard.

## Repair

The tool lists maps with the shared helper (`tools/map_files.py` `map_files`, both `.bsp` and `.chim`), and the
image step runs it after the CHIM frame maps are written, before the world heap gate and the content fingerprint
that read its companions. On the v0.0.44-dev1 image's files it finds 19 guard types instead of 13, among them the
outdoor Hlaalu guard, the Ebonheart Imperial guard and the guards of the intro docks; the limit is 32. A guard
model made by the intro's own bake that cannot be rebaked exactly is skipped and named in the receipt; any other
guard still stops the step. The other tools that list only `*.bsp` were checked one by one; that work, with a test that
refuses a new `*.bsp`-only listing outside a list of reasoned exceptions, follows in the next development line.
The world heap gate, which counts every guard's torch in every map, passes on those files with all 19 guard types.

## Verification

`tests/test_guard_torch_assets.py`: a guard in a `.chim` frame map is found, and the image step runs the torch
step after the frame maps. The torch bake ran on the v0.0.44-dev1 image's files with the build's NPC settings: all
19 guard types in 33 s. To do: the v0.0.44 image's own receipt, and a night still and clip of a Balmora street
guard.

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
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

Related bugs in other categories:

- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types

<!-- END GENERATED CATEGORY -->
