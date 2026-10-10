# SEYDA-LANTERNS-MISSING-31: Seyda Neen's lanterns light the night but are not in its maps

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev5 |
| Where | Seyda Neen maps (lantern meshes absent) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev5 (last seen) |
| Severity | medium: Lamp light is lit at night but the lantern meshes are not in the maps. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.31-dev5 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev5; cause known.

## Symptom

At night in Seyda Neen, walls are lit by lamp light with no lantern to be seen
("searchlights").

## Where

The night lamp table (`id1/world/lamps.awl`, written by
`tools/light_sources.py` from the original placements) lists Seyda Neen's
lanterns; the Seyda Neen maps do not contain their meshes.

## How it happened

The Seyda Neen scenery index used to build the Seyda maps has no light
placements (LIGH records), so the eight `light_com_lantern_02` lanterns and the
opening lantern never reached the maps, while the lamp table, built from the
original data, has them.

## Why it was not caught

The lamp table was checked against the census, not against the meshes present
in each map.

## Reproduction

v0.0.31-dev5, Seyda Neen at night near the houses by the docks; `dbg lamps`
lists lamps where no lantern is drawn.

## Repair

Not yet: add light placements to the Seyda Neen scenery conversion so the
lantern meshes are in the maps. Until then the lamp light is correct in place
but its lantern is invisible.

## Verification

Pending.

## Prevention

A lights gate per map: every lit lamp must have its mesh in that map, or be
reported.

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
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [EMISSIVE-UNSHIPPED-31](EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [LIGHT-ENTITIES-UNWIRED-33](LIGHT-ENTITIES-UNWIRED-33.md): Morrowind lights are never turned into Quake light entities, so the light compiler bakes nothing

<!-- END GENERATED CATEGORY -->
