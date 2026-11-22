# AmiWind v0.0.68-dev7 (in development)

_Last updated with AmiWind v0.0.68-dev7 (22 November 2026)._

Development snapshot, 22 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev6](RELEASE-v0.0.68-dev6.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The seventh snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one mends the way into and through the opening and changes the game's scene
palette, so that ice and snow keep a cool cast. After going out to the Census and Excise Office's courtyard and back in, the use key can reach the back room's
items and doors again. Switching the debug free flight off where the player's box touches the world no longer throws the
player back to where the flight began. The builder's check of the opening (the opening journey) now comes down the ship's
plank to the dock guard and walks to the crab meat along the table's edge. Its emulator presets,
`AmiWind-v0.0.68-dev7-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev7-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs.

How each change was checked is said on its line. The back room's use key was seen working in play: the opening journey,
run on the dev6 image with this snapshot's engine changes, passed all 50 of its checks. The gates of the commits are 12480
(the back room), 12481 (the free flight), 12460 and 12482 (the opening journey) and 12328 (the scene palette). The bug
tracker entries of these changes are set fixed in source; they are closed when this snapshot is recorded.

## New since v0.0.68-dev6

### Solstheim and the whole game: the scene palette

- **Ice and snow keep a cool cast.** The game draws every texture with one palette of 256 colours. Sixteen of its colours
  were near-duplicate dark olives and browns that together cover 0.27 percent of the image's pixels; they are replaced by
  a ramp of cool off-white to blue-grey, sampled from Solstheim's ice and snow textures (the Mortrag Glacier's iceberg and
  ice textures, the ice layers, Castle Karstaag's and the snow ground). At the outdoor light levels ice and snow now keep
  a cool cast instead of turning brown-grey; the palette cannot make them brighter than the light allows. About 6 percent
  of all scenery texels in the game move onto the ramp, each to the colour nearest its own source colour: water,
  waterfalls, silver, blades, blue glass and the carried lanterns are among what changes a little
  ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md)). Every texture is re-baked once, so the
  first build with it is one full rebuild. Checked by the gate 12328 and by the glacier test images' pictures and pans, on
  which the maintainer chose this palette over the old one. The carried lantern's and the dock guard's confirmed looks
  are checked by the look book on this snapshot's image before the snapshot is delivered; that check is not yet made.

### Seyda Neen

- **The census back room answers the use key again after a visit to the courtyard.** Going out to the Census and Excise
  Office's courtyard and back in, the use key's list of reachable things kept the courtyard's rows, so the back room's
  items and doors had no row to answer the use key. The list is now read from the room at every arrival: each time the
  game starts a map, it clears the list's record of which map it belongs to, so a room entered from outdoors reads its
  own rows even when its world model takes the model slot the last map's model had
  ([ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68](../../bugs/ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68.md)). Seen in play: the
  opening journey on the dev6 image with this engine passed 50 of 50 checks. Covered by new tests of the focus table's
  reset and the gate 12480. The earlier place that told a new map only by its model's slot is a second finding: two more
  caches do the same, and they are not changed in this snapshot
  ([MAP-CHANGE-TOLD-BY-MODEL-SLOT-68](../../bugs/MAP-CHANGE-TOLD-BY-MODEL-SLOT-68.md), open).

### Debug tools

- **Switching the free flight off where the player's box touches the world lifts the player clear there.** The stuck check
  of the game falls back to a remembered free spot, and the free flight's debug switch left that spot where the flight
  began, so switching the flight off inside a solid moved the player back there. Switching it off now keeps the place as
  the spot to fall back to, and the player is lifted clear on the spot
  ([JOURNEY-DOCK-NOCLIP-UNSTUCK-RACE-68](../../bugs/JOURNEY-DOCK-NOCLIP-UNSTUCK-RACE-68.md)). This is a debug feature; a
  normal game does not have the flight. The opening journey's flight to the plank went through and the journey passed 50
  of 50 on the dev6 image. Covered by a new test of the stuck check and the gate 12481.

## Builder and tools

- **The opening journey meets the dock guard from the ship's side.** Its first step now comes down the ship's plank to the
  guard on the pier, and waits for his greeting, which needs the player within the original's reach of him. The game was
  right: a player coming down the plank is greeted on it, and the check's old stop point lay out of the guard's reach, so
  its first step could not get past the race menu
  ([DOCK-GREETING-OUT-OF-REACH-67](../../bugs/DOCK-GREETING-OUT-OF-REACH-67.md)). The gate is 12460. A report of the same
  step failing about half the time, from a free-flight switch that is a toggle, is closed as a duplicate of the free-flight
  entry above ([JOURNEY-STEP1-FLIGHT-NOCLIP-TOGGLE-68](../../bugs/JOURNEY-STEP1-FLIGHT-NOCLIP-TOGGLE-68.md)).
- **The walk to the crab meat ends beside the table, not against its edge.** The back room's table could stop the player
  just outside the reach of the take, so the journey ended in its second step. The walk's point is now on the free side of
  the table's edge
  ([JOURNEY-CRAB-WALK-POINT-AT-TABLE-EDGE-68](../../bugs/JOURNEY-CRAB-WALK-POINT-AT-TABLE-EDGE-68.md)). Covered by the
  checked script of the gate 12482. The journey is the builder's check of the opening and the look book's journey page is
  made from it.
- **The bug tracker** records, besides the entries above: the dock guard's first walk of a new game held about 10 units
  short of the foot of the plank, where two dock pieces meet
  ([DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68](../../bugs/DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68.md), open); the look book's
  journey page not being judged on the delivered development images
  ([LOOKBOOK-JOURNEY-PAGE-NEVER-JUDGED-68](../../bugs/LOOKBOOK-JOURNEY-PAGE-NEVER-JUDGED-68.md), open); a second emulator
  session with the same job name failing on the container name and the journey reporting every check as failed
  ([SESSION-SAME-JOB-NAME-CLASH-68](../../bugs/SESSION-SAME-JOB-NAME-CLASH-68.md), open); and the image step's torch check
  taking about three times its recorded time, which fails the build's speed check, a repeat of
  [IMAGE-GUARD-TORCHES-SLOW-66](../../bugs/IMAGE-GUARD-TORCHES-SLOW-66.md)
  ([IMAGE-TORCHES-GUARD-3X-BASELINE-68](../../bugs/IMAGE-TORCHES-GUARD-3X-BASELINE-68.md), a duplicate of it).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (its first cells are in
  the build since dev3, its glacier is being compared), the expansions' remaining scripts and dialogue, the save with
  their counts and the playtests.
- **Solstheim's glacier:** the ice was drawn brown-grey and with a sheer drop in the test builds; the colour is mended by
  the new scene palette in this snapshot, and the glacier's nine cells stay out of the build while the comparison of the
  ways to fit its ice goes on ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md)).
- **Audits of what the original has**, planned: every creature record checked field by field against its original
  (CREATURE-RECORDS-PARITY-AUDIT-68), every lever, valve, button and crank listed with whether it works
  (ACTIVATORS-AUDIT-ALL-LANDS-68), and the progress summary showing cells converted but not yet in an image
  (TOOLKIT-SOL-CONVERTED-COUNT-68); see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev6](RELEASE-v0.0.68-dev6.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The census back room after the courtyard.** Start a new game, take the papers, and go through the Census and Excise
  Office to its courtyard and back into the back room. Aim at the crab meat, the plate, the other items on the table and
  the doors: each shows its prompt and takes the use key. Do it twice, and once after loading a save made in the back
  room, and say what happens.
- **Colours after the new palette.** Look at snow and ice (Solstheim's cells through the debug teleport), water, waterfalls,
  silver, blades, blue glass and a carried lantern, and at the dock guard in Seyda Neen: each should look as it did, a
  little cooler where it was near the ramp. Say what looks different.
- **The opening from the ship to the papers.** Start a new game: the guard on the pier greets the player coming down the
  plank, the race menu opens, and the way on to the papers on the table works. The guard may wait a little nearer the town
  than the foot of the plank (the entry for his held walk is open); say where he stood.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run (1,062 run and 9 are carried
by AmiWind's own code, of 1,074); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
part has come. No script changed since dev6.

- **Seyda Neen:** going back into the census office from its courtyard after a played session stops the game with a
  model cache error ([CENSUS-COURTYARD-REENTRY-CRASH-68](../../bugs/CENSUS-COURTYARD-REENTRY-CRASH-68.md), open). The dock
  guard's first walk can be held about 10 units short of the plank's foot
  ([DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68](../../bugs/DOCK-GUARD-WALK-HELD-AT-PIECE-JOINT-68.md), open). Two more caches
  of the game tell a new map only by its model's slot, so after a map change in a long session a scripted animation of the
  last map can be applied to an actor of the new one; found in the code, not seen in play
  ([MAP-CHANGE-TOLD-BY-MODEL-SLOT-68](../../bugs/MAP-CHANGE-TOLD-BY-MODEL-SLOT-68.md), open).
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
  [DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md), open). The door rule of dev6 (a load door a
  script has switched off is passed by) also stays open until seen in play
  ([DOOR-LOAD-DISABLED-STILL-USED-68](../../bugs/DOOR-LOAD-DISABLED-STILL-USED-68.md)).
- **The glacier's ice:** the colour is mended by the new scene palette (above), but the glacier's nine cells are not in the
  build, and in the glacier test images the Mortrag Glacier still shows a sheer vertical drop where the original slopes. It
  is seen with today's methods and with method E (the reduced collision and the simplified drawn mesh together), so it does
  not come from the method chosen, and the sheer walls follow the original's own shapes. Seen from on top of a shard, the
  field around looks empty at the default draw distance (300; up to 540 in the options)
  ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md), open).
- **Entrances that cannot be reached:** 13 exterior entrances of Solstheim and Mournhold have no standing spot at the
  threshold in the converted collision, or the door lies out of the use reach, so the player may not be able to use them;
  the door check lists them so that a build is not stopped
  ([DOOR-USE-COLLISION-EXPANSIONS-68](../../bugs/DOOR-USE-COLLISION-EXPANSIONS-68.md), open).
- **Bodies the game places dead:** creatures that the game places dead in rooms (skeletons, dead scamps, scribs and
  centurions, the Hall of Ministry's dead rat) are not spawned, so their bodies are missing: the room's entity names a
  corpse base and the spawn of a room's placed creature takes only living actors
  ([ROOM-PLACED-CORPSES-NOT-SPAWNED-68](../../bugs/ROOM-PLACED-CORPSES-NOT-SPAWNED-68.md), open).
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
  ([SOL-MODULE-CONVERSION-HALF-CORES-68](../../bugs/SOL-MODULE-CONVERSION-HALF-CORES-68.md)), the image step's torch check
  takes about three times its recorded time
  ([IMAGE-GUARD-TORCHES-SLOW-66](../../bugs/IMAGE-GUARD-TORCHES-SLOW-66.md)), and the stall check reported
  zero busy cores while a stage's worker pools ran
  ([STALL-ZERO-CORES-WHILE-POOLS-BUSY-68](../../bugs/STALL-ZERO-CORES-WHILE-POOLS-BUSY-68.md)); all open.
- **Wild creatures:** a wilderness mudcrab in the Ascadian Isles turned into several copies that stand inside each other
  and jump between positions ([CREATURE-DUPLICATE-SPAWN-WARP-68](../../bugs/CREATURE-DUPLICATE-SPAWN-WARP-68.md), seen
  once, cause not known); a hostile scrib out of reach runs away instead of attacking
  ([CREATURE-HOSTILE-FLEES-67](../../bugs/CREATURE-HOSTILE-FLEES-67.md)); all open.
- **Reduced models' seams:** the models of creatures and people reduced for the game still have open seams and, on the
  skeletal ones, thinned limbs ([ACTOR-BAKE-NO-SEAM-STOP-68](../../bugs/ACTOR-BAKE-NO-SEAM-STOP-68.md),
  [SKEL-POSE-GRID-THINS-LIMBS-68](../../bugs/SKEL-POSE-GRID-THINS-LIMBS-68.md), open).
- **The werewolf:** turning into one changes only the stats and takes the gear off
  ([WEREWOLF-TRANSFORM-RULES-PARTIAL-68](../../bugs/WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md)), the player keeps their own
  body ([WEREWOLF-BODY-NOT-DRAWN-63](../../bugs/WEREWOLF-BODY-NOT-DRAWN-63.md)), and the reduction of the outer measures
  leaves the werewolf's head whole at every target and reports that as a pass
  ([WEREWOLF-HEAD-NOT-REDUCED-68](../../bugs/WEREWOLF-HEAD-NOT-REDUCED-68.md)); open.
- **Old Mournhold's sewers:** with collision off the use key does nothing on levers and cranks
  ([USE-KEY-DEAD-IN-NOCLIP-68](../../bugs/USE-KEY-DEAD-IN-NOCLIP-68.md), open).
- **In the tools:** a CHIM import request for one cell whose coordinate starts with a minus sign is refused
  ([AW-CHIMPORT-ONE-NEGATIVE-CELL-68](../../bugs/AW-CHIMPORT-ONE-NEGATIVE-CELL-68.md)); the source catalogue cache puts the
  settings of unrelated modules into one key
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
  ([TRACKER-GUARD-SHIPPED-STEP-68](../../bugs/TRACKER-GUARD-SHIPPED-STEP-68.md)); a second emulator session with the same
  job name fails to start and its journey reports every check as failed
  ([SESSION-SAME-JOB-NAME-CLASH-68](../../bugs/SESSION-SAME-JOB-NAME-CLASH-68.md)); all open.
- **In the tools, builder:** the scene palette change of this snapshot re-bakes every Balmora interior room, although 24 of its 43 room
  maps come out byte for byte the same (the residents' models do change with the palette, so their re-bake is needed)
  ([BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68](../../bugs/BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68.md)); a fresh census stage
  ran on under 4 of 22 cores for about 6 minutes before its worker pool started
  ([BUILD-CENSUS-PHASE-UNDERUSED-68](../../bugs/BUILD-CENSUS-PHASE-UNDERUSED-68.md)); both open.
- **The look book** checks only the numbers on its pages, so a palette change that alters the colours of every confirmed
  look cannot fail a page and its stills are compared by hand
  ([LOOKBOOK-NO-COLOUR-CHECK-68](../../bugs/LOOKBOOK-NO-COLOUR-CHECK-68.md)), and its journey page is not judged on the
  delivered development images, so the dock guard's confirmed look is checked by hand with the journey until that is built
  ([LOOKBOOK-JOURNEY-PAGE-NEVER-JUDGED-68](../../bugs/LOOKBOOK-JOURNEY-PAGE-NEVER-JUDGED-68.md)); both open.
- From [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build),
  [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build),
  [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and
  its snapshots: their Known lists stand for what is not named here, among them Mournhold's and Solstheim's unfinished
  play. Every other open entry is in the [bug tracker](../../BUGS.md).
