# AmiWind v0.0.68-dev9 (in development)

_Last updated with AmiWind v0.0.68-dev9 (23 November 2026)._

Development snapshot, 23 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev8](RELEASE-v0.0.68-dev8.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The ninth snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one finishes the build of Solstheim's cells (all 153 are built) and mends
what kept its quest and underwater entrances shut: the ice covers and the rock that a quest stage removes are hidden as
they should be, a door under the crosshair takes the use key from a creature standing around the player, and a player put
into water stays at that depth. Named objects whose script answers on use now take the use key. The player in werewolf
form is drawn as the werewolf, and a script's ForceGreeting opens the conversation as the original does. The builder's
release check refuses a release with a missing space. Its emulator presets, `AmiWind-v0.0.68-dev9-FS-UAE.fs-uae` and
`AmiWind-v0.0.68-dev9-WinUAE.uae`, both start with 32 MB of Fast RAM, which the game needs.

How each change was checked is said on its line. Every change here is covered by tests and by the gate of its commits
(12760 for the sea cells, 12840, 12841 and 12842 for the entrances and the use key, 12783 for the werewolf, 12547 for
ForceGreeting, 12828 for the build cache). The entrances, the ice wall's question and the player's werewolf form are seen
in play on the PC emulator, said on their lines; the rest is not yet seen in play. The bug tracker entries are set fixed
in source where the change mends a fault; they are closed when this snapshot is recorded.

## New since v0.0.68-dev8

### Solstheim

- **All 153 cells of Solstheim are built.** The two open-sea cells that dev8 left out, -29,23 and -28,24, hold nothing but
  water. The CHIM import took every open-sea cell for the main island's, so these two were counted wrongly and never
  built; it now names each cell's island from the master that holds its record
  ([TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68](../../bugs/TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68.md)). Covered by tests and the
  gate 12760; not yet seen in play.
- **Entrances that a quest stage opens are usable.** A placement that an expansion's script switches off was not hidden:
  the ice covers at Stahlman's Gorge and at the Caves of Fjalding and the rock at Glenschul's Tomb stayed drawn and solid
  after their quest stages, so the entrances could not be used. The pieces a script switches off are now matched by their
  stable reference and hidden; the same hides 840 placements of Mournhold
  ([EXPANSION-STORE-DISABLE-NOT-HIDDEN-68](../../bugs/EXPANSION-STORE-DISABLE-NOT-HIDDEN-68.md)). Seen in play on the PC
  emulator: after the quest stages the covers and the rock are gone, and Stahlman's Gorge, the Caves of Fjalding and
  Glenschul's Tomb were entered. The Mournhold placements are not checked in play yet.
- **A door the crosshair meets takes the use key from a creature around the player.** A creature's use box that held the
  player's eye took the focus, so the use key went to the creature and the door beside it could not be used, among them the
  Unmarked Shipwreck's trapdoor with a dreugh attacking. A load or hinged door the crosshair ray meets now has the focus
  ([FOCUS-EYE-INSIDE-ACTOR-BOX-68](../../bugs/FOCUS-EYE-INSIDE-ACTOR-BOX-68.md)). Seen in play: the first use key loaded the
  Unmarked Shipwreck, Upper Level.
- **A player put into water stays at that depth.** A teleport with a height into water (a script's Position of the player,
  `dbg tp X Y Z`) moved the player to the water's top or to the scene's spawn; it now leaves the player where it was put
  ([SWIM-PLAYER-DOES-NOT-STAY-AT-DEPTH-68](../../bugs/SWIM-PLAYER-DOES-NOT-STAY-AT-DEPTH-68.md)). Covered by tests and the
  gate 12840; the underwater entrances above were entered in play, the depth itself is not checked on its own.
- **A named object that a script answers on use takes the use key.** Placed activators whose script reads OnActivate had no
  use in play: 1,712 of them, among them beds, levers, cave-ins, shrines, the Skaal stones and the Halls of Penumbra's ice
  wall ([ROOM-SCRIPTED-ACTIVATOR-NO-USE-68](../../bugs/ROOM-SCRIPTED-ACTIVATOR-NO-USE-68.md)). Seen in play at the Halls of
  Penumbra's ice wall: the use key asks whether to throw the flaming eye at it, and Yes takes the eye, advances the quest
  stage and swaps the sconces. The other objects are covered by tests and the gate 12842 only.

### The werewolf

- **The player in werewolf form is drawn as the werewolf.** In third person the werewolf is drawn, and in first person its
  claws, readied as the original has them. The change comes by a script, the console, `dbg werewolf on|off` or the
  werewolf robe; the change back is the original's: the robe is taken away and the other items stay in the inventory. The
  werewolf is drawn only by a model that passes the builder's outer-hull check. The werewolf's two animation tables are
  let go on the change back and loaded again at the next change, and the set is let go at the next frame after the robe
  comes off, also while a torch is carried; `dbg werewolf` names the body and the arms only when they are assembled
  ([WEREWOLF-TABLES-STAY-LOADED-68](../../bugs/WEREWOLF-TABLES-STAY-LOADED-68.md),
  [WEREWOLF-SET-KEPT-WITH-TORCH-68](../../bugs/WEREWOLF-SET-KEPT-WITH-TORCH-68.md),
  [DBG-WEREWOLF-STATUS-ARMS-MISREAD-68](../../bugs/DBG-WEREWOLF-STATUS-ARMS-MISREAD-68.md),
  [WEREWOLF-TRANSFORM-RULES-PARTIAL-68](../../bugs/WEREWOLF-TRANSFORM-RULES-PARTIAL-68.md)). Seen in play on the PC emulator
  by all four routes, with the tables given back after every change back; covered by tests and the gate 12783.
- **ForceGreeting opens the conversation as the original does.** A script's ForceGreeting now opens the conversation with a
  living person even in a fight or knocked down, and is held back from a werewolf player
  ([MWSCRIPT-FORCEGREETING-TALK-RULES-68](../../bugs/MWSCRIPT-FORCEGREETING-TALK-RULES-68.md)). Seen in play on the PC
  emulator for the first and the werewolf cases (gate 12547); the greeting after the change back and a creature under the
  crosshair are not checked yet.

## Builder and tools

- **A release is refused while a space is missing.** The release check refuses a release candidate or final while any cell,
  room or load door of a shipped master is missing from the build; no kind of space is a reason to leave one out
  ([RELEASE-GATE-COMPLETENESS-LOST-67](../../bugs/RELEASE-GATE-COMPLETENESS-LOST-67.md)).
- **The boot settings size is checked again in the image's last step**, so a settings file grown past the engine's command
  buffer is found before the image is delivered, not after
  ([CFG-OVER-COMMAND-BUFFER-68](../../bugs/CFG-OVER-COMMAND-BUFFER-68.md)).
- **The door check judges by what play showed.** It uses the walk-out arrival inside the frame's core and within the
  original's reach, a door under water as a swimming player uses it, a door in the border copy of a neighbouring frame, and
  runs each door of a doorway that scripts switch between with the others switched off
  ([DOOR-USE-COLLISION-EXPANSIONS-68](../../bugs/DOOR-USE-COLLISION-EXPANSIONS-68.md),
  [DOOR-CHECK-NO-SWIM-CASE-68](../../bugs/DOOR-CHECK-NO-SWIM-CASE-68.md),
  [DOOR-CHECK-DOORWAY-STAGES-68](../../bugs/DOOR-CHECK-DOORWAY-STAGES-68.md)); the doors in the check's known list are
  fewer, the well and the ladder having left it after play showed them working.
- **A reused stage copies a file that is at the file system's link limit** instead of refusing the whole stage's reuse
  ([REUSE-POOL-LINK-LIMIT-68](../../bugs/REUSE-POOL-LINK-LIMIT-68.md)), and the reuse check reads every cache opener,
  among them the creature models' caches, so a rebuild of the actor library is counted unit by unit.
- **Test sessions run the emulator in its deterministic mode by default** (a way past the load stall in testing). The
  shipped presets are unchanged.

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (all its cells are in
  the build, its glacier since dev8), the expansions' remaining scripts and dialogue, the save with their counts and the
  playtests.
- **Solstheim's forests and distance:** the trees' method awaits the maintainer's choice from the pictures, and the region
  draw distance for Solstheim's six regions is a trial until the frame rate is measured on real hardware.
- **The werewolf for non-player characters:** the people a script turns into werewolves are not yet drawn as werewolves.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev8](RELEASE-v0.0.68-dev8.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The quest entrances.** Finish the quest stages that remove the ice covers at Stahlman's Gorge and the Caves of Fjalding
  and the rock at Glenschul's Tomb, and enter each. Swim down to the entrance under the Mortrag Glacier. Say where a cover
  stays or an entrance cannot be used.
- **Use on scripted objects.** Use a bed, a lever, a cave-in and a shrine, and the Halls of Penumbra's ice wall. Say what
  answers and what does not.
- **The werewolf.** Become a werewolf by a script, the console and the robe and look at the body in both views; change
  back. Say what looks wrong or is missing.
- **Mournhold.** Walk the districts and look for anything that was visible before and is now gone: 840 placements are hidden
  by the quest-stage rule.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Seen in play:** on the PC emulator with the gated engines, the three quest entrances and the Unmarked Shipwreck's
  entrance, the Halls of Penumbra's ice wall's question and quest stage, the player's werewolf form, and ForceGreeting for
  the first two cases. The other changes are covered by tests and the gates named above, not yet seen in play.
- **The Halls of Penumbra's ice wall** plays no breaking animation and stays in the way after its quest stage
  ([MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68](../../bugs/MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68.md), being fixed).
- **The werewolf of non-player characters:** the people a script turns into werewolves are not drawn as werewolves yet
  ([NPC-WEREWOLF-NO-MODEL-66](../../bugs/NPC-WEREWOLF-NO-MODEL-66.md), being fixed).
- **Creatures get no conversation** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open).
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play; the maintainer
  chooses the trees' method.
- **A rebuilt CHIM world differs from the cached one:** rebuilt from unchanged inputs it wrote files that differ from the
  cached build, so the stages after it run again
  ([CHIM-REBUILD-NOT-IDENTICAL-68](../../bugs/CHIM-REBUILD-NOT-IDENTICAL-68.md), open).
- From [v0.0.68-dev8](RELEASE-v0.0.68-dev8.md#known-in-this-build),
  [v0.0.68-dev7](RELEASE-v0.0.68-dev7.md#known-in-this-build), [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build),
  [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build), [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and
  its snapshots: their Known lists stand for what is not named here, among them the census courtyard re-entry stop,
  Mournhold's and Solstheim's unfinished play, the open builder entries and the look book's open entries. Every other open
  entry is in the [bug tracker](../../BUGS.md).
