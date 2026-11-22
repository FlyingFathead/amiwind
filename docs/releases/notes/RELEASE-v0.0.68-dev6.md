# AmiWind v0.0.68-dev6 (in development)

_Last updated with AmiWind v0.0.68-dev6 (22 November 2026)._

Development snapshot, 22 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev5](RELEASE-v0.0.68-dev5.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The sixth snapshot of v0.0.68. The version has no title yet. Two things change in the game. Where a script switches
between two doors at one place, the use key, the prompt and the map's door markers now take only the door that is
switched on; and the scripted objects of Mournhold's five districts (366 on the data of the last build: living and dead
trees, the districts' ambient sounds, the fabricants' attacks, turning signs, Azura's statue at the end of the main
quest, the city gates and others) are placed at their spot on the district frames and the engine now attaches their
scripts there. The builder's test images also wait for their test world. Its emulator presets,
`AmiWind-v0.0.68-dev6-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev6-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs.

How each change was checked is said on its line. None of the changes of this snapshot has been seen in play yet: they
are covered by their tests and by the gates of their own commits (the doors 12400, the expansions' scripts 12441, the
builder's wait 12330). The bug tracker entries are set fixed when this snapshot is recorded and the changes are seen in
play.

## New since v0.0.68-dev5

### Mournhold

- **The scripted objects of Mournhold's five districts run on their frames.** The game data keeps a district as an
  interior cell, and the build presents it as outdoor frames, so the script step wrote the districts' scripted objects as
  room rows, and the engine never attached a room row outdoors: 366 objects of the districts (Temple courtyard 209, Plaza
  Brindisi Dorom 58, Godsreach 45, Great Bazaar 40, Royal Palace courtyard 13 on the data of the dev5 build) had a script
  that was bound and never ran. The script step now keeps such a row at its moved place in the presented world, with the
  interior mark, and the engine places it on the district frame that contains it, so every script of a district runs while
  that district is loaded, as the original runs an interior cell. The scripts are the courtyard's living and dead trees
  (which one shows depends on the ash storm), the districts' ambient sounds and fountains, the Plaza's fabricant attacks
  and their rubble, the turning signs, the gate messages, the city gates, and Azura's statue outside the Temple, which stays
  hidden until Almalexia's death. Counted from the script file of the dev5 build and the same data with the change: the
  objects of the districts that are bound and never attached fall from 366 to 0, and the file differs only in its binding
  rows (421 rows change their flags and place; every other part is byte for byte the same). No memory is added: the table
  plan already counted a district as one room with all its rows. Each frame now runs the scripts of its attached rows; the
  Temple courtyard's frame (`mh0007`) runs 70 of them, 63 of them on every frame. What is not known is the cost in frames
  of that, which is not measured (the entry for the districts' frame rate,
  [DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md), stays open). The districts' look changes as in
  the original: the dead trees, the rubble and the statue are hidden or shown by their scripts
  ([EXPANSION-SCRIPTS-NOT-ATTACHED-66](../../bugs/EXPANSION-SCRIPTS-NOT-ATTACHED-66.md), open until seen in play). Covered
  by new tests and the gate 12441; not seen in play.

### Doors

- **A load door that a script has switched off is no longer taken by the use key.** Where two doors stand in one doorway
  and a script switches between them, the aim took the first door of the doorway whatever its state. Skaal Village's
  Rigmor's Hut (`Ex_S_door_rigmor`) and The Blodskaal's House (`Ex_S_door_rigmor2`), which the village's script swaps when
  the attack comes, gave Rigmor's Hut after the attack too, and the stage doors of the Raven Rock colony led into their
  rooms before their buildings stood. Now a door that a script has switched off is passed by, as the original takes a
  disabled object out of the scene: the other door of the doorway, or none, is aimed at, shows its prompt, is used by the
  use key and is shown on the map. A script's own Activate still acts on the door it names, whatever its state, as in the
  original. The console's door status listing names a door that is switched off. The cost is one lookup in the world's
  change list for each door the view ray meets. [The door mapping page](../../DOOR_MAPPING.md) says what the rule is
  ([DOOR-LOAD-DISABLED-STILL-USED-68](../../bugs/DOOR-LOAD-DISABLED-STILL-USED-68.md), open until seen in play). Covered by
  a new test of two doors in one doorway, which fails on the old pick, and the gate 12400; not seen in play.

## The builder's counts of the expansions

- **The record of the expansions' actors and the script tracker read the frame stores.** The actor check counted only the
  rooms' entity tracker and the open world's actor table, so the 57 district actors and 201 outdoor actors of Solstheim
  that the stores of the frames place were counted as not placed, and Solstheim's 135 built cells as missing; it also
  counted 74 people as without their script although their scripts only declare the variables the dialogue reads and need
  no binding. The script tracker counted no exterior of an expansion as in the image, so the scripts that run on Solstheim's
  frames read as present only in an add-on. All three read the stores' frames now. On the data of the dev5 build the script
  tracker shows 1,062 scripts that run (927 before) and 3 that exist only in an add-on and are not in the image (138
  before); the 3 are the script of a snow door in the glacier's corner (the cells of the Mortrag Glacier are not in the
  image yet) and two scripts that only declare the variables the dialogue reads
  ([EXPANSION-COUNTS-MISS-FRAME-STORES-68](../../bugs/EXPANSION-COUNTS-MISS-FRAME-STORES-68.md), open). Covered by new
  tests and the gate 12441. [The MWScript tracker](../../MWSCRIPT_FEATURES.md) is measured for this snapshot.

## Builder and tools

- **A Solstheim test image waits for its test world.** The image step of a test image that carries a Solstheim test world
  did not wait for the stages that make it, so a build that reused everything else could assemble the image before the
  world existed and install nothing of the glacier. The image step now waits for them. This is for test images only; a
  normal build does not use that route
  ([BUILD-CHIM-SOL-TEST-IMAGE-NO-WAIT-68](../../bugs/BUILD-CHIM-SOL-TEST-IMAGE-NO-WAIT-68.md), open). Covered by a new
  test and the gate 12330.
- **The bug tracker** records, besides the entries above, a build that reuses a run and rebuilds the stages that run had
  itself taken from an earlier run
  ([BUILD-REUSE-CHAIN-ABSENT-STAGE-68](../../bugs/BUILD-REUSE-CHAIN-ABSENT-STAGE-68.md)), a fix recorded for one entry that
  marks the other entries of its planning item as fixed
  ([TRACK-FIXED-STEPS-WHOLE-HOME-68](../../bugs/TRACK-FIXED-STEPS-WHOLE-HOME-68.md)) and the write guard counting the
  delivery's record of what a build shipped as a write outside the intake
  ([TRACKER-GUARD-SHIPPED-STEP-68](../../bugs/TRACKER-GUARD-SHIPPED-STEP-68.md)); all open. It also records sightings of
  three earlier entries
  ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md),
  [IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66](../../bugs/IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66.md),
  [BUILD-CHIM-WORLD-POOL-BROKEN-64](../../bugs/BUILD-CHIM-WORLD-POOL-BROKEN-64.md)), and the changes of this
  snapshot that are fixed in source.

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (its first cells are in
  the build since dev3, its glacier is being compared), the expansions' remaining scripts and dialogue, the save with
  their counts and the playtests.
- **Solstheim's glacier:** the ice is drawn brown-grey and with a sheer drop in the test builds; the cause of the colour
  is known and is being worked on in a test build, and none of that work is in this snapshot
  ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md)).
- **Audits of what the original has**, planned: every creature record checked field by field against its original
  (CREATURE-RECORDS-PARITY-AUDIT-68), every lever, valve, button and crank listed with whether it works
  (ACTIVATORS-AUDIT-ALL-LANDS-68), and the progress summary showing cells converted but not yet in an image
  (TOOLKIT-SOL-CONVERTED-COUNT-68); see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev5](RELEASE-v0.0.68-dev5.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The districts' trees and sounds.** Walk Mournhold's Temple courtyard: the living or the dead trees (by the ash storm)
  are shown and the others hidden, the ambient and fountain sounds play, the Plaza's rubble and Azura's statue outside the
  Temple are hidden at the start of a new game. Look at the frame rate in the Temple courtyard, which runs the most
  scripts, and say how it feels against the earlier snapshot.
- **The doors of the Skaal village.** In Skaal Village, aim at the doors of Rigmor's Hut and The Blodskaal's House before
  the attack and after it: only the door that is switched on shows its prompt, is used by the use key and has a marker on
  the map. In Raven Rock, the colony's stage doors should lead in only once their buildings stand.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run (1,062 run and 9 are carried
by AmiWind's own code, of 1,074); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
part has come.

- **Solstheim:** the cells are reached only with the debug teleport. No door, travel or place name leads there, and the
  sea around the coast, the people, the creatures and the containers outdoors are not in. The glacier and its eight
  neighbouring cells are not in: the comparison of the ways to fit its ice is under way, two ice coast cells convert with
  a memory ring far over the budget ([SOL-ICE-CELLS-RING-OVER-68](../../bugs/SOL-ICE-CELLS-RING-OVER-68.md)), and one cell
  stops for a person placed outdoors without a ground class
  ([SOL-COVENTINA-NO-GROUND-CLASS-68](../../bugs/SOL-COVENTINA-NO-GROUND-CLASS-68.md)); both open. Twelve of Solstheim's
  models with stairs keep the original's collision for their steps, and the glacier's two icebergs are the same
  ([CHIM-STAIR-METHOD1-UNFIXED-48](../../bugs/CHIM-STAIR-METHOD1-UNFIXED-48.md), open). Fort Frostmoth's dock ran at about
  a quarter of the island's usual frame rate when looking over the dock and the ship
  ([SOL-FROSTMOTH-DOCK-FRAME-RATE-68](../../bugs/SOL-FROSTMOTH-DOCK-FRAME-RATE-68.md)), and loading a frame spent about two
  and a half seconds reading eight kilobytes of area tables
  ([AREA-TABLES-SLOW-READ-ON-LOAD-68](../../bugs/AREA-TABLES-SLOW-READ-ON-LOAD-68.md)); both open.
- **The expansions' scripts:** four scripted references in the Mortrag Glacier's corner (the ice sounds and a snow door)
  stay outside the image until the glacier's cells are in it, and 20 of Bloodmoon's 155 new exterior cells are in no frame
  of the image yet; the scripts of Mournhold's districts are seen running only in the tests so far, and the Temple
  courtyard's frame runs 63 more scripts on every frame, so its frame rate is to be measured
  ([EXPANSION-SCRIPTS-NOT-ATTACHED-66](../../bugs/EXPANSION-SCRIPTS-NOT-ATTACHED-66.md),
  [DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md), open).
- **The glacier's ice:** in the glacier test images the Mortrag Glacier's ice draws brown-grey instead of white and shows a
  sheer vertical drop where the original slopes. It is seen with today's methods and with method E (the reduced collision and
  the simplified drawn mesh together), so it does not come from the method chosen; the cause of the colour is known (the image's palette has no
  white), a fix is being tested and is not in this snapshot, and the sheer walls follow the original's own shapes
  ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md), open).
- **Entrances that cannot be reached:** 13 exterior entrances of Solstheim and Mournhold have no standing spot at the
  threshold in the converted collision, or the door lies out of the use reach, so the player may not be able to use them;
  the door check lists them so that a build is not stopped
  ([DOOR-USE-COLLISION-EXPANSIONS-68](../../bugs/DOOR-USE-COLLISION-EXPANSIONS-68.md), open).
- **Bodies the game places dead:** creatures that the game places dead in rooms (skeletons, dead scamps, scribs and
  centurions, the Hall of Ministry's dead rat) are not spawned, so their bodies are missing: the room's entity names a
  corpse base and the spawn of a room's placed creature takes only living actors
  ([ROOM-PLACED-CORPSES-NOT-SPAWNED-68](../../bugs/ROOM-PLACED-CORPSES-NOT-SPAWNED-68.md), open).
- **Scripted outdoor objects missing from the world:** 190 outdoor objects that scripts switch on and off are not in the
  built world at all, so nothing hides or shows them: pieces of the opening and the stages of Tel Uvirith among them
  ([SCRIPTED-TARGETS-NOT-IN-IMAGE-68](../../bugs/SCRIPTED-TARGETS-NOT-IN-IMAGE-68.md), open).
- **The Ghostfence:** the glow and the curtain's layers are off by default until their cost in frames is measured, and the
  curtain's own scrolling layers have not been seen in play, so the entry for the curtain that does not move stays open
  ([GHOSTFENCE-NO-ANIMATION-46](../../bugs/GHOSTFENCE-NO-ANIMATION-46.md)).
- **A build can still run out of memory on a 32 GB machine,** and the plan for the memory runs the outdoor world stage on
  5 of 22 workers, which takes about an hour instead of about half that
  ([BUILD-MEMPLAN-CHIM-5-OF-22-68](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md),
  [BUILD-TESTER-32GB-OOM-67](../../bugs/BUILD-TESTER-32GB-OOM-67.md),
  [BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md), open). After its optimizer check the image step ran
  on one of 22 cores for more than six minutes
  ([BUILD-IMAGE-AFTER-OPTIMIZER-SERIAL-68](../../bugs/BUILD-IMAGE-AFTER-OPTIMIZER-SERIAL-68.md)), Solstheim's world stage
  converted on about half of its cores
  ([SOL-MODULE-CONVERSION-HALF-CORES-68](../../bugs/SOL-MODULE-CONVERSION-HALF-CORES-68.md)), and the stall check reported
  zero busy cores while a stage's worker pools ran
  ([STALL-ZERO-CORES-WHILE-POOLS-BUSY-68](../../bugs/STALL-ZERO-CORES-WHILE-POOLS-BUSY-68.md)); all open.
- **Wild creatures:** a wilderness mudcrab in the Ascadian Isles turned into several copies that stand inside each other
  and jump between positions ([CREATURE-DUPLICATE-SPAWN-WARP-68](../../bugs/CREATURE-DUPLICATE-SPAWN-WARP-68.md), seen
  once, cause not known); a hostile scrib out of reach runs away instead of attacking
  ([CREATURE-HOSTILE-FLEES-67](../../bugs/CREATURE-HOSTILE-FLEES-67.md)); all open.
- **Seyda Neen:** going back into the census office from its courtyard after a played session stops the game with a
  model cache error ([CENSUS-COURTYARD-REENTRY-CRASH-68](../../bugs/CENSUS-COURTYARD-REENTRY-CRASH-68.md), open).
- **Reduced models' seams:** the models of creatures and people reduced for the game still have open seams and, on the
  skeletal ones, thinned limbs ([ACTOR-BAKE-NO-SEAM-STOP-68](../../bugs/ACTOR-BAKE-NO-SEAM-STOP-68.md),
  [SKEL-POSE-GRID-THINS-LIMBS-68](../../bugs/SKEL-POSE-GRID-THINS-LIMBS-68.md), open).
- **The werewolf:** turning into one changes only the stats and takes the gear off
  ([WEREWOLF-TRANSFORM-RULES-PARTIAL-68](../../bugs/WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md)), the player keeps their own
  body ([WEREWOLF-BODY-NOT-DRAWN-63](../../bugs/WEREWOLF-BODY-NOT-DRAWN-63.md)), and the reduction of the outer measures
  leaves the werewolf's head whole at every target and reports that as a pass
  ([WEREWOLF-HEAD-NOT-REDUCED-68](../../bugs/WEREWOLF-HEAD-NOT-REDUCED-68.md)); open.
- **Old Mournhold's sewers:** with collision off the use key does nothing on levers and cranks
  ([USE-KEY-DEAD-IN-NOCLIP-68](../../bugs/USE-KEY-DEAD-IN-NOCLIP-68.md)); the scripted teleport into Sotha Sil, Outer
  Flooded Halls lands in the hall's water
  ([ROOM-ARRIVAL-FLOODED-ON-ROOF-67](../../bugs/ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md)); both open.
- **The debug teleport's list and the door check:** the fixes of dev5 for the teleport's place list and the door check
  stay open until seen in play
  ([TP-LIST-MODULE-STORE-PLACES-68](../../bugs/TP-LIST-MODULE-STORE-PLACES-68.md),
  [DOOR-CHECK-MODULE-FRAME-MAPS-67](../../bugs/DOOR-CHECK-MODULE-FRAME-MAPS-67.md)).
- **In the tools:** a CHIM import request for one cell whose coordinate starts with a minus sign is refused
  ([AW-CHIMPORT-ONE-NEGATIVE-CELL-68](../../bugs/AW-CHIMPORT-ONE-NEGATIVE-CELL-68.md)); one new row in the expansions'
  grounding id file re-keys the base world stage and the Mournhold module
  ([BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68](../../bugs/BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68.md)); the source
  catalogue cache puts the settings of unrelated modules into one key
  ([BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68](../../bugs/BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68.md)); a delivery resumed for a newer
  commit stops for want of its source export
  ([DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68](../../bugs/DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68.md)); the builder's
  slow-stage warning compared a stage that had to run with the few seconds an earlier build took to reuse it
  ([STALL-SLOW-STAGE-VS-REUSE-TIME-68](../../bugs/STALL-SLOW-STAGE-VS-REUSE-TIME-68.md)); the memory report counts the
  planes only a model's standing hull uses as drawn bytes
  ([CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68](../../bugs/CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68.md)); the release readiness list
  does not name the Solstheim test route's options, which a release candidate or final still refuses
  ([BUILD-READINESS-MISSES-PLAN-WAIVERS-68](../../bugs/BUILD-READINESS-MISSES-PLAN-WAIVERS-68.md)); a build that reuses a
  run rebuilds the stages that run had itself taken from an earlier run
  ([BUILD-REUSE-CHAIN-ABSENT-STAGE-68](../../bugs/BUILD-REUSE-CHAIN-ABSENT-STAGE-68.md)); a fix recorded for one entry
  marks the other entries of its planning item
  ([TRACK-FIXED-STEPS-WHOLE-HOME-68](../../bugs/TRACK-FIXED-STEPS-WHOLE-HOME-68.md)); the write guard counts the
  delivery's record of what a build shipped as a write outside the intake
  ([TRACKER-GUARD-SHIPPED-STEP-68](../../bugs/TRACKER-GUARD-SHIPPED-STEP-68.md)); all open.
- **In the tools, builder:** a change of the scene palette re-bakes every Balmora interior room, although 24 of its 43 room
  maps come out byte for byte the same (the residents' models do change with the palette, so their re-bake is needed)
  ([BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68](../../bugs/BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68.md)); a fresh census stage
  ran on under 4 of 22 cores for about 6 minutes before its worker pool started
  ([BUILD-CENSUS-PHASE-UNDERUSED-68](../../bugs/BUILD-CENSUS-PHASE-UNDERUSED-68.md)); both open.
- **The look book** checks only the numbers on its pages, so a palette change that alters the colours of every confirmed
  look cannot fail a page and its stills are compared by hand
  ([LOOKBOOK-NO-COLOUR-CHECK-68](../../bugs/LOOKBOOK-NO-COLOUR-CHECK-68.md), open).
- From [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build),
  [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and
  its snapshots: their Known lists stand for what is not named here, among them Mournhold's and Solstheim's unfinished
  play. Every other open entry is in the [bug tracker](../../BUGS.md).
