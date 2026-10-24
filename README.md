<p align="center">
  <img src="resources/media/AmiWind_logo.png" width="900" alt="AmiWind: an open-source RPG engine for the Commodore Amiga">
</p>

# AmiWind

_Last updated with AmiWind v0.0.50 (24 October 2026)._

An unofficial, experimental RPG engine and enthusiast project bringing Morrowind
to the Commodore Amiga, featuring CHIM: an AmiQuake-based engine and an asset
conversion pipeline that builds the game from your own legally obtained copy of
Morrowind, and, in time, a base for your own Amiga RPG adventures.

Like community projects such as
[OpenMW](https://openmw.org), [MGE XE](https://github.com/Hrnchamd/MGE-XE) and
[MWSE](https://github.com/MWSE/MWSE), AmiWind ships with no game data or proprietary assets.

*Not affiliated with or endorsed by Bethesda Softworks or ZeniMax. Please support the original creators: buy Morrowind.*

<p align="center">
  <img src="docs/images/amiwind-v0.0.32-gallery.gif" width="800" alt="AmiWind v0.0.32 in Vivec: ten in-game screenshots in turn">
</p>

<p align="center">Not painted backdrops: every frame is rendered in real time by the engine.</p>

More in the [gallery](docs/GALLERY.md).

## Where AmiWind stands (24 October 2026)

The newest release is **v0.0.50: The Doors: Riders On The CHIM**: every entrance of the game leads into its
interior and every way out leads back, running on CHIM Engine v0.2.2 ([release notes](docs/RELEASE-v0.0.50.md)). The project's own builds have had every exterior cell of Vvardenfell on CHIM since v0.0.43 (a build from the
repository does so only from v0.0.47, when the cell list became part of the repository and the default): 1,409
cells, counting the 61 in the town frames (1,348 are one-cell region frames; 1,292 land cells, 98 sea-floor cells
and 19 open-sea cells), with no classic region maps left outdoors. What these numbers count:
[the counting table](docs/chim/CELL_TRACKER.md#what-we-count); every cell: the
[CHIM Progress Tracker](docs/chim/PROGRESS_TRACKER.md). Since v0.0.48 every interior of the base game but two (the
prison and the census office) is built as a CHIM room, with the people the game places in them. Solstheim is not
converted.

What comes next is in the [roadmap](docs/ROADMAP.md): in v0.0.51, much smaller actor models (body parts stored once,
[modular NPCs](docs/MODULAR_NPCS.md)), the game's scripts and object state, and Bloodmoon, along with the open bugs
from the playtests.

### Memory: 32 MB of Fast RAM is the safe minimum (23 October 2026)

The base game's main pieces are finally coming together:
- every interior of the base game on its way in as a CHIM room;
- the people and creatures standing where the game places them;
- every NPC speaking with its own voice.

The good news: the whole thing still takes a reasonable amount of disk space. The sad part: some of it would need
far too much squeezing to fit a 16 MB expansion. Everything runs so smoothly with 32 MB that 32 MB is the default
from here on. On today's accelerator cards that is rarely a problem: many of them carry well over 32 MB of Fast
RAM, and AmiWind puts the extra to use. Most of the island can still be explored with 16 MB: of the base game's 1,134 interiors, the 16
biggest ask for 32 MB at the door (and 5 region frames at their border), and the rest open as before.

For now the game requires **32 MB of Fast RAM, the safe minimum**, which should be enough for the entire game. More
RAM is used automatically (a larger game heap, CHIM's caches and reading ahead). 16 MB still starts, with a warning
at boot, but loads more often. The emulator presets and the launcher start with 32 MB. Why, with the measured
numbers: [why 32 MB](docs/REAL_HARDWARE.md#why-32-mb-of-fast-ram).

### What v0.0.50 changed

Every door leads where the game says it does. All of the base game's 3,133 load doors and jail markers go through
one door table built from the game's own door records, and the image no longer builds when one does not lead
anywhere. The ways out of the rooms around Vivec and Ebonheart, Pelagiad's houses and the caves, tombs and the
shipwreck near Seyda Neen open now; the opening's prison ship, pier and census office keep the doors the opening
scene gives them. A new version number now rebuilds only the
engine and the image, proven by a build where only the version changed.

### What v0.0.49 changed

The builder: a new version number no longer rebuilds the CHIM world, only the engine and the image that show it, and
release candidates and finals reuse the caches like development builds. This release's final was built from its
development build's caches (39 of 43 stages reused; one more CHIM world build, repaired for v0.0.50). The docs now describe the current game throughout, with the second real-hardware
figure (an A3000 with a 68060, through RTG on the tester's own modified build). The game is v0.0.48's.

### What v0.0.48 changed

The indoors follow the outdoors onto CHIM: 1,132 of the base game's 1,134 interiors are CHIM rooms, their models and
textures stored once. The people and creatures the game places in them stand where it puts them, grounded when the
game is built ([actor placement](docs/ACTOR_PLACEMENT.md)), with their full set of animations and their own voices,
and the plants in the rooms can be picked. There are a Stats window and a Magic window placeholder, the original
movement speeds, burning campfires and the original's sound markers. CHIM moves to 0.2.2 with a compatibility table,
and the builder rebuilds less and keeps more cores busy.

Earlier releases: the [release notes](docs/RELEASE-v0.0.50.md) link back through every version, and the sections the
front page used to carry are kept in [earlier README sections](docs/README_ARCHIVE.md).

### What works, and the honest limits

- **The whole main island is in.** All of Vvardenfell's outdoors, 1,409 exterior cells, is converted and streamed
  as you walk; visit the towns and cities of the main island, such as Seyda Neen, Balmora, Vivec and many others.
- **Every interior of the base game is in.** 1,132 of the 1,134 are CHIM rooms; the two where the opening sequence
  runs (the prison ship and the census office) stay classic room maps on purpose until rooms have object state. The
  people and creatures the game places in a room stand in it with their full set of animations and their own voices.
- **Every door leads in and back out.** All 3,133 load doors and markers of the base game resolve through one door
  table; the build fails if one does not ([door graph](docs/chim/DOOR_GRAPH.md)).
- **Play:** create your character through the opening sequence; the inventory, the journal and the map; saving and
  loading, with what you pick up staying picked after a save and a load; basic hand-to-hand combat (damage, armour,
  block, knockdown, knockout, fatigue, death); a torch in hand to explore Vvardenfell at night and underground;
  mushrooms to pick indoors and out; the original movement speeds; weather by region, and music streamed from disk.
- **Not yet:** quests, dialogue, services, schedules, weapon and magic combat and most other game logic are
  unfinished, and items and containers in rooms are not live objects yet; the jail markers are in the door table for
  the jail system to come. Akulakhan's Chamber, the game's final room, cannot be entered yet: it ends the game (fixed
  first in v0.0.51; [v0.0.50 release notes](docs/RELEASE-v0.0.50.md#known-in-this-build)).
- The reference target is an A1200 with AGA, a 68040 with FPU, 2 MiB Chip and 32 MiB Fast RAM (the safe minimum;
  16 MiB starts with a warning); development and
  every performance figure so far come from emulators and are relative. The first real-hardware figures, from testers
  in October 2026: about 0.2 frames per second on an A4000 with a 68060 at 100 MHz (an earlier build), and about 0.6
  to 0.7 on an A3000 with a 68060 at 80 MHz through RTG (a tester's own modified build): not playable yet. The game
  aims at today's accelerated 68k Amigas, with a classic 68060 as the floor. See [AmiWind on real hardware](docs/REAL_HARDWARE.md) and [AmiWind on the 68060](docs/68060.md).
- Crossing from one outdoor cell to the next is streamed; walking into or out of a town is still a level change
  ([cell crossings](docs/chim/CELL_CROSSINGS.md)).
- The known problems are listed in [the bug register](docs/BUGS.md) and under "Known in this build" in each
  release's notes.

## Build it from your own Morrowind

**Original Morrowind game files are required. You must provide your own copy**, and you need your own licensed
Amiga Kickstart 3.1 ROM to run the result. The repository includes neither. AmiWind recommends the GOG GOTY edition
(the best tested; the Steam GOTY edition is a supported fallback with bitmap fonts). More: [About AmiWind](docs/ABOUT.md).

On Ubuntu/Debian (or Ubuntu under WSL), compile with:

```sh
./build.sh --autoinstall
```

and, with FS-UAE installed, build and run in one go:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file "/path/to/your/kickstart-3.1-a1200.rom"
```

`--autoinstall --plan` shows the setup steps without installing anything. On Windows start with
`.\setup-windows.cmd -Plan` (experimental; [Windows setup guide](docs/WINDOWS_BUILD.md)). A normal build includes
everything the release ships; the default builder is CHIM. The recorded v0.0.31 Seyda Neen maps
(`--seyda-recorded DIR`) are optional and NOT RECOMMENDED since v0.0.31: by default Seyda Neen is converted from
your data ([which Seyda Neen is in my build](docs/LINUX_BUILD.md#which-seyda-neen-is-in-my-build)). For a quick
test image of one spot see [MiniWind: the test ground](docs/MINIWIND.md), the
[build type reference](docs/MINIWIND_PLAYTESTER.md) and the [CHIM build guide](docs/chim/build_guide/README.md).

Everything else about building, the build speed options, the FPU support library and running the image in FS-UAE or
WinUAE: [Building and playing](docs/BUILDING_AND_PLAYING.md), the [Linux build guide](docs/LINUX_BUILD.md) and the
[FS-UAE launcher](docs/FS-UAE-LAUNCHER.md). The newest emulator presets are
[`AmiWind-v0.0.50-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.50-FS-UAE.fs-uae) and
[`AmiWind-v0.0.50-WinUAE.uae`](resources/emulators/AmiWind-v0.0.50-WinUAE.uae).

## Where to read more

- Project: [FAQ](docs/FAQ.md) · [Gallery](docs/GALLERY.md) · [Project state](docs/PROJECT_STATE.md) ·
  [Roadmap](docs/ROADMAP.md) · [Changelog](docs/CHANGELOG.md) · [Open bug reports](docs/BUGS.md)
- How it works: [Architecture](docs/ARCHITECTURE.md) · [Actor placement](docs/ACTOR_PLACEMENT.md) · [CHIM](docs/chim/README.md) ·
  [CHIM progress tracker](docs/chim/PROGRESS_TRACKER.md) · [CHIM progress map (colours)](docs/chim/CHIM_PROGRESS_MAP.md) · [Asset coverage](docs/ASSET_COVERAGE.md)
- Building: [Building and playing](docs/BUILDING_AND_PLAYING.md) · [Build dependencies](docs/BUILD_DEPENDENCIES.md) ·
  [Build/compiler toolkit roadmap](docs/BUILD_TOOLKIT_ROADMAP.md) · [Release workflow](docs/RELEASE_WORKFLOW.md)
- Development: [Repository layout](docs/REPOSITORY_LAYOUT.md) · [Project rules](docs/PROJECT_RULES.md) (including the
  required Linux and Windows compatibility) · [Polycount Inspector](docs/POLYCOUNT_INSPECTOR.md) ·
  [Earlier README sections](docs/README_ARCHIVE.md)
- Licences and credits: [About AmiWind](docs/ABOUT.md) · [Licensing and credits](docs/LICENSING_AND_CREDITS.md)

## About

Created by **FlyingFathead a.k.a. Horstator**. Thanks to: **ChaosWhisperer**.
**Official project repository:** [FlyingFathead/amiwind](https://github.com/FlyingFathead/amiwind).

AmiWind runs on the CHIM engine, built on GPLv2 code from **id Software's Quake** (John Carmack and the id team) and
its Amiga port **AmiQuake** (Peter McGavin, NovaCoder, Stephen Leary). The CHIM builder that converts your own
Morrowind files is GPLv3 ([LICENSE](LICENSE)). The public source package holds no Quake or Morrowind game data, ROMs
or compiled AmiWind executable; game images you build yourself are private build outputs. Copyrights stay with their
holders; the full statement is in [About AmiWind](docs/ABOUT.md).

> Massive thanks to everyone in the Amiga community who have been willing to
> share code and ideas to make this dream come true to a beloved platform.
> *May the wind be on your back!*

---

<p align="center"><i>AmiWind is brought to you by <a href="https://github.com/FlyingFathead/">FlyingFathead</a></i></p>
