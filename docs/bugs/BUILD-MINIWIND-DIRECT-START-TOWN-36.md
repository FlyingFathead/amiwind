# BUILD-MINIWIND-DIRECT-START-TOWN-36: A MiniWind build of another town refuses its own direct start: the start check assumed Balmora

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | tools/build.py configure_direct_start (MiniWind scope) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | high: every MiniWind build of a town other than Balmora (Vivec stage A) is refused before any stage; no wrong payload |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 6891f7a, engine 6891f7a, CHIM world 6891f7a |
| CHIM engine version | CHIM 0.1.0, engine 6891f7a, world format 0.5 |
| Build note | MiniWind vivec-arena-chim stage A request, refused by the build check before any stage |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 11 October 2026

Fixed in source on v0.0.36-integration-r1 (`tools/build.py`), with a regression test. Not shipped at the time of writing.

## Symptom

The first Vivec stage A request (`aw request --kind miniwind --preset vivec-arena-chim --flags "--miniwind-town vivec_arena"`)
was refused by the build check: `--direct-to-game-map vivec_arena: Vivec, Arena is not in this build (it holds balmora)`.

## Where

`tools/build.py`, `configure_direct_start`: for a MiniWind build the start point was checked against a fixed town list
`['balmora']`, not against the MiniWind build's own town.

## How it happened

MiniWind started as a Balmora-only build. `--miniwind-town` later made other towns possible (configure_miniwind sets
`args.miniwind_town` and the CHIM area), but the direct start check kept its Balmora list. Every MiniWind preset until
vivec-arena-chim either started in Balmora or named no start area.

## Why it was not caught

The direct start tests only used Balmora starts, and no MiniWind build of another town had run before.

## Reproduction

`python3 tools/build.py --miniwind --miniwind-town vivec_arena --direct-to-game-map vivec_arena --check ...` on any
commit before the fix.

## Repair

The MiniWind scope holds `args.miniwind_town` (default Balmora), the town `configure_miniwind` already resolved.

## Verification

`tests/test_direct_start.py` `test_miniwind_start_in_its_own_town`: a Vivec Arena MiniWind starts at the Arena, and
a Balmora start in it is refused naming the build's town. Full gate on the merged head.

## Prevention

The start scope comes from the same resolved option as the build's area; the regression test covers a town other than
Balmora.

General rule (maintainer order, 11 October 2026: a build of one area starts the player in that area), for every partial-area
build (MiniWind presets and recipes, `--miniwind-town`, direct starts):

- **The start follows the content.** Without `--miniwind-town`, an explicit start inside a town (the area, one of its
  rooms or a cell of its grid) makes that town the MiniWind town (`direct_start.start_town`); without an explicit start a
  MiniWind build starts at its town's own arrival point, a full build with the new game. The resolved start and the
  source of the choice are in `build-state.json` (`start`).
- **A start outside the built content is refused before any stage**, naming what the build holds (areas, interiors,
  cells; `direct_start.valid_starts`). No fallback to another town.
- **Image start check** (seconds, after every map write, before packing): the start map (the map, or the town's CHIM
  frame map `<town>-chim`) is in the final payload, and an explicit arrival on a Quake map has a standing spot on its
  collision (`direct_start.image_start_check`; `start-check.json`, image `build.json` `start`).
- Tests: `tests/test_direct_start.py` `StartFollowsContent` (every preset in `config/recipes/miniwind/` starts inside its
  own content, a start outside is refused, the Vivec Arena preset starts in the Arena with no `--miniwind-town`, the
  image check).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
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
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Placed items, ingredients included, are left out of converted interiors
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
