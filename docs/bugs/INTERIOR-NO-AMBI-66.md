# INTERIOR-NO-AMBI-66: The room stage stops on interior cells without AMBI

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 13 November 2026, in v0.0.66-dev2 |
| Where | room conversion, stage chim-room-batches: the interior reader (src/mwad/interior.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev2 |
| Severity | high: the build with the expansions stops in the room stage |
| Family | Content silently missing from a build (`build-content-missing`) |
| Fix commit | `0be241df` |
| Fixed on | 2026-11-13 |
| Planning item | `INTERIOR-NO-AMBI-66` |
| Playtest version | 2026_11_13_v0.0.66-dev2_full-v0.0.66-dev2_b59f971 |
| From commit | source and engine b59f971 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (a build stop, before any image) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.66-dev2 (0be241df) | 2026-11-13 | gate 10700 passed on c9d30f8e, which holds it | the Mournhold plazas are set aside by the room stages, an interior without AMBI takes the reference default, every refusal names its cell |
| shipped | a numbered build | v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e | 2026-11-14 | the delivered build | the build holds 0be241df |
| confirmed by a build | a numbered build | v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e | 2026-11-14 | the dev2 build log | with Tribunal selected the room stages passed with the Mournhold plazas set aside; a builder fix, no play check applies |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-13: reported in v0.0.66-dev2
- 2026-11-13: fixed in source: a gated commit, v0.0.66-dev2 (0be241df); gate 10700 passed on c9d30f8e, which holds it: the Mournhold plazas are set aside by the room stages, an interior without AMBI takes the reference default, every refusal names its cell
- 2026-11-14: shipped: a numbered build, v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e; the delivered build: the build holds 0be241df
- 2026-11-14: confirmed by a build: a numbered build, v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e; the dev2 build log: with Tribunal selected the room stages passed with the Mournhold plazas set aside; a builder fix, no play check applies

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev2 (13 November 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 13 November 2026](#status-13-november-2026)
- [Symptom](#symptom)
- [How it happened](#how-it-happened)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 13 November 2026

Fixed in v0.0.66-dev2.

## Symptom

With the expansions on, the room stage stopped after about six minutes with "Interior AMBI missing/invalid", naming
no room.

## How it happened

The interior reader required an AMBI subrecord (the cell's ambient, sunlight and fog) in every interior cell. Five
cells of Tribunal have none: Mournhold, Godsreach; Mournhold, Great Bazaar; Mournhold, Plaza Brindisi Dorom;
Mournhold, Royal Palace: Courtyard; Mournhold, Temple Courtyard. All five are flagged "behave like exterior". The
original and the reference engine treat such a cell as an exterior: sky, the region's weather and the moving sun, no
cell ambient (OpenMW `mwworld/scene.cpp`: the interior ambient only for a cell that is neither exterior nor
quasi-exterior; `worldimp.cpp` `updateWeather`). The base game has no such cell and no interior without AMBI.

## Repair

- A behave-like-exterior cell is not a room: the room plan (`tools/door_graph.py`) sets it aside, and the room stage
  (`tools/chim_room_batches.py`) leaves it out and lists it with its master as an exterior-like cell, waiting for the
  Mournhold exterior work. Doors into it stay unlinked, as for any room not converted in a build. Mournhold's ordinary
  interiors, which have AMBI, convert as rooms as before.
- An ordinary interior without AMBI reads with the reference engine's default: ambient, sunlight and fog black, fog
  density 0, so it is lit by its own lights only (OpenMW `components/esm3/loadcell.cpp`, `mwrender/renderingmanager.cpp`
  `configureAmbient`). No such cell exists in the three game files today.
- Every refusal of the interior reader names its cell, and one read lists every bad cell together.

## Verification

- The reader over all 1,328 interiors of the merged game files: no refusal; the five cells above are the only
  behave-like-exterior cells.
- tests/test_interior_no_ambi.py: an interior without AMBI reads with the default mood, a behave-like-exterior cell is
  set aside by the room stage with its master, an invalid AMBI refuses naming every bad cell, a cell with AMBI reads as
  before. tests/test_door_graph.py: the plan sets the exterior-like cell aside, never in the parity batch.
- The base game alone: no cell is flagged, so its room plan, room units and their keys are unchanged.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- ACTOR-LIBRARY-BASE-ARCHIVE-66 (no report page): The actor library baked the creatures from the base game archive alone, so the 37 creature meshes of Tribunal and Bloodmoon were missing
- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- ACTOR-MOVING-RUNTIME-GROUND-48 (no report page): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- BUILD-AWF-AWS-EXTENSION-CLASH-54 (no report page): New fog and smoke tables took the extensions .awf and .aws, which already mean font and sprite: the palette overlay parsed the fog table as a font
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64 (no report page): A MiniWind build of the v0.0.64-dev2 line stops in the intro stage: the seam check stops the bake of the character creation class NPC with 14 new uncovered openings
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-NPC-GALLERY-MISSING-25](BUILD-NPC-GALLERY-MISSING-25.md): Normal images had no NPC gallery: the builder never ran the gallery stage (Gallery catalogue missing)
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- CHIM-FENCE-WRONG-ARCHIVE-64 (no report page): The see-through texture check read a texture from the wrong archive and stopped the CHIM stage
- CHIM-LARGE-ROOMS-EXPANSIONS-66 (no report page): With the expansions selected, the CHIM interiors stage stopped: the large-rooms table listed none of their large rooms
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- EXPANSION-DOORS-HELD-BACK-66 (no report page): With the expansions selected, the image step would stop on 273 doors and markers that lead to places the build does not hold
- EXPANSION-TABLES-BASE-ONLY-66 (no report page): Some of the builder's tables read the base game only while Tribunal and Bloodmoon are selected
- EXTERIOR-EXPANSION-ONLY-CELLS-66 (no report page): With the expansions selected, the world scenery and world flora stages would stop on the placements of Solstheim's exterior cells
- EXTERIOR-PLAN-MASTER-LAYERS-66 (no report page): With the expansions selected, the world terrain stage stopped: the exterior plan and the world survey hashed different game data
- FOCUS-ROOM-BACK-TABLE-58 (no report page): In the Census and Excise Office the back-room table with the Iron Dagger is not drawn and aiming at the dagger shows no item box
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- IMAGE-IDE-CYLINDER-TAIL-59 (no report page): On the emulated A1200 IDE port the last 144 sectors of the world partition AW_WORLD0 were unreadable, so loading Khuul stopped the game
- IMAGE-WORLD-BATCH-PAIRS-52 (no report page): The image stopped writing a world partition: the boot units moved off DH0 (source, volume path pairs) were turned into paths before the pairs were read
- INTERIOR-ACTIVATORS-LEFT-OUT-52 (no report page): Interiors leave out every activator but the beds: the heart of Lorkhan is missing from Akulakhan s Chamber, and bar counters, shrines and Dwemer machinery from hundreds of rooms
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- JOURNAL-EXPANSION-OVERRIDES-66 (no report page): With the expansions selected, the world UI stage stopped on a journal stage both the base game and an expansion hold
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- MINIWIND-EXTERIOR-CHIM-INTERIORS-52 (no report page): An exterior MiniWind stops in its image step: the image is told to install the CHIM interior store that the exterior scope does not build
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- PLAYER-WEREWOLF-ROBE-NOT-BAKED-66 (no report page): With Bloodmoon selected, the player parts stage stopped on the werewolf robe, a worn part with no player model
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- REF-IDENTITY-MERGED-MASTER-66 (no report page): With both expansions selected the build stops in its focus stage: a merged reference number does not fit the stable id
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- ROBE-PART-NOT-BAKED-62 (no report page): An equipped robe taken from Tarhiel is drawn in first person but not on the third-person body or in the inventory picture
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-NPC-GROUNDING-48](ROOM-BATCH-NPC-GROUNDING-48.md): The residents of rooms no town list holds have no grounding class: --room-batches 5 is refused (62 NPCs in 22 rooms)
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- ROOM-EMPTY-CELL-66 (no report page): Four expansion interior cells with no scenery were refused by the room batches stage as having no placement to convert
- [ROOM-OBJECTS-MISSING-62](ROOM-OBJECTS-MISSING-62.md): In the Andrano Ancestral Tomb only the doors can be used: no containers, items or creatures
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TP-LIST-UNBUILT-EXTERIORS-66 (no report page): The teleport place list would list Solstheim places the image has no world for
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative
- VIVEC-HOVER-VERIFY-48 (no report page): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect
- WORLD-SURVEY-EXPANSION-ATLAS-66 (no report page): With both expansions selected the build stops in its world survey: a terrain subdivision outside the island's atlas

Related bugs in other categories:

- BUILD-ACTOR-SPEC-EXPANSIONS-66 (no report page): With the expansions selected, the image stage stopped on the actor spec check: its room counts were not like for like, and the places the build sets aside counted as missing
- [INTERIOR-SUNLIGHT-UNBAKED-51](INTERIOR-SUNLIGHT-UNBAKED-51.md): Interiors are baked without their cell sunlight: Akulakhan's Chamber is nearly black where the original is lit red

<!-- END GENERATED CATEGORY -->
