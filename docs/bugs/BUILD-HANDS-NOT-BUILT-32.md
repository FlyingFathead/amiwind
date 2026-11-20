# BUILD-HANDS-NOT-BUILT-32: Per-race first-person hands are not built by the builder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Builder stage hand-catalog (tools/build.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.32 |
| Severity | high: Every race falls back to Nord hands and torch silently. |
| Family | Content silently missing from a build (`build-content-missing`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev
- 2026-10-08: Release coverage test; per-race hands built by default: BUILD-HANDS-NOT-BUILT-32 fixed in source: a default `hand-catalog` builder stage, installed by the image step after the sky palette bank; on owned data its command reproduces all 42 ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (not shipped at the time of writing; a finished from-scratch image is still to confirm
it). Found by the builder defaults audit (every option and stage compared with the v0.0.31
payload).

## Symptom

v0.0.31 ships 40 `progs/hands/*.mdl`, `gfx/hand-models.awh` and `gfx/hand-torch.awt`, made only by
the standalone `tools/prepare_hand_catalog.py`, which no builder step calls. A from-scratch build has
none of them, so every race falls back to the Nord hands and torch.

## Where

`tools/prepare_hand_catalog.py` (standalone); `tools/build.py` has no step for it.

## How it happened

The catalog was produced by hand for a release and its output carried forward in patched images.

## Why it was not caught

Release images were patched from earlier images instead of being built from scratch
(BUILD-NOT-FROM-SCRATCH-32), so a missing builder stage never showed.

## Reproduction

A from-scratch build with the repository builder; compare its payload with v0.0.31.

## Repair

- New default builder stage `hand-catalog` (`tools/build.py`, `hand_catalog_status`,
  `hand_catalog_steps`): `prepare_hand_catalog.py --palette <intro scene palette> --runtime-palette
  --topology source --out <run>/hand-catalog`. It depends only on the `intro` stage, so it runs in
  parallel with the rest of the chain (about two minutes on one core). It runs in every real AGA
  build with 3D hands; sprite hands, dry runs, terrain-only builds and the rc3 image recovery make
  none. `build-state.json` records `hand_catalog`, and the build prints its status.
- v0.0.31's hands use the image's final palette: the scene palette with the reserved UI bank and
  the sky colour bank. `--runtime-palette` derives exactly those bytes from the scene palette with
  the image step's own code (`ui_palette.reserved_palette` and `sky_palette_overlay.banked_palette`,
  both factored out of the image path, so there is one implementation). The authored source
  topology is what v0.0.31 shipped (the tool's own default stays `reduced`). The catalogue report
  records the palette it used.
- The image step takes `--hand-catalog DIR` and installs the models, `gfx/hand-models.awh` and
  `gfx/hand-torch.awt` in `finalize_image`, right after the sky palette bank and before the guard
  torches and every final gate (`prepare_hand_catalog.install`). It installs only when every file
  matches the catalogue report and the report's palette is the stage's final palette; otherwise
  nothing is installed and the image stops. It writes `hand-catalog-staging.json`.
- The sky palette overlay read `gfx/hand-models.awh` as a character head preview (same `AWH1`
  magic) and would stop on any stage that already holds the catalogue; it now recognises the hand
  catalogue (model paths only, no pixels).

## Verification

- Owned data, dev1 scene: the builder's exact `hand-catalog` command made all 42 files (40 models,
  catalogue, torch metadata) byte-identical to v0.0.31, and `install` accepted the v0.0.31 final
  palette. The same conversion against the plain scene palette differs in 30 of the 42 files,
  which is why the step derives the runtime palette.
- `tests/test_hand_catalog_step.py`: palette derivation (UI bank only when the scene has no UI
  receipt, sky bank only on the approved sky input), conversion and report use the runtime
  palette, install copies everything or nothing (other palette, changed file, existing target,
  unsafe path), install comes after the sky step and before the guard torches, and the sky
  overlay accepts the hand catalogue while still reading head previews.
- `tests/test_release_coverage.py` and `tests/test_build_defaults.py`: the default build runs
  `hand-catalog` before `image` and passes `--hand-catalog`; the release feature `hands-per-race`
  names that step.
- Pending: a finished from-scratch image compared file by file with v0.0.31.

## Prevention

`config/release-features.json` maps every file class v0.0.31 ships to a feature and its default
builder steps; `tests/test_release_coverage.py` fails when a shipped class has no feature or a
feature's step is not in the default build, and its list of known builder gaps may only shrink.
`tools/payload_coverage.py check` compares a built payload or staged image with the release, by
feature, for the from-scratch gate.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ACTOR-LIBRARY-BASE-ARCHIVE-66](ACTOR-LIBRARY-BASE-ARCHIVE-66.md): The actor library baked the creatures from the base game archive alone, so the 37 creature meshes of Tribunal and Bloodmoon were missing
- [ACTOR-LIBRARY-LEFT-OUT-48](ACTOR-LIBRARY-LEFT-OUT-48.md): The actor library made no model for corpse creatures and for town NPCs standing outside the towns: 9 outdoor references left out
- [ACTOR-MOVING-RUNTIME-GROUND-48](ACTOR-MOVING-RUNTIME-GROUND-48.md): Moving actors (levitation, flying creatures, jumping, swimming, knockback, scripted SetPos) need runtime grounding beyond the build-time bake
- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- BUILD-AWF-AWS-EXTENSION-CLASH-54 (no report page): New fog and smoke tables took the extensions .awf and .aws, which already mean font and sprite: the palette overlay parsed the fog table as a font
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64](BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64.md): A MiniWind build of the v0.0.64-dev2 line stops in the intro stage: the seam check stops the bake of the character creation class NPC with 14 new uncovered openings
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LAYER-SETS-NEVER-TAKEN-67](BUILD-LAYER-SETS-NEVER-TAKEN-67.md): A default build with expansions selected took none of their finished outdoor cells: the cell list was resolved before the expansions were selected
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
- [CHIM-FENCE-WRONG-ARCHIVE-64](CHIM-FENCE-WRONG-ARCHIVE-64.md): The see-through texture check read a texture from the wrong archive and stopped the CHIM stage
- [CHIM-LARGE-ROOMS-EXPANSIONS-66](CHIM-LARGE-ROOMS-EXPANSIONS-66.md): With the expansions selected, the CHIM interiors stage stopped: the large-rooms table listed none of their large rooms
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-REGION-DOORS-NO-ROOMS-48](CHIM-REGION-DOORS-NO-ROOMS-48.md): The load doors of CHIM region frames never lead into a room
- [CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48](CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48.md): Marking rooms as needing 32 MB rewrote 16 room maps after the optimizer receipt, and the image step stopped
- [CHIM-ROOM-LAVA-UNDER-WATER-48](CHIM-ROOM-LAVA-UNDER-WATER-48.md): CHIM rooms could not hold a lava pool whose bed reaches under the water level: 3 base-game rooms set aside
- [CHIM-ROOM-SHELL-NO-HULL-48](CHIM-ROOM-SHELL-NO-HULL-48.md): Batch CHIM rooms declared no standing hull, so the actor ground check refused all 1,910 of their residents
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [EXPANSION-DOORS-HELD-BACK-66](EXPANSION-DOORS-HELD-BACK-66.md): With the expansions selected, the image step would stop on 273 doors and markers that lead to places the build does not hold
- [EXPANSION-TABLES-BASE-ONLY-66](EXPANSION-TABLES-BASE-ONLY-66.md): Some of the builder's tables read the base game only while Tribunal and Bloodmoon are selected
- [EXTERIOR-EXPANSION-ONLY-CELLS-66](EXTERIOR-EXPANSION-ONLY-CELLS-66.md): With the expansions selected, the world scenery and world flora stages would stop on the placements of Solstheim's exterior cells
- [EXTERIOR-PLAN-MASTER-LAYERS-66](EXTERIOR-PLAN-MASTER-LAYERS-66.md): With the expansions selected, the world terrain stage stopped: the exterior plan and the world survey hashed different game data
- FOCUS-ROOM-BACK-TABLE-58 (no report page): In the Census and Excise Office the back-room table with the Iron Dagger is not drawn and aiming at the dagger shows no item box
- [GODSREACH-CANAL-NO-WATER-67](GODSREACH-CANAL-NO-WATER-67.md): Godsreach's canal is dry: the district has no water below its streets
- [GUARD-TORCH-REBAKE-MISMATCH-48](GUARD-TORCH-REBAKE-MISMATCH-48.md): Eight guards first staged in v0.0.48 get no torch: their base models do not rebake exactly
- [GUARD-TORCH-TYPES-LIMIT-48](GUARD-TORCH-TYPES-LIMIT-48.md): The image step stops on Too many distinct staged guard models: the batch rooms bring more than 32 guard types
- IMAGE-IDE-CYLINDER-TAIL-59 (no report page): On the emulated A1200 IDE port the last 144 sectors of the world partition AW_WORLD0 were unreadable, so loading Khuul stopped the game
- IMAGE-WORLD-BATCH-PAIRS-52 (no report page): The image stopped writing a world partition: the boot units moved off DH0 (source, volume path pairs) were turned into paths before the pairs were read
- [INTERIOR-ACTIVATORS-LEFT-OUT-52](INTERIOR-ACTIVATORS-LEFT-OUT-52.md): Interiors leave out every activator but the beds: the heart of Lorkhan is missing from Akulakhan s Chamber, and bar counters, shrines and Dwemer machinery from hundreds of rooms
- [INTERIOR-NO-AMBI-66](INTERIOR-NO-AMBI-66.md): The room stage stops on interior cells without AMBI: the Mournhold plazas with Tribunal on
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [JOURNAL-EXPANSION-OVERRIDES-66](JOURNAL-EXPANSION-OVERRIDES-66.md): With the expansions selected, the world UI stage stopped on a journal stage both the base game and an expansion hold
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- MINIWIND-EXTERIOR-CHIM-INTERIORS-52 (no report page): An exterior MiniWind stops in its image step: the image is told to install the CHIM interior store that the exterior scope does not build
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYER-WEREWOLF-ROBE-NOT-BAKED-66](PLAYER-WEREWOLF-ROBE-NOT-BAKED-66.md): With Bloodmoon selected, the player parts stage stopped on the werewolf robe, a worn part with no player model
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [REF-IDENTITY-MERGED-MASTER-66](REF-IDENTITY-MERGED-MASTER-66.md): With both expansions selected the build stops in its focus stage: a merged reference number does not fit the stable id
- [RELEASE-PRIVATE-NAMES-48](RELEASE-PRIVATE-NAMES-48.md): Two public files named the private working folder, and seven public lines used a banned abbreviation for actor behaviour
- [ROBE-PART-NOT-BAKED-62](ROBE-PART-NOT-BAKED-62.md): An equipped robe taken from Tarhiel is drawn in first person but not on the third-person body or in the inventory picture
- [ROOM-ACTORS-FLOATING-48](ROOM-ACTORS-FLOATING-48.md): Regression: 1,662 residents of batch CHIM rooms stood above the floor, never fitted to it
- [ROOM-BATCH-HARVEST-48](ROOM-BATCH-HARVEST-48.md): Harvestable plants in batch rooms may stay baked scenery
- [ROOM-BATCH-NPC-GROUNDING-48](ROOM-BATCH-NPC-GROUNDING-48.md): The residents of rooms no town list holds have no grounding class: --room-batches 5 is refused (62 NPCs in 22 rooms)
- [ROOM-BATCH-WATER-OUTSIDE-48](ROOM-BATCH-WATER-OUTSIDE-48.md): Room batches refused rooms whose cell water lies under or over everything the room places (water outside the room bounds)
- [ROOM-EMPTY-CELL-66](ROOM-EMPTY-CELL-66.md): Four expansion interior cells with no scenery were refused by the room batches stage as having no placement to convert
- [ROOM-OBJECTS-MISSING-62](ROOM-OBJECTS-MISSING-62.md): In the Andrano Ancestral Tomb only the doors can be used: no containers, items or creatures
- [ROOMS-SET-ASIDE-NOT-BUILT-67](ROOMS-SET-ASIDE-NOT-BUILT-67.md): Rooms that no door leads to are set aside and not built, although a script, a teleport or travel can lead there
- [SEYDA-CONTAINERS-NOT-DRAWN-67](SEYDA-CONTAINERS-NOT-DRAWN-67.md): Seyda Neen's crates, barrels, chest and sacks are not drawn and cannot be opened
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- [STAGE-READS-SELECTED-MASTERS-67](STAGE-READS-SELECTED-MASTERS-67.md): No build stage proves it read the game files the build selected, so a stage that reads only the base game goes unnoticed
- [TP-LIST-UNBUILT-EXTERIORS-66](TP-LIST-UNBUILT-EXTERIORS-66.md): The teleport place list would list Solstheim places the image has no world for
- [TREE-SCALE-001](TREE-SCALE-001.md): Non-unit-scale tree sprites omitted; bounds too conservative
- [VIVEC-HOVER-VERIFY-48](VIVEC-HOVER-VERIFY-48.md): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect
- [WORLD-SURVEY-EXPANSION-ATLAS-66](WORLD-SURVEY-EXPANSION-ATLAS-66.md): With both expansions selected the build stops in its world survey: a terrain subdivision outside the island's atlas

Related bugs in other categories:

- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch

<!-- END GENERATED CATEGORY -->
