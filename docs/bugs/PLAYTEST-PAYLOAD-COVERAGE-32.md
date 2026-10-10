# PLAYTEST-PAYLOAD-COVERAGE-32: The v0.0.32-dev1 playtest has no first-person hands and no harvest

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | v0.0.32-dev1 playtest package (hands and harvest files) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | high: The dev1 playtest shipped without first-person hands and harvestable plants; no packaging coverage gate. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open (process). Found by the payload diff of the v0.0.32-dev1 playtest against v0.0.31.

## Symptom

The dev1 playtest build lacks file classes v0.0.31 ships: the 40 first-person hand models
(`.mdl`), `hand-models.awh`, `hand-torch.awt`, the 371 harvest catalogues and the shared harvest
models. In play there are no first-person hands and no harvestable mushrooms.

## Where

The v0.0.32-dev1 playtest package. The builder on the v0.0.32 development line now makes both
classes (BUILD-HANDS-NOT-BUILT-32, BUILD-HARVEST-NOT-BUILT-32).

## How it happened

dev1 was built from a source snapshot (978475d, branched from 5aacdc0) that predates the merges of
the hand-catalog builder step (6741425) and the harvest step (6b9c2ff). A dev build was cut from a
snapshot without re-checking its release coverage against the last release.

## Why it was not caught

No packaging step compares a playtest payload with the last release. `tools/payload_coverage.py
check` exists (it lists missing features and release classes, with `--allow-known-gaps`) and is
tested in `tests/test_release_coverage.py`, but neither the builder (`tools/build.py`,
`tools/build_aga.py`) nor the packaging (`tools/package_dry_run.py`) runs it.

## Reproduction

`tools/payload_coverage.py check` on the dev1 payload manifest: the hands and harvest features and
their release classes are reported missing.

## Repair

Not yet. The fix to make: playtest and release packaging run `payload_coverage.py check` on the
finished payload against the last release, and a missing feature or release class blocks
packaging unless it is listed as a known issue of that build. dev2 and later are built from a
source that contains the hand and harvest steps.

## Verification

Pending: the next playtest payload shows no missing class, or only listed known issues.

## Prevention

The packaging gate above, with a test that a payload missing a release class is refused unless it
is listed as a known issue.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
