# CHIM build guide

How to build AmiWind with the repository builder (`./build.sh`, `tools/build.py`),
from a complete release-style image to a quick test of one spot. Every build
uses your own Morrowind files; the builder never downloads or ships game data.
The basic setup (dependencies, SDK, map tools) is in the
[Linux build guide](../../LINUX_BUILD.md).

## Which build do I want?

| I want to ... | Build | Page |
| --- | --- | --- |
| play the whole game, as a release ships it | a normal build, no extra options | [Linux build guide](../../LINUX_BUILD.md) |
| choose the legacy or the CHIM builder | `--builder` | [Builder types](BUILDER_TYPES.md) |
| test one town quickly (Balmora on CHIM) | a MiniWind playtest build | [MiniWind](MINIWIND.md) |
| leave videos, music, voices, interiors or the NPC gallery out to build faster | `--exclude ...` | [Quick test builds](QUICK_TEST_BUILDS.md) |
| build only what one area references | `--exclude-unreferenced` | [Quick test builds](QUICK_TEST_BUILDS.md#only-what-the-area-references---exclude-unreferenced) |
| start straight in a town, a room or a spot, without the intro | `--direct-to-game-map` | [Start straight in the game](DIRECT_START.md) |
| build faster, reuse earlier stages, see where the time goes | `--jobs`, `--reuse-from`, the build profile | [Speed](SPEED.md) |
| follow a build on the map while it runs | the live build tracker (`--live-tracker`) | [Live build tracker](#live-build-tracker) |
| run the image on a slow accelerator in FS-UAE | the emulator presets | [Emulator presets](EMULATOR_PRESETS.md) |
| change the CHIM texture effects | `--chim-texture-effect` | CHIM texture effects (`docs/chim/TEXTURE_EFFECTS.md`, added with the CHIM builder) |
| choose how a CHIM world is lit | `--chim-lighting-type` | [Builder types](BUILDER_TYPES.md#chim-lighting-type) |

## Live build tracker

A guided CHIM build can show its progress on the AmiWind Toolkit's map while it runs: the cells converted so far, the
current stage, the cells done out of the total and a rough time left. At the start of a guided build the builder asks once.
In plain words, the choices are:

- **File (the default): no server.** The builder keeps a small page and data file in `BUILD/toolkit/live/`, prints the address
  of the page and you open it from disk; it refreshes itself every 10 seconds. Nothing listens on your computer.
- **Server:** starts a small local web server on `127.0.0.1` only (this machine; read-only; low priority; Python standard
  library) and prints `Track the build on the map: http://127.0.0.1:PORT/`, again in the final summary. It stops when the build
  ends, or press Enter with `--keep-tracker`; Ctrl+C cancels the build and stops it.
- **No.**

Nothing leaves your computer either way. `--live-tracker file|server` starts it without asking (non-guided builds are off
unless you give it), `--no-live-tracker` turns the offer off, and `--no-cell-progress` turns off the build's progress data
altogether. The details, and how to look at a finished build, are in
[Track your own build](../../AMIWIND_TOOLKIT.md#track-your-own-build); what the colours and statuses mean is in the
[CHIM Progress Tracker guide](../PROGRESS_TRACKER.md).

## What release builds refuse

Release candidates and finals are always complete and always built from
scratch: quick test options are refused for them. The list is in
[Quick test builds](QUICK_TEST_BUILDS.md#what-release-builds-refuse).

## Pages

- [Builder types](BUILDER_TYPES.md)
- [MiniWind](MINIWIND.md)
- [Quick test builds](QUICK_TEST_BUILDS.md)
- [Start straight in the game](DIRECT_START.md)
- [Speed](SPEED.md)
- [Emulator presets](EMULATOR_PRESETS.md)
