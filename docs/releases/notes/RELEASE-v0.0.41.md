# AmiWind v0.0.41: More Fixes, Fewer Planes (A Telvanni Root Story)

Running on CHIM Engine v0.2.1, world format 0.7. Previous release: [v0.0.40](RELEASE-v0.0.40.md).

The first regional CHIM release. Rings 0 to 4 of Vvardenfell, from the sea inwards, are on CHIM. So are two whole
Morrowind regions, the Bitter Coast and Azura's Coast, with their towns: Seyda Neen, Balmora, the whole city of
Vivec, Hla Oad, Sadrith Mora and Vos. "Fewer planes": the collision behind large irregular meshes now compiles into
compact hulls instead of chains of thousands of separate planes. The Telvanni roots and towers that did not fit
the memory budget fit now.

## What is in this release

- 723 cells on CHIM: 619 land cells, 99 seabed cells and 5 open-sea cells, each converted from your own copy of
  Morrowind. The rest of the island is in the classic world as before; the [CHIM Progress Tracker](../../chim/PROGRESS_TRACKER.md)
  shows which cell is which.
- Every CHIM cell passes the builder's checks before it ships. Those checks cover its memory budget, its stairs and
  ramps (walked with the player's box), its seams to the neighbouring cells, the residents standing on the ground,
  and the harvestable plants and other objects counted against the previous release.

## What changed since v0.0.40

- **Regions, not rings.** A build takes whole Morrowind regions (`tools/chim_cell_list.py --region`), so towns are
  no longer cut at the edge of the CHIM area. Rings still set the order: the coast first, then inwards.
- **Rings 3 and 4.** The cell list comes from the progress tracker. Cells not ready yet stay in the classic world
  by name, together with the neighbours that keep them from being enclosed by CHIM cells (`--open-pockets`).
- **Collision that compiles.** When the collision compiler refused a large irregular mesh (Ashurnibibi's ruins,
  Telvanni roots, Dwemer ruins), the mesh kept a raw chain of collision pieces. The refusal is now retried with
  coplanar facets merged, and every fallback is logged with its reason
  ([CHIM-COLLISION-UNION-FALLBACK-41](../../bugs/CHIM-COLLISION-UNION-FALLBACK-41.md)).
- **Telvanni towns on a memory budget.** A per-mesh recipe for Sadrith Mora and Vos and their surroundings reduces
  the roots, the slave market, the boats, the doorways, the turret, the tower, the manors and the house pods; two
  large roots get coarser collision.
- **Vos.** A walkway stair that runs under the Velothi temple's base no longer starts inside the temple's collision:
  the temple keeps its own collision surfaces ([CHIM-VOS-TEMPLE-WALKWAY-41](../../bugs/CHIM-VOS-TEMPLE-WALKWAY-41.md)).
- **Harvestable plants on CHIM region cells.** Region cells now get and keep their own harvest catalogues; before,
  their mushrooms were only placed while an old neighbouring map still carried them. 229 plants that were placed
  nowhere are back, and an island-wide check fails the build if any plant is missing
  ([HARVEST-CHIM-REGION-LOSS-41](../../bugs/HARVEST-CHIM-REGION-LOSS-41.md)).
- **Residents at the edge of Vivec.** Each resident belongs to one town frame only (Nels Llendo was placed by both
  Vivec and Seyda Neen); ground under residents keeps Morrowind's own height samples; an actor the normal search
  cannot stand on the ground is searched a little wider, without moving anyone else
  ([CHIM-VIVEC-FRAME-WIDE-41](../../bugs/CHIM-VIVEC-FRAME-WIDE-41.md)).
- **The Dunmer streetlight** is replaced by a simple lantern model everywhere.
- **Seabed cells.** Land records that lie entirely under water are converted as their own CHIM cells instead of being
  taken for open sea, and the build names any such cell it cannot place
  ([CHIMPORT-OCEAN-LAND-41](../../bugs/CHIMPORT-OCEAN-LAND-41.md)).
- **Seyda Neen** builds as a CHIM town from your data, with its giant mushrooms and closed seams.
- **Lava regions within the storage budget.** Two more lava terrain regions are split, and the scenery stage names
  every over-budget region in one pass ([BUILD-LAVA-TERRAIN-BUDGET-38](../../bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md)).
- **Audits that say how old they are.** Every audit result records when it ran, with which AmiWind and CHIM version
  and which converter. A build that refuses a cell says so and how to measure it again
  ([CHIMPORT-STATUS-STALE-41](../../bugs/CHIMPORT-STATUS-STALE-41.md)).
- **The builder names every frame over the memory budget**, and by how much.
- **The Guard marker** is back at the lower right; `dbg landfill on/off` switches the distant land layer.
- **Toolkit.** The World Map can paint and copy cell selections (shift-drag for a rectangle), and the toolkit server
  can serve any built CHIM world to the map inspector.

## Known in this build

- [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md): two banner-draped giant mushrooms at Vivec's entrance show
  open cap bands.
- [INTERIOR-CREATURES-MISSING-41](../../bugs/INTERIOR-CREATURES-MISSING-41.md): no creature is placed in any interior yet;
  among others, the demigod Vivec is missing from his palace.
- [CHIM-STATICS-FALLBACK-41](../../bugs/CHIM-STATICS-FALLBACK-41.md): if a town frame's CHIM world cannot load, the map
  stops instead of running without its chunks.
- [ENGINE-060-FSCC-41](../../bugs/ENGINE-060-FSCC-41.md): the engine is built for the 68040; on a 68060 some float
  comparisons go through the CPU library, and their cost is not measured yet ([AmiWind on the 68060](../../68060.md)).

Fourteen of Vivec's 144 interiors are not in this build yet; their doors say the area is unavailable. They are the
first item of [v0.0.42](../../history/plans/PLAN-v0.0.42.md). See the [bug register](../../BUGS.md) for everything else.

## Validation and delivery

One gate on the release commit: the full test suite, the Amiga engine build, and the host parity checks. Then a
full build with the repository builder from the game data, with no private-test waivers. Every CHIM gate passes:
memory, stairs, zone walk, seams, residents, and the entity tracker against the baseline of placed objects. Then a boot smoke of that
image in the emulator: it boots, loads a map and plays. The public source contains no game data. See the
[release workflow](../../RELEASE_WORKFLOW.md) and the [roadmap](../../ROADMAP.md).
