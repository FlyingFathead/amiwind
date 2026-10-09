# Historical README before v0.0.16

This preserves the prior source snapshot; its versions and status are historical.

<!-- contents start -->
## Contents

- [AmiWind](#amiwind)
- [Current state of the project](#current-state-of-the-project)
- [About AmiWind](#about-amiwind)
- [Standing on the shoulders of giants](#standing-on-the-shoulders-of-giants)
- [Current checkpoint: runtime v0.0.15-dev2 / source 0.12.1.dev1](#current-checkpoint-runtime-v0015-dev2--source-0121dev1)
- [Start from your own installation](#start-from-your-own-installation)
- [Project layout](#project-layout)

<!-- contents end -->

> Development checkpoint **v0.0.15-dev2 / source 0.12.1.dev1**: see
> [setup](AGA_BUILD.md), [validation](CHECKPOINT_017_VALIDATION.md)
> and the [WinUAE preset](../resources/emulators/AmiWind-v0.0.15-dev2-WinUAE.uae).
> Linux users: [FS-UAE playtesting](FS-UAE-PLAYTESTING.md) and its versioned preset.

# AmiWind

*For years, they thought the Nerevarine would never appear on the Commodore Amiga…*

*Well, those n'wahs were wrong!*

**Introducing AmiWind — A Morrowind conversion pipeline and demake for
Commodore Amiga.**

*The prophecy said nothing about the frame rate.*

## Current state of the project

**A small, traversable Morrowind demake is running on the Amiga AGA development
target.** The current demo includes a bounded Seyda Neen exterior and a separate
prison-ship interior. Fargoth and two guards have dressed, animated idle models;
they turn toward the player and can play original greetings. Walking, mouse look,
collision, Nord hands, streamed music, menus and a debug console are working.

This is an early proof of concept. The scripted opening, character creation,
full conversations, quests, NPC walking and combat are not implemented. Water
colour, audio stalls and scene geometry still need work. The tested emulator
reference is A1200/AGA with 68040/FPU, 2 MiB Chip and 16 MiB Fast RAM; stock A1200
performance is unproven. See the [checkpoint details](CHECKPOINT_017_VALIDATION.md)
and [next steps](SEYDA_NEEN_NEXT_STEPS.md).

**Runtime: v0.0.15-dev2. Source/build tools: 0.12.1.dev1.** The public dry-run image
boots to a versioned notice screen. Build locally with your own Morrowind files
for the playable scene; see [build instructions](LINUX_BUILD.md).

| Ship and dock | NPCs in town |
| :---: | :---: |
| <img src="images/amiwind-v0.0.15-dev2-dock.png" width="400" height="237" alt="AmiWind: ship and dock at Seyda Neen"> | <img src="images/amiwind-v0.0.15-dev2-npc.png" width="400" height="237" alt="AmiWind: NPC beside a Seyda Neen building"> |
| **Guard near town** | **Town center** |
| <img src="images/amiwind-v0.0.15-dev2-guard.png" width="400" height="237" alt="AmiWind: guard near the town's buildings"> | <img src="images/amiwind-v0.0.15-dev2-town.png" width="400" height="237" alt="AmiWind: town center and tower"> |
| **Waterfront buildings** | |
| <img src="images/amiwind-v0.0.15-dev2-waterfront.png" width="400" height="237" alt="AmiWind: wooden and stone buildings by the waterfront"> | |

*Owner-supplied development screenshots from v0.0.15-dev2. Capture margins are
cropped; all five images are 954 × 565 pixels, without rescaling the game view.
Debug FPS values show individual moments, not a hardware benchmark.*

## About AmiWind

Created by **FlyingFathead a.k.a. Horstator**\
Thanks to: **ChaosWhisperer**

> Massive thanks to everyone in the Amiga community who have been willing to
> share code and ideas to make this dream come true to a beloved platform.
> *May the wind be on your back!*

A fan-made tribute, free and open-source conversion tools, and an experimental
Amiga runtime. We are working toward a small, walkable slice of Vvardenfell;
this is a proof of concept, not a finished Morrowind port. The A500 experiment
is preserved alongside the accelerated AGA development track.
**Official project repository:** [FlyingFathead/amiwind](https://github.com/FlyingFathead/amiwind).
**Repository root: `amiwind/`.** This directory contains the conversion tools,
complete native engine source, tests and documentation. `engine/aga/` is part of
this repository, not a second repository. See [repository layout](REPOSITORY_LAYOUT.md).

Source **0.12.1.dev1** consolidates the former two-package ZIP. Runtime source
remains **v0.0.15-dev2**; this repository/build-tools update adds no gameplay fixes.

**Original Morrowind game files are required. You must provide your own copy.**
Please support the original work by purchasing Morrowind from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).

Portions of the AGA runtime are based on **id Software's Quake** and
**AmiQuake**, used under the **GNU GPL version 2** with the original notices
preserved. AmiWind's host tools and original A500 runtime are
**GPL-3.0-only**; see [LICENSE](LICENSE). OpenMW is a reference for file formats
and behaviour; the current converters are standalone tools and bundle none of
its code. Earlier opening experiments used it for external captures. See
[licensing and credits](LICENSING_AND_CREDITS.md) for component details.

Please also support [Cloanto / Amiga Forever](https://www.amigaforever.com/) for
licensed Amiga ROMs. Supply a suitable Kickstart ROM yourself; none is included
in the public repository. Public test records identify tested ROMs by checksum.

The setup model is similar to OpenMW: point the tools at your installed game
folder. Conversion runs locally and writes to a separate workspace. This
independent project is not an OpenMW release or an official Bethesda product.

> **Public source package — no commercial game data or ROMs.** No Quake or
> Morrowind game data, reusable game artwork, music, voices, game
> executables, Amiga Kickstart ROMs or Workbench files are included. This source
> package includes the selected development screenshots for documentation, but
contains no compiled AmiWind executable or assembly recovered
> from a game binary. GPL-licensed engine source is distinct from game assets.
> Supply your own Morrowind installation to convert its data, and a suitable
> licensed Kickstart ROM to run the resulting demo in an emulator. Compiling
> the engine alone does not require game data or a ROM.

Copyrights remain with their respective holders, including the original code
contributors. Each component retains its applicable licence. Morrowind and
The Elder Scrolls, Quake, Amiga and related names belong to their respective
owners. AmiWind is an independent fan tribute, not affiliated with or endorsed
by Bethesda/ZeniMax, id Software, Commodore, Cloanto or the OpenMW project.
The GPL does not grant rights to redistribute game assets or ROMs. Locally
generated game images are private build outputs, not public source releases.

## Standing on the shoulders of giants

Thanks to **Bethesda and the Morrowind creators**, **Jeremy Soule** for the
soundtrack, **OpenMW's contributors**, **id Software and the Quake source
contributors**, **Peter McGavin**, **NovaCoder**, and **Stephen Leary / terriblefire**
for the Amiga rendering lineage. Thanks also to **Timo Heimonen** for the
[Hunter performance-patch study](HUNTER_STUDY.md), the **Niftools/PyFFI**,
**vasm**, **amitools**, **FS-UAE** and **WinUAE** communities, and **UESP** for
its invaluable Morrowind reference work. These credits acknowledge the work;
they do not imply endorsement or permission to redistribute game content.

The dream: bring a little Vvardenfell to a beloved machine through careful
conversion, lookup tables, bounded memory, streaming and measured optimization.
Tests, profilers and an [optimization history](OPTIMIZATION_HISTORY.md)
keep us honest about what the hardware can actually do.

## Current checkpoint: runtime v0.0.15-dev2 / source 0.12.1.dev1

This hotfix restores the ship's curved interior hull, floors and stair/plank
surfaces from the source geometry while keeping detail reduction elsewhere.
`dbg scene change` opens a scene-picker popup for the prison and Seyda Neen;
`debug` and `amiwind debug` prefixes also work. The existing E hatch links remain.
Escape → Options → Graphics now exposes fog/draw distance; the console also
accepts `dbg fog distance 500` or `dbg draw distance 500`. Default stays 700. Left/Right nudges by 10, Shift by 1; `dbg fps on` shows
a lightweight frame-rate counter.

The image starts inside the ship, with baked dim lighting. This is a location
preview: character creation, Jiub/guard scripts and the Census office are not
implemented. Music retains its track across loads; audio stalls remain open.
The [follow-up register](SEYDA_NEEN_NEXT_STEPS.md) preserves the complete
area, NPC, container, sky, water-feedback and performance requests.

The console defaults to a compact font, supports scrollback and Shift+§/Shift+F10
fullscreen. `dbg console font normal` restores larger text, and the old retro
font remains available. `dbg coords on` now includes `DEG` heading and pitch.
The Nord eye height is calibrated separately from the unchanged collision hull.

Nord hands draw/sheath with F and play a visual punch with Mouse1. Escape opens
a menu; unimplemented options are greyed out. The extended flat sea remains a
temporary backdrop, not converted coastline. See [debug controls](DEBUG_OVERLAYS.md).

A bounded Seyda Neen scene boots from HDF with textured terrain, shared building
meshes, tree sprites, fog, WASD/mouse and full-song stereo streaming. Fargoth
and two guards now use dressed, animated idle models; E auditions an original
greeting. Nearby NPCs now turn toward the player and give a bounded proximity
greeting; walking routes are not yet implemented. This is a limited actor
prototype, not a full dialogue system. Player
collision uses scaled humanoid dimensions with ground support and stair fixes,
while retaining the preferred Quake walking bob.
Architectural collision pieces now have explicit bounds to remove spurious
solid extensions. Terrain and building collision remain approximate. See the
[validation record](CHECKPOINT_017_VALIDATION.md) for tested scope and limits,
and [filesystem diagnosis](FILESYSTEM_REVALIDATION.md) for the earlier defect.

Exploration and battle have separate shuffle bags; Shift+F5/F6 navigate playback
history. Prior native tests completed distinct full songs. This checkpoint keeps
that implementation; it does not claim glitch-free audio at stock speed.

Use **2 MiB Chip + 16 MiB Fast**, AGA, 040/FPU and KS3.1 for the current emulator
reference; see [WinUAE setup](WINUAE.md). **Stock A1200 playability remains
unproven.** Quests, the Census office, Balmora, NPC walking and combat remain future work. Music
streams during play; world geometry is resident. Prior checkpoints remain
preserved for comparisons. See [controls](AGA_BUILD.md),
[roadmap](ROADMAP.md) and [optimization history](OPTIMIZATION_HISTORY.md).

Next: complete the connected [Seyda Neen starting area](SEYDA_NEEN_SCOPE.md),
including the opposing shore and Silt Strider approach. Exteriors come first,
then complete the opening sequence and separately loaded Census office, followed
by local interactions such as containers. Day/night, a cheap sun and locally
converted sky backdrops are [planned](DAY_NIGHT_AND_SKY.md).
Asset mappings and lessons learned live in the
[implementation journal](IMPLEMENTATION_JOURNAL.md). The [conversion recipes](CONVERSION_RECIPES.md)
record reusable stages, build provenance and controlled A/B experiments.
The optional [sprite-hand build](FIRST_PERSON_HANDS.md) preserves the default 3D path.

The preserved **A500 v0.0.6 checkpoint-005** offers the opening, original terrain,
full installed OST and a voice cue on the emulated 1 MiB/KS1.3 target. The later
v0.0.7 scenery experiment adds impostors but is too slow at about 1.35 fps.
Earlier setup and test records remain in [opening demo](OPENING_DEMO.md) and
[checkpoint-005 validation](CHECKPOINT_005_VALIDATION.md).

## Start from your own installation

On Linux, start with the guided builder:

```sh
./build.sh --install-dependencies --plan
./build.sh --versions
./build.sh --check
```

It asks for your Morrowind installation root (or Data Files), verifies known
input sizes and SHA-256 hashes, and checks the selected build's dependencies. Follow [Linux installation and building](LINUX_BUILD.md)
for the host packages, cross-compiler and full HDF command. Outputs default to ignored `out/`; use `--workspace` to choose another location.
[Windows/WSL setup](WINDOWS_BUILD.md), [reference versions](BUILD_DEPENDENCIES.md),
and [the asset-free CI build](CI_DRY_RUN.md) have separate guides. This builds the experimental scene, not the whole
game. A plain `./build.sh` guides the AGA build when the prerequisites are installed.

The lower-level terrain commands need Python 3.10 or newer and no third-party
Python packages. On Windows or Linux:

```sh
python tools/mwad.py setup --data-files "/path/to/Morrowind/Data Files" --workspace "../morrowind-amiga-workspace" --target a500
python tools/mwad.py convert --workspace "../morrowind-amiga-workspace"
```

Replace the game path with your own. On Linux, use `python3` if necessary.
An existing installation works; a clean reinstall is not required. The current
converter uses the base master/archive and does not apply mod load orders.
See [setup and input requirements](SETUP.md).

## Project layout

| Location | Contents |
| --- | --- |
| `src/mwad/` | PC setup, inventory, conversion and verification |
| `runtime/` | 68000 display/audio/wireframe runtime and portable C terrain reader |
| `engine/aga/` | Complete GPLv2-compatible AGA engine source, Makefile, boot checker and QuakeC |
| `config/` | A500/A1200 planning profiles |
| `tests/` | Synthetic fixtures generated at test time and runtime checks |
| `tools/` | Checkout entry point and source-release checker |
| `docs/` | Architecture, formats, project state and roadmap |
| `resources/emulators/` | Versioned public presets with no ROM, HDF or personal paths |
| `../morrowind-amiga-workspace/` | External original/converted data and build outputs |

The game folder can also stay in its existing installation location. Both game
inputs and outputs are rejected beneath distributable source paths; ignored
`out/` is the designated exception for local work. Keep using your existing
installation rather than copying game data into the checkout.

[Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) ·
[Roadmap](ROADMAP.md) · [World mapping](WORLD_MAPPING_PLAN.md) · [Development](DEVELOPMENT.md) ·
[Project status](PROJECT_STATE.md) · [Content policy](CONTENT_POLICY.md) ·
[Character sprite design](SPRITE_PIPELINE.md) · [Host-to-Amiga build plan](PIPELINE.md)

The planned [OpenMW baking backend](OPENMW_BAKER.md) will reuse OpenMW's
actor assembly, animation and rendering on the host. It is not integrated yet.

[Hunter study](HUNTER_STUDY.md) and [Doom/AmiQuake study](ENGINE_STUDY.md)
record concrete rendering ideas and target differences.
