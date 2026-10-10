# ARENA-PIT-NO-INTERIOR-33: The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | engine/aga/src/aw_arena.c fallback; builder (Arena withdrawn from v0.0.33) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | low: Intended for v0.0.33 (the Arena was withdrawn); the fight works on the gallery floor, but nothing on screen says why. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |
| Build note | owner playtest of a v0.0.33 build; the exact image commit is not in the report |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open, by design for v0.0.33: the Arena Pit (vai000) is converted only on the arena-interiors line, not by the release builder; dbgmode arenapit falls back to the gallery floor and says so on the console only. Later: the Pit in a MiniWind scope (queued) and an on-screen notice.

## Symptom

In the owner's playtest the Arena minigame opened on a flat test plane instead of the Arena Pit.

## Where

builder (the Vivec Arena is withdrawn from v0.0.33; tools/build.py --extra-town vivec_arena builds the exterior only), engine/aga/src/aw_arena.c fallback.

## How it happened

v0.0.33 withdrew the Vivec Arena from the default build; the Pit interior conversion lives on a separate line that is not in the release builder. The minigame falls back to the gallery floor by design and prints "The Arena Pit is not in this build; using the gallery floor." on the console.

## Why it was not caught

The fallback message goes to the console, which a player does not see.

## Reproduction

Always.

## Repair

Not yet. (1) Show the fallback on screen in the minigame title card. (2) Build the Pit with the builder: the MiniWind Arena Pit scope (direct start, presets and the Pit interior; queued) and later the full Arena.

## Verification

None yet: an Arena MiniWind boots into the Pit; a build without it shows the on-screen notice.

## Prevention

Combat and death behaviour follow the original rules with the source named (OpenMW source, game settings); every presentation change gets a fixture or an in-game clip.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

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
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
