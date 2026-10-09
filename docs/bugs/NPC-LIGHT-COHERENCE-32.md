# NPC-LIGHT-COHERENCE-32: characters are lit by the floor below them, not by the light where they stand

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | Actor static light in converted interiors (engine r_light.c R_LightPoint) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: Characters do not match the room around them (Jiub, Socucius Ergalla); no gameplay effect. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 64f9df5 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
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

## Status: 9 October 2026

Open: repaired in source (branch v0.0.33-ship-light), not yet in a built image. Proven in FS-UAE
on the v0.0.32 image with the changed engine and the prison ship and Census office maps re-baked
by the changed converter functions (see "Verification").

## Symptom

Owner, playing CHIM Preview 1 (v0.0.32 content): "I think once again the NPC lighting isn't
following any coherence." Characters do not match the light of the room around them: Jiub stands
under the hold's lantern but is lit like the dark wall behind him; in the Census and Excise Office
Socucius Ergalla is nearly black in front of a candle-lit wall.

## Where

Actor static light in the engine (`engine/aga/src/r_light.c`, `R_LightPoint`, called for every
alias model by `r_main.c`), fed by the interior bake (`tools/interior_lighting.py`).

## How it happened

Quake lights a model by the lightmap of the floor straight below it (`R_LightPoint` traces down
from the model's origin). v0.0.30 extended the trace to the converted objects' floors
(`aw_actor_brush_light`), but the rule is still "the floor decides". In the converted interiors
that floor often has nothing to do with the light on the character's body:

- Prison ship: the lantern hangs 48 units above the floor next to Jiub. Its light reaches his
  head and shoulders (in the original Jiub is 2.4 times as bright as the wall behind him), but the
  floor below him is outside the lantern's reach in the bake, so he got the ambient only.
- Census office: Socucius Ergalla stands on a rug in a candle-lit corner; the floor sample under
  him is far darker than the light on the walls around him (0.35 of the wall where the original
  has about 1.0).

The alias renderer then adds the classic fixed-direction shading on top of that one value, which
cannot repair a wrong value.

## Why it was not caught

The v0.0.30 check compared the character with the floor below him ("now matches the floor light
where he stands"), not with the original at the same pose.

## Reproduction

New Game: Jiub at the start; `dbg tp census`, look at Socucius Ergalla (`aw_aim 0 15`). Compare
with OpenMW at the same pose and time.

## Repair

The Quake way (an engine-side light grid, as newer Quake light compilers store for models): the
interior converters bake the same light the walls get (cell ambient, lamps with their falloff,
box zones; no facing term, a body is lit from every side) on a coarse grid over the sealed
interior and store it in the worldspawn (`"_aw_lightgrid"` and `"_aw_lightgridN"` keys, ignored
by the server like every key starting with "_"). Step 16, 32 or 64 units, the smallest that keeps
the grid at most 8,192 points (prison ship 12 x 39 x 10 at 16, Census office 15 x 22 x 7 at 32).
The engine reads the grid when the map loads (`R_LightGridNewMap`) and lights each character by
the grid at the middle of its model's height, trilinear, a few multiplies per character per
frame; the view model by the grid at the view. Maps without a grid (exteriors, older maps) keep
the floor sample; `aw_actor_light_grid 0` (saved setting, default 1) restores the floor sample
everywhere (the previous method stays selectable). `aw_light_probe` prints the grid and floor
light at the player's position. Lightmaps of every map are unchanged by the grid.

Exteriors are not affected: there the characters take the cell's ambient and the dynamic lights
(torches, night lamps), the same lights that light the walls; measured below.

## Verification

FS-UAE, standard profile, headlamp off, clock held at 12:00 (Balmora at 22:21). A = v0.0.32
image; C = the same image with the changed engine and the re-baked maps; "grid off" =
`aw_actor_light_grid 0` in C. OpenMW 0.48 at the same pose and time. Mean luma of the character
and of the wall next to him:

| Pose | A v0.0.32 | C grid off | C repaired | OpenMW |
| --- | --- | --- | --- | --- |
| Jiub at the start (character / wall) | 35.1 / 35.8 = 0.98 | 25.8 / 15.5 = 1.67 | 33.0 / 15.5 = 2.13 | 25.8 / 10.6 = 2.44 |
| Socucius Ergalla, Census office | 13.5 / 38.6 = 0.35 | 13.5 / 38.6 = 0.35 | 25.2 / 38.6 = 0.65 | 20.7 / 19.8 = 1.04 |
| Hlaalu guard, Balmora at night (exterior, no grid; guard / ground) | 33.6 / 39.3 = 0.85 | - | 34.5 / 39.3 = 0.88 | not matched |

(In C with the grid off the ship's walls are already darker from OPENING-BRIGHT-31's new bake;
the character still follows only the floor.) A rerun of A in a second session gave the same
frames to 0.01 luma (drift control); the exterior view is unchanged between A and C (whole view
22.96 in both; the guard's own pixels differ by his animation and torch flicker). The Census office walls are about twice as bright as
in the original (the office keeps its v0.0.32 bake), so the character-to-wall ratio there is the
fair measure. Tests: `tests/test_light_grid_native.py` compiles the real `r_light.c`: grid
parsing, trilinear sample, body centre, clamping at the grid edge, the ambient floor, the setting,
malformed or incomplete grids falling back to the floor light, keys split over chunks;
`tests/test_ship_light.py`: grid keys round trip, Jiub's chest brighter than the floor below him,
no grid for a cell without lights.

## Prevention

Character light is judged against the original at the same pose (character-to-wall ratio), not
against the floor below the character.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Lighting, lamps and night (`lighting-night`). Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. See [families](README.md#families).

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
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
