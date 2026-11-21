# AmiWind v0.0.68-dev2 (in development)

_Last updated with AmiWind v0.0.68-dev2 (20 November 2026)._

Development snapshot, 20 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev1](RELEASE-v0.0.68-dev1.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The second snapshot of v0.0.68. The version has no title yet. It is not Solstheim yet: that is the work of the line, in
progress on its own branches (see [the roadmap](../../ROADMAP.md)). This snapshot mends what the maintainer's playtest of
the v0.0.67 release found in the hands: a light and a one-handed weapon held together, the third-person fists, readied
magic through doors and the item information box. It brings the water of Old Mournhold's two levers and the drowning of
people under water, both seen working in play. It adds the console commands of the original
that were missing (weather, werewolf, scripts, sounds and placing), fixes the region table that made the end of the main
quest and Mournhold's weather lines change the wrong region, and brings builder and tool work: the build's memory plan,
the region converter for Solstheim's open terrain, and the outer-hull measure of reduced models. Its emulator presets,
`AmiWind-v0.0.68-dev2-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev2-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs.

How each change was checked is said on its line. The hands fixes were seen in play on the v0.0.68-dev1 image run with this
snapshot's engine (gates 12220 and 12221 of their branch). The water levers, the floating crates and the drowning were
seen in play on a v0.0.68-dev1 image run with this snapshot's engine and script file (gates 12280 and 12281 of their
branch). The other changes are covered by their tests and the gates of their own branches (the water plane 12260, the
console commands 12262, the region converter 12044, the outer-hull measure 12240, the memory plan 12160).

## New since v0.0.68-dev1

### Fixed and seen in play

These came out of the maintainer's playtest of the v0.0.67 release on 20 November. They were seen in play on the
v0.0.68-dev1 image with this snapshot's engine. The bug tracker entries are set fixed when this snapshot is recorded.

- **A light and a one-handed weapon are held together, and both are drawn.** As in the original, a carried light in the
  left hand is held beside a one-handed weapon, a thrown weapon or the fists, in first person, in third person and in the
  inventory picture; before, the two replaced each other and the light shone from no visible model. A two-handed weapon,
  the bow or the crossbow, or readied magic, puts the light away until it is sheathed again
  ([LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67](../../bugs/LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67.md)).
- **The light key.** Raising the hands with a light equipped lights it beside the weapon or the fists; the light key
  after that puts out only the light, or lights it again, and a notice names the light and the key. The light stays in
  the hand while it is out. With the hands down the key does what it did before.
- **Third-person fists draw and punch with the original's hand-to-hand animations.** Raising the fists, a punch (chop,
  slash or thrust by the movement) and lowering them play the original's group, also while running, and the stance key
  works while the run key is held. Before, the fists showed no draw, no punch and no lowering in third person: a punch
  was heard and struck while the body did not move
  ([PLAYER-PUNCH-THIRDPERSON-39](../../bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
  [TP-DRAW-WEAPON-LAGS-67](../../bugs/TP-DRAW-WEAPON-LAGS-67.md),
  [FIGHT-STANCE-KEY-IGNORED-WHILE-RUNNING-67](../../bugs/FIGHT-STANCE-KEY-IGNORED-WHILE-RUNNING-67.md)). The
  [third-person page](../../THIRD_PERSON.md) has the detail.
- **Readied magic stays readied through doors.** What the hands hold crosses a door, a teleport or a cell change: the
  weapon or fists, the light and whether it is lit, and now readied magic, which turned into the fists after a door
  ([HANDS-STATE-LOST-THROUGH-DOORS-67](../../bugs/HANDS-STATE-LOST-THROUGH-DOORS-67.md)).
- **Enter only closes the item information box.** It no longer takes off a worn item while the player is reading about
  it; the item's action stays on the box's button and on the use key
  ([ITEM-VIEW-ENTER-UNEQUIPS-67](../../bugs/ITEM-VIEW-ENTER-UNEQUIPS-67.md); [inventory](../../INVENTORY.md)).

### New

- **Moving water in rooms, seen in play.** `SetWaterLevel` and `ModWaterLevel` move a room's water:
  the water plane, the swimming and the view under it follow, the level is saved with the game, and a placement the plane
  passed is drawn on its right side. A room whose water lies under every placement now has its plane, and the floating
  crates of Old Mournhold: Forgotten Sewer ride the water the crank raises. `GetWaterLevel` reads the room's own level
  (it read the water in the player's column, so it read 0 in Old Mournhold: Temple Sewers West). These are Old
  Mournhold's two water levers
  ([MWSCRIPT-WATER-LEVEL-STATIC-67](../../bugs/MWSCRIPT-WATER-LEVEL-STATIC-67.md),
  [GETWATERLEVEL-COLUMN-NOT-ROOM-67](../../bugs/GETWATERLEVEL-COLUMN-NOT-ROOM-67.md)). Seen in play: in Temple Sewers
  West the torch lever floods the hideout in about 12 seconds and the torches burn out; in Forgotten Sewer the crank
  raises the water, the crates float on it, the trap door then opens into the flooded hall, the same crank drains it
  again, and the level holds when the player leaves and comes back. A scripted object placed in a room without an entity
  of its own now answers `SetPos` and `GetPos`, which is what lets the crates ride the water
  ([SETPOS-MOVER-NO-ENTITY-68](../../bugs/SETPOS-MOVER-NO-ENTITY-68.md)), and a script reaches by name an object that only
  an expansion places, which is how the torch lever reaches the gang
  ([EXPANSION-TABLES-BASE-ONLY-66](../../bugs/EXPANSION-TABLES-BASE-ONLY-66.md)).
- **People drown under water in rooms, seen in play.** By the original's rule an NPC whose head is under water and who
  has no Water Breathing holds its breath for 20 seconds, then loses 3 health a second, so the flood the lever raises in
  Old Mournhold: Temple Sewers West drowns the Black Dart gang: all four were dead in the play check. The rule now takes
  every person by their fight state, so the people living in a room are counted too
  ([ACTOR-DROWNING-NOT-CARRIED-67](../../bugs/ACTOR-DROWNING-NOT-CARRIED-67.md)).
- **More of the original's console commands, typed on the console.** `ChangeWeather` and `ModRegion` (a region's weather
  and its chances); `BecomeWerewolf` and `SetWerewolfAcrobatics`; `StartScript`, `StopScript` and `ScriptRunning`
  (CONSOLE-STARTSCRIPT-STOPSCRIPT-67); `PlaySound`, `PlaySoundVP`,
  `PlaySound3D`, `PlaySound3DVP`, `GetSoundPlaying`, `StreamMusic` and `SayDone`; and `PlaceAtPC`, `PlaceAtMe` and
  `PlaceItem`. A sound or an object that no script of the game names is answered and not played or placed yet. Covered by
  tests and the gate; not seen in play. [The console command list](../../CONSOLE_COMMANDS_MORROWIND.md) states each
  command's state (393 commands, 54 of them planned).
- **ModRegion keeps the original's chances.** With fewer than ten chances given, the other weathers no longer keep the
  region's own chances, and a chance over 100 is refused
  ([MODREGION-KEEPS-UNGIVEN-CHANCES-68](../../bugs/MODREGION-KEEPS-UNGIVEN-CHANCES-68.md)).

### Fixed

- **A script's region is the region it names.** In an image with the expansions the table of regions counted the base
  game's regions only, so a script's `ChangeWeather` and `ModRegion` changed another region: the end of the main quest
  changed the Grazelands' weather instead of Red Mountain's, and Tribunal's Mournhold weather lines did nothing. The
  table now follows the masters the build uses
  ([REGION-INDEX-BASE-ONLY-68](../../bugs/REGION-INDEX-BASE-ONLY-68.md)). Covered by tests and the gate.

### Builder and tools

- **The region converter, for Solstheim's open terrain.** A CHIM import cell now uses the frame settings and converter
  switches of a default build, so its units carry the keys a build asks for and its memory figures are measured on frames
  stored as a build stores them; a new region cell shape builds each cell as the frame a build installs for it, with its
  neighbours' placements and terrain in an apron; and a build's world stage for Solstheim takes the units a CHIM import
  made from the shared storage pool instead of converting them again
  ([CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68](../../bugs/CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68.md),
  [CHIMPORT-HEAP-NOT-BUILD-FRAMES-68](../../bugs/CHIMPORT-HEAP-NOT-BUILD-FRAMES-68.md)). Solstheim's open terrain is
  converted cell by cell on this converter, but it is not in the game yet, and a build module that would install it is
  work in progress: this snapshot's game has no Solstheim terrain, and the progress tracker still counts it as not in
  the game.
- **The build's memory plan.** A full build with no measurement of its own plans its memory from the reference build's
  stage peaks (`config/build-memory.json`): two stages that cannot fit side by side run one after another, and every
  reduction is written as a warning in the log. The room stages store each resident the moment it is baked, so a stop
  loses little, and each CHIM area's source catalogue is kept in the unit cache across runs (210 of the 294 CPU minutes
  of one CHIM stage were that catalogue). The first-minute check runs the reader of every table builder on the selected
  game files and names every failing reader together, and a module's store that cannot fit one partition is named right
  after its world stage. This is the plan itself, not yet the whole of it: see Known in this build
  (BUILD-TESTER-32GB-OOM-67).
- **The outer-hull measure of reduced models.** `tools/outer_hull.py` measures a reduced actor model against its
  original's outer measures (the box, the girth of each part, the share of the surface still covered, open edges the
  original does not have, the joins) and exits with an error when a model fails. Its first run on the v0.0.67 library
  failed the guar family, the Alit and 77 of the 83 creature models. The measure and its test are in; the reduction
  method that uses it is not in this build, and the seams stay as they were
  ([ACTOR-BAKE-NO-SEAM-STOP-68](../../bugs/ACTOR-BAKE-NO-SEAM-STOP-68.md)).
- **The build pages carry the line's version** (the build cache and the build profile).
- **The bug tracker** records the faults and sightings of the evening of 20 November (see Known in this build).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island, the expansions'
  remaining scripts and dialogue, the save with their counts and the playtests.
- **Audits of what the original has**, planned: every creature record checked field by field against its original
  (CREATURE-RECORDS-PARITY-AUDIT-68), every lever, valve, button and crank listed with whether it works
  (ACTIVATORS-AUDIT-ALL-LANDS-68), and the progress summary showing cells converted but not yet in an image
  (TOOLKIT-SOL-CONVERTED-COUNT-68); see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of the v0.0.67 snapshots](RELEASE-v0.0.67-dev3.md#in-game-checklist-for-this-snapshot) stands. In
addition: carry a light and a one-handed weapon together and raise the hands (both are held, the light key puts out only
the light); draw and punch with the fists in third person, also while running; ready a spell and walk through a door
(the spell stays readied); read an item's information box and press Enter (it only closes); in Old Mournhold: Temple
Sewers West and Forgotten Sewer, turn the water levers and watch the water, the crates and the people in it; type
`ChangeWeather` and `ModRegion` on the console.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run; the
[CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Wild creatures:** a wilderness mudcrab in the Ascadian Isles turned into several copies that stand inside each other
  and jump between positions, and the combat music kept playing after they were dead; both mudcrabs left empty corpses
  ([CREATURE-DUPLICATE-SPAWN-WARP-68](../../bugs/CREATURE-DUPLICATE-SPAWN-WARP-68.md), seen once, cause not known). A
  hostile scrib out of reach runs away instead of attacking
  ([CREATURE-HOSTILE-FLEES-67](../../bugs/CREATURE-HOSTILE-FLEES-67.md)); all open.
- **Seyda Neen:** going back into the census office from its courtyard after a played session stops the game with a
  model cache error ([CENSUS-COURTYARD-REENTRY-CRASH-68](../../bugs/CENSUS-COURTYARD-REENTRY-CRASH-68.md), open).
- **Reduced models' seams:** the models of creatures and people reduced for the game still have open seams and, on the
  skeletal ones, thinned limbs, because the rest frame is stored on a byte grid spanning every pose and the default bake
  runs no seam check ([ACTOR-BAKE-NO-SEAM-STOP-68](../../bugs/ACTOR-BAKE-NO-SEAM-STOP-68.md),
  [SKEL-POSE-GRID-THINS-LIMBS-68](../../bugs/SKEL-POSE-GRID-THINS-LIMBS-68.md), open). The outer-hull measure above shows
  which models fail; the reduction that fixes them is not in this build.
- **The werewolf:** turning into one changes only the stats and takes the gear off; the health, the readied spell,
  temporary effects, the closed windows and the witnesses of the change are not carried
  ([WEREWOLF-TRANSFORM-RULES-PARTIAL-68](../../bugs/WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md)), and the player keeps his
  own body ([WEREWOLF-BODY-NOT-DRAWN-63](../../bugs/WEREWOLF-BODY-NOT-DRAWN-63.md)); open.
- **Old Mournhold's sewers:** the first crank of Forgotten Sewer was worked in the play check through the same use as the
  key but not yet by the key itself from a spot where the player stands, and whether the dead count of the Black Dart gang
  is right after a real fight without the lever is still to be checked. With collision off the use key does nothing on
  levers and cranks ([USE-KEY-DEAD-IN-NOCLIP-68](../../bugs/USE-KEY-DEAD-IN-NOCLIP-68.md)); the scripted teleport into
  Sotha Sil, Outer Flooded Halls lands in the hall's water
  ([ROOM-ARRIVAL-FLOODED-ON-ROOF-67](../../bugs/ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md)); both open.
- **The console:** the table of the original's console commands leaves out 110 functions of the script language, most of
  which already work when typed ([CONSOLE-CENSUS-MISSES-FUNCTIONS-68](../../bugs/CONSOLE-CENSUS-MISSES-FUNCTIONS-68.md),
  open).
- **Solstheim:** its open terrain is not in the game. Two ice coast cells convert with a memory ring far over the budget
  ([SOL-ICE-CELLS-RING-OVER-68](../../bugs/SOL-ICE-CELLS-RING-OVER-68.md)) and one cell stops for a person placed outdoors
  without a ground class ([SOL-COVENTINA-NO-GROUND-CLASS-68](../../bugs/SOL-COVENTINA-NO-GROUND-CLASS-68.md)); both open.
- **A build can still run out of memory on a 32 GB machine.** The memory plan above is in; the split of the CHIM world
  stage's main process, which holds about 24 GiB, is in work
  ([BUILD-TESTER-32GB-OOM-67](../../bugs/BUILD-TESTER-32GB-OOM-67.md),
  [BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md), open).
- **In the tools:** a CHIM import request for one cell whose coordinate starts with a minus sign is refused
  ([AW-CHIMPORT-ONE-NEGATIVE-CELL-68](../../bugs/AW-CHIMPORT-ONE-NEGATIVE-CELL-68.md)); one new row in the expansions'
  grounding id file re-keys the base world stage and the Mournhold module
  ([BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68](../../bugs/BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68.md)); the source
  catalogue cache puts the settings of unrelated modules into one key
  ([BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68](../../bugs/BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68.md)); a delivery resumed for a newer
  commit stops for want of its source export
  ([DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68](../../bugs/DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68.md)); all open.
- From [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)
  and its snapshots: their Known lists stand for what is not named here, among them Mournhold's and Solstheim's
  unfinished play. Every other open entry is in the [bug tracker](../../BUGS.md).
