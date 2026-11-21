# AmiWind v0.0.68-dev3 (in development)

_Last updated with AmiWind v0.0.68-dev3 (21 November 2026)._

Development snapshot, 21 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev2](RELEASE-v0.0.68-dev2.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The third snapshot of v0.0.68. The version has no title yet. It brings the first of Solstheim into the build: the 135
finished open terrain cells of the island, as a world of their own, reached by a debug teleport only for now and not yet
seen in play. It also adds the original's console commands for spells, items and topics (family 6 of the list), makes the list of taken and disabled outdoor pieces unlimited, hides every outdoor piece a script can
switch off, and brings builder work for Solstheim's collision and for the keys of the outdoor world stage. Its emulator
presets, `AmiWind-v0.0.68-dev3-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev3-WinUAE.uae`, both start with 32 MB of Fast RAM,
which the game needs.

How each change was checked is said on its line. None of the changes of this snapshot has been seen in play yet: they are
covered by their tests and by the gates of their own branches (the console commands 12263, the outdoor pieces taken or
disabled 12264, the outdoor pieces that scripts switch off 12265, and the Solstheim branch with the builder work 12050,
12054 and 12055). The bug tracker entries are set fixed when this snapshot is recorded and the changes are seen in play.

## New since v0.0.68-dev2

### Solstheim, first cells in the build

- **135 of Solstheim's 144 open terrain cells are in the build, as a world of their own.** Of the 135 finished cells,
  110 are land and 25 are sea floor; the build module for Bloodmoon's island (work in progress) holds them as frames.
  [The CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) counts from the newest ingested build, which is not this
  snapshot's, so it still counts Solstheim's cells as not in the game until this snapshot's build is ingested. Two more of Solstheim's
  rocks (`terrain_rock_bm_65` and `terrain_rock_bm_64`) were accepted as standing-hull chains, each with its measured
  depth, before the list was counted again. They are in the build, to be seen in play:
  - The cells are reached only with the debug teleport to their frames (`dbg tp` to `sl0000` up to `sl0134`). No door,
    travel route or place name leads to Solstheim yet.
  - There are no people, creatures or containers outdoors beyond what the frames carry, and no sea frames around the
    coast.
  - The trees are the original's models.
  - The glacier and its eight neighbouring cells are not in yet: their collision is being reworked (see Builder and
    tools below and Known in this build).

### More of the original's console commands

- **Console commands of the original for spells and items, typed on the console.** `Cast`, `ExplodeSpell`,
  `RemoveSpellEffects`, `GetSpellEffects`, `GetEffect`, `HasItemEquipped`, `Drop` and `AddTopic` (family 6 of the
  original's commands). The console finds the spell, the item and the topic from what is typed, as the commands that
  were already in do; `Cast` by the player selects the spell, as the original does. `Drop` with a count below 0 is
  refused and with 0 does nothing. [The console command list](../../CONSOLE_COMMANDS_MORROWIND.md) states each command's
  state (395 commands, 309 of them run through the script interpreter, 48 planned). Covered by tests and the gate; not
  seen in play.
- **`GetEffect` knows all 143 magic effects.** It knew 84, up to Fortify Skill, and named three of them by another name
  than the game's; a `GetEffect` of any of the other 59 (the resistances, absorbs, summons, bound items, Tribunal's and
  Bloodmoon's) compiled to a constant 0. It now takes each effect by its game setting id, with or without the `sEffect`
  prefix, or by number ([GETEFFECT-TABLE-84-OF-143-68](../../bugs/GETEFFECT-TABLE-84-OF-143-68.md)). The three game
  files' own `GetEffect` lines name five effects, all at the numbers they had, so their compiled code is unchanged.

### Fixed

- **Taken and disabled outdoor pieces have no limit.** The list of outdoor pieces taken or disabled held 64 for each map;
  past that a taken piece stayed drawn and solid. It is now one bit for each placement a frame owns, sized from the
  build's own count (Vivec's frame, the largest with 7,537 placements, needs 943 bytes; the median frame 46), so every
  placement of a loaded frame can be gone at once. An id that belongs to no loaded frame is refused, counted and named in
  `chim status`. What is taken or disabled is saved as before
  ([CHIM-GONE-LIST-64-CAP-68](../../bugs/CHIM-GONE-LIST-64-CAP-68.md)). Covered by tests and the gate; not seen in play.
- **Outdoor pieces that a script switches off are hidden.** A script that disabled an outdoor piece hid only carriable
  lights, so a disabled building stage or marker stayed drawn and solid. Every outdoor piece that a script of the game
  can disable or enable now has its hide row, in Vvardenfell and in Mournhold's districts, and the build's check refuses
  an image where one is not linked
  ([OUTDOOR-DISABLE-NOT-HIDDEN-68](../../bugs/OUTDOOR-DISABLE-NOT-HIDDEN-68.md)). Measured on the v0.0.67 release
  build: 459 Vvardenfell placements with 1,579 pieces, 18,948 bytes of rows on disk. Covered by tests and the gate; not
  seen in play. See Known in this build for the objects that are not in the world at all.
- **A scripted `Drop` leaves what the actor carries, as in the original.** Checked against the original's rule, the
  behaviour was right: the entry is closed as not a fault
  ([DROP-ONLY-WHAT-IS-CARRIED-68](../../bugs/DROP-ONLY-WHAT-IS-CARRIED-68.md)).

### Builder and tools

- **The outdoor world stage is keyed by the base game's files again.** Since the source catalogue cache, a change of
  the expansions' files or of the selection of masters would have rebuilt the whole base world. A stage now reads the
  expansion layers only by its own code; measured on the v0.0.68-dev1 build's 50 stages, only the outdoor world stage's
  key changes, back to the base game's files
  ([BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68](../../bugs/BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68.md)).
- **Collision for Solstheim's ice, in the larger map format.** Some standing-hull unions the collision compiler refuses
  in its standard format (more than 32,767 nodes) are compiled in the larger one for the meshes a list names: 27 of 57
  copies of the iceberg shard were raw chains of 1.79 MB each and are about 0.95 MB compiled, and the glacier's two
  icebergs come out at 6.9 and 4.4 MB instead of 10.8 and 6.1 MB
  ([CHIM-COLLISION-UNION-FALLBACK-41](../../bugs/CHIM-COLLISION-UNION-FALLBACK-41.md)). A union that would be over one
  image's budget keeps its fallback instead of stopping the stage. No other unit kind changes its key.
- **A neighbour's model pieces beyond a frame's edge are left to the frame of their own cell.** The pieces of a large
  model (around Solstheim's glacier, 163 iceberg tiles) were all given to one corner chunk of each neighbouring frame, so
  one memory ring held them all; they are now left out of a frame where the cell under them has a frame of its own, and
  stay where no such frame exists
  ([CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68](../../bugs/CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68.md)). The base world's
  frames do not change.
- **Solstheim's world stage takes the units a conversion run of the same cells already made.** The stage reads and feeds
  the builder's shared storage pool, and the pool's cache now reaches the converter's worker processes
  ([SOL-MODULE-CACHE-NOT-PICKLED-68](../../bugs/SOL-MODULE-CACHE-NOT-PICKLED-68.md)): in this snapshot's build it took
  19,434 units (772.9 MB) from the pool and converted the rest.
- **The reference of Solstheim's cells is published again** from the project's cell tracker: 144 cells, 135 finished, 8
  that fail the memory check (the glacier's neighbours) and the glacier's own cell, which is not converted yet.
- **The bug tracker** records the faults and sightings of the night of 20 to 21 November (see Known in this build).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (its first cells are in
  this snapshot), the expansions' remaining scripts and dialogue, the save with their counts and the playtests.
- **Audits of what the original has**, planned: every creature record checked field by field against its original
  (CREATURE-RECORDS-PARITY-AUDIT-68), every lever, valve, button and crank listed with whether it works
  (ACTIVATORS-AUDIT-ALL-LANDS-68), and the progress summary showing cells converted but not yet in an image
  (TOOLKIT-SOL-CONVERTED-COUNT-68); see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev2](RELEASE-v0.0.68-dev2.md#in-game-checklist-for-this-snapshot) stands. In addition: teleport with
`dbg tp` to Solstheim's frames, from `sl0000` up to `sl0134`, and look at the ground, the rocks, the trees and the
coast (the nine cells around the glacier are not there); type `Cast`, `ExplodeSpell`, `GetEffect`, `HasItemEquipped`,
`Drop` and `AddTopic` on the console; take or disable many pieces outdoors in one place with the console and see them
leave; in a stronghold that builds in stages, see the stage's pieces switch.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run (927 run and 9 are carried by
AmiWind's own code, of 1,074); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
part has come.

- **Solstheim:** the cells are reached only with the debug teleport. No door, travel or place name leads there, and the
  sea around the coast, the people, the creatures and the containers outdoors are not in. The glacier and its eight
  neighbouring cells are not in: their collision is being reworked, and two ice coast cells convert with a memory ring far
  over the budget ([SOL-ICE-CELLS-RING-OVER-68](../../bugs/SOL-ICE-CELLS-RING-OVER-68.md)), and one cell stops for a
  person placed outdoors without a ground class
  ([SOL-COVENTINA-NO-GROUND-CLASS-68](../../bugs/SOL-COVENTINA-NO-GROUND-CLASS-68.md)); both open. Twelve of
  Solstheim's models with stairs keep the original's collision for their steps, because the builder's stair method
  cannot yet make them pass its stair check: a door, the Dwemer steam machine, two barrow tombs, the colony's buildings
  and wall, its pier, a bridge and a garden plot
  ([CHIM-STAIR-METHOD1-UNFIXED-48](../../bugs/CHIM-STAIR-METHOD1-UNFIXED-48.md), open); see whether the steps of the
  colony pier and the bridge can be walked.
- **Scripted outdoor objects missing from the world:** 190 outdoor objects that scripts switch on and off are not in the
  built world at all, so nothing hides or shows them: the Ghostfence's glow, pieces of the opening and the stages of Tel
  Uvirith among them
  ([SCRIPTED-TARGETS-NOT-IN-IMAGE-68](../../bugs/SCRIPTED-TARGETS-NOT-IN-IMAGE-68.md), open).
- **A build can still run out of memory on a 32 GB machine,** and the plan for the memory runs the outdoor world stage on
  5 of 22 workers, which takes about an hour instead of about half that, because it counts the stage's large main
  process ([BUILD-MEMPLAN-CHIM-5-OF-22-68](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md),
  [BUILD-TESTER-32GB-OOM-67](../../bugs/BUILD-TESTER-32GB-OOM-67.md),
  [BUILD-CHIM-MAIN-MEMORY-46](../../bugs/BUILD-CHIM-MAIN-MEMORY-46.md), open).
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
  ([WEREWOLF-TRANSFORM-RULES-PARTIAL-68](../../bugs/WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md)), and the player keeps his
  own body ([WEREWOLF-BODY-NOT-DRAWN-63](../../bugs/WEREWOLF-BODY-NOT-DRAWN-63.md)); open.
- **Old Mournhold's sewers:** with collision off the use key does nothing on levers and cranks
  ([USE-KEY-DEAD-IN-NOCLIP-68](../../bugs/USE-KEY-DEAD-IN-NOCLIP-68.md)); the scripted teleport into Sotha Sil, Outer
  Flooded Halls lands in the hall's water
  ([ROOM-ARRIVAL-FLOODED-ON-ROOF-67](../../bugs/ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md)); both open.
- **The console:** the table of the original's console commands leaves out 110 functions of the script language, most of
  which already work when typed ([CONSOLE-CENSUS-MISSES-FUNCTIONS-68](../../bugs/CONSOLE-CENSUS-MISSES-FUNCTIONS-68.md),
  open).
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
  ([CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68](../../bugs/CHIM-HEAP-SPLIT-HULL-PLANES-DRAWN-68.md)); all open.
- From [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build), [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build)
  and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named
  here, among them Mournhold's and Solstheim's unfinished play. Every other open entry is in the
  [bug tracker](../../BUGS.md).
