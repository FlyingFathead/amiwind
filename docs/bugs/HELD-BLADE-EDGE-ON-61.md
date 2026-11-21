# HELD-BLADE-EDGE-ON-61: A held weapon seen edge-on from behind in third person shows only its hilt: the thin blade draws no pixels

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 5 November 2026, in v0.0.61-dev1 |
| Where | third-person player body at the normal camera distance (48 to 60): item models of tools/npc_items.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.61-dev2 |
| Severity | medium: a drawn claymore looks like a short stick at the hand, so the weapon seems missing from the player hands; NPC weapons share the same models |
| Family | Mesh converter geometry (`converter-geometry`) |
| Playtest version | 2026_11_05_v0.0.61-dev1_full-v0.0.61-dev1_374d59b |
| From commit | source 374d59b, engine 374d59b, CHIM world 374d59b |
| CHIM engine version | CHIM 0.2.2, engine 374d59b, world format unknown |
| Unknown because | the world format of the image was not read for this entry |
| Platform or emulator | FS-UAE, JIT, 68040, 32 MB Fast |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| shipped | a development build | v0.0.61-dev2 | 2026-11-06 | the bug journal entry of 2026-11-06: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered | Set fixed in v0.0.61-dev2: CHARGEN-INVENTORY-LOCKED-60, CHARGEN-NO-STARTING-CLOTHES-60, SERVICE-REFUSAL-UNCLOTHED-60, FP-WEAPON-SWAY-60, HELD-BLADE-EDGE-ON-61, CARRIED-RECORDS-SEARCH-PER-KIND-61, INVENTORY-OPEN-COST-MANY-KINDS-61, TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61, MUSIC-DEATH-TRACK-RANDOM-60, BLANK-PAPER-READ-60, COLLECT-CAPACITY-REJECTED-60 and TOMB-MUSIC-OVER-AMBIENT-60. |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-05: reported in v0.0.61-dev1
- 2026-11-06: v0.0.61-dev2: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered: The points the v0.0.61-dev2 release notes list as not yet seen in game were played on that image at 32 MB Fast in ...
- 2026-11-06: shipped: a development build, v0.0.61-dev2; the bug journal entry of 2026-11-06: The v0.0.61-dev2 image checked in game; CONTAINER-STRIP-OPEN-MANY-KINDS-61 and CREATURE-COMBAT-FRAMES-MISSING-61 registered: Set fixed in v0.0.61-dev2: CHARGEN-INVENTORY-LOCKED-60, CHARGEN-NO-STARTING-CLOTHES-60, SERVICE-REFUSAL-UNCLOTHED-60, FP-WEAPON-SWAY-60, HELD-BLADE-EDGE-ON-61, CARRIED-RECORDS-SEARCH-PER-KIND-61, INVENTORY-OPEN-COST-MANY-KINDS-61 ...

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- [ACTOR-BAKE-NO-SEAM-STOP-68](ACTOR-BAKE-NO-SEAM-STOP-68.md): The creature library's default bake route and the residents' bake run no seam check, so models with open seams and thinned limbs reach the image unjudged
- [ASH-TREE-HOLES-62](ASH-TREE-HOLES-62.md): The reduced-polygon ash tree in the Ashlands shows holes in its surface
- [ATRONACH-FLAME-MESH-62](ATRONACH-FLAME-MESH-62.md): The flame atronach's reduced mesh is broken and it has no flames
- [AW-20260928-21](AW-20260928-21.md): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- BALMORA-GROUND-DENTS-51 (no report page): Sharp V-shaped dents in Balmora s ground beside the canal wall (cell -3,-2), reported by the maintainer as back
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- [CANDLESTICK-CANDLES-FLOAT-67](CANDLESTICK-CANDLES-FLOAT-67.md): The candles of the three-candle Silver Candlestick do not touch the holder and seem to float
- [CENSUS-SHELF-PLATE-BAKED-67](CENSUS-SHELF-PLATE-BAKED-67.md): Census and Excise Office: a plate on the bookshelf is drawn as part of the room and cannot be taken, although in the original it is a separate item
- [CHIM-CAVE21-NONCONVEX-FACE-48](CHIM-CAVE21-NONCONVEX-FACE-48.md): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- [CHIM-COLLISION-ROOM-FILLED-54](CHIM-COLLISION-ROOM-FILLED-54.md): One convex collision piece fills the room above a floor of the same mesh: seven trapdoors and a Redoran hut door cannot be used
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- [CHIM-DOOR-TERRAIN-COARSE-54](CHIM-DOOR-TERRAIN-COARSE-54.md): The 128-unit terrain tiles bridge the dip a door sits in: two Dwemer doors have ground 170 to 190 units above the threshold
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
- [CREATURE-MESH-HOLES-62](CREATURE-MESH-HOLES-62.md): The Alit model has a hole in its upper torso, and the inspect line shows health 0.0 while it fights
- [EXPANSION-ROOMS-REFUSED-66](EXPANSION-ROOMS-REFUSED-66.md): Seven expansion rooms are not converted: the room stage refuses them
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- [GHOSTFENCE-NO-ANIMATION-46](GHOSTFENCE-NO-ANIMATION-46.md): The Ghostfence's shimmering curtain does not move: its texture scroll is dropped by the converter
- [INLAND-SHORE-29](INLAND-SHORE-29.md): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LAVA-POOL-NOT-LAVA-NAMED-66](LAVA-POOL-NOT-LAVA-NAMED-66.md): The hot-oil pools of two Sotha Sil rooms were refused as lava pools without upward lava faces, so both rooms were not converted
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-REDUCTION-SEAMS-62](MESH-REDUCTION-SEAMS-62.md): Reduced actor models lose seams and thin their limbs, and nothing compared them with the original
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [PRISON-SHIP-TABLE-DARK-TRIANGLE-67](PRISON-SHIP-TABLE-DARK-TRIANGLE-67.md): A large dark triangle lies across the table in the prison ship hold
- [ROOM-EFFECT-MODEL-NO-TRIANGLES-66](ROOM-EFFECT-MODEL-NO-TRIANGLES-66.md): A summoning effect model without drawn triangles refused the whole Dome of Sotha Sil room
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- [SEAM-AUDIT-IGNORES-RIM-TEARS-54](SEAM-AUDIT-IGNORES-RIM-TEARS-54.md): The seam audit reports meshes with torn rims as ok
- [SKY-GROUND-28](SKY-GROUND-28.md): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes
- [TOWN-PAVEMENT-WEDGE-62](TOWN-PAVEMENT-WEDGE-62.md): A wedge of pavement sticks up from the street in Suran, the same kind of fault as once seen in Balmora
- [WEREWOLF-HEAD-NOT-REDUCED-68](WEREWOLF-HEAD-NOT-REDUCED-68.md): The outer-measures reduction leaves the werewolf's head whole at every target and reports that as a pass

Related bugs in other categories:

- [PLAYER-EQUIPMENT-NOT-WORN-54](PLAYER-EQUIPMENT-NOT-WORN-54.md): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks

<!-- END GENERATED CATEGORY -->
