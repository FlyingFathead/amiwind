# AmiWind v0.0.38-dev3 - Lava Is All You Need

Full current-game development playtest using the full-world recipe, normal startup,
supported interiors and NPC gallery. MiniWind remains diagnostic only.

## Candidate changes

- Legacy exterior terrain conversion now includes original lava pools, liquid beds,
  contact entities and ambient sound. Terrain near elevated lava retains finer detail
  so coarse terrain does not bury exposed pools.
- Mesh conversion retains explicit original nonsolid collision markers, including
  fire ferns. Existing native validation covers selected routes, not every cell.
- Nonsolid mesh point hulls now contain an explicit empty node. This corrects a
  candidate-build regression where empty hull roots were read as solid everywhere.
  The rebuilt actor-contact gate restores all 116 grounded placements, retaining
  the same three explicit exceptions as the dev2 control.
- Third-person and vanity camera availability follows the introductory permission
  gate. Current-state regression checks accompany the change.
- Cell progress reporting distinguishes source references, converted geometry and
  deferred gameplay; a green geometry audit does not promise complete game content.

## Known in this build

All exterior CHIM rings 0, 1 and 2 are still a target, not a completed claim.
Coast object omissions, six collision holds, deferred actors and creatures,
unimplemented plant interactions, lava smoke, and measured streaming/performance
work remain open. Interiors may use BSP29, CHIM or both.

- [BUILD-LAVA-COVERAGE-38](../../bugs/BUILD-LAVA-COVERAGE-38.md): legacy lava repair is a candidate; complete packaged pool coverage and owner playtest remain pending.
- [CHIM-FERN-NCO-SOLID-38](../../bugs/CHIM-FERN-NCO-SOLID-38.md): scoped fern crossings do not close all six cell holds.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): coast ownership and missing-object coverage remain unresolved.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): deferred actors and unimplemented gameplay remain distinct from converted geometry.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): nonblocking streaming and measured performance work remain pending.
- [UI-KEY-HELP-STALE-38](../../bugs/UI-KEY-HELP-STALE-38.md): sparse help pages and raw action labels remain; a more readable layout is requested.
- [PLAYER-JUMP-THIRDPERSON-38](../../bugs/PLAYER-JUMP-THIRDPERSON-38.md): the owner reports missing third-person jump animation.
- [WORLD-SLOPE-STUCK-38](../../bugs/WORLD-SLOPE-STUCK-38.md): dev2 terrain trapping reported at cell 7,14; diagnosis pending.
- [WORLD-SHORE-OPEN-GEOMETRY-38](../../bugs/WORLD-SHORE-OPEN-GEOMETRY-38.md): dev2 shoreline objects at cells 6,16 and 6,15 show suspect open geometry; diagnosis pending.

The source inventory accounts for all 349 original exterior lava references.
This count alone does not establish their final packaged presence. The earlier pinned candidate
passed 3,959 source tests with three expected platform skips, compilation and
the baseline native smoke check. Exact-package checks remain separate.

Later candidate changes add seven measured terrain subdivisions and Land Fill
Independence v1 (`dbg land fill 0/1`). Their full source and target gates are
pending; the earlier test count does not certify these changes. Separately,
all 27 lava-bearing CHIM frames passed full-margin geometry, heap, simulated
allocation and stair gates (5,696 stair/ramp checks, 593 advisory findings).
Cell 6,21 needed allocation recovery in the simulation; native checking remains
required. Neither these frames nor the new controls are claimed delivered.

The lava candidate has scoped native and original-game comparison evidence.
Full-package validation and delivery are separate gates. No completed delivery is
claimed by this source preparation. Current issue status is in [BUGS.md](../../BUGS.md).
