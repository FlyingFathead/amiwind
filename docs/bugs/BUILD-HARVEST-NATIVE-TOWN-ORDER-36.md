# BUILD-HARVEST-NATIVE-TOWN-ORDER-36: The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.36-dev2 |
| Where | tools/build_aga.py harvest_fingerprint_entries: catalogue to map check |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36-dev3 |
| Severity | high: Fails every build with a CHIM-native Balmora late in its image step |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.36-dev2 |
| From commit | source 642c1ea, engine 642c1ea, CHIM world 642c1ea |
| CHIM engine version | CHIM 0.1.0, engine 642c1ea, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in v0.0.36-dev3.

## Symptom

The v0.0.36-dev2 build with a CHIM-native Balmora, resumed after
[BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md), stopped again in its image step, after
the map optimizer pass over 2,658 maps: "Harvest catalogue has no matching map: harvest-bm008.txt".

## Where

`tools/build_aga.py`, `harvest_fingerprint_entries()`: every harvest catalogue must belong to a map in the image, to a
region of a town whose CHIM frame map (`maps/<town>-chim.bsp`) is in the image, or to a removed legacy map.

## How it happened

The harvest step runs in the middle of the image step, before the CHIM frame maps are written. A town on the legacy
chain still has its region maps at that point, so its catalogues match; a CHIM-native town (built from the game data
by `tools/chim_town.py`) has neither region maps nor, yet, its frame map, so its 17 Balmora catalogues looked like
catalogues without a map.

## Why it was not caught

No full build had a CHIM-native Balmora with harvest before v0.0.36-dev2; the CHIM-native test areas had no harvest
catalogue ([CHIM-NATIVE-HARVEST-MISSING-36](CHIM-NATIVE-HARVEST-MISSING-36.md)). The first dev2 run stopped earlier,
on the legacy Balmora cache, so this check was reached only on the second run.

## Reproduction

Always: a full build with harvest and a CHIM-native Balmora.

## Repair

The harvest step (`tools/harvest_build.py`, `install`) writes a CHIM town's catalogues after the per-map heap check
instead of before it: they take no part in that check ("CHIM frame: no per-map heap check"), and every later check
of the image runs once the frame maps are written. A first repair recognised CHIM-native towns from the staged files
(a region table without any legacy chain file); the full test suite showed that this would also accept a real fault
(a CHIM town whose frame map is missing, CHIM-HARVEST-REMOVED-MAPS-33), so it was replaced before any build used it.

## Verification

Regression test in `tests/test_harvest_build.py`: the heap check sees only the per-map catalogues, the CHIM town's
catalogue is written afterwards and admitted. The pure CHIM test of CHIM-HARVEST-REMOVED-MAPS-33 (a missing frame map
still fails) passes again. The v0.0.36-dev3 build runs the image step with a CHIM-native Balmora.

## Prevention

A CHIM town's catalogue is written only where no check can read it before the town's frame map exists; the
missing-frame-map refusal stays exact.

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
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning

<!-- END GENERATED CATEGORY -->
