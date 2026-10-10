# BUILD-STANDALONE-STAGES-32: Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Standalone door overlay and interior section tools |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Closed: neither tool output is in v0.0.31; no builder step missing. |
| Family | Content silently missing from a build (`build-content-missing`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Closed: neither tool's output is in v0.0.31, so no builder step is missing for this release.
Found by the builder defaults audit (every option and stage compared with the v0.0.31 payload).

## Symptom

`tools/prepare_original_door_overlay.py` and `tools/prepare_interior_sections.py` are standalone and
not called by the builder. Whether any v0.0.31 map depends on them is not yet known.

## Where

The two tools above.

## How it happened

Same as the other standalone stages.

## Why it was not caught

Release images were patched from earlier images instead of being built from scratch
(BUILD-NOT-FROM-SCRATCH-32), so a missing builder stage never showed.

## Reproduction

A from-scratch build with the repository builder; compare its payload with v0.0.31.

## Repair

No builder change needed. Checked against the v0.0.31 image:

- `prepare_interior_sections.py` writes `interior-sections.txt`, section maps with appended IDs
  and their harvest and door banks. v0.0.31 ships none of them (no `interior-sections.txt`, no
  appended interior maps): the tool's output is not in the release.
- `prepare_original_door_overlay.py` adds original exterior entrance doors to world maps (it
  refuses town maps). All 2,724 maps of v0.0.31 were scanned for entities bound to the 1,108
  original exterior entrances: none of the 2,532 world maps has one. The 102 maps that have
  them are Seyda Neen, Balmora and the intro docks, whose doors come from the normal town
  conversion.

Both tools stay standalone experiments. `config/release-features.json` would show any of their
output in a payload as files no feature explains.

## Verification

- Release payload (v0.0.31, all three partitions) read file by file: no section files or appended
  interior maps; entity scan of every map for original exterior entrance references as above.
- `tests/test_release_coverage.py`: every shipped file class belongs to a feature with default
  builder steps; neither tool is one of them.

## Prevention

`config/release-features.json` maps every file class v0.0.31 ships to a feature and its default
builder steps; `tests/test_release_coverage.py` fails when a shipped class has no feature or a
feature's step is not in the default build, and its list of known builder gaps may only shrink.
`tools/payload_coverage.py check` compares a built payload or staged image with the release, by
feature, for the from-scratch gate.

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
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch

<!-- END GENERATED CATEGORY -->
