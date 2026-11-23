# AmiWind v0.0.68-dev11 (in development)

_Last updated with AmiWind v0.0.68-dev11 (23 November 2026)._

Development snapshot, 23 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev10](RELEASE-v0.0.68-dev10.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The eleventh snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one makes fights smoother when blows land, takes the offer to talk away from a
character who is a werewolf, gives the creatures that have lines rows in the dialogue and voice tables, and gives each of
Solstheim's weathers its own look: a blizzard is a storm blowing north, and each weather has its own fog distance and
cloud speed. Its emulator presets, `AmiWind-v0.0.68-dev11-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev11-WinUAE.uae`, both
start with 32 MB of Fast RAM, which the game needs.

How each change was checked is said on its line. Every change here is covered by tests and by the gate of its commits. The
fight's frame times, the werewolf's missing offer to talk and the glacier's weathers are seen in play, said on their lines;
the rest is not yet seen in play. The bug tracker entries are set fixed in source where the change mends a fault; they are
closed when this snapshot is recorded.

## New since v0.0.68-dev10

### Fights

- **Fights no longer stutter when blows land.** Each blow read the fighters' whole spell lists from the disk again, and the
  sounds of a fight were read in the frame that needed them. The lists are now kept from the start of the fight, and the
  fight's sounds are loaded with the area
  ([AMBIENT-SOUND-READ-IN-FRAME-68](../../bugs/AMBIENT-SOUND-READ-IN-FRAME-68.md),
  [MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68](../../bugs/MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68.md)). Seen in play with six
  fighters (Toralf's band): the worst frame of the fight went from 219 ms to 50 ms, and from 296 ms to 28 ms with the think
  cap on; the blows read nothing from the disk. Still left: the first read of a voice line happens in the frame that says it.
- **`dbg combat` says where a fight's time goes.** It prints the worst frame of the fight, the worst think and the fight's
  sounds. The new cvar `aw_combat_think_cap` limits how many fighters think in one frame; it is off by default and the
  default changes only after the comparison in play.

### Werewolves and talking

- **A character in werewolf form can no longer be talked to**, as in the original: the use key offers nothing on the wild
  hunt's werewolf but its name ([NPC-WEREWOLF-TALK-OFFERED-68](../../bugs/NPC-WEREWOLF-TALK-OFFERED-68.md)). Seen in play.
- **The creatures that have lines have rows in the dialogue and voice tables**: 46 creatures over the three masters, 9 of
  them with recorded voices, among them Almalexia, Vivec, Yagrum Bagarn, Dagoth Ur, the draugr lord Aesliip and the rieklings
  Dulk and Krish ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md)). Talking to them is not done
  yet: the rows are there, the conversation is not.

### Solstheim's weather

- **A blizzard is a storm**, as in the original: a weather whose wind passes the game's storm limit is a storm, and a
  blizzard's wind blows north. Characters facing into it shield their eyes, and its snow drifts with the wind
  ([BLIZZARD-NOT-A-STORM-68](../../bugs/BLIZZARD-NOT-A-STORM-68.md)). The six regions' weather chances, colours and light
  already matched the original.
- **Each weather has its own fog distance and cloud speed**, scaled from the original's values; clear weather is
  unchanged. Snow falls in its own space ([WEATHER-FOG-CLOUDS-ONE-LOOK-68](../../bugs/WEATHER-FOG-CLOUDS-ONE-LOOK-68.md)).
  `dbg weather look off` gives the old look back, and `dbg weather` prints the numbers. Seen in play on a test image at the
  glacier under clear weather, snow and a blizzard: a blizzard's fog is about four times nearer and its clouds six times
  faster.
- **The falling effect for ash and blight storms is a switch, off by default.** `dbg ashfall 1` lets the ash fall as a
  blizzard's snow does and `dbg ashfall 2` at the old ash's speed, to compare in play before any default changes
  (BLIGHT-WIND-SPRITES-68).

## Builder and tools

- **The build volume's cleanup keeps the old runs of a build for good when a finished build request named them**
  (open; [JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68](../../bugs/JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68.md)).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island, the expansions' remaining
  scripts and dialogue, the save with their counts and the playtests.
- **Solstheim's forests and distance:** the trees' method awaits the maintainer's choice from the pictures, and the region
  draw distance for Solstheim's six regions is a trial until the frame rate is measured on real hardware.
- **Solstheim's weather:** each weather's own cloud picture and the slowed walk in storms.
- **The werewolf's remaining rules:** silver weapons' extra damage, the werewolf's own sounds and the readier attack on a
  werewolf.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev10](RELEASE-v0.0.68-dev10.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **A fight with several fighters.** Start a fight with four or more (Toralf's band, the Skaal hunt) and say whether a blow
  makes the game stop for a moment. `dbg combat` shows the worst frame.
- **The werewolf.** Look at a turned character with the use key: only its name should show, no offer to talk.
- **The weather on Solstheim.** Walk the glacier in clear weather, snow and a blizzard: say whether the blizzard looks like a
  storm (close fog, fast clouds, snow blown north) and whether characters shield their eyes facing it.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Seen in play:** the fight's frame times with six fighters, the werewolf character's missing offer to talk and the
  glacier's three weathers on a test image. The other changes are covered by tests and the gates of their commits, not yet
  seen in play.
- **Each weather's own cloud picture is left** ([WEATHER-CLOUD-TEXTURES-68](../../bugs/WEATHER-CLOUD-TEXTURES-68.md)), and
  **the walk is not slowed in storms** ([STORM-WALK-NOT-SLOWED-68](../../bugs/STORM-WALK-NOT-SLOWED-68.md)).
- **A voice line's first read still happens in the frame that says it**, so a fight's first lines can still cost a frame.
- **Creatures that have lines cannot be talked to yet** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open).
- **The broken ice wall cannot be passed:** the chamber behind it cannot be entered
  ([PENUMBRA-ICE-WALL-NO-PASSAGE-68](../../bugs/PENUMBRA-ICE-WALL-NO-PASSAGE-68.md)).
- **Silver weapons' extra damage, the werewolf's own sounds and the readier attack on a werewolf are left**
  ([WEREWOLF-FIGHT-RULES-LEFT-68](../../bugs/WEREWOLF-FIGHT-RULES-LEFT-68.md)).
- **Akulakhan's Chamber keeps its old look:** it cannot hold its end poses within 32 MB yet.
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play; the maintainer
  chooses the trees' method.
- **A rebuilt CHIM world differs from the cached one**
  ([CHIM-REBUILD-NOT-IDENTICAL-68](../../bugs/CHIM-REBUILD-NOT-IDENTICAL-68.md), open).
- From [v0.0.68-dev10](RELEASE-v0.0.68-dev10.md#known-in-this-build),
  [v0.0.68-dev9](RELEASE-v0.0.68-dev9.md#known-in-this-build), [v0.0.68-dev8](RELEASE-v0.0.68-dev8.md#known-in-this-build),
  [v0.0.68-dev7](RELEASE-v0.0.68-dev7.md#known-in-this-build), [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build),
  [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build), [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and
  [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named here,
  among them the census courtyard re-entry stop, Mournhold's and Solstheim's unfinished play, the open builder entries and the
  look book's open entries. Every other open entry is in the [bug tracker](../../BUGS.md).
