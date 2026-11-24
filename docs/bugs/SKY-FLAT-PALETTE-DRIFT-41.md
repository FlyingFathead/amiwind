# SKY-FLAT-PALETTE-DRIFT-41: Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.41 |
| Where | prepare_quake.py palette sample; prepare_shared_sky_assets.py fallback; exterior_sky_build.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.46 |
| Severity | high: Every exterior of v0.0.40 and v0.0.41 has a flat grey-blue sky without clouds; the build printed only a warning |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.41 release image 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source ce7ace6, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.5 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-17: reported in v0.0.41
- 2026-10-17: SKY-FLAT-PALETTE-DRIFT-41: SKY-FLAT-PALETTE-DRIFT-41: the maintainer asked where the clouds and the sun had gone.
- 2026-10-20: TRACKER-REGISTER-SIZE-33 and TRACKER-REGISTER-SIZE-36: the archive split by version range: TRACKER-REGISTER-SIZE-33 (PERSISTING, reported a fifth time): the register audit of 20 October 2026 took the single bug archive to 232,832 bytes, 89 ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.56 (30 October 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
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

## Symptom

On 17 October 2026 the maintainer asked where the clouds and the sun had gone: the camera benchmark frames of the
v0.0.41 release image at the Balmora benchmark cameras show a flat grey-blue sky with no clouds.

Checked in FS-UAE (JIT preset, a fresh play copy of the v0.0.41 release image, Balmora camera bm1, clock stopped
and set, headlamp off) at 08:00, 12:00, 18:00 and 22:00, looking level, pitched up 30 degrees and towards the
sun's path:

- No clouds at any hour: the whole sky above the horizon is one colour (palette index 224 under the day/night
  colour tables), at every pitch.
- The sun is there: at 08:00 looking east, 20 degrees up, the sun disc and its halo show. At noon it is near
  the zenith (about 76 degrees up by the engine's orbit), outside a level or 30-degree view, so a noon frame
  never shows it.
- The day/night colours work: grey-blue by day, brown at 18:00, near black at 22:00.

The engine's settings were the defaults: `aw_sky_type 3`, `aw_clouds 1`, `aw_cloud_type` classic,
`aw_day_clouds 100`, `aw_sun 1`, `aw_daynight 1`, `aw_skyline_fill 0`. The night sky loaded ("Owned night sky:
27648 bitmap bytes").

## Where

- `tools/prepare_quake.py` (the `scene` stage): the scene palette is sampled from the textures of the Seyda Neen
  scenery stage.
- `tools/prepare_shared_sky_assets.py` `prepare_staged_sky`: the owned cloud sky and its palette bank are only
  prepared for one approved palette (`sky_palette_overlay.approved`, a SHA-256 fingerprint); any other palette
  gives a `fallback_warning`.
- `tools/exterior_sky_build.py` `configure_staged_maps`: with no prepared sky it installs the converted maps'
  own reserved sky texture, a 256 x 128 placeholder of index 224 in both layers.

## How it happened

Commit 01bdf9f (15 October 2026, v0.0.40-dev2 line, "Align town ownership to original cells") widened the Seyda
Neen scenery scope to cover the cell-aligned town (`town_grid.scenery_radius`: radius 11,500 to 29,772, and the
larger area rectangle in `config/seyda_area.json`). The scenery stage then held 183 textures instead of 107. The
scene palette is a 224-colour quantisation of those textures, so it changed (221 of 256 colours). The changed
palette no longer matched the approved fingerprint, the shared sky preparation fell back with "Unsupported
original palette fingerprint; no reservation/reindex performed", and the image shipped the placeholder.

Measured on the build volume: every build up to v0.0.38 (13 October, c2c2050) has the cloud sky (SHA-256
92a874a1...) with status `prepared_owned_clouds`; the v0.0.41-dev5 regional build and the v0.0.41 release image
have the one-colour sky (30f78f90...), status `fallback_warning`, no `gfx/sky-palette-bank.json`. v0.0.40 contains
01bdf9f and is affected the same way (its image is no longer on the build volume).

## Why it was not caught

- The fallback was a warning line in the image log, not an error, although every real build has the maintainer's data
  files: nothing can legitimately fall back there.
- The palette is derived data: nothing tied it to the scenery scope, so a scope change for another reason (town
  ownership) moved every colour without any check noticing.
- The always-included check tests only that `gfx/aw_shared_sky.lmp` exists, not that it has clouds; the frame
  checks and benchmarks ran with the flat sky as their baseline.

## Reproduction

Any build from 01bdf9f on: the image log has "Shared sky vivid/cloud preparation unavailable: Unsupported
original palette fingerprint", and `image/sky-asset-preparation/fallback-warning.json` exists. In game every
exterior sky is flat.

## Repair

- `prepare_shared_sky_assets.prepare_staged_sky` converts the owned cloud sky for whatever palette the build has:
  a palette the sky colour bank was not made for gets the clouds by nearest colour against that palette
  (`prepared_owned_clouds_palette_matched`). No bank is reserved, so no other staged file changes: no texture or
  map is converted again. The bank method stays for the palette it was made for. Without the bank the twilight
  tones come from the nearest palette colours. Checked on the real v0.0.41 palette (SHA-256 e7ce2a84...): the
  converted sky (18debc84...) alone, put into the v0.0.41 release image, shows clouds at noon and red and gold
  clouds at dusk in FS-UAE; the maintainer judged the noon and dusk frames good.
- `build_aga` image step: a `fallback_warning` from the shared sky preparation with owned data files stops the
  build, naming the reason and the staged palette's SHA-256, instead of shipping a flat sky.
- Tests: `tests/test_prepare_shared_sky_assets.py` (another palette gets palette-matched clouds and nothing else
  changes), `tests/test_prepare_quake_palette.py` (the image step refuses the fallback).
- Tried first and taken out again: sampling the palette from the old Seyda Neen texture set (4b20d7c). It brought
  back the old texture sample, but the palette sample also holds the Seyda Neen ground textures, which the larger
  area changed as well: a MiniWind built with it got a third palette (1654dedf...), still not the one the bank
  was made for, and stopped in the image step on the refusal above. It would also have converted every texture
  again. The palette stays the v0.0.41 one.

## Verification

Pending: the dev1 build (image log "sky assets" with `prepared_owned_clouds_palette_matched`) and the same
FS-UAE frames with clouds.

## Prevention

- The image step refuses the fallback (above).
- Every stand-in asset, not only the sky, goes through one rule (`tools/placeholder_policy.py`): a stand-in
  shared sky, night sky, night-windows table, interface font, startup-screen font or intro video stops the image
  step, naming the unit, each input with its SHA-256 and the reason, instead of a warning line. A test build can
  let a named one through with `--allow-placeholder NAME` (refused for release candidates and finals, recorded in
  the image receipt as `placeholders_allowed`). A stand-in that every build ships today because of an open bug
  (the empty night-windows table, [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md)) is printed and
  recorded with that bug instead of stopping the build; once the bug is fixed it stops the build again.
- The earlier proposal (check the palette right after the `census` stage) is no longer needed: since the
  palette-matched method every palette gets the cloud sky, so there is nothing left to catch early.

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
- [BUILD-CHIM-SOL-TEST-IMAGE-NO-WAIT-68](BUILD-CHIM-SOL-TEST-IMAGE-NO-WAIT-68.md): In a Solstheim test image build the image step did not wait for the Solstheim test world it installs, so a build with everything else reused assembled the image before that world existed
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
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
- [INVISIBLE-WALLS-NOT-BUILT-68](INVISIBLE-WALLS-NOT-BUILT-68.md): Invisible walls of the game outside the opening are not built: five at Mournhold's city edges, which show "You may not leave the city this way." in the original, and one at exterior cell 15,5, so the player can walk where the original stops him
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
- [SCRIPTED-TARGETS-NOT-IN-IMAGE-68](SCRIPTED-TARGETS-NOT-IN-IMAGE-68.md): Outdoor objects that the game's scripts switch on and off (the Ghostfence's glow, the opening's barriers, parts of the Telvanni stronghold) are not in the built world at all
- [SEYDA-CONTAINERS-NOT-DRAWN-67](SEYDA-CONTAINERS-NOT-DRAWN-67.md): Seyda Neen's crates, barrels, chest and sacks are not drawn and cannot be opened
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SOL-MODULE-CACHE-NOT-PICKLED-68](SOL-MODULE-CACHE-NOT-PICKLED-68.md): The Solstheim build module's world stage stopped at once: the shared unit cache it installs could not be handed to the converter's worker processes
- [STAGE-READS-SELECTED-MASTERS-67](STAGE-READS-SELECTED-MASTERS-67.md): No build stage proves it read the game files the build selected, so a stage that reads only the base game goes unnoticed
- [SWIM-SINKS-BELOW-SURFACE-68](SWIM-SINKS-BELOW-SURFACE-68.md): A swimming player sinks back below the surface after swimming up: the crossing is swum fully under water
- [TP-LIST-MODULE-STORE-PLACES-68](TP-LIST-MODULE-STORE-PLACES-68.md): The teleport list leaves out the Solstheim places and beings of an image that holds the island
- [TP-LIST-UNBUILT-EXTERIORS-66](TP-LIST-UNBUILT-EXTERIORS-66.md): The teleport place list would list Solstheim places the image has no world for
- [TREE-SCALE-001](TREE-SCALE-001.md): Non-unit-scale tree sprites omitted; bounds too conservative
- [VIVEC-HOVER-VERIFY-48](VIVEC-HOVER-VERIFY-48.md): Vivec (the god) floats in meditation: verify whether it is his animation over a grounded collision origin or an active effect
- [WORLD-SURVEY-EXPANSION-ATLAS-66](WORLD-SURVEY-EXPANSION-ATLAS-66.md): With both expansions selected the build stops in its world survey: a terrain subdivision outside the island's atlas

Related bugs in other categories:

- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars

<!-- END GENERATED CATEGORY -->
