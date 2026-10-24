# GHOSTFENCE-NO-ANIMATION-46: the Ghostfence's shimmering curtain does not move

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46-dev1 |
| Where | the Ghostfence curtain around Red Mountain, e.g. beside Ghostgate (cell 2,4) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46-dev1 (last seen) |
| Severity | medium: a landmark of the main quest loses its moving curtain; the fence reads as a still wall |
| Family | Mesh converter geometry (`converter-geometry`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_20_v0.0.46-dev1_dev1-try2_e86b1704 |
| From commit | source e86b170, engine e86b170, CHIM world e86b170 |
| CHIM engine version | CHIM 0.2.1, engine e86b170, world format 0.7 |
| Build note | the v0.0.46 playtest the maintainer played on 20 October 2026 (the dev1 playtest build of that evening) |
| Platform or emulator | FS-UAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46 (21 October 2026)._

<!-- contents start -->
## Contents

- [Status: 21 October 2026](#status-21-october-2026)
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

## Status: 21 October 2026

The turbulent curtain is the default of a build from v0.0.47-dev1 (decided for the project, 21 October 2026):
`--chim-uv-scroll turbulent` is what a build does unless it is given `--chim-uv-scroll off`, the still texture of
before. In game, `dbg ghostfence off` (`aw_ghostfence 0`, not saved) draws every turbulent texture straight and
still, and `dbg ghostfence on` ripples it again. Not yet seen in a full build: v0.0.47-dev1 is the first.

20 October 2026: cause found; the repair went into the source behind `--chim-uv-scroll turbulent`, off by default,
checked in game in a fresh play copy and compared with OpenMW.

## Symptom

The maintainer, playing the v0.0.46 playtest: the Ghostfence shows no animation. In the original, the curtain
between the pylons moves all the time, a white-blue shimmer like water and electricity at once. In AmiWind it is a
still picture of that texture.

## Where

Everywhere along the Ghostfence around Red Mountain. The curtain is made of the meshes `x/ex_gg_fence_s_01` to
`_s_04` and `x/ex_gg_fence_s_h_01`, with 67 exterior placements. For example beside Ghostgate, in cell 2,4.

## How it happened

Each curtain mesh is three see-through layers: Material alpha 0.5, emissive 0.3, textures `Tx_GG_fence_01` and
`Tx_GG_fence_02`. Each layer has a NiUVController:

- the texture moves up by one or two texture heights in 8 seconds (V translation keys 0 to 1 and 0 to 2);
- it sways sideways by 0.05 of the texture width (U keys 0, 0.05, 0, -0.05, 0 every 2 seconds).

The layers move at different speeds, and together that makes the shimmer. OpenMW applies these keys to the
texture coordinates over time (rule from OpenMW file `components/nifosg/controller.cpp`, UVController).

The scenery stage (`tools/prepare_scenery.py`) read the shapes, their textures and their materials, but no
controllers. So the CHIM builder turned the curtain into an ordinary lit texture with a glow (`emit3_N`), and
nothing in the engine moved it.

## Why it was not caught

Texture controllers were not on any list of what the converter keeps or drops, and no check compares an animated
original surface with the converted one. Only Quake's own animated texture chains have a bug so far
([CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md)).

## Reproduction

Always. Stand at the Ghostfence beside Ghostgate and look at the curtain between two pylons.

## Repair

Quake already has this kind of surface. A texture whose name starts with `*` is drawn turbulent: `model.c` gives it
`SURF_DRAWTURB`, and `D_DrawTurbulent8` ripples it over time without light, as Quake's water and teleporter fields.
That is the plan recorded in [IDEAS](../chim/IDEAS.md#the-ghostfence-as-a-quake-turbulent-surface).

- **Scenery stage:** a shape's NiUVController U and V translation keys are kept in its material (`uv_scroll`),
  only when they move.
- **CHIM builder:** new setting `uv_scroll`, with `build.py --chim-uv-scroll` and `chim_build.py --uv-scroll`.
  - `off` is the default: a still texture, as before.
  - `turbulent` names such a shape's texture `*scrollN`.
  - Lava keeps its own path. Textures larger than 64 x 64 stay still.
  - Only models with a scrolling texture get a new unit key.
- **Engine:** Quake's turbulent drawing reads a 64 x 64 texture. The curtain's textures are 32 x 32, like 979 of the
  1,131 textures of the v0.0.46 world. The CHIM loader now tiles a 16 or 32 texel turbulent texture to 64 x 64 when
  it loads it (`ChimFormat_TileTurbulent`). Every mip level is the source level repeated, so the faces keep their
  mapping.

The same rule covers every exterior shape whose texture scrolls:

| What | Exterior placements |
| --- | --- |
| The fence | 67 |
| The Vivec waterfalls | 85 |
| The ash mire | 78 |
| The Vivec water plane | 1 |

Differences from the original that remain:

- A turbulent surface is opaque; the original curtain is half transparent.
- It ripples instead of scrolling upwards.
- It ignores the night and the fog. The maintainer chose this "lit from afar" look on 18 October 2026.

The flickering light style for the glow is not done.

## Verification

Done (source, 20 October 2026):

- `tests/test_uv_scroll.py`: the controller keys are kept, the key and name rules, lava and large textures stay
  still, the option reaches the conversion, and the loader wiring.
- `tests/aga_chim_turbulent_test.c`: which textures are tiled, and every mip level checked against the small
  texture's own repetition.
- The engine compiles without warnings.

Done in game, 20 October 2026, in a fresh play copy of the v0.0.46 image:

- The curtain's two textures were renamed in the play copy as the converter names them. No build: the pixels,
  sizes and texture ids are the built ones.
- With the fixed engine, the curtain beside the pylon west of Ghostgate (global 18860 41458) ripples. Frames 3
  seconds apart show its pattern moved.
- With the engine before the fix and the unchanged image, the curtain stands still.
- OpenMW reference at the same place: the half-transparent white-blue curtain.

To do:

- A world build with the turbulent default (v0.0.47-dev1) and a look at the fence, the Vivec waterfalls and the ash
  mire in it.
- `dbg ghostfence off` also stills Quake water in the interiors: it is one switch for every turbulent texture.

## Prevention

The scenery stage now records texture controllers, and the census above lists every scrolling exterior texture.
The next step is a converter check that lists every controller type it drops (NiUVController, NiFlipController,
NiAlphaController) per model.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
- CHIM-ROOM-LAVA-TOP-ROUNDING-48 (no report page): A lava room was kept as a room map: the pool top compared rounded (record -66.55, brush -66.56)
- [CHIM-STRIDER-SCALED-SEAMS-36](CHIM-STRIDER-SCALED-SEAMS-36.md): Seyda Neen's silt strider (scale 0.89 variant) still shows open seams; Balmora's (scale 1.0) is closed
- [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md): Terrain triangle diagonals differ from the OpenMW 0.48 reference
- [CONVERT-COLLISION-FALLBACK-32](CONVERT-COLLISION-FALLBACK-32.md): Five Balmora meshes fall back to a collision union in qbsp
- [CONVERT-DEGENERATE-FACES-32](CONVERT-DEGENERATE-FACES-32.md): The converter writes degenerate faces (no area, slivers, repeated vertices)
- [CONVERT-FACE-PLANE-32](CONVERT-FACE-PLANE-32.md): Converter takes a merged face's plane from its first three vertices
- [CONVERT-FACE-WINDING-32](CONVERT-FACE-WINDING-32.md): Six prison faces are wound opposite to their plane side
- [CONVERT-MERGE-NONPLANAR-32](CONVERT-MERGE-NONPLANAR-32.md): Merged polygons can be slightly non-planar (up to about 0.05 units)
- [CONVERT-QHULL-FLAT-32](CONVERT-QHULL-FLAT-32.md): Collision building fails on a flat mesh (chitin shortbow)
- [CONVERT-TEXCOORD-RANGE-32](CONVERT-TEXCOORD-RANGE-32.md): Converter does not check the 16-bit texture-coordinate range
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [SKY-REDMOUNTAIN-BLUE-44](SKY-REDMOUNTAIN-BLUE-44.md): Inside the Ghostfence at Red Mountain the sky and horizon are clear blue instead of the region's red ash weather

<!-- END GENERATED CATEGORY -->
