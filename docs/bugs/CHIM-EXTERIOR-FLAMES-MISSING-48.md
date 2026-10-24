# CHIM-EXTERIOR-FLAMES-MISSING-48: CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 23 October 2026, in v0.0.47 |
| Where | CHIM frame maps and batch room maps: no aw_flame entities (tools/chim/frame_map.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.47 (last seen) |
| Severity | medium: Every fire outdoors on CHIM is unlit: 719 fire emitters on 719 placements in 299 of 1,351 frames of the v0.0.47 world, and the hearths of batch rooms |
| Family | Lighting, lamps and night (`lighting-night`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.47 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.1, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | maintainer's playtest |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
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

## Status: 23 October 2026

Open: repaired in source on the branch v0.0.48-chim-fires, not yet in a built image. Reported by the maintainer on
23 October 2026: the fire of the fireplace in the earlier versions' Census and Excise Office should burn on every
campfire across the map, and it does not in the CHIM exteriors.

## Symptom

Outdoors on CHIM (the towns and every region frame), a campfire, brazier, fire pit, torch or flame lamp shows its
model but no fire. The rooms converted the earlier way (Quake room maps) still burn. CHIM rooms made in batches lost
their hearth's fire too.

## Where

- The engine draws a placed fire's flame from the `aw_flame` entities of the map it has loaded
  (`engine/aga/src/aw_guard_torch.c`, `static_flames_load`: the loaded map's entity text, at most 128 per map; each
  frame the best 12 on screen within 640 units animate, as since FLAME-RANGE-NEAREST-32).
- The room and town converters write one `aw_flame` per particle emitter of a placed mesh
  (`tools/prepare_mesh_bsp.py`, `flame_entities`).
- A CHIM model keeps the same emitters in its own entity lump, in the model's frame (`tools/chim/models.py`,
  `variant_flames`).
- The frame maps of the CHIM towns (`tools/chim/frame_map.py` `build`, made from the game data), the region frames
  (`_region_map_game_data`) and the batch rooms' shell maps (`tools/chim_room_batches.py`) wrote no `aw_flame`.

## How it happened

The CHIM world stored the emitters with each model, but nothing read them: the engine reads static flames only from
the map's entities, and when the towns and regions moved to frame maps made from the game data (no legacy region map
to copy from), no step put the flames there. The batch rooms' shell map was made the same way.

## Why it was not caught

No check counted flames per frame map against the flame emitters of the frame's placements, and the evidence frames of
the CHIM towns were taken by day, where a missing flame is easy to miss.

## Reproduction

Any CHIM exterior with a fire, for example the fire pits of the Ashlander camps in the Grazelands or the West Gash.
Counted on the v0.0.47 release build's CHIM world (read only): the five town and special frame maps hold 0 `aw_flame`
entities; the world's models hold 719 fire emitters on 719 placements in 299 of the 1,351 frames.

## Repair

On v0.0.48-chim-fires (`tools/chim/flames.py`): every frame map gets the `aw_flame` rows of the placements its frame
owns, made from the CHIM models' own emitters turned by each placement's angles (the engine's model turn), at the
places the town converter puts them (checked against `flame_entities` on the same placements). The town frame maps,
Seyda Neen's special maps, the region frame maps (also in their pass-cache key, only when a frame has flames) and the
batch rooms' shell maps (from the room record and the interior store) carry them. A room converted whole keeps its
own map's flames unchanged.

- One animation for every fire: a flame is the engine's own particle flame (the hearth colour table and embers for
  the large ones), drawn from the row's size and shape. Nothing per fire is stored but its row: 106,859 bytes of
  entity text over the whole island with the fires' light keys, at most 7,350 bytes in one map (Vivec), counted in the
  map's `_chim_hunk_rest`.
- The fires' light, on by default (the maintainer, 23 October 2026: "set it on by default but add some dbg command
  like dbg campfires on|off"): each fire's first flame row carries its light record's radius and brightness
  (`aw_flame_light`; all 719 fire placements found theirs), and the engine lights the placed models round it when
  their chunk is read (`chim_chunks.c`, the rooms' rule), added to the dimmed ambient outdoors: 6,320 placements in
  299 frames, 144 in the busiest fire frame (Vivec). `dbg campfires off` hides the fires outdoors at once (flames,
  their light on the models, their night lamp rows). The ground gets no stored light yet (terrain lightmaps, planned);
  at night the nearest fires light it as night lamps. The CHIM world store is unchanged (frame maps only).
  [CHIM lighting](../chim/LIGHTING.md#the-fires-light-on-by-default).
- Not fire: 850 emitters whose mesh is a blight or mist cloud, a steam or lava vent, lava sparks or the ash mire get no
  flame (they would burn in the air), counted in each map's record.
- The cap: at most 49 flames in one frame (Vivec), 19 in a region frame; no frame reaches the engine's 128, so the cap
  stays. A frame over it keeps the largest flames first and counts the rest.
- Edicts: an `aw_flame` is removed by QuakeC at spawn (QC-AW-FLAME-SPAWN-32); the freed slot is reused at load, so
  the high-water mark grows by one at most.

## Verification

To do: a MiniWind of a fire pit cell and the census office on CHIM, day and night, headlamp off and on, with the
frame counters (`dbg rcount`) before and after. Unit tests: `tests/test_chim_exterior_flames.py`.

## Prevention

`tools/chim/flames.py measure` counts the fire emitters, flame rows and frames over the cap of a built world; every
frame map's record carries its flame report (placements, emitters, written, over the cap, not fire).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

- [ANIMKIT-TORCH-STANDING-35](ANIMKIT-TORCH-STANDING-35.md): With the animation kit, guards hold their torch only while standing; walking and running drop it
- [BALMORA-LAMPS-DIM-31](BALMORA-LAMPS-DIM-31.md): Balmora's street lamps are far too dim at night
- [CENSUS-OFFICE-BRIGHT-32](CENSUS-OFFICE-BRIGHT-32.md): The Census and Excise Office walls are about twice as bright as the original
- [CHIM-MESHLESS-LIGHTS-33](CHIM-MESHLESS-LIGHTS-33.md): Exterior lights without a mesh have no CHIM light path: 2,284 placed lights give no light in a CHIM frame
- CHIM-ROOM-LIGHT-FLAT-48 (no report page): CHIM rooms light each placement at one level: Temple arch trims and Rithleen walls look flat and brighter than the room maps baked light
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
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

Related bugs in other categories:

- [CHIM-FRAME-ALONE-FLAMES-48](CHIM-FRAME-ALONE-FLAMES-48.md): A town frame map read alone stops in its flames step: the frame-alone world holds its frames by index, the flames lookup walked them as a list
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped

<!-- END GENERATED CATEGORY -->
