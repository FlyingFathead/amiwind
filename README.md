<p align="center">
  <img src="resources/media/AmiWind_logo.png" width="900" alt="AmiWind: an open-source RPG engine for the Commodore Amiga">
</p>

# AmiWind

_Last updated with AmiWind v0.0.68-dev12 (24 November 2026)._

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

## Where AmiWind stands

**The newest release is v0.0.67: Tribunal Introduced.** It brings Tribunal, the first expansion, into the game:
Tribunal's additions to Vvardenfell are in the build, and Mournhold can be reached from Ebonheart through the
characters' own dialogue and walked from the palace to the Plaza. Its quests and much of its play are not ready, and in
this release Solstheim is not in the game. It runs on CHIM Engine v0.2.2 and needs 32 MB of Fast RAM. The detail:
the [v0.0.67 release notes](docs/releases/notes/RELEASE-v0.0.67.md). The release before it, **v0.0.66: Forward It Is**,
is in [its notes](docs/releases/notes/RELEASE-v0.0.66.md).

**In development: v0.0.68-dev12**, the twelfth snapshot of the next version, **Solstheim Is Here** (the release for
which Solstheim is to be complete). Since v0.0.67 all 153 of Solstheim's cells are built and its quest and underwater
entrances can be used (seen in play), fights no longer stutter when blows land, and Solstheim's weathers have their own
look; the snapshot itself lays out the talk window as the original's, with the disposition bar, the speaker's services
and the name on the title bar (seen in play), and lets the builder clear the cache entries no recent build uses. Most of
the expansions' play is not yet seen in play. The notes of this snapshot:
[v0.0.68-dev12](docs/releases/notes/RELEASE-v0.0.68-dev12.md); the earlier snapshots, dev1 to dev11, are in the
[changelog](docs/CHANGELOG.md).

## What already works

- **Vvardenfell, whole.** All 1,408 exterior cells of the main island on CHIM, streamed as you walk, and 1,121 of its
  1,123 interiors as CHIM rooms (the prison ship and the census office are room maps of their own, counted as ready), with the
  people and creatures the game places in them ([CHIM progress tracker](docs/chim/PROGRESS_TRACKER.md),
  [the map's colours](docs/chim/CHIM_PROGRESS_MAP.md)). Every load door
  of the base game leads in and back out.
- **Play:** character creation through the opening; the inventory, the journal and the map; saving and loading, with what
  you change staying changed; combat and casting by the original's rules; talking and the services; crime with
  witnesses, guards, fines and jail; alchemy; containers and bodies to search; torches and lanterns; weather, music and
  travel by silt strider, boat, gondola and guild guide; levelling and resting as in the original
  ([game features](docs/GAME_FEATURES.md)).
- **Tribunal, the first steps:** Tribunal's additions to Vvardenfell are in the build, and Mournhold is reached from
  Ebonheart through the characters' own dialogue; its five districts can be walked, slowly (8 to 16 frames a second in
  the emulator).
- **The game's scripts:** of the 1,074 scripts the original uses, 1,063 run and 9 more are carried by AmiWind's own code,
  235 of Tribunal's 236 among them ([the MWScript tracker](docs/MWSCRIPT_FEATURES.md)).
- **Hardware:** the target is an A1200-class machine with AGA, a 68040 with FPU, 2 MiB Chip and 32 MiB Fast RAM, in
  emulators with JIT; accelerators such as the PiStorm are a route to real hardware (16 MiB starts with a warning, and
  parts of the game run wrongly or not at all). The figures so far come from emulators and the Raspberry Pi 4B
  ([real hardware](docs/REAL_HARDWARE.md)).

## What comes next

- **Tribunal in play:** Mournhold's quests and most of its play are still to be seen in play, and so are the districts'
  frame rate, the Plaza's view from its arrival point and Godsreach's canal.
- **Bloodmoon:** Solstheim's cells are built and its entrances can be used, but no door or journey leads there from
  Vvardenfell yet; most of its objects and quests are not yet seen in play.
- **Talking:** conversation with the creatures that have lines and the Companion Share entry are still to come; the
  talk window and persuasion are seen working in play ([the bug tracker](docs/BUGS.md)).
- **Resting:** the wilderness creature came too often in one session; fixed in source, still to be seen in play.
- **The base game:** the end of the main quest in the Heart Chamber; pickpocketing, picking owned locks and locks on
  doors and containers; making your own enchantments; schedules by the time of day; the shores still run in saw-tooth steps.

**Then v0.0.68** continues with the expansions' finished content: Tribunal's Mournhold with its quests and Bloodmoon's
Solstheim, with their scripts; a build that fits a 32 GB machine; then the rest of the open plan. The order of record is
the [roadmap](docs/ROADMAP.md); no dates are promised. Every system of the base game with its state:
[game features](docs/GAME_FEATURES.md). Known problems: [the bug tracker](docs/BUGS.md).

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
everything the release ships, Tribunal and Bloodmoon read by default where you own them (`--no-dlc` for the base game
alone). The recorded v0.0.31 Seyda Neen maps (`--seyda-recorded DIR`) are optional and NOT RECOMMENDED since v0.0.31
([which Seyda Neen is in my build](docs/LINUX_BUILD.md#which-seyda-neen-is-in-my-build)). For a quick test image of one
spot: [MiniWind: the test ground](docs/MINIWIND.md) and the [build type reference](docs/MINIWIND_PLAYTESTER.md).

**If a build fails, send the file `logs/BUILD-REPORT-<run>.txt`** from the build workspace (`out/` by default; the
build prints where it is): one file with what failed and every setting, kept on your computer until you send it
([when a build fails](docs/LINUX_BUILD.md#when-a-build-fails)). **A build that stopped, out of memory included, is
never started over:** do not delete the build folder, run the same command again from the same folder, and the
finished work is taken back; the build's last lines say what to change first
([the build stopped or ran out of memory: what now?](docs/LINUX_BUILD.md#the-build-stopped-or-ran-out-of-memory-what-now)).

The emulator presets of this version are
[`AmiWind-v0.0.68-dev12-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.68-dev12-FS-UAE.fs-uae) and
[`AmiWind-v0.0.68-dev12-WinUAE.uae`](resources/emulators/AmiWind-v0.0.68-dev12-WinUAE.uae); both start with 32 MB of Fast
RAM, the requirement. The presets of earlier versions are beside them in [resources/emulators](resources/emulators/). Everything
else about building and playing: [Building and playing](docs/BUILDING_AND_PLAYING.md), the
[Linux build guide](docs/LINUX_BUILD.md) and the [FS-UAE launcher](docs/FS-UAE-LAUNCHER.md).

## Where to read more

- Every document, by topic: [the documentation index](docs/README.md) · every release with its notes:
  [releases](docs/releases/README.md) · the history of every version: [changelog](docs/CHANGELOG.md)
- Project: [FAQ](docs/FAQ.md) · [Gallery](docs/GALLERY.md) · [Project state](docs/PROJECT_STATE.md) ·
  [Roadmap](docs/ROADMAP.md) · [Open bug reports](docs/BUGS.md)
- How it works: [Architecture](docs/ARCHITECTURE.md) · [CHIM](docs/chim/README.md) ·
  [CHIM progress tracker](docs/chim/PROGRESS_TRACKER.md) · [Game features](docs/GAME_FEATURES.md)
- Building: [Building and playing](docs/BUILDING_AND_PLAYING.md) · [Build dependencies](docs/BUILD_DEPENDENCIES.md) ·
  [Release workflow](docs/RELEASE_WORKFLOW.md)
- Development: [Repository layout](docs/REPOSITORY_LAYOUT.md) · [Project rules](docs/PROJECT_RULES.md) ·
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
