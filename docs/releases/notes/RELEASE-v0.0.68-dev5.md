# AmiWind v0.0.68-dev5 (in development)

_Last updated with AmiWind v0.0.68-dev5 (21 November 2026)._

Development snapshot, 21 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev4](RELEASE-v0.0.68-dev4.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The fifth snapshot of v0.0.68, and a small step. The version has no title yet. People knocked out in water now drown at
once and a drowning person makes the drowning sound; the debug teleport's place list now counts Solstheim's places and
its outdoor people and creatures; and the builder's door check now walks the lands that have a store of their own,
Solstheim and Mournhold's districts, and lists the 13 entrances it cannot reach there. Nothing else of the game changes. Its emulator presets, `AmiWind-v0.0.68-dev5-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev5-WinUAE.uae`, both
start with 32 MB of Fast RAM, which the game needs.

How each change was checked is said on its line. None of the changes of this snapshot has been seen in play yet: they
are covered by their tests and by the gates of their own branches (the drowning 12274, the door check 12012). The bug
tracker entries are set fixed when this snapshot is recorded and the changes are seen in play.

## New since v0.0.68-dev4

### Water

- **A person knocked out in water drowns at once, and a drowning person makes the drowning sound.** In the original's
  rules, an actor knocked out (by fatigue, not knocked down) with its feet under water has no breath left from that
  moment and takes the suffocation damage from that frame; while an actor takes that damage, the drowning sound plays
  on it whenever it is not already playing. In the engine, the point under the feet and the combat layer's knocked-out
  state now put a person into the drowning table at once, stepped as submerged, and Water Breathing still keeps the person
  breathing. The player's drowning sample from the image's settings starts on the person's own sound channel and starts
  again once its length has passed. Two more counters on the breath status lines show how often each happened, and New
  Game clears them. The drowning table's rows grow from 8 to 12 bytes (32 rows, 384 bytes, 128 more), there is one more
  point test per person in a room with water each frame, and no new file or allocation. The rules are pure functions with
  a native test of their own. People still do not swim up for air and do not yet drown in the water outdoors
  (ACTOR-KNOCKED-OUT-IN-WATER-DROWNS-68, ACTOR-DROWN-SOUND-68; the water row of
  [the game features](../../GAME_FEATURES.md) says what is carried). Covered by tests and the gate 12274; not seen in
  play.

### Solstheim

- **The debug teleport's place list counts the frames of the expansions' own stores.** The table of named places and
  of the people and creatures standing outdoors near them read only the base world's frames, so every named place of
  Solstheim and its outdoor people and creatures were listed as not built. On the data of the v0.0.68-dev4 build the
  table now holds 94 places (82 before; the one left out is the Mortrag Glacier, whose cells are not in yet) and 1,104
  outdoor people and creatures (902 before), none of Solstheim's listed as not built (202 before); no earlier row
  changed and Mournhold's rows are as before
  ([TP-LIST-MODULE-STORE-PLACES-68](../../bugs/TP-LIST-MODULE-STORE-PLACES-68.md), open until seen in play). Covered by
  new tests and the gate of this snapshot; not seen in play.

## Builder and tools

- **The door check walks the lands that have a store of their own.** The image step ran the door check before it
  installed the stores of the lands with a frame of their own (Solstheim, Mournhold's districts), and the check read only
  the base world's directory, so every exterior entrance of those lands was listed as not usable although the door table
  linked them. The check now runs after the stores are installed, reads the lands' own rows files as part of the one
  outdoor directory and traces a door's wall in its own store's world. A frame that stands alone, with no frame across
  any side of its core, is checked in itself with the frame running at the door, as a town is, because the player arrives
  there by a door or a teleport; six entrances of Mournhold's Royal Palace courtyard had been listed as not usable for
  that reason alone ([DOOR-CHECK-MODULE-FRAME-MAPS-67](../../bugs/DOOR-CHECK-MODULE-FRAME-MAPS-67.md), open). On the
  stage folders of the v0.0.68-dev4 build the check reads 1,225 exterior entrances, 1,224 usable after walking in (1,102
  before, when none of the 123 entrances of the two lands was walked), 1,222 both ways and 1,210 with the wall traced; the
  base world's own counts are as before (1,102 usable, one known trapdoor). The baseline file stays at the base world's
  numbers, so a build without the expansions is still compared. Covered by new tests of the check, and the gate 12012.
- **The 13 entrances the check cannot reach are listed.** In the converted collision of their frames, 11 entrances have no
  standing spot within 80 units above the threshold and 2 have the door out of the use reach (82 and 86 units): seven ice
  cave doors, Castle Karstaag's Throne Room door, Glenschul's Tomb, Rimhull's trapdoor, two Raven Rock houses of later
  colony stages and the ladder to Bamz-Amschend in Mournhold. A whole-world image stops on an unreachable entrance that is
  not on the known list, so they are on the list in `config/door-check-known.json` with what was measured, under the new
  entry [DOOR-USE-COLLISION-EXPANSIONS-68](../../bugs/DOOR-USE-COLLISION-EXPANSIONS-68.md); each leaves the list when the
  check reaches it. [The door mapping page](../../DOOR_MAPPING.md) says what the check covers now.
- **The bug tracker** records the faults of the glacier work and of the palette test builds (see Known in this build).

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

The [checklist of dev4](RELEASE-v0.0.68-dev4.md#in-game-checklist-for-this-snapshot) stands. In addition: in a room with
water, knock a person out with the feet in the water (fatigue to zero) and watch the person's breath run out at once; listen
for the drowning sound on a person who takes the suffocation damage, and check that it is not played over itself; with
Water Breathing on that person, check that nothing happens.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run (927 run and 9 are carried by
AmiWind's own code, of 1,074); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
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
- **The glacier's ice:** in the glacier test images the Mortrag Glacier's ice draws brown-grey instead of white and shows a
  sheer vertical drop where the original slopes. It is seen with today's methods and with method E (the reduced collision and
  the simplified drawn mesh together), so it does not come from the method chosen; the cause of the colour is known (the image's palette has no
  white), a fix is being tested and is not in this snapshot, and the sheer walls follow the original's own shapes
  ([SOL-GLACIER-ICE-BROWN-SHEER-68](../../bugs/SOL-GLACIER-ICE-BROWN-SHEER-68.md), open).
- **Entrances that cannot be reached:** 13 exterior entrances of Solstheim and Mournhold have no standing spot at the
  threshold in the converted collision, or the door lies out of the use reach, so the player may not be able to use them;
  the door check lists them so that a build is not stopped
  ([DOOR-USE-COLLISION-EXPANSIONS-68](../../bugs/DOOR-USE-COLLISION-EXPANSIONS-68.md), open).
- **Doors that a script swaps:** where a script switches between two doors at one place (the houses of the Skaal village
  before and after the attack, Raven Rock's buildings at each stage of the colony), the use key can still pick the door
  the script has switched off, so the door may lead to the wrong room; the door check is right at the game's start
  ([DOOR-LOAD-DISABLED-STILL-USED-68](../../bugs/DOOR-LOAD-DISABLED-STILL-USED-68.md), open).
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
  ([BUILD-READINESS-MISSES-PLAN-WAIVERS-68](../../bugs/BUILD-READINESS-MISSES-PLAN-WAIVERS-68.md)); all open.
- **In the tools, builder:** a change of the scene palette re-bakes every Balmora interior room, although 24 of its 43 room
  maps come out byte for byte the same (the residents' models do change with the palette, so their re-bake is needed)
  ([BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68](../../bugs/BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68.md)); a fresh census stage
  ran on under 4 of 22 cores for about 6 minutes before its worker pool started
  ([BUILD-CENSUS-PHASE-UNDERUSED-68](../../bugs/BUILD-CENSUS-PHASE-UNDERUSED-68.md)); both open.
- **The look book** checks only the numbers on its pages, so a palette change that alters the colours of every confirmed
  look cannot fail a page and its stills are compared by hand
  ([LOOKBOOK-NO-COLOUR-CHECK-68](../../bugs/LOOKBOOK-NO-COLOUR-CHECK-68.md), open).
- From [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and
  its snapshots: their Known lists stand for what is not named here, among them Mournhold's and Solstheim's unfinished
  play. Every other open entry is in the [bug tracker](../../BUGS.md).
