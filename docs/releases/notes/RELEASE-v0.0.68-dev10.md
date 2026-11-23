# AmiWind v0.0.68-dev10 (in development)

_Last updated with AmiWind v0.0.68-dev10 (23 November 2026)._

Development snapshot, 23 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev9](RELEASE-v0.0.68-dev9.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The tenth snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one gives Bloodmoon's werewolves their bodies and their fight: the characters
a script turns into werewolves are drawn as werewolves, fight with their claws only, and every werewolf is drawn at its
race's size. A script's animation group on a placed object now leaves the object in its end pose, so the Halls of
Penumbra's ice wall breaks and the Clockwork City's lever doors open. Its emulator presets,
`AmiWind-v0.0.68-dev10-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev10-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs.

How each change was checked is said on its line. Every change here is covered by tests and by the gate of its commits. The
werewolves' fight, the player's werewolf size and the ice wall's breaking are seen in play on the PC emulator, said on
their lines; the rest is not yet seen in play. The bug tracker entries are set fixed in source where the change mends a
fault; they are closed when this snapshot is recorded.

## New since v0.0.68-dev9

### The werewolf

- **The characters a script turns into werewolves are drawn as werewolves.** Bloodmoon's scripts turn people into
  werewolves: the Skaal hunt's seven, the wild hunt's four, and the characters of the maze and the ceremony. They are now
  drawn with the werewolf's body, hold nothing in their hands, and a dead one stays a werewolf corpse
  ([NPC-WEREWOLF-NO-MODEL-66](../../bugs/NPC-WEREWOLF-NO-MODEL-66.md)). Seen in play on the PC emulator.
- **A werewolf fights with its claws only.** A turned character attacks without a weapon, a shield, armour or spells, and
  has its own gear back when it changes back. Its claw blows follow the original's claw rule. The player in werewolf form
  cannot ready magic, and a fleeing actor turns back from a werewolf near it
  ([NPC-WEREWOLF-FIGHTS-ARMED-68](../../bugs/NPC-WEREWOLF-FIGHTS-ARMED-68.md)). Seen in play: the Skaal hunt's characters
  attacked the honor guards with their claws only, no weapon and no spell. The refusal to ready magic is covered by tests
  and not yet seen in play.
- **Every werewolf is drawn at its own race's and sex's size.** The player's werewolf was checked in play for six races
  ([WEREWOLF-RACE-SCALE-68](../../bugs/WEREWOLF-RACE-SCALE-68.md)).
- **UndoWerewolf gives the player back his own attributes and skills** and takes the werewolf robe away (seen in play).

### Scripted objects

- **A script's PlayGroup or LoopGroup on a placed object leaves it in the animation's end pose.** The object is drawn and
  collided in that pose, and the pose is kept in the save. The Halls of Penumbra's ice wall breaks, the Sotha Sil lever
  doors open and the Bamz-Amschend cave-ins fall
  ([MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68](../../bugs/MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68.md)). Seen in play: the ice wall breaks,
  and a lever in the Outer Flooded Halls opens its door. The cave-ins are covered by tests only.

## Builder and tools

- **The plan's completeness report counts the cells inside the towns' frames as built**, so the report no longer lists
  them as missing before the build
  ([COMPLETENESS-PLAN-TOWN-CELLS-MISSING-68](../../bugs/COMPLETENESS-PLAN-TOWN-CELLS-MISSING-68.md)).
- **The public progress tracker is written again from the dev9 build.** It shows Solstheim at 150 of 150 land cells and
  101 of 101 rooms ([DOCS-PROGRESS-TRACKER-STALE-64](../../bugs/DOCS-PROGRESS-TRACKER-STALE-64.md)).
- **The container census test counts the room pose function among the functions** that match a reference in either form.

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island, the expansions' remaining
  scripts and dialogue, the save with their counts and the playtests.
- **Solstheim's forests and distance:** the trees' method awaits the maintainer's choice from the pictures, and the region
  draw distance for Solstheim's six regions is a trial until the frame rate is measured on real hardware.
- **The werewolf's remaining rules:** silver weapons' extra damage, the werewolf's own sounds and the readier attack on a
  werewolf.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev9](RELEASE-v0.0.68-dev9.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The werewolves of the scripts.** Take part in the Skaal hunt and the wild hunt, and look at the turned characters:
  body, size, hands and corpse. Say what looks wrong.
- **Fighting a werewolf.** Fight a turned character and fight as a werewolf: only claws, no spells. Say what a turned
  character still uses.
- **Animated objects.** Break the Halls of Penumbra's ice wall, pull the Sotha Sil levers and look at the Bamz-Amschend
  cave-ins. Say what stays in the way.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Seen in play:** on the PC emulator with the gated engines, the turned characters as werewolves and their claw fight, the
  player's werewolf at six races' sizes, UndoWerewolf, the ice wall breaking and a lever door in the Outer Flooded Halls.
  The other changes are covered by tests and the gates of their commits, not yet seen in play.
- **The broken ice wall cannot be passed:** the player does not get into the chamber behind it. The quest does not need it
  (PENUMBRA-ICE-WALL-NO-PASSAGE-68).
- **The use key offers to talk to a werewolf** (NPC-WEREWOLF-TALK-OFFERED-68).
- **Silver weapons' extra damage, the werewolf's own sounds and the readier attack on a werewolf are left**
  ([WEREWOLF-FIGHT-RULES-LEFT-68](../../bugs/WEREWOLF-FIGHT-RULES-LEFT-68.md)).
- **Akulakhan's Chamber keeps its old look:** it cannot hold its end poses within 32 MB yet.
- **Creatures get no conversation** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open).
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play; the maintainer
  chooses the trees' method.
- **A rebuilt CHIM world differs from the cached one**
  ([CHIM-REBUILD-NOT-IDENTICAL-68](../../bugs/CHIM-REBUILD-NOT-IDENTICAL-68.md), open).
- From [v0.0.68-dev9](RELEASE-v0.0.68-dev9.md#known-in-this-build),
  [v0.0.68-dev8](RELEASE-v0.0.68-dev8.md#known-in-this-build), [v0.0.68-dev7](RELEASE-v0.0.68-dev7.md#known-in-this-build),
  [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build), [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build),
  [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build), [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build),
  [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build), [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build)
  and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named
  here, among them the census courtyard re-entry stop, Mournhold's and Solstheim's unfinished play, the open builder entries
  and the look book's open entries. Every other open entry is in the [bug tracker](../../BUGS.md).
