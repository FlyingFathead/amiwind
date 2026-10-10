# BUILD-HARVEST-NOT-BUILT-32: Mushroom harvest data is not built by the builder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | builder harvest stage (tools/harvest_build.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | high: A from-scratch build ships no harvestable mushrooms. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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

Fixed in source on v0.0.32-harvest (not shipped at the time of writing; a finished from-scratch image is still to
confirm it). Owner decision 8 October 2026: a default builder step for every map family, with the
Seyda Neen catalogues regenerated against the maps the build ships. Found by the builder defaults
audit (every option and stage compared with the v0.0.31 payload).

## Symptom

v0.0.31 ships 371 `id1/harvest-*.txt` (world, Seyda Neen, Balmora, docks) and 11
`progs/harvest/*.mdl`, made only by a standalone chain (`prepare_harvest.py`,
`prepare_harvest_alias.py`, `prepare_harvest_room.py`) that needs a private harvest plan. No builder
step writes them; a from-scratch build has no harvestable mushrooms.

## Where

The harvest preparation tools (standalone); no builder step.

## How it happened

Harvest was prepared outside the builder and carried forward in patched images.

A hand step also hid a builder gap: the v0.0.29 harvest chain worked only because Balmora's 134
baked mushrooms (17 maps) were removed by hand. The builder's own Balmora maps bake all 134 as brush
entities, so a builder-made image with harvest would have failed the geometry gate (or doubled the
plants) without that hand step. The image step now removes them (`clear_baked`, commit 0331f76).

## Why it was not caught

Release images were patched from earlier images instead of being built from scratch
(BUILD-NOT-FROM-SCRATCH-32), so a missing builder stage never showed, and the hand removal in
Balmora was never written down as a builder step.

## Reproduction

A from-scratch build with the repository builder; compare its payload with v0.0.31.

## Repair

What the shipped data was, traced from the release payloads: the 371 catalogues (AWH4) and 11 shared
models were assembled for v0.0.29-rc1 from three separate conversions and carried forward unchanged;
the plan ("AmiWind external harvest plan 1") is derivable from the player's own data and the
builder's outputs; the admitted map set and a Seyda Neen trial catalogue were not
(HARVEST-PILOT-SHIPPING-32), and the Seyda Neen catalogues were stale (HARVEST-SEYDA-STALE-32).
The repair makes all of it in the builder (`tools/harvest_build.py`,
[EXTERNAL_HARVEST_MODELS.md](../EXTERNAL_HARVEST_MODELS.md#builder-step)):

- New default builder stage `harvest` (`harvest_build.py prepare`, after `census`, which writes the
  scene palette): every exterior original small-mushroom placement of the master is checked with
  the catalogue graph rules, exported once (`prepare_scenery.export_refs`, 32-pixel materials) and
  each model converted once against the image's final palette (`prepare_hand_catalog.runtime_palette`,
  the same derivation the hand catalogue uses). Settings as shipped: 256 plants per map (the
  runtime bound), interned root spans, per-map model registries. No plan input.
- Image step, before the final map passes (`clear_baked`, hook in `build_aga.py image`): brush
  mushrooms a converter baked into a map where a harvestable plant goes are removed with
  `tools/remove_harvest_geometry.py` (exact reference and pose; every surviving surface and hull
  verified). Only Balmora's converter bakes them; v0.0.29 removed them by hand.
- Image step, after the last map change (`install`, hook in `finalize_image` after the map
  optimisation, before the entity tracker, heap audit and content fingerprint): the plan comes
  from the region directories the image ships (`world/regions.awr`, `seyda-regions.txt`,
  `balmora-regions.txt`, the intro docks route bounds); the geometry gate runs on every candidate's
  final map (HARVEST-GEOMETRY-GATE-32); admission is the repository heap check
  (`check_world_map_heap.inspect_maps`, new `only` filter) run on the candidate maps with their
  catalogues installed; refused maps keep no catalogue, unused models are dropped, and a map whose
  baked mushrooms were removed must be admitted or the build stops. Receipts:
  `image/harvest/harvest-plan.json`, `harvest-staging.json`, `harvest-baked-removal.json`;
  `build.json`, `build-state.json` and `build-summary.json` record `harvest`.
- `--no-harvest` is a DEBUGGING ONLY opt-out with a warning (pattern of `--no-npc-gallery`).
- `config/release-features.json`: the `harvest` feature names the `harvest` step and the
  `--harvest` image option; the list of known builder gaps is now empty.
- `tools/entity_tracker.py` counts the plants of each map's harvest catalogue as placed (before,
  catalogue plants did not count, and removing Balmora's baked mushrooms would have read as a loss:
  [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md)).

## Verification

Measured on owned data (GOG master) with the repository code, on the final maps of the dev1
image stage (Seyda Neen sub-cells and intro docks are the recorded v0.0.31 maps of the
BUILD-SEYDA-REGEN-30 exception, after the image passes):

- Harvest step: 934 exterior placements, 8 shared models, byte-identical to v0.0.31's 8 non-pilot
  models; the derived palette equals v0.0.31's final palette.
- Image half: 2,661 exterior maps considered, 388 cover plants, 381 admitted with 8,023 plants
  (v0.0.31: 371 catalogues; v0.0.29: 347 of 390 maps admitted). Plants per admitted map: 1 to 77,
  median 19 (world up to 77, Seyda Neen up to 25, Balmora up to 10). Refused by the heap check:
  sn018, sn019, sn020, sn021, sn026, sn035, sn055 (see HEAP-SEYDA-OVERLAP-32 and
  [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): six of them had harvest in
  v0.0.31); minimum clearance of an admitted map 28,780 bytes. Opt-in towns get none
  ([HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md)).
- Against v0.0.31's catalogues: all 308 world, all 17 Balmora and the intro docks catalogue are
  byte-identical; the Seyda Neen catalogues are regenerated (HARVEST-SEYDA-STALE-32).
- Balmora: 134 baked mushrooms in 17 maps removed; without the removal the geometry gate stops on
  exactly those 17 maps.
- Byte-identical at `--jobs` 2 and 16 (every model, catalogue, changed map and receipt). Time at
  16 jobs: harvest step 20 s, removal 12 s, image install 21 s.
- `tests/test_harvest_build.py` (synthetic data): plan and catalogues from the master and the
  staged region tables, heap admission, geometry gate failures, removal, palette and master
  binding, byte-identical output for every `--jobs`, hook order in the image step;
  `tests/test_release_coverage.py` and `tests/test_build_defaults.py`: default step, image
  option, `--no-harvest` classified, empty gap list. Full suite green in Docker.
- Pending: a finished from-scratch image compared file by file with v0.0.31.

## Prevention

`config/release-features.json` maps every file class v0.0.31 ships to a feature and its default
builder steps; `tests/test_release_coverage.py` fails when a shipped class has no feature or a
feature's step is not in the default build, and the list of known builder gaps (now empty) may
only shrink. `tools/payload_coverage.py check` compares a built payload or staged image with the
release, by feature, for the from-scratch gate. The harvest data is rebuilt from the final maps in
every image, so it cannot drift from the maps it ships with.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions

<!-- END GENERATED CATEGORY -->
