# INTERIOR-MORAG-TONG-FPS-43: the Morag Tong Guild interior runs at a very low frame rate

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 17:56 +0300: maintainer pinned the suspect: the big planter tree in the middle, entity 93, func_wall, source ref 378691, model *90 (local 130 -5 18)
- Reported with v0.0.43-dev2 at 2026-10-18 17:57 +0300: maintainer pinned a second suspect: a wooden table, entity 6, func_wall, source ref 65016, model *4 (local 7 125 20): 'feels like polycount 1 million'
- Reported with v0.0.43-dev2 at 2026-10-18 20:12 +0300: maintainer: Vivec Redoran Plaza is a frame-rate killer too; the planter plants (func_wall model *79, ref 466735) should probably be sprites
- Reported with v0.0.44-dev1 at 2026-10-19 13:28 +0300: image step stopped: the Balmora Mages Guild plant sprite was placed but not installed (only Vivec's room installer copied sprites); fixed for every installer

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Morag Tong Guild interior (Angahran's room); the large plant in the middle of the room is a suspect |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | medium: an interior the player must visit is barely playable; no crash |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Status: 18 October 2026](#status-18-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Second room: Vivec, Redoran Plaza, 18 October 2026](#second-room-vivec-redoran-plaza-18-october-2026)
- [Decision and where the rest lies, 18 October 2026](#decision-and-where-the-rest-lies-18-october-2026)
- [Redoran Plaza planters: the A/B plan](#redoran-plaza-planters-the-ab-plan)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Open. Measured on the v0.0.43-dev2 build. The builder rule (plants and static trees of every interior drawn as
sprites) is the default by decision for the project, 18 October 2026, on its own branch and gated; the in-game A/B
(same pose, `dbg rcount`, headlamp off) is still to be run. The meshes that draw the most faces after it are
ranked below.

## Symptom

Inside the Morag Tong Guild the frame rate drops far below other interiors of the same size. The maintainer
pinned the planter ash tree in the middle of the room, with its roots and grass clumps (entity 93, model *90,
source reference 378691, `flora_ashtree_05`), and a wooden table (entity 6, model *4, source reference 65016:
the desk `contain_de_desk_01`), and suggested drawing the plant as a sprite.

## Where

Interior converter (`tools/prepare_area.py`, `tools/prepare_mesh_bsp.py`), every converted interior.

## How it happened

Measured read-only on the dev2 map `bmmoragtong.bsp` (BSP29, 122 models):

- The room has 34,801 faces, 18,521 planes, 2,515 nodes and 3,790 clipnodes; all but 42 faces belong to the
  121 placement models. The world is the six-brush box around the room, so the whole map is **one vis
  leaf**: the visible share from the room centre is 100 %. Every placement in front of the camera is drawn
  every frame (only its bounding box is tested against the view). This is the known interior form of
  [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): 183 of the 197 converted interiors have one vis leaf,
  the other 14 have two.
- The converter does not blow meshes up: every model has slightly fewer faces than its original triangles
  (coplanar triangles merged). The planter tree: 1,475 original triangles in three bark shapes, 1,454 faces
  (4.2 % of the room), 528 planes, 316 clipnodes. Its four grass clumps (`flora_ash_grass_r_01`, nonsolid,
  NCO marker): 60 faces each. The desk: 415 original triangles, 366 faces; its 448 planes and 319 clipnodes
  are its collision (25 convex parts), which the renderer does not walk (a placement is drawn through the
  world's nodes, `r_bsp.c` `R_DrawSubmodelPolygons`), so they cost memory, not frame time.
- The heaviest meshes of the room are the 15 chairs `furn_de_chair_03` (486 original triangles, 458 faces
  each, 6,870 faces: 19.8 %), the room shell corners and the stairs.
- Morag Tong is not an outlier: the median converted interior has 12,545 faces, the largest 45,350 (Vivec,
  Foreign Quarter Lower Waistworks); Morag Tong is 13th of 197.

## Second room: Vivec, Redoran Plaza, 18 October 2026

The maintainer called Vivec, Redoran Plaza (map `vri003`) "a framerate killer" and pinned model *79 (source
reference 466735). Measured read-only on the dev2 map:

- 21,002 stored faces, 28,734 planes, 5,663 nodes, 13,686 clipnodes, 117 models; one vis leaf. Placements that
  share a model are drawn once each, so the room draws 26,044 faces (151 placements); Morag Tong draws 35,125.
- *79 is no plant: `ex_vivec_g_r_02`, a Vivec wall piece, 132 original triangles, 105 faces (330 planes and 254
  clipnodes of collision).
- The plants that cost are the 27 tramaroot planters (`contain_tramaroot_01` to `_06`, 330 to 426 original
  triangles each, converted at about their original count): 10,337 faces, 39.7 % of the room. They are
  containers (the tramaroot can be picked), so the sprite rule keeps their meshes and picks.
- The sprite rule draws the 24 grass clumps (`flora_ash_grass_b/r/w_01`, 60 faces each) as sprites: 1,440
  faces, 5.5 % of the room. The four scathecraw plants (containers, 680 faces) keep their meshes.
- Other heavy meshes: the plaza shell `in_v_plaza_01` (2,176 triangles, 1,924 faces) and ten street lights
  (151 faces each, 1,510).

The tramaroot planters need their own step: a per-mesh recipe (pot and roots reduced, the pick kept) or the
planted part as a sprite on a kept container, each as a measured A/B.

## Decision and where the rest lies, 18 October 2026

Decided for the project, 18 October 2026 (the maintainer): plants and trees in interiors become sprites by default
(`AMIWIND_INTERIOR_PLANTS` auto, `tools/interior_plants.py`); the earlier rules stay selectable. "Let's see where
the rest of the poly-excess lies after that": all 197 converted interiors of v0.0.43-dev2 draw 3,256,404 faces
(every placement counted); the sprite rule takes 84,672 of them, leaving 3,171,732. The 20 meshes that draw the
most of the rest (1,151,368 faces, 36 %), with the step of the interior procedure that fits each:

| # | Mesh | Record | Copies | Faces drawn | Original triangles | Faces each | Step that fits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `i/in_velothismall_hall_01.nif` | STAT | 316 | 118,816 | 520 | 376 | room shell: per-mesh visual recipe (collision kept), then sections at doorways |
| 2 | `d/in_velothismall_ndoor_01.nif` | DOOR | 359 | 105,187 | 340 | 293 | door: per-mesh visual recipe keeping the door and its collision |
| 3 | `f/furn_de_chair_03.nif` | STAT | 225 | 103,050 | 486 | 458 | furniture: per-mesh recipe (ratio 0.2 measured: 458 to 150 faces) |
| 4 | `l/light_de_lamp_01.nif` | LIGH | 323 | 85,595 | 280 | 265 | lamp: per-mesh recipe keeping the light entity |
| 5 | `x/ex_vivec_waterspout_02.nif` | STAT | 318 | 67,098 | 248 | 211 | per-mesh recipe (14 Vivec rooms) |
| 6 | `f/furn_de_tapestry_10.nif` | STAT | 387 | 65,403 | 208 | 169 | flat hanging: flattened panel (surface_flatten visual_panel) A/B |
| 7 | `o/contain_com_sack_02.nif` | CONT | 330 | 64,680 | 196 | 196 | container: container-keeping reduction (mesh and pick kept) |
| 8 | `o/contain_barrel_01.nif` | CONT | 214 | 56,924 | 336 | 266 | container: container-keeping reduction |
| 9 | `f/furn_de_tapestry_07.nif` | STAT | 325 | 54,925 | 208 | 169 | flat hanging: flattened panel A/B |
| 10 | `i/in_sewer_pillar00.nif` | STAT | 286 | 50,336 | 204 | 176 | room shell: per-mesh recipe, then sections |
| 11 | `i/in_velothilarge_con_01.nif` | STAT | 55 | 44,660 | 905 | 812 | room shell: per-mesh recipe, then sections |
| 12 | `i/in_sewer_bcorr3_00.nif` | STAT | 38 | 43,016 | 692 | 1132 | converter grows it to 1.6x its triangles: find the face split first (a converter fix), then recipe |
| 13 | `i/in_hlaalu_room_corner.nif` | STAT | 109 | 42,183 | 437 | 387 | room shell: per-mesh recipe, then sections |
| 14 | `i/in_v_s_int_corner_01.nif` | STAT | 517 | 39,292 | 100 | 76 | small shell piece (76 faces), many copies: sections |
| 15 | `i/in_hlaalu_hall_corner_01.nif` | STAT | 111 | 37,851 | 402 | 341 | room shell: per-mesh recipe, then sections |
| 16 | `f/furn_de_tapestry_02.nif` | STAT | 219 | 37,011 | 208 | 169 | flat hanging: flattened panel A/B |
| 17 | `i/in_velothismall_dj_01.nif` | STAT | 417 | 35,028 | 102 | 84 | small shell piece (84 faces), many copies: sections |
| 18 | `l/light_paper_lantern_01.nif` | LIGH | 191 | 34,762 | 194 | 182 | lamp: per-mesh recipe keeping the light entity |
| 19 | `o/contain_com_basket_01.nif` | CONT | 228 | 33,288 | 146 | 146 | container: container-keeping reduction |
| 20 | `f/furn_de_bookshelf_01.nif` | STAT | 77 | 32,263 | 452 | 419 | furniture: per-mesh recipe |

Most meshes keep 80 to 95 % of their original triangles (coplanar triangles merged). The exception is
`in_sewer_bcorr3_00`: 1,132 faces each from 692 triangles, the only mesh in the top list the converter grows.
The repeated furniture, tapestries and room shell pieces are the per-mesh recipe step; containers need a
reduction that keeps the container; the many small shell pieces only shrink with sections.

## Redoran Plaza planters: the A/B plan

The 27 tramaroot planters of Redoran Plaza (10,337 faces, 39.7 % of the room) are containers you can pick from,
so they keep their meshes. Two measured options, same room, same pose, `dbg rcount`, headlamp off, clip:

- **A: reduction that keeps the pick.** A per-mesh visual recipe for `contain_tramaroot_01` to `_06`
  (`config/visual-recipes.json`, interior scope): the visual mesh reduced (ratio 0.5 and 0.2 tried), the original
  mesh kept as collision, the container record and its pick unchanged. Measure faces, the planter's outline
  against the original in OpenMW, and that the pick still opens the container.
- **B: the plant as a sprite on a kept container.** The planter split by its NIF shapes: the pot stays a mesh
  (the container, its collision and pick), the plant shapes become a shaded sprite with the outline from its
  alpha (the interior plant sprite). Measure faces, sprite slots (one per mesh and light step), and the look from
  the room's walkways.

Both are converter changes behind a switch, the current mesh kept selectable; the one the maintainer picks from
the A/B becomes the default for every tramaroot planter on the island (they are not only in Vivec).

## Why it was not caught

The builder checks interiors against their model, heap and coordinate limits, not against a face or frame
budget; plants became sprites only in rooms over the model limit.

## Reproduction

In v0.0.43-dev2, enter the Morag Tong Guild and look towards the planter in the middle of the room;
`dbg rcount` counts the faces drawn.

## Repair

Step 1 of [Interiors over a limit](../INTERIOR_SECTIONS.md#interiors-over-a-limit-the-order), extended to every
room (`tools/interior_plants.py`, `AMIWIND_INTERIOR_PLANTS`):

- `auto` (new default): in every converted interior the nonsolid static plants are sprites (the existing
  shaded sprite of the world flora, outline from its alpha), and so are the static trees; a tree that is solid
  in the original keeps its collision as a collision-only model (the CHIM sprite recipe's rule).
- `plants`: plants only; `over-limit`: the v0.0.42 rule; `meshes`: every plant a mesh.

A/B/C on the planter (faces, converter measured on the dev2 source): A today 1,694 faces (tree 1,454 + grass
240); B mesh reduction of the tree (ratio 0.2) 761 faces (tree 521); C sprites (tree and grass) 0 faces, five
sprites, the tree's 16 collision parts kept. The tree's NIF has no separate root part (three bark shapes,
each spanning the trunk), so "trunk as geometry, roots as sprite" would need a cut by height.

Island-wide (all 197 dev2 interiors): nonsolid static plants are 397 placements, 78,502 faces in 74 rooms;
static trees 10 placements, 8,121 faces in 6 rooms; harvestable plants (460 placements, 82,123 faces) keep
their meshes and picks. That is 2.7 % of the 3,175,563 interior faces: the sprite rule alone does not make
Morag Tong fast. The larger levers, each a measured A/B: per-mesh visual recipes for the repeated furniture
(chairs at ratio 0.2: 150 faces each, 4,620 faces saved in this room) and occlusion inside rooms.

## Verification

`tests/test_interior_limits_steps.py`: the modes, the tree rule (a solid tree keeps a collision-only model, a
nonsolid one is skipped, a usable one keeps its mesh) and the room converter's wiring. In-game A/B pending.

## Prevention

A per-room drawing-cost check in the builder next to the existing interior limits (a face budget in the room
receipt, to be added with the furniture recipes).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- DEMOWIND-54 (no report page): Requested: DemoWind, a small fullscreen AGA build with only cheap animated effects, browsed one by one
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-CEILF-PER-EDGE-36](ENGINE-CEILF-PER-EDGE-36.md): R_EmitEdge calls the C library ceil twice per edge
- [ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md): The 68040 build converts every drawn surface's gradients to fixed point that nothing reads
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-FPCR-DANCE-36](ENGINE-FPCR-DANCE-36.md): Every float-to-int conversion in the engine saves, changes and restores the FPU control register
- ENGINE-RTG-SLOW-PATH-52 (no report page): With a graphics card installed the engine picks an RTG screen, then draws it through the slow generic path: the direct CyberGraphX copy is switched off
- [ENGINE-UPSTREAM-ASM-UNUSED-36](ENGINE-UPSTREAM-ASM-UNUSED-36.md): The engine is built without AmiQuake's 68k assembly: spans, fixed point and maths run as C at -O1
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): Upstream AmiQuake's assembly D_DrawSpans8 has the shape of the sprite span loop; it never runs at the default d_subdiv16 1
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- [INTERIOR-FAR-BLANK-MANOR-56](INTERIOR-FAR-BLANK-MANOR-56.md): In Ald'ruhn's Manor District the far parts appear as blank spots instead of fading into dark grey, and the room is slow
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [PERF-ARENA-PIT-SLOW-48](PERF-ARENA-PIT-SLOW-48.md): The Vivec Arena Pit runs slowly: a large interior with heavy drawn and collision geometry
- [PRISON-SHIP-RENDER-COST-56](PRISON-SHIP-RENDER-COST-56.md): The prison ship's hold draws slower than the Vivec Arena Pit: frame rate dips in the opening room
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera
- SKEL-16MB-TRAP-52 (no report page): With skeletal actors the game stops loading Balmora at 16 MB of Fast RAM with a software failure (error 80000027); the baked build loads
- SKEL-RUNTIME-COST-52 (no report page): The skeletal prototype poses every vertex twice a drawn frame, with three divisions and three float-to-integer conversions each: it must cost what a baked frame costs
- [SPRITE-BAD-TYPE-THREADED-56](SPRITE-BAD-TYPE-THREADED-56.md): R_DrawSprite: Bad sprite type ends a load (dbg aw hors 0) on Amiberry with the threaded CPU: the game stays on Loading
- [TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)

<!-- END GENERATED CATEGORY -->
