# AmiWind v0.0.68-dev12 (in development)

_Last updated with AmiWind v0.0.68-dev12 (24 November 2026)._

Development snapshot, 24 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev11](RELEASE-v0.0.68-dev11.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The twelfth snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one lays out the talk window as the original's, with the disposition bar,
the services the speaker offers and the speaker's name on the title bar; it lets the builder age its caches, so entries no
recent build uses are cleared; and it writes the main page again as a short summary of where the project stands. Its
emulator presets, `AmiWind-v0.0.68-dev12-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev12-WinUAE.uae`, both start with 32 MB of
Fast RAM, which the game needs.

How each change was checked is said on its line. Every change here is covered by tests and by the gate of its commits. The
talk window and persuasion are seen in play; the rest is not a change to play. The bug tracker entries are set fixed in
source where the change mends a fault; they are closed when this snapshot is recorded.

## New since v0.0.68-dev11

### Talking

- **The talk window is laid out as the original's.** The right column starts with the disposition bar and its number out
  of 100 (for a person only); below it come only the services the speaker offers, in the original's order (Persuasion for
  a person, Barter, Spells, Travel, Spellmaking, Enchanting, Training, Repair), a divider row, the topics, and Goodbye at
  the bottom. The divider cannot be chosen: the arrows and the wheel step over it. The speaker's name is on the window's
  title bar in the game's header font, as on the inventory and the map, and the conversation starts below it; the text and
  the column keep the console font ([DIALOGUE-WINDOW-LAYOUT-57](../../bugs/DIALOGUE-WINDOW-LAYOUT-57.md)). Seen in play.
- **Persuasion works**, seen in play on the v0.0.68-dev11 image: Admire, Intimidate, Taunt and the three bribes each answer with
  their line and move the disposition, and taunts repeated long enough make the person attack
  ([PERSUASION-BROKEN-62](../../bugs/PERSUASION-BROKEN-62.md)).
- **`dbg npcs talk` also reaches a creature that has lines**, for checks of the creature speakers' rows.

## Builder and tools

- **The build cache ages.** An entry of the CHIM unit cache, the image pass cache or the world terrain cache, and a shared
  pool key of the sound, video, script and resident NPC stages, is kept while a build has used or written it within the
  last 14 days (`--grace-days`), or while a kept run or the run a kept stage came from used or wrote it; every other entry
  expires with its files. Caches whose use is not recorded per entry are kept whole, and the plan marks a sub-cache that
  nothing used as dormant ([BUILD-CACHE-NO-RETENTION-55](../../bugs/BUILD-CACHE-NO-RETENTION-55.md),
  [the build cache](../../BUILD_CACHE.md#unit-cache-ageing)).
- **The collector walks the build runs on all its worker processes**, no longer one run after another on one core
  ([GC-RUN-WALK-ONE-CORE-68](../../bugs/GC-RUN-WALK-ONE-CORE-68.md)).

## Documentation

- **The main page is a short summary of where the project stands**: the status names no date, the current snapshot is one
  paragraph, and what works and what comes next were checked against the bug tracker. A test refuses a status that names a
  version older than the current one or a "Last updated" line of another version
  ([README-STATUS-STALE-SCATTERED-68](../../bugs/README-STATUS-STALE-SCATTERED-68.md)).

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island, the expansions' remaining
  scripts and dialogue, the save with their counts and the playtests.
- **Talking:** conversation with the creatures that have lines, and the Companion Share entry.
- **Solstheim's forests and distance:** the trees' method awaits the maintainer's choice from the pictures, and the region
  draw distance for Solstheim's six regions is a trial until the frame rate is measured on real hardware.
- **Solstheim's weather:** each weather's own cloud picture and the slowed walk in storms.
- **The werewolf's remaining rules:** silver weapons' extra damage, the werewolf's own sounds and the readier attack on a
  werewolf.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev11](RELEASE-v0.0.68-dev11.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The talk window.** Talk to a person, a merchant and a trainer: the bar with its number on top (not for a creature),
  only the services the speaker offers, the divider, the topics, Goodbye at the bottom, and the name on the title bar.
- **Persuasion.** Admire, Intimidate, Taunt and a bribe: say whether the bar moves and the speaker answers.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Seen in play:** the talk window and persuasion. The builder's cache ageing is covered by tests and a dry run; it
  changes nothing in the game.
- **A companion has no Companion Share entry**, and there is no share window yet
  ([DIALOGUE-COMPANION-SHARE-MISSING-68](../../bugs/DIALOGUE-COMPANION-SHARE-MISSING-68.md)).
- **Creatures that have lines cannot be talked to yet** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open).
- **A video started by a script can always be skipped**, also the ones the original plays to the end
  ([MWSCRIPT-PLAYBINK-SKIP-FLAG-68](../../bugs/MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md)).
- **Builder:** the reuse keys read by lookup (the CHIM units, the CHIMport cells, the ocean) record no use, so the collector
  keeps them whole ([CACHE-KEY-LOOKUP-NO-USE-68](../../bugs/CACHE-KEY-LOOKUP-NO-USE-68.md)); the build volume's cleanup
  keeps the runs a finished build request named
  ([JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68](../../bugs/JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68.md), open).
- From [v0.0.68-dev11](RELEASE-v0.0.68-dev11.md#known-in-this-build), [v0.0.68-dev10](RELEASE-v0.0.68-dev10.md#known-in-this-build),
  [v0.0.68-dev9](RELEASE-v0.0.68-dev9.md#known-in-this-build), [v0.0.68-dev8](RELEASE-v0.0.68-dev8.md#known-in-this-build),
  [v0.0.68-dev7](RELEASE-v0.0.68-dev7.md#known-in-this-build), [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build),
  [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build), [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build),
  [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build), [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build),
  [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build) and
  [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named here,
  among them the weathers' own cloud pictures and the storm walk, the broken ice wall's chamber, the werewolf's remaining
  rules, the census courtyard re-entry stop, Mournhold's and Solstheim's unfinished play, the open builder entries and the
  look book's open entries. Every other open entry is in the [bug tracker](../../BUGS.md).
