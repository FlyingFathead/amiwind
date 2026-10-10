# OPENING-BRIGHT-31: the prison ship hold is brighter than the original

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev2 |
| Where | Prison ship hold lighting (opening scene) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev2 (last seen) |
| Severity | medium: Opening scene 1.2 to 2.5 times brighter than the original; no gameplay effect. |
| Family | Lighting, lamps and night (`lighting-night`) |
| Playtest version | v0.0.31-dev2 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open: repaired in source (branch v0.0.33-ship-light), not yet in a built image. Proven in FS-UAE
on the v0.0.32 image with the prison ship map re-baked by the changed converter functions (see
"Verification"). Earlier status (7 October 2026): measured against the original, no repair.

## Symptom

The opening scene is "too bright"; it should be murky (owner, 7 October: about 0.4 of luma too
bright at the back of the hold, about 0.6 wanted there), with a warm lantern toward Jiub. Again on
CHIM Preview 1 (v0.0.32 content), 9 October: "we need current luma at that very end of the ship
where you're at with Jiub to ~0.5 of what it is and a yellow hue to the lamp above Jiub" (the
lantern is [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md)).

## Where

The prison ship map's baked light (`tools/prepare_interior.py`, `tools/interior_lighting.py`).
Correction of the earlier note: the ship is not excluded from the interior luma setting; `dbg
luma` reports 1.2 in effect there (measured on the v0.0.32 image).

## How it happened

The ship's placed objects are baked by AmiWind's own offline bake (the map's own brushes are only
the dark sealing box; there are no light entities for the light compiler to use). That bake added
the cell's ambient (luma 64) everywhere and each lantern linearly to its radius, with no facing
term, and the interior luma setting 1.2 multiplies it at run time. Measured with headlamp off at
the same start pose (local 0 -35, clock 12:00), v0.0.32 against the original (OpenMW): the 3D
view is 1.67 to 2.42 times brighter (looking north 25.3 against 15.2 mean luma, at the lantern
31.5 against 13.0, at Jiub 27.3 against 14.6). v0.0.31-dev2 measured 1.2 to 2.5 times.

## Why it was not caught

The ship was never compared light by light with the original.

## Reproduction

New Game (or `dbg tp prisonship`), headlamp off; compare the hold with OpenMW at the same
position, heading and time.

## Repair

A per-cell bake profile (`interior_lighting.CELL_PROFILES`, used by every interior converter
through `cell_lighting`; cells without an entry bake byte for byte as before). The ship's entry:

- the original attenuation (`falloff: original`, [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md): a third
  at the radius, fading out by twice the radius) and the facing term (a face turned away from a
  lamp gets none of it, as in the original);
- two box zones at the start end of the hold (local y below 0, soft edge 24 units): all light at
  0.71 and the ambient at a further 0.35, so the lanterns stand out of a darker hold. The 0.71
  was chosen from an in-game sweep of the static light multiplier on the re-baked map;
- warm faces and glowing lantern glass ([OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md)).

The wood colour asked for on 7 October (a warm table for the whole hold from its ambient colour)
is not part of this repair: only lantern-lit faces take the warm table.

## Verification

FS-UAE, standard profile, headlamp off, clock 12:00, start pose (local 0 -35 5): v0.0.32 image
(A) against the same image with the changed engine and the re-baked ship map (C), and OpenMW at
the same pose. Mean luma of the 3D view:

| View from the start | A v0.0.32 | C repaired | C / A | OpenMW | C / OpenMW |
| --- | --- | --- | --- | --- | --- |
| North (`aw_aim 90 0`) | 25.3 | 14.3 | 0.57 | 15.2 | 0.94 |
| Lantern (`aw_aim 51 -20`) | 31.5 | 12.8 | 0.41 | 13.0 | 0.98 |
| Jiub (`aw_aim 76 0`) | 27.3 | 15.1 | 0.55 | 14.6 | 1.04 |
| East (`aw_aim 0 0`) | 20.5 | 9.9 | 0.48 | - | - |
| South (`aw_aim 270 0`) | 12.8 | 6.1 | 0.47 | - | - |
| West (`aw_aim 180 0`) | 17.6 | 9.1 | 0.51 | - | - |

Mean over the six start views: 0.50 of v0.0.32; the three views also captured in OpenMW are 0.94
to 1.04 of the original. Tests: `tests/test_ship_light.py` (the profile, the zones, the original
falloff and facing term, every other cell's bake unchanged against the previous bake over random
faces).

## Prevention

The ship's start poses are in the original-versus-AmiWind capture set; cell lighting choices live
in one tested table.

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
- [LIGHT-STYLES-UNDEFINED-33](LIGHT-STYLES-UNDEFINED-33.md): The flicker and pulse lightstyles of the light design are never defined, and styles below 32 dim with daylight
- LIGHT-UV-DISTANCE-29 (no report page): Texture scale changes dynamic-light reach on surfaces
- [NIGHT-0400-DARK-31](NIGHT-0400-DARK-31.md): Exterior suddenly much darker around 04:00
- [NIGHT-RUST-31](NIGHT-RUST-31.md): Night tint rounds dark colours to rust-red speckle
- [NPC-LIGHT-COHERENCE-32](NPC-LIGHT-COHERENCE-32.md): Characters are lit by the floor below them, not by the light where they stand
- [OPENING-JIUB-LANTERN-32](OPENING-JIUB-LANTERN-32.md): The lantern above Jiub gives no warm light and hides its candle
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
