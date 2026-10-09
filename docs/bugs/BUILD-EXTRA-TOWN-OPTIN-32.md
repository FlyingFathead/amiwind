# BUILD-EXTRA-TOWN-OPTIN-32: A default build leaves out the Vivec Arena preview that v0.0.32 ships

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | default build (tools/build.py town selection) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1, v0.0.32-dev2 (last seen) |
| Severity | high: A default build silently leaves out the Vivec Arena preview that v0.0.32 ships (19 files). |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line, not shipped at the time of writing. Found by the CHIM
builder's payload measurement of the v0.0.32-dev1 image.

## Symptom

v0.0.32 ships the Vivec Arena as an outside-only preview, but a default `build.sh` /
`tools/build.py` run does not make it, and `tools/payload_coverage.py check` on the dev1 payload
reports 19 files no feature explains: `id1/maps/va000.bsp` to `va015.bsp`,
`id1/maps/vivec_arena.bsp`, `id1/scene-doors-vivec_arena.txt` and `id1/vivec_arena-regions.txt`.

## Where

- `tools/build.py`: towns after Seyda Neen and Balmora were imported only with the opt-in
  `--extra-town TOWN`; the town table (`config/towns.json`) had no way to say a town ships.
- `config/release-features.json` and `config/release-payload-classes.json`: no feature and no
  recorded class for the Arena files.

## How it happened

The Arena was converted as an opt-in town while it was a measurement, and the v0.0.32 dev builds
passed `--extra-town vivec_arena` by hand. When the owner decided that v0.0.32 ships the Arena
preview, nothing moved it into the default build or into the release feature list, the same
pattern as world flora (BUILD-FLORA-OPTIN-32).

## Why it was not caught

The release coverage list was recorded from v0.0.31, which has no Arena, and no test tied the
towns a release ships to the default build. `tests/test_build_defaults.py` classified
`--extra-town` as "opt-in, not shipped", which was true until the owner's decision.

## Reproduction

`tools/payload_coverage.py check` on the dev1 or dev2 payload manifest: 19 files no feature
explains, 4 classes not in the release. `tools/build.py --plan` without `--extra-town`: no
`town-vivec_arena` stage.

## Repair

- Town table: a town after Seyda Neen and Balmora may carry `"shipped_since": "vX.Y.Z"`, the
  release that first ships it; `vivec_arena` has `v0.0.32`. Validated in `tools/town_config.py`
  (a release version, not on Seyda Neen, Balmora or a blocked town); `shipped_extra_towns()` lists
  them in table order.
- Builder (`tools/build.py`, `town_selection`): every real AGA build imports the shipped towns in
  table order, right after Balmora's interiors, then the `--extra-town` towns in command order.
  `--extra-town` of a shipped town has no effect (a note says so). Debugging-only opt-outs, with
  a warning: `--no-extra-town TOWN` (shipped towns only) and `--only-core-towns` (Seyda Neen and
  Balmora only). Contradictory options stop the build before any work. Asset-free dry runs,
  terrain builds and the rc3 image recovery import none. `build-state.json` records
  `extra_towns` and `extra_town_selection`; the build summary footer has an `Extra towns` line.
- Release coverage: feature `extra-towns` with `"towns": "shipped"`; `tools/payload_coverage.py`
  fills in each shipped town's map, region maps, region table, door table and interior maps,
  and its `town-<id>` step, from the town table, so a newly shipped town needs no edit there.
  `config/release-payload-classes.json` now records v0.0.32: the classes of the v0.0.32-dev2
  payload (`classes --recorded-from`), which are v0.0.31's plus the 4 Arena classes; to be
  recorded again from the published v0.0.32 payload.

## Verification

- `tests/test_build_defaults.py` (`ShippedTowns`): the town table ships the Arena; the default
  plan has `town-vivec_arena` after `balmora-interiors` and `door-audio` depends on it;
  `--extra-town vivec_arena` gives the default plan; `--no-extra-town vivec_arena` and
  `--only-core-towns` remove exactly that stage and leave the image command unchanged;
  `--extra-town vivec_foreign` still adds a town that is not shipped; contradictory options exit
  1; dry-run, terrain and recovery import none; receipt and summary record the selection;
  invalid `shipped_since` values are refused. Every `debug opt-out` option is "DEBUGGING ONLY".
- `tests/test_release_coverage.py`: the 19 Arena files belong to `extra-towns` only; a payload
  without them misses the feature and its 4 classes and fails; with them nothing is
  unexplained; marking another town shipped adds its patterns and step.
- Updated: `tests/test_vis_options.py`, `tests/test_builder_stage_entries.py`.
- Removing `shipped_since` from the Arena row (scratch copy in Docker) gives 21 failures and 4 errors in these tests.
- `tools/payload_coverage.py check` on the dev2 payload manifest: no unexplained file, no missing
  feature or class; `extra-towns` 19 files.
- Pending: a from-scratch default build of the release candidate compared with the payload.

## Prevention

Shipped towns are data in the town table, read by both the builder and the coverage check;
`tests/test_build_defaults.py` fails when a shipped town leaves the default build, and the
payload check fails when a payload lacks a shipped town's files.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms

<!-- END GENERATED CATEGORY -->
