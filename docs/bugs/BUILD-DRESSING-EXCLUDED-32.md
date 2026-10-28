# BUILD-DRESSING-EXCLUDED-32: The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Mesh converter append_meshes (tools/prepare_mesh_bsp.py), Seyda Neen interiors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.32 |
| Severity | high: Converter dropped six dressing pieces without a receipt. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
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

## Status: 8 October 2026

Open: repaired in source (v0.0.32-dressing-receipts), not yet in a built image. Found in the
v0.0.32-dev1 census of the Census and Excise Office (maintainer question about one entity fewer than
v0.0.31). Project decision (8 October 2026): A, the Seyda Neen interiors keep their dressing, with a
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

Project decision A, in source:

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- ACTOR-MOVING-RUNTIME-GROUND-48 (no report page): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- BUILD-AWF-AWS-EXTENSION-CLASH-54 (no report page): New fog and smoke tables took the extensions .awf and .aws, which already mean font and sprite: the palette overlay parsed the fog table as a font
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- IMAGE-WORLD-BATCH-PAIRS-52 (no report page): The image stopped writing a world partition: the boot units moved off DH0 (source, volume path pairs) were turned into paths before the pairs were read
- INTERIOR-ACTIVATORS-LEFT-OUT-52 (no report page): Interiors leave out every activator but the beds: the heart of Lorkhan is missing from Akulakhan s Chamber, and bar counters, shrines and Dwemer machinery from hundreds of rooms
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- MINIWIND-EXTERIOR-CHIM-INTERIORS-52 (no report page): An exterior MiniWind stops in its image step: the image is told to install the CHIM interior store that the exterior scope does not build
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-NPC-GROUNDING-48](ROOM-BATCH-NPC-GROUNDING-48.md): The residents of rooms no town list holds have no grounding class: --room-batches 5 is refused (62 NPCs in 22 rooms)
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative
- VIVEC-HOVER-VERIFY-48 (no report page): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect

Related bugs in other categories:

- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch

<!-- END GENERATED CATEGORY -->
