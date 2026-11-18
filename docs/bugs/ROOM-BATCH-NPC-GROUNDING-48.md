# ROOM-BATCH-NPC-GROUNDING-48: the residents of rooms no town list holds have no grounding class

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | config/actor_grounding.json; tools/actor_grounding_census.py (exterior only) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.66-dev2 |
| Severity | critical: Regressed in v0.0.66-dev2 (was high): every batch past the rooms the towns list is refused until its residents are classified |
| Family | Content silently missing from a build (`build-content-missing`) |
| Fix commit | `85255fdf` |
| Fixed on | 2026-11-14 |
| Planning item | `REGISTER-STALE-SWEEP-66` |
| Came back (regression) | in v0.0.66-dev2 (fixed in v0.0.48-dev2 before) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source f2b9693, engine f2b9693, CHIM world f2b9693 |
| CHIM engine version | CHIM 0.2.1, engine f2b9693, world format 0.12 |
| Platform or emulator | not in game (a builder stage refuses the batch; nothing reaches the game) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.66-dev2 (85255fdf) | 2026-11-14 | tools/actor_grounding_census.py measures the rooms the build converts; the expansions' classes in a file beside the base game's; the build preflight checks every room resident before any stage | every resident of the selected masters' rooms has a grounding class, so the room batches stage no longer stops on an unclassified resident |
| shipped | the v0.0.66-dev2 release build | v0.0.66-dev2 (3988c6e4, build 2026_11_14_v0.0.66-dev2_full) | 2026-11-15 | the delivered dev2 build holds the commit (its source commit is a descendant of the fix) | a numbered build carries the fix |
| confirmed by a build | the v0.0.66-dev2 and later chain builds | v0.0.66-dev2 (3988c6e4, build 2026_11_14_v0.0.66-dev2_full) | 2026-11-15 | the chim-room-batches stage ran in full (1,059 room units, 2,147 resident bakes) and the build was delivered; every later dev build reused or ran the stage without a refusal | a builder-only fix: the stage that was refused runs to its end, nothing changes in play |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-23: reported in v0.0.48-dev2
- 2026-11-14: fixed in source: a gated commit, v0.0.66-dev2 (85255fdf); tools/actor_grounding_census.py measures the rooms the build converts; the expansions' classes in a file beside the base game's; the build preflight checks every room resident before any stage: every resident of the selected masters' rooms has a grounding class, so the room batches stage no longer stops on an unclassified resident
- 2026-11-14 02:06 +0200: came back in v0.0.66-dev2 (fixed in v0.0.48-dev2 before): Seen again with both expansions on: the room batches stage stopped on 179 NPCs in 78 Tribunal and Bloodmoon rooms without a class; the list had gained their rooms, not their classes
- 2026-11-15: shipped: the v0.0.66-dev2 release build, v0.0.66-dev2 (3988c6e4, build 2026_11_14_v0.0.66-dev2_full); the delivered dev2 build holds the commit (its source commit is a descendant of the fix): a numbered build carries the fix
- 2026-11-15: confirmed by a build: the v0.0.66-dev2 and later chain builds, v0.0.66-dev2 (3988c6e4, build 2026_11_14_v0.0.66-dev2_full); the chim-room-batches stage ran in full (1,059 room units, 2,147 resident bakes) and the build was delivered; every later dev build reused or ran the stage without a refusal: a builder-only fix: the stage that was refused runs to its end, nothing changes in play

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev2 (14 November 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 14 November 2026 (came back in v0.0.66-dev2)](#status-14-november-2026-came-back-in-v0066-dev2)
- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [What was done](#what-was-done)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 14 November 2026 (came back in v0.0.66-dev2)

Seen again in the v0.0.66-dev2 build, the first with both expansions on by default: the room batches stage stopped
before its first room on 179 resident NPCs in 78 Tribunal and Bloodmoon rooms without a grounding class. The room list
had gained the expansions' rooms as layer batches (eb32036b) but the classes file had not been made again, and the
census that makes it refused: it asked the interior reader for every room of the list whatever the selected masters,
so with the base game alone it stopped on the first expansion room, a Mournhold district that the room stage sets
aside as an exterior ([INTERIOR-NO-AMBI-66](INTERIOR-NO-AMBI-66.md)).

Fixed on the v0.0.66 line, not yet in a build:

- `tools/actor_grounding_census.py --rooms` measures the rooms the build converts, by the build's own rules: the
  batches of the selected masters only, and the cells flagged "behave like exterior" set aside by the same code the
  stage runs (`chim_room_batches.exterior_like_rooms`), each named with its master. `--write-rooms` measures the whole
  list with every master it names (the two room files below hold the whole list) and refuses a master selection that
  would leave a layer out.
- The classes now cover 1,323 rooms and 3,637 references: 3,422 on the floor, 157 authored dead, 56 kept off the floor
  and 2 with no floor under them, kept where the game puts them. The base game's 3,007 references keep exactly their
  classes; 356 references are Tribunal's (one of them in a base-game room, Ebonheart's Grand Council Chambers) and 274
  Bloodmoon's. The expansions' references kept off the floor: four creatures in Old Mournhold and the Sotha Sil halls,
  two draugr and a frost atronach, three ice trolls in the Caverns of Karstaag and a werewolf of the Mortrag Glacier
  maze; with no floor under them, a smuggler in the Royal Palace and the other maze werewolf. Five Mournhold districts
  are set aside, as the stage sets them aside.
- The expansions' references are in a file of their own, `config/actor_grounding_rooms_layers.json`, which
  `tools/actor_grounding.py` reads together with the base game's `config/actor_grounding_rooms.json`. The base game's
  file keeps its bytes. Written into it, the new classes also moved the key of every actor ground-fit unit, whose code
  names that file; in a file of their own they move only the keys of the 13 stages that look up a room class (the
  CHIM world, the towns and the image among them, their units restored from the unit cache) and no unit key.
- The build preflight checks every NPC and creature resident of every room the room batches convert, with the selected
  expansions, before any stage: about 6 seconds with both expansions, 2 with the base game alone. With the classes of
  before it names 627 unclassified references in 135 rooms in the first minute instead of 14 minutes in.

## Status: 23 October 2026

Fixed in v0.0.48-dev2 (branch v0.0.48-room-grounding), by rule rather than by a class per NPC: every NPC and
creature reference of every room of the list is classified per reference from the game data, by the maintainer's rule
of 22 October 2026 (actors start where the game puts them; see
[room residents by rule](../NPC_GROUND_CONTACT.md#room-residents-by-rule)). `tools/actor_grounding_census.py --rooms`
measures the feet against the room's own floor (its placements' visible and collision triangles) and writes
`config/actor_grounding_rooms.json`; `tools/actor_grounding.py` reads it by reference number for an actor the policy
does not name. 1,134 rooms, 3,007 references: 2,819 on the floor, 143 authored dead, 45 kept off the floor (43
swimming or flying creatures and two NPCs, listed with their heights), none without a floor; 1,270 levelled lists
deferred. Measured in the stage on every batch: no batch is refused for grounding any more (Ald-ruhn's first batch,
refused before for 62 NPCs, converts its 28 rooms). Not yet seen in a build or in the game.

## Symptom

`--room-batches 5` (Ald-ruhn, part 1): the room batches stage converted the 27 rooms (56 s on 5.6 of 8 cores), then
stopped in the residents step: `Unclassified initial support state: tuundir`. The fail-fast check added on the branch
now lists the whole gap in 4 s: 62 resident NPCs in 22 of the 27 rooms.

## Where

`config/actor_grounding.json`, `tools/actor_grounding.py` `initial_state`, and the residents step
(`prepare_area.populate`).

## How it happened

The grounding policy (CHIM-ACTOR-GROUNDING-POLICY-36) is an explicit list: every placed NPC is either standing on the
ground or a documented exception, and nothing is guessed. `tools/actor_grounding_census.py` fills the list by measuring
the exterior placements. Interior NPCs were added room by room when a town listed its rooms (the Arena Waistworks
precedent, be71cd90). Rooms by batch bring in hundreds of rooms no town lists, and their residents were never measured.

## What was done

Not a hand-made class per NPC (the plan above this fix): the rule the region frames use
(`tools/chim/region_actors.py`), per reference. Classes: `floor` (ordinary contact), `off_floor` and `no_floor`
(kept at the authored spot, `aw_ground_mode 1`, listed with the script), `authored_dead`. The tolerance is the
exterior census's (32 game units up, 128 down: the fitter's reach and `AW_NPCFloor`). The policy keeps its word for the
ids it names; one conflict is listed to check (a Hlaalu guard in Caldera Mine, 177 units above its floor, policy
ground).

## Verification

`tests/test_room_grounding.py` (synthetic rooms: standing, sitting on a chair, authored high with a script, no floor,
authored dead; the file holds no positions; lookup only by reference; the preflight passes with the file and still
refuses an actor neither names), `tests/test_room_batches.py` `GroundingPreflight`. In the stage on all 40 batches:
no grounding refusal.

v0.0.66-dev2: `tests/test_room_grounding_layers.py` (synthetic base and Tribunal masters with an exterior-like
district: the base game alone measures the base batches only, where the earlier census stopped on the district; with
Tribunal the district is set aside and named; `--write-rooms` holds the whole list and refuses a selection without a
layer; the build preflight names an unclassified room resident, passes with the written classes with and without the
expansion, and runs before any stage). On the game data: the build preflight finds no unclassified resident with both
expansions (3,637 references in 1,323 rooms) or with the base game alone (3,007 in 1,134), and the stage's own check
on its plan of the v0.0.66-dev2 build (1,124 rooms) finds none.

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
- [INTERIOR-NO-AMBI-66](INTERIOR-NO-AMBI-66.md): The room stage stops on interior cells without AMBI: the Mournhold plazas with Tribunal on
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- JOURNAL-EXPANSION-OVERRIDES-66 (no report page): With the expansions selected, the world UI stage stopped on a journal stage both the base game and an expansion hold
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- MINIWIND-EXTERIOR-CHIM-INTERIORS-52 (no report page): An exterior MiniWind stops in its image step: the image is told to install the CHIM interior store that the exterior scope does not build
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- PLAYER-WEREWOLF-ROBE-NOT-BAKED-66 (no report page): With Bloodmoon selected, the player parts stage stopped on the werewolf robe, a worn part with no player model
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [REF-IDENTITY-MERGED-MASTER-66](REF-IDENTITY-MERGED-MASTER-66.md): With both expansions selected the build stops in its focus stage: a merged reference number does not fit the stable id
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- ROBE-PART-NOT-BAKED-62 (no report page): An equipped robe taken from Tarhiel is drawn in first person but not on the third-person body or in the inventory picture
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- ROOM-EMPTY-CELL-66 (no report page): Four expansion interior cells with no scenery were refused by the room batches stage as having no placement to convert
- [ROOM-OBJECTS-MISSING-62](ROOM-OBJECTS-MISSING-62.md): In the Andrano Ancestral Tomb only the doors can be used: no containers, items or creatures
- [SEYDA-CONTAINERS-NOT-DRAWN-67](SEYDA-CONTAINERS-NOT-DRAWN-67.md): Seyda Neen's crates, barrels, chest and sacks are not drawn and cannot be opened
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- [STAGE-READS-SELECTED-MASTERS-67](STAGE-READS-SELECTED-MASTERS-67.md): No build stage proves it read the game files the build selected, so a stage that reads only the base game goes unnoticed
- TP-LIST-UNBUILT-EXTERIORS-66 (no report page): The teleport place list would list Solstheim places the image has no world for
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative
- VIVEC-HOVER-VERIFY-48 (no report page): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect
- WORLD-SURVEY-EXPANSION-ATLAS-66 (no report page): With both expansions selected the build stops in its world survey: a terrain subdivision outside the island's atlas

<!-- END GENERATED CATEGORY -->
