# AmiWind v0.0.41-dev5: More Fixes, Fewer Planes (A Telvanni Root Story)

Development snapshot, 16 October 2026. Running on CHIM Engine v0.2.1. Previous snapshot:
[v0.0.41-dev4](RELEASE-v0.0.41-dev4.md).

The first regional CHIM build: the whole Bitter Coast and Azura's Coast regions join rings 0 to 4, with
Seyda Neen, Balmora, the whole city of Vivec, Hla Oad, Sadrith Mora and Vos on CHIM.

## What changed since v0.0.41-dev4

- **Regions, not rings.** A build now takes whole Morrowind regions (`tools/chim_cell_list.py --region`), so
  towns are no longer cut at the edge of the CHIM area. Rings still set the order.
- **Collision that compiles.** Large irregular meshes (Ashurnibibi's ruins, Telvanni roots, Dwemer ruins)
  kept raw chains of collision pieces when the collision compiler refused them; the refusal is now retried
  with coplanar facets merged, and every fallback is logged with its reason
  ([CHIM-COLLISION-UNION-FALLBACK-41](../../bugs/CHIM-COLLISION-UNION-FALLBACK-41.md)).
- **Telvanni towns on a memory budget.** A per-mesh recipe for Sadrith Mora and Vos (and their surroundings)
  reduces the roots, the slave market and the boats; two large roots get coarser collision.
- **The Dunmer streetlight** is replaced by a simple lantern model everywhere.
- **Audits that say how old they are.** Every audit result records when, with which AmiWind and CHIM version
  and with which converter it ran; a build that refuses a cell says so and how to measure it again
  ([CHIMPORT-STATUS-STALE-41](../../bugs/CHIMPORT-STATUS-STALE-41.md)).
- **The master builder names every frame over the memory budget, and by how much.**

## Known in this build

- [CHIM-VIVEC-FRAME-WIDE-41](../../bugs/CHIM-VIVEC-FRAME-WIDE-41.md): three residents at the edge of the Vivec frame may
  stand off the ground or out of reach; accepted for this private playtest only.
- [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md): two banner-draped giant mushrooms at Vivec's entrance show
  open cap bands.
- [CHIM-STATICS-FALLBACK-41](../../bugs/CHIM-STATICS-FALLBACK-41.md): if a town frame's CHIM world cannot load, the map
  stops instead of running without its chunks.

See the [bug register](../../BUGS.md).
