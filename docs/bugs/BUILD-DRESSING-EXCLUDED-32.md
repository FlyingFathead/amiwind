# BUILD-DRESSING-EXCLUDED-32: The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt

## Status: 8 October 2026

Open: repaired in source (v0.0.32-dressing-receipts), not yet in a built image. Found in the
v0.0.32-dev1 census of the Census and Excise Office (owner question about one entity fewer than
v0.0.31). Owner decision (8 October 2026): A, the Seyda Neen interiors keep their dressing, with a
heap check, the earlier skip rule kept as an option, and a track of what is added ("keep a track on
what's going"). Prevention: every omission is receipted, and the image step compares its entity
tracker with the last release.

## Symptom

v0.0.32-dev1's `census.bsp` has 136 `func_wall` entities, v0.0.31's 137. The missing one is a
lantern hook (reference 321381, `f/Furn_Com_Lantern_Hook.NIF`) on the wall by a lantern flame; the
flame now hangs without its hook. The v0.0.32-dev3 from-scratch census step lacks it too.

Measured against the whole v0.0.31 payload (all 2,724 maps, entity tracker per cell, 8 October
2026): the v0.0.32-dev2 image places everything v0.0.31 placed except six dressing placements in
three Seyda Neen interiors, all removed by this rule:

| Cell | Category | Placements |
| --- | --- | --- |
| Census and Excise Office | static | 1 lantern hook |
| Arrille's Tradehouse | static | 1 lantern hook |
| Arrille's Tradehouse | plant | 2 ferns |
| Terurise Girvayne's House | plant | 2 grass tufts |

(v0.0.32-dev1 also lacked 914 harvestable plants in 67 exterior cells: dev1 had no harvest step,
BUILD-HARVEST-NOT-BUILT-32; dev2 has them.)

## Where

`tools/prepare_mesh_bsp.py` `append_meshes`: unless the caller passes `retain_dressing=True`,
placements whose mesh path contains `flora_`, `marker_`, `scum_`, `lantern_hook` or `furn_de_rope`
are skipped. The Seyda Neen scene and the interior converters (`prepare_census.py`,
`prepare_interior.py`, `prepare_area.py` outside Balmora) use the default; the world, town, Balmora
region and door overlay converters retain dressing.

## How it happened

The rule dates from v0.0.16 and is unchanged at v0.0.31. The v0.0.31 Census office was not made by
the repository builder (earlier releases patched maps into previous images,
BUILD-NOT-FROM-SCRATCH-32), so it kept the hook; v0.0.32 is the first image built from the
repository, which drops it. The census also differs from v0.0.31 elsewhere in its bytes (not yet
compared).

## Why it was not caught

- The skip left no trace: the placement was in the selected group, but in neither the compiled
  models nor the receipt's `omitted` list.
- The entity tracker only fails against `--entity-baseline`, which the guided build never passed;
  dev1 had no baseline. Its reports held counts per category, and the gate allowed losses below
  10 placements or 5 % per category, so one static could not show.

## Reproduction

Compare the `aw_ref` values of `func_wall` entities in `census.bsp` of v0.0.31 and of any repository
build; or `intro-scene/census-conversion.json`: reference 321381 is in the group's references,
not in `models` and not in `omitted`.

## Repair

Owner decision A, in source:

- The Seyda Neen interior converters (`prepare_census.py`, `prepare_interior.py`, the Seyda Neen
  rooms of `prepare_area.py`) keep their dressing: `INTERIOR_DRESSING` (`flora_`, `scum_`,
  `lantern_hook`, `furn_de_rope`); editor markers stay out (receipted). `append_meshes` takes
  `retain_dressing` as True (keep all), False (skip all) or the fragments to keep.
- The earlier rule stays selectable: `--skip-dressing` (`tools/build.py`, passed to the interior,
  census and area steps; debugging only).
- Track: the image step writes `dressing-track.json` beside the image (private): every dressing piece
  placed in an interior map, per map, with reference, id, model, rule and cell, plus each map's
  modelled heap estimate and gate from `world-map-heap.json`; `build.json` records the piece and map
  counts. Each conversion receipt also lists its retained pieces (`dressing_retained`).
- Heap: the image step's world-map heap gate checks every map with its dressing. The dev2 estimates
  of the three maps that regain the six pieces have ample clearance (Census office 3.1 MB, Arrille's
  Tradehouse 4.1 MB); the inline model budget (220) is far away (136 and 121 models).

Prevention, in source:

- `append_meshes` lists every placement it leaves out in its result's `omitted` with the rule
  (`dressing excluded by the mesh converter (lantern_hook)`); the census, interior and area
  converters merge it into their receipts' `omitted`. The exclusion list is the named constant
  `DRESSING_EXCLUDED`.
- The entity tracker records per cell and category a SHA-256 of the sorted placed reference numbers
  (`placed_digests`); the image build's private report also lists the numbers (`placed_refs`).
  `compare` fails when any cell and category has fewer placements than the baseline, or the same
  number of other placements (same master only), and names the missing references when both sides
  list them.
- `config/entity-baseline.json` (`entity_tracker.py baseline`): the v0.0.31 release baseline, counts
  and digests only, no reference numbers. `tools/build.py` passes it to the image step by default
  (`--no-entity-baseline` is a debugging opt-out; `--accept-entity-loss REASON` records an intended
  loss). Each release replaces the baseline with its own.

With A, a repository image places the six pieces again and passes the baseline; with
`--skip-dressing` it fails on them unless the loss is accepted with `--accept-entity-loss REASON`.
The interiors may also gain dressing that v0.0.31 lacked; the track lists it.

## Verification

- `tests/test_mesh_omissions.py`: every reference handed to `append_meshes` is placed or receipted;
  retained dressing is placed; the three interior converters merge the receipt.
- `config/entity-baseline.json` made from the v0.0.31 payload (2,724 maps, all equal to the
  release readback by SHA-256, with its harvest catalogues); compared with dev2's image report it
  shows exactly the six placements above.
- `tests/test_mesh_omissions.py`: the interior rule keeps hooks, ropes and ferns, omits markers
  (receipted) and lists the retained pieces; `--skip-dressing` restores the earlier rule and reaches
  the interior, census and area steps only.
- `tests/test_entity_tracker.py`: the dressing track lists interior pieces per map with heap rows;
  one missing placement fails with digests; same count with other
  placements fails; gains pass; another master skips the digest check; the private report names the
  references and the baseline holds none; the guided build passes the baseline by default.

- Pending: a from-scratch image with the six pieces back, its dressing track and heap rows.

## Prevention

The two repairs above: no silent converter drops, and every image is compared placement by
placement (per cell and category) with the last release.
