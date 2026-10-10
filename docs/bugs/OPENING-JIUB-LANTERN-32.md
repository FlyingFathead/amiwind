# OPENING-JIUB-LANTERN-32: the lantern above Jiub gives no warm light and hides its candle

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | Prison ship lantern (light_com_lantern_02_200_Boat): converter bake and renderer colour table |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: The opening scene's key light reads as a grey box; no gameplay effect. |
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
on the v0.0.32 image with the prison ship map re-baked by the changed converter functions and the
changed engine (see "Verification").

## Symptom

Owner, playing CHIM Preview 1 (v0.0.32 content), opening scene: "a yellow hue to the lamp above
Jiub. I've been talking about the lantern above his head in the prison ship, but it's still not
working as it should." The hanging lantern reads as a grey box; nothing about it looks lit.

## Where

The prison ship map (`tools/prepare_interior.py`, the shared bake in
`tools/interior_lighting.py`, the mesh converter `tools/prepare_mesh_bsp.py`) and the surface
colour table choice in the renderer (`engine/aga/src/r_surf.c`, `R_SurfaceWarm`).

## How it happened

The lantern is `light_com_lantern_02_200_Boat` (radius 200 original units, colour 245 140 40,
flicker slow), hanging at local (20.7, -9.2, 22.6), 50 units above the floor next to Jiub. Three
separate causes, measured on the v0.0.32 image and its maps:

1. Baked light has no colour. Lightmaps hold one brightness per sample and every face is drawn
   with the plain colour table, so the lantern's orange light lands as grey. The warm colour table
   (`aw_light_hue`) existed, but only surfaces lit by a dynamic light (torches, night lamps) and
   night-glowing windows used it.
2. The glass is drawn opaque. In the original the panes (`Tx_window_pane`) are translucent and the
   candle and its flame show through them; the lantern mesh itself has no emissive material
   (EMISSIVE-UNSHIPPED-31). AmiWind draws the panes as solid faces, so the candle and its flame
   (`aw_flame` at 20.15 -8.94 17.77, inside the box) are hidden.
3. The panes were baked like walls: the hook point of the light is inside the lantern, so the
   panes got the full lantern light with no facing term and showed as a flat light-grey box
   (mean luma 50 in the lantern area of the start view looking up, against 26 after the repair).

Quake mechanisms checked first: light entities and ericw light only light the map's own brushes;
the ship's converted objects are baked by AmiWind's own bake, so the colour has to come from the
surface's colour table (Quake has no coloured software lighting) and the glow from the existing
self-lit material marking (`emitN`), both chosen per surface when the surface cache builds it,
never per pixel.

## Why it was not caught

The ship was never compared light by light with the original (OPENING-BRIGHT-31); the earlier
lantern work measured how far the light reached (LIGHT-FALLOFF-31), not what the lantern itself
looks like.

## Reproduction

New Game (or `dbg tp prisonship`), headlamp off, look up at the lantern to the right of Jiub
(`aw_aim 51 -20` from the start).

## Repair

- Warm faces: the bake gives a face the lightstyle 31 (`interior_lighting.WARM_STYLE`, engine
  `AW_WARM_STYLE`) when warm lights add at least 24 light at its centre. The engine shows style
  31 exactly like style 0 (`R_AnimateLight` copies the value) and builds those surfaces with the
  warm colour table (`R_SurfaceWarm`). No extra lightmap, no per-pixel cost; `dbg warm light 0`
  restores the plain table.
- Glowing glass: in cells that opt in (`glowing_glass` in the cell profile), the glass of a
  lantern with a flame inside (texture named like a pane or glass) is marked self-lit at level 7
  (`emit7_` texture, the existing `aw_emissive` path) and takes the warm style.
- The ship's profile (`interior_lighting.CELL_PROFILES['imperial prison ship']`) turns both on;
  every other cell bakes byte for byte as before (test over random faces against the previous
  bake, and the Census office map re-baked with identical lightmaps).

## Verification

FS-UAE, v0.0.32 image (A) against the same image with the changed engine and the re-baked ship
map (C), same start pose (local 0 -35 5), clock held at 12:00, headlamp off, standard profile.
Lantern area of the start view looking up (`aw_aim 51 -20`), mean luma and warmth (mean red minus
blue):

| Frame | Luma | Warmth |
| --- | --- | --- |
| A v0.0.32 | 50.0 | 9.9 |
| C repaired | 26.1 | 10.7 |
| C with `dbg warm light 0` | 25.5 | 6.5 |

The pane now glows warm against a darker hold; switching the warm table off returns the same
frame grey. Tests: `tests/test_ship_light.py` (warm faces only near warm lights and facing them,
glass glow only in the ship and only for panes of lanterns with a flame),
`tests/test_light_grid_native.py` (style 31 shown like style 0 in the real `r_light.c`).

## Prevention

Cell lighting choices live in one table (`CELL_PROFILES`) with tests, and the ship's start poses
are in the original-versus-AmiWind capture set (OpenMW at the same pose).

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
- [OPENING-BRIGHT-31](OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- SKY-MIDNIGHT-29 (no report page): Dense clouds still hide the midnight sky
- [TERRAIN-LIGHT-UNIFORM-32](TERRAIN-LIGHT-UNIFORM-32.md): Open-world terrain lightmaps are nearly uniform
- TORCH-LIGHT-29 (no report page): Torch flames look weak and provide little immediate light
- TORCH-NPC-LIGHT-29 (no report page): Nearby NPCs do not visibly respond to torchlight
- TORCHTEST-DARKNESS-29 (no report page): Torch test room floor stays dim gray at zero light

<!-- END GENERATED CATEGORY -->
