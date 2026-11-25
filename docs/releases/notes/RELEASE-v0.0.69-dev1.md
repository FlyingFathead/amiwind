# AmiWind v0.0.69-dev1 (in development)

_Last updated with AmiWind v0.0.69-dev1 (25 November 2026)._

Development snapshot, 25 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md).

The first snapshot of v0.0.69. The version has no title yet. It is a small snapshot of what was found while the v0.0.68
release was built: a place shows on the world map as soon as the player has explored any one of its own cells, and the
builder's check of that release from nothing is written down with the two weak spots it measured. Its emulator presets,
`AmiWind-v0.0.69-dev1-FS-UAE.fs-uae` and `AmiWind-v0.0.69-dev1-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs. Otherwise the game is the one of v0.0.68. The map change is checked by the test suite and the gate of this
snapshot, and was checked in play on its image.

## New since v0.0.68

### Fixed

- **A place shows on the world map as soon as the player has explored any one of its own cells.** The original marks a
  place on the normal map when any cell of it has been explored. Before, only the explored state of the place's averaged
  marker spot counted, so a place whose cells spread out, such as Raven Rock on Solstheim, stayed hidden while the player
  stood in it. The explored mask is now built before the places, and each place tests its own cells as they are read
  ([MAP-PLACE-HIDDEN-IN-ITS-OWN-CELL-68](../../bugs/MAP-PLACE-HIDDEN-IN-ITS-OWN-CELL-68.md)).
  Checked in play on this snapshot's image: after the same short walk into Raven Rock that left the v0.0.68 map empty,
  its marker shows on the normal map.

### Builder and tools

- **The v0.0.68 release was built again from nothing and came out the same.** The build ran in an empty workspace with
  nothing reused, and every game data file was identical to the released image. The check also measured two weak spots,
  both planned for the next snapshots and not changed here: the expansion stages use under half of their cores
  ([TRIBUNAL-STAGE-UNDERUSED-68](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md)), and the actor library's stage is limited by
  memory, with five of its twenty-two units running side by side
  ([BUILD-MEMPLAN-CHIM-5-OF-22-68](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md)).
- **The bug tracker** records these entries and the sightings made after the v0.0.68 release.

## What the v0.0.69 line works on

- **Tribunal and Bloodmoon played through:** the quests of both expansions from start to finish, every creature checked
  against its original record, and the frame rate of Mournhold's districts, as the
  [roadmap](../../ROADMAP.md) lists.
- **A faster build:** the expansion stages on all their cores and the actor library planned by memory, so that a
  build from nothing takes less time on a 32 GB machine.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The game of this snapshot is the game of v0.0.68, so the
[checklist of the v0.0.68 release](RELEASE-v0.0.68.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The place marker on the map.** Walk into Raven Rock on Solstheim, open the world map and look for the place's marker
  on the normal map; it shows once any cell of the place has been explored. Look at one more place whose cells spread
  out, and at a place not yet visited, whose marker stays hidden.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **The build:** the expansion stages use under half of their cores
  ([TRIBUNAL-STAGE-UNDERUSED-68](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md)) and the actor library is limited by memory
  ([BUILD-MEMPLAN-CHIM-5-OF-22-68](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md)); both are planned for the next snapshots.
- **No ripples on the water** under a swimmer or a player walking on water
  ([WATER-RIPPLES-UNDER-ACTORS-MISSING-68](../../bugs/WATER-RIPPLES-UNDER-ACTORS-MISSING-68.md)).
- **The journal's topic list has no letter index yet:** every topic is in one scrolling list
  ([JOURNAL-TOPIC-LETTER-INDEX-68](../../bugs/JOURNAL-TOPIC-LETTER-INDEX-68.md)).
- **The memory box can name the target by its map file label:** when a load runs out of memory the box writes the target
  as an internal label (for example rifa4ef181ed) instead of the place's name
  ([LF5-BOX-DESTINATION-MAP-NAME-68](../../bugs/LF5-BOX-DESTINATION-MAP-NAME-68.md)); the box offers OK only, and Load
  Game and New Game follow.
- **Water Walking is applied deep under the water too,** where the original refuses the spell
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- **An object in Solstheim's eastern waters is not drawn but still stops a player walking on the water** (cell -19, 17,
  on the way from Khuul); walking around it reaches Solstheim
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)).
- **Creatures that have lines cannot be talked to yet** ([DIALOGUE-CREATURE-SPEAKERS-66](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md), open), and
  **a companion has no Companion Share entry** ([DIALOGUE-COMPANION-SHARE-MISSING-68](../../bugs/DIALOGUE-COMPANION-SHARE-MISSING-68.md)).
- **A video started by a script can always be skipped,** also the ones the original plays to the end
  ([MWSCRIPT-PLAYBINK-SKIP-FLAG-68](../../bugs/MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md)).
- **Solstheim's weather:** each weather's own cloud picture is left
  ([WEATHER-CLOUD-TEXTURES-68](../../bugs/WEATHER-CLOUD-TEXTURES-68.md)) and the walk is not slowed in storms
  ([STORM-WALK-NOT-SLOWED-68](../../bugs/STORM-WALK-NOT-SLOWED-68.md)).
- **The werewolf:** silver weapons' extra damage, the werewolf's own sounds and the readier attack on a werewolf are left
  ([WEREWOLF-FIGHT-RULES-LEFT-68](../../bugs/WEREWOLF-FIGHT-RULES-LEFT-68.md)).
- **The broken ice wall cannot be passed:** the chamber behind it cannot be entered
  ([PENUMBRA-ICE-WALL-NO-PASSAGE-68](../../bugs/PENUMBRA-ICE-WALL-NO-PASSAGE-68.md)).
- **Mournhold's districts run at a low frame rate** ([DISTRICT-FRAME-RATE-LOW-67](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md));
  the cost of the districts' scripts in frames is not measured.
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play; the region
  distance of Solstheim is a trial until the frame rate is measured on real hardware. Akulakhan's Chamber keeps its old
  look, as it cannot hold its end poses within 32 MB yet.
- **Builder:** the reuse keys read by lookup record no use, so the collector keeps them whole
  ([CACHE-KEY-LOOKUP-NO-USE-68](../../bugs/CACHE-KEY-LOOKUP-NO-USE-68.md)); the build volume's cleanup keeps the runs a
  finished build request named
  ([JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68](../../bugs/JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68.md), open).
- From [v0.0.68](RELEASE-v0.0.68.md#known-in-this-build) and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and their
  snapshots: their Known lists stand for what is not named here, among them the census courtyard re-entry stop,
  Mournhold's and Solstheim's unfinished play, the open builder entries and the look book's open entries. Every other
  open entry is in the [bug tracker](../../BUGS.md).
