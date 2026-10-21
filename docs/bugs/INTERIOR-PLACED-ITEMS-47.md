# INTERIOR-PLACED-ITEMS-47: placed items, ingredients included, are left out of converted interiors

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 21 October 2026, in v0.0.46 |
| Where | Every converted interior (small items deferred by the interior converter) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: Original loot and ingredients missing from every room; no crash or data loss |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.46 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.1, engine unknown, world format 0.7 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | not in game (counted from the master and the image's entity tracker data) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47 (21 October 2026)._

## Status: 21 October 2026

Open. Present in v0.0.46 and every earlier build with converted interiors (the converter has always deferred them).
No repair yet: a placed item with state needs a live pickup object, not baked scenery; see Repair.

## Symptom

The maintainer, 21 October 2026, about the Luminous Russula in caves "that go to your inventory": in the original game
some ingredients lie in rooms as items (an `ingred_russula_01` on a shelf or a table) and are taken straight into the
inventory. In AmiWind's converted interiors those items are not there at all: nothing is drawn and nothing can be
taken.

## Where

Every converted interior. The interior converters keep only static scenery, doors, containers, lights and a few
activators; every placed item (ingredients `INGR`, and also `MISC`, `BOOK`, `WEAP`, `ARMO`, `CLOT`, `ALCH`, `APPA`,
`LOCK`, `PROB`, `REPA`, `LEVI`) is left out with the reason "small item or actor deferred"
(`src/mwad/interior.py` `omission_reason`).

Counted from the master against the v0.0.46 image (entity tracker data): 2,581 placed ingredients in interiors, 294 of
them in the shipped interiors, none drawn, none takeable. The shipped rooms with the most: Vivec, Hlaalu Alchemist
21; Vivec, Telvanni Alchemist 20; Vivec, St. Olms Farmers and Laborers Hall 20; Vivec, Aurane Frernis: Apothecary 16;
Vivec, St. Delyn Canal North-Two 12; Vivec, St. Olms Tanners and Miners Hall 12. The Luminous Russula as a placed
ingredient (`ingred_russula_01`) is in 15 interior placements, 8 of them in shipped rooms; the cave mushrooms
themselves are organic containers (HARVEST-INTERIOR-PICK-47), not items.

## How it happened

Items were deferred when the interior converter was written: a placed item that can be taken has state (taken, its
count, its owner), and the runtime has no placed-item object yet; leaving it out was chosen over drawing an item that
cannot be taken. The player's own dropped items are a separate, small mechanism (`aw_inventory_state_t` drops,
UI-INVENTORY-INTEGRATION-40).

## Why it was not caught

The entity tracker counts the omission as deliberate ("deliberately_skipped") and the tracker gate only fails on a
category that loses placements against its baseline, so a category that was never placed never shows as a loss.

## Reproduction

Any shop or house with items in the original, for example Balmora, Morag Tong Guild (7 placed ingredients in the
original): the shelves are empty in AmiWind. The image's `entity-tracker.json` lists the interior items under
"skipped": "small item or actor deferred".

## Repair

Not repaired. What the original and OpenMW do (OpenMW 0.51 `apps/openmw/mwclass/ingredient.cpp` activation and
`apps/openmw/mwworld/actiontake.cpp`): activating a placed item takes it into the inventory and deletes the reference
from the cell; the cell's saved state keeps it deleted; placed items do not respawn; an item with an owner is stolen
when taken (crime). The design for AmiWind, on the same principle as the harvest plants: a placed item with state is
a live object, never baked; taken = gone and remembered in the save (one fact per original placement, keyed by its
original identity like the harvest slots). Ownership needs the theft rules first; until then an owned item cannot be
offered as free loot (the harvest step applies the same rule to owned plants).

## Verification

Counts above from the master and the v0.0.46 image's entity tracker data, 21 October 2026. Nothing repaired yet.

## Prevention

When placed items are added, the entity tracker's item category for interiors becomes a counted category with a
baseline, so a later loss fails the gate.

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
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [HARVEST-INTERIOR-PICK-47](HARVEST-INTERIOR-PICK-47.md): Mushrooms inside interiors cannot be picked
- [HARVEST-ORGANIC-PLANTS-47](HARVEST-ORGANIC-PLANTS-47.md): Only the small mushrooms can be picked; every other harvestable plant is scenery
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete

<!-- END GENERATED CATEGORY -->
