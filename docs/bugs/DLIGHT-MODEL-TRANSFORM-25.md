# DLIGHT-MODEL-TRANSFORM-25: Dynamic lights on translated or rotated models (caves) were placed in world coordinates where the surfaces need model-local ones

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 2 October 2026, in an unknown version |
| Where | renderer: dynamic light marking and accumulation on transformed brush models |
| Reproduction | always |
| Duplicate of | no |
| Persists in | unknown |
| Severity | medium: torch light lands in the wrong place on cave models |
| Family | Lighting, lamps and night (`lighting-night`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-02: reported
- 2026-10-02: rc7: contact fitting, fog-off sky and cave lighting: The F/V temporary torch uses existing dynamic lighting.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66 (16 November 2026)._

## Status: 16 November 2026

Open. Repaired in source for v0.0.25-rc7: dynamic marking and accumulation use the same model transform; tests exercise actual surface lighting. Cave appearance and Amiga performance were left to the playtest and no later check is recorded. Exposed by the F/V temporary torch work before v0.0.25-rc7. Recorded as an entry from the bug journal on 16 November 2026.

## Symptom

The F/V temporary torch lit translated or rotated cave models in the wrong place.

## Where

Renderer: dynamic light marking and accumulation on transformed brush models.

## How it happened

As recorded in the bug journal: see the dated history in the timeline below.

## Why it was not caught

Not recorded.

## Reproduction

As in the symptom; reproduction: always.

## Repair

Dynamic marking and accumulation now use the same model transform.

## Verification

See the status and the timeline below.

## Prevention

Not recorded.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-EXTERIOR-FLAMES-MISSING-48](CHIM-EXTERIOR-FLAMES-MISSING-48.md): CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- [CHIM-ROOM-LIGHT-FLAT-48](CHIM-ROOM-LIGHT-FLAT-48.md): CHIM rooms light each placement at one level: Temple arch trims and Rithleen walls look flat and brighter than the room maps baked light
- [DLIGHT-WALLS-31](DLIGHT-WALLS-31.md): Torches barely light town walls at night
- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [ENGINE-FLAME-LIGHT-KEY-WARNING-51](ENGINE-FLAME-LIGHT-KEY-WARNING-51.md): Every Seyda Neen load prints "aw_flame_light is not a field" ten times: the fire rows key no QuakeC field
- [FLAME-RANGE-NEAREST-32](FLAME-RANGE-NEAREST-32.md): A hearth fire shows only up close when many candles are nearer
- GUARD-COLD-28 (no report page): Night-guard torches not admitted on cold visits
- [GUARD-TORCH-ALDRUHN-CYCLE-56](GUARD-TORCH-ALDRUHN-CYCLE-56.md): Ald'ruhn's guards do not carry torches by the day and night cycle (beside the temple at least)
- [GUARD-TORCH-BRIGHT-31](GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- [GUARD-TORCH-CHIM-FRAMES-44](GUARD-TORCH-CHIM-FRAMES-44.md): Outdoor guards carry no torch at night: the torch step never read the CHIM frame maps
- [GUARD-TORCH-CYCLE-29](GUARD-TORCH-CYCLE-29.md): Guard torch intermittently absent during night-cycle observation
- [INTERIOR-BAKE-UNIFORM-32](INTERIOR-BAKE-UNIFORM-32.md): Some interior bakes are uniform (lights possibly missing)
- INTERIOR-FOG-UNUSED-51 (no report page): Interiors have no fog: the cell's fog colour and density are never used, so misty caves and tinted rooms show none
- [INTERIOR-LIGHT-29](INTERIOR-LIGHT-29.md): Interiors lack convincing local illumination
- [INTERIOR-NPC-LIGHT-29](INTERIOR-NPC-LIGHT-29.md): Census Office characters appear too dark under room lighting
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
- [SKY-MIDNIGHT-29](SKY-MIDNIGHT-29.md): Dense clouds still hide the midnight sky
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TAKEN-LIGHT-BAKED-LIGHT-61](TAKEN-LIGHT-BAKED-LIGHT-61.md): A taken candle or lamp leaves its own light baked into the room around it
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- [THIRALAS-HOUSE-RED-LIGHT-65](THIRALAS-HOUSE-RED-LIGHT-65.md): Draren Thiralas' house in Seyda Neen is lit all red and yellow inside
- [TORCH-LIGHT-29](TORCH-LIGHT-29.md): Torch flames look weak and provide little immediate light
- [TORCH-NPC-LIGHT-29](TORCH-NPC-LIGHT-29.md): Nearby NPCs do not visibly respond to torchlight
- [TORCHTEST-DARKNESS-29](TORCHTEST-DARKNESS-29.md): Torch test room floor stays dim gray at zero light
- [WEATHER-AMBIENT-SUN-UNUSED-51](WEATHER-AMBIENT-SUN-UNUSED-51.md): Exteriors take only the sky and fog colours of the weather: its ambient and sun colours are never used, so the land under an ash or blight storm (Red Mountain) is lit neutral
- [WEATHER-CLOUD-TEXTURES-68](WEATHER-CLOUD-TEXTURES-68.md): Every weather shows the same clouds, recoloured: the original has a cloud texture per weather
- [WEATHER-FOG-CLOUDS-ONE-LOOK-68](WEATHER-FOG-CLOUDS-ONE-LOOK-68.md): Every weather drew the clear weather's fog distance and cloud speed: a blizzard looked as far and as calm as a clear day apart from its colour

<!-- END GENERATED CATEGORY -->
