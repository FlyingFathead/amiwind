# AmiWind v0.0.68-dev4 (in development)

_Last updated with AmiWind v0.0.68-dev4 (21 November 2026)._

Development snapshot, 21 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev3](RELEASE-v0.0.68-dev3.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The fourth snapshot of v0.0.68. The version has no title yet. It builds every invisible wall of the game as a solid
box a script can switch, adds the Ghostfence's glow and the curtain's own moving layers behind switches, takes the
original's console commands for the interpreter's own opcodes, for moving between cells and for every other function of
the script language, and brings builder work for the glacier of Solstheim and for the image's disk plan. Its emulator
presets, `AmiWind-v0.0.68-dev4-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev4-WinUAE.uae`, both start with 32 MB of Fast RAM,
which the game needs.

How each change was checked is said on its line. None of the changes of this snapshot has been seen in play yet: they are
covered by their tests and by the gates of their own branches (the walls and the Ghostfence with the console commands
12271 and 12273, the glacier's builder work 12057, 12323 and 12327, the image's disk plan 12011). The bug tracker entries
are set fixed when this snapshot is recorded and the changes are seen in play.

## New since v0.0.68-dev3

### Invisible walls and the opening's barriers

- **Every collision marker of the game is a solid box a script can switch.** The game's masters place markers that have
  only their collision left: the five lids over Mournhold's districts, which show "You may not leave the city this way."
  in the original, the wall at exterior cell 15,5 and the platform under the falling mage at -3,-8. They were not in the
  image at all; now each is a box at the original's place, size and turn, written to the image's wall table (1,218 bytes
  for the three game files, 13.6 s to write). The engine reads the table at every server spawn and sweeps the boxes of
  the loaded map as it does the opening's, for the player walking or levitating. A box is on while the list of what
  scripts took or disabled has no row against it, so a script's Disable switches it off, and a box the player met
  answers a script's `GetCollidingPC` for a tenth of a second, which the lids' message script reads. The opening's own
  boxes keep their tables byte for byte and their story condition, so with no row against them they behave as before
  ([INVISIBLE-WALLS-NOT-BUILT-68](../../bugs/INVISIBLE-WALLS-NOT-BUILT-68.md)). The boxes' builder is a module of its own,
  so only the engine and the image stage are built again for it and no CHIM world stage is. Covered by tests and the
  gate 12271; not seen in play.

### The Ghostfence

- **The pylons' glow, the blight cloud's plume and the curtain's scrolling layers, each behind a switch.** The 132
  particle emitters of the Ghostfence's 66 pylons and the blight cloud over Dagoth Ur's mountain are each drawn as one
  sprite, baked at image assembly from the emitter's own settings in the original's model (birth rate, life, speed,
  wind, grow and fade, colour keys, texture, blend). The engine draws the nearest in front of the view, and a row whose
  placement a script disabled is not drawn, so the pylons go dark once the Heart is destroyed. The curtain's three
  layers (two of one texture at two speeds, one of the other, each swaying) are composed into one texture once a drawn
  frame, with a slow pulse, and drawn from it. The switches are settings that are not saved, set in the image's default
  settings: the glow is off (`aw_glow 0`) until its cost in frames is measured, the curtain is off (`aw_curtain 0`, the
  rippling curtain as before), and `dbg glow` and `dbg curtain` on the debug console change them, `dbg glow draw` and
  `dbg glow range` set the glow's draw count and range ([GHOSTFENCE-NO-ANIMATION-46](../../bugs/GHOSTFENCE-NO-ANIMATION-46.md)). The builder's part is a module of its
  own that only the image step reads. Covered by tests and the gate 12273; not seen in play, and its frame cost is not
  measured.

### More of the original's console commands

- **The interpreter's own opcodes typed on the console** (family 7 of the original's commands): `MenuMode`,
  `OnActivate`, `CellChanged`, `GetSecondsPassed`, `Random`, `XBox`, `GetButtonPressed`, `DontSaveObject`, `Fall` and
  `GetSquareRoot`, each answering what its opcode reads by OpenMW's rules: `MenuMode` is 1 while the console is open,
  `Random` takes the next roll of the one generator the scripts use, `GetSquareRoot` of a negative number is 0, and
  `DontSaveObject` and `Fall` do nothing. `CellChanged` and `OnActivate` read the target's own script, never the
  console's scratch one.
- **The cell commands:** `PositionCell`, `PlaceItemCell`, `AIFollowCell`, `AIEscortCell` and `GetPCCell`. The image holds
  a table of every cell a console line can name, on disk and none of it resident: 1,423 interior and exterior names with
  the districts the build presents as exterior cells, and 1,559 grid cells named as OpenMW names them (its own name, else
  its region's, else the default). `PositionCell` of the player goes into the room at the point, as a door arrival would,
  where before it went to the cell by the debug teleport and without the point; a cell the game does not have does
  nothing, as in the original; `AIFollowCell` into an unknown cell goes outdoors and `AIEscortCell` into one starts no
  package.
- **The list of console commands names every function of the script language.** 107 functions that the compiler knows but
  the list did not name were added, grouped as the original registers them; 105 of them already ran when typed, and
  `MessageBox` and `Say3D` stay planned. [The console command list](../../CONSOLE_COMMANDS_MORROWIND.md) now counts 502
  commands, 428 of them run through the script interpreter and 36 planned (dev3's count was 395, 309 and 48)
  ([CONSOLE-CENSUS-MISSES-FUNCTIONS-68](../../bugs/CONSOLE-CENSUS-MISSES-FUNCTIONS-68.md)). A test fails when a function
  of the compiler has no row. Covered by tests and the gates 12271 and 12273 of the branch; not seen in play.

## Builder and tools

- **Solstheim's glacier: named sets of mesh methods.** `config/mesh-method-sets.json` names sets of ways to fit the
  glacier's ice into memory, each for the listed ice models only: the baseline (today's methods), `C` (the collision with
  exact footing on the iceberg shard and both icebergs: faces the player can stand on are kept, the others become convex
  pieces tested against today's collision on an 8-unit grid and split where one would rise over it, measured on the nine
  glacier cells' copies before any run: nothing lost, the shard's pieces 0.24 of today's, the icebergs' 0.30 and 0.74),
  `D` (the shard's drawn mesh simplified with its seams locked) and `E` (both). `--chim-mesh-method-set NAME` reaches only
  Solstheim's stages, and a CHIM import takes the set with `--mesh-method-set` (the master builder's request takes it as
  `mesh_method_set`); the set is part of each cell's key. The base world's command, key and output are the same with any
  set. Covered by tests and the gates 12057 and 12323.
- **The glacier test images' route.** The test image of named Solstheim cells converts its world stage through a runner
  of its own, from the shared storage pool and the folder's own master alone
  ([CHIM-SOL-TEST-MASTERS-NOT-IN-FOLDER-68](../../bugs/CHIM-SOL-TEST-MASTERS-NOT-IN-FOLDER-68.md)), leaves the Solstheim
  module out of the image, says so in its plan and its records, and is refused for a release candidate or a final
  ([CHIM-SOL-TEST-TWO-CHIMSOL-STORES-68](../../bugs/CHIM-SOL-TEST-TWO-CHIMSOL-STORES-68.md)). The first-minute check that
  every finished cell of a selected expansion is built accepts that only for such a test image on a development version.
  Gates 12323 and 12327.
- **The glacier's two icebergs on the stair check's known list.** The Mortrag Glacier's two icebergs fail the stair
  check on natural ice terraces and keep the original's collision, as the twelve of Solstheim's models with stairs
  already do ([CHIM-STAIR-METHOD1-UNFIXED-48](../../bugs/CHIM-STAIR-METHOD1-UNFIXED-48.md)). The glacier itself is not in
  the build: the comparison of the methods is under way, and its current state is on
  [the glacier page](../../chim/SOLSTHEIM_GLACIER.md), which now says how a way is chosen for a build and describes the
  sets.
- **The image's disk plan counts the expansions' stores.** The payload preflight planned the disk layout before the
  image step installed Solstheim's, Mournhold's and the Tribunal rooms' stores, which added 172,615,780 bytes in 3,798
  files to the boot partition in the v0.0.68-dev3 build, and the overrun was met only after the image step's own work. The
  preflight now counts each store's files at their own sizes and the first plan moves what the boot partition cannot hold;
  on that build's stage folders the count equals the image's record byte for byte
  ([IMAGE-BOOT-PAYLOAD-OVER-2GIB-48](../../bugs/IMAGE-BOOT-PAYLOAD-OVER-2GIB-48.md)). Gate 12011.
- **The bug tracker** records the faults and sightings of the night and the morning of 20 to 21 November (see Known in
  this build).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (its first cells are in
  the build since dev3, its glacier is being compared), the expansions' remaining scripts and dialogue, the save with
  their counts and the playtests.
- **Audits of what the original has**, planned: every creature record checked field by field against its original
  (CREATURE-RECORDS-PARITY-AUDIT-68), every lever, valve, button and crank listed with whether it works
  (ACTIVATORS-AUDIT-ALL-LANDS-68), and the progress summary showing cells converted but not yet in an image
  (TOOLKIT-SOL-CONVERTED-COUNT-68); see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev3](RELEASE-v0.0.68-dev3.md#in-game-checklist-for-this-snapshot) stands. In addition: walk to the
edge of each of Mournhold's districts and try to leave it where the original stops the player, and see the message; at
exterior cell 15,5, find the wall; with the glow and the curtain switched on by `dbg glow` and `dbg curtain`, look at the Ghostfence's
pylons, the blight cloud over Red Mountain and the curtain, and read the frame rate beside them; type
`PositionCell`, `PlaceItemCell`, `AIFollowCell`, `AIEscortCell`, `GetPCCell`, `Random`, `MenuMode` and `GetSquareRoot`
on the console.

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
  ([CHIM-STAIR-METHOD1-UNFIXED-48](../../bugs/CHIM-STAIR-METHOD1-UNFIXED-48.md), open). In dev3's build, Fort Frostmoth's
  dock ran at about a quarter of the island's usual frame rate when looking over the dock and the ship
  ([SOL-FROSTMOTH-DOCK-FRAME-RATE-68](../../bugs/SOL-FROSTMOTH-DOCK-FRAME-RATE-68.md)), and loading a frame spent about two
  and a half seconds reading eight kilobytes of area tables
  ([AREA-TABLES-SLOW-READ-ON-LOAD-68](../../bugs/AREA-TABLES-SLOW-READ-ON-LOAD-68.md)); both open.
- **Scripted outdoor objects missing from the world:** 190 outdoor objects that scripts switch on and off are not in the
  built world at all, so nothing hides or shows them: pieces of the opening and the stages of Tel Uvirith among them. The
  Ghostfence's glow now has its own rows in this snapshot, behind a switch that is off
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
- From [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build),
  [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build), [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build)
  and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named
  here, among them Mournhold's and Solstheim's unfinished play. Every other open entry is in the
  [bug tracker](../../BUGS.md).
