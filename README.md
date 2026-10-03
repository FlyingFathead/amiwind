<p align="center">
  <img src="resources/media/AmiWind_logo_clear_background.png" width="900" alt="AmiWind  -  A Commodore Amiga demake of Morrowind">
</p>

# AmiWind - Bringing TES III: Morrowind to Commodore Amiga

## v0.0.27 — Rocks, Mushrooms, and Then Some

Vvardenfell is getting its rough edges back. **37,960 rocks and 816 giant
mushrooms** now bring familiar silhouettes to the island's terrain: boulders
along the coast, rocky hillsides, and those enormous mushroom canopies in the
Ascadian Isles. Getting Morrowind onto an Amiga means making room for all of it.

The mushroom caps are closed! All five giant-mushroom models retain their joined
cap sections and original UVs, keeping the undersides, rims and textures together.
The screenshots below show that work running in WinUAE.

The **“and Then Some”** reaches beneath the scenery, too. This update brings
bounded town-map work for Seyda Neen and Balmora, memory checks on the final map
payloads, and preservation of held controls and player state during automatic
cell changes. The map panel keeps its town markers, loading text waits two
seconds by default, and an 18-track music catalogue is included. Image assembly
generates both WinUAE and FS-UAE configurations, including multi-HDF layouts.

Want to know what goes into putting a rock on an Amiga? Start with
[What are rocks?](docs/WHAT_ARE_ROCKS.md), then explore the
[v0.0.27 release notes](docs/RELEASE-v0.0.27.md).

**Heavy development is still under way.** Expect surprising performance and
stability dips as we bring more of the world together, measure its costs, and
optimize. Memory estimates and build checks help us catch problems; they do not
replace walking through the game. Please be patient—and keep the playtest
reports coming. The In-Game map is still a terrain-overview prototype; the full
video catalogue and condition-aware voiced dialogue remain on the roadmap.

See the [memory notes](docs/MEMORY_ALLOCATION.md),
[cell-changing checklist](docs/CELL_CHANGING.md),
[bug journal](docs/BUG_JOURNAL.md) and [roadmap](docs/ROADMAP.md) for the details.
Original-game assets, converted proprietary content and ROMs are not distributed
with AmiWind; you provide your own legally obtained files.

### v0.0.27 — Rocks, Mushrooms, and Then Some: playtest screenshots

These Ascadian Isles screenshots were captured in WinUAE during the rc2
playtest: closed caps, joined rims and textured undersides. They show the mushroom
work that carries into v0.0.27; town-boundary testing is tracked separately.

| Closed cap and rim | Giant mushrooms on the hillside |
| --- | --- |
| ![Closed giant-mushroom cap in rc2](docs/images/amiwind-v0.0.27-rc2-mushroom-cap.png) | ![Ascadian Isles giant mushrooms in rc2](docs/images/amiwind-v0.0.27-rc2-ascadian-mushrooms.png) |

![Joined mushroom underside in rc2](docs/images/amiwind-v0.0.27-rc2-mushroom-underside.png)

Rc3 adds a surrounding LAND apron at the Seyda Neen handoff and preserves
held controls during automatic cell/sub-cell changes. The transition regression
checks noclip, health, hands and torch state. See [cell changing](docs/CELL_CHANGING.md);
Rc3 assembly, filesystem readback, both emulator mounts and independent HDF
checksums passed. Owner boundary/input acceptance remains pending.

Large outputs automatically split into simultaneously mounted HDFs, each below
4 GiB with filesystem partitions below 2 GiB. Every assembled image emits both
WinUAE and FS-UAE configurations listing all disks, plus their paths in the final
[build output](docs/BUILD_OUTPUT.md). Rc3 uses two HDFs; this is not disk swapping.
`dbg map tp` and `dbg tp map` both open the world-map teleport picker.

### Assemble first, measure, then optimize

The current goal is to bring the authored landscape and required gameplay state
together so we can test a complete, representative workload. The present disk
footprint and conversion cost are a working baseline, not the intended final
optimized design. Town subdivisions remain necessary for frame cost.

Further work will measure duplicated geometry/textures in cell overlap, then
investigate shared model/texture storage, deduplication of identical edge data,
conversion-cache reuse and safer mesh reduction. Mirroring is an option only
where it preserves authored geometry, placement, UVs and collision. Optimization
must retain closed mushroom seams and continuous terrain handoffs. Track actual
payload bytes separately from HDF capacity/free-space headroom, and compare
resident memory, loading time and FPS. See the [optimization roadmap](docs/ROADMAP.md#assemble-first-then-optimize-the-measured-world).

**Latest published release: [v0.0.26](https://github.com/FlyingFathead/amiwind/releases/tag/v0.0.26).**
The following v0.0.26 results describe that released baseline, not a new rc3
Docker or Linux validation run.

**v0.0.26 full conversion, game entry and hosted CI passed; publication completed.**
The final Docker helper/export run completed the full recipe on Windows 11 with
Docker Desktop's WSL 2 Linux engine. All 3,551 NPC models and 2,526 terrain regions
passed, including the strict packaged actor-ground gate with zero unresolved
findings. The verified v0.0.26 HDF is 3,489,693,696 bytes with SHA-256
`da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`; WinUAE 6.0.3
played the opening movie, entered Jiub's prison scene and responded to Enter/Escape.
Conversion elapsed was 1,566.061 seconds (26 minutes 6 seconds), excluding export, provisioning and emulator testing; the cached run reported 78 warnings. The local wrapper
suite passed 433 tests with 3 skips. See the [v0.0.26 release notes](docs/RELEASE-v0.0.26.md).

The earlier **cold rc1-identity** Docker conversion took 35 minutes 3 seconds and
also passed the full content, strict actor-ground and WinUAE game-entry checks.
It produced the same-sized HDF with rc1 identity; its evidence remains in the
[Docker validation record](docs/VALIDATION-DOCKER-2026-10-02.md).

**Linux remains the established build foundation. Native Windows is experimental:**
intermittent Python worker failures and incomplete cancellation cleanup remain
documented [known issues](docs/BUG_JOURNAL.md). Preserve failed-run logs and start
a fresh run using validated model caches; general stage resume is not available.
Use the [Windows setup/build scripts](docs/WINDOWS_BUILD.md) or the existing
[Linux build path](docs/LINUX_BUILD.md).

The [Docker build helper](docs/DOCKER_BUILD.md) takes your own Morrowind installation
as private runtime input. Images contain only source/tools; game data, converted
assets and ROMs stay outside image layers and public releases. The published rc1
remains immutable. See the
[Docker roadmap](docs/DOCKER_BUILD_ROADMAP.md) and [rc1 release notes](docs/RELEASE-v0.0.26-rc1.md).

**F**, then **V** equips a [torch converted from the original game](docs/TORCH.md),
with an animated grip and flame attached to its source emitter. The debug header
shows the region from the game's own records. This includes the rc8 torch-crash
correction; target playtesting is required before final release. The longstanding
brief fist-visibility blink remains open.

Character conversion now uses a [verified persistent host cache](docs/NPC_MODEL_CACHE.md).
The full NPC gallery remains enabled by default; reused models retain the same
Amiga format and quality.

A completed rc3 terrain run can be reused through
[engine/image recovery](docs/IMAGE_RECOVERY.md). Build receipts retain timing,
compiler/tool versions, warning counts, output size and SHA-256; see
[build output](docs/BUILD_OUTPUT.md). The [Windows checkpoint](docs/VALIDATION-WINDOWS-2026-10-02.md)
records successful full conversion, recovered image assembly and WinUAE game entry.

The base-game island now has a playable terrain pass following the recovered
polygon survey: **2,526 terrain regions**, with local coordinates rebased at
boundaries. **Detailed Seyda Neen and Balmora remain intact**, including their
existing interiors and characters. Outside those towns this pass contains
terrain and water in the v0.0.26 baseline. The v0.0.27 candidate adds the rock
and giant-mushroom families described above; other settlement scenery and
actors remain future work.
Bloodmoon and Tribunal expansion content are excluded.

**J** opens the progression journal; **M** opens the island map. Older saved
configurations regain these keys when unassigned. Journal headings stay centred
on the left page and wrap onto multiple lines. See the
[v0.0.25 gameplay scope](docs/RELEASE-v0.0.25.md).

v0.0.25-rc1 brought the Seyda Neen handoff inside its ground coverage and preserved
original shoreline samples that coarse terrain had submerged. A normal-view
compass (off by default; `dbg compass on`) and GLOBAL/LOCAL XYZ aid navigation; the M marker uses the same source
coordinates and keeps its zoom on reopen. Debug flight supports Ctrl at twice
Shift speed. M/N console typing is protected; debug Alt+M exposes the desktop.
Bindings have their own [keymap file and reference](docs/KEYMAPS.md).

| Welcome to Balmora | Dagoth Ur, in the character gallery |
| :---: | :---: |
| ![Balmora bridge in v0.0.24](docs/images/amiwind-v0.0.24-balmora-bridge.png) | ![Dagoth Ur's gold mask in the native gallery](docs/images/amiwind-v0.0.24-dagoth.png) |
| **Vvardenfell world map** | **Two-page progression journal** |
| ![Vvardenfell map with source coordinates](docs/images/amiwind-v0.0.25-rc1-map.png) | ![Dated progression journal](docs/images/amiwind-v0.0.25-dev1-journal.png) |

*Native FS-UAE captures at integer scale: map from v0.0.25-rc1, journal from
v0.0.25-dev1, town/gallery from v0.0.24. [Capture details](docs/GAMEPLAY_MEDIA.md).*

Character creation follows the opening registration sequence: name, race,
gender, head and hair, class, birthsign and a final review. The appearance
screen has a rotating head preview; a birthsign is shown after its selection
stage. Character choices and earned journal history persist in saves.

`dbg gallery` opens the inspection plane for **2,935 original NPC/creature
records and all 3,551 converted model assets**. Search by friendly name or
source ID, inspect equipped/base-body variants, and return to the captured game
state. Dagoth Ur's protected mask geometry and original gold texture use an
exact-model allowance, enabled by default with `aw_allow_poly_budget_over true`
and `aw_poly_budget_over_cap auto`. Wheel cycles models; middle-click opens the browser. [Gallery controls](docs/CHARACTER_MODEL_GALLERY.md).

Balmora has 64 overlapping exterior regions and 43 destination interiors,
including Tharys Ancestral Tomb. Seyda Neen retains 25 regular regions, its
opening scenes and converted interiors. Aim at doors or residents and press
**E**. NPC interaction currently provides bounded authored greetings. Full
combat, quest simulation, services, schedules and inventory remain unfinished.

Initial actor contact is checked before world-terrain and again on final image
contents. The rc7 fitter checks the actual idle mesh, preserves authored
coordinates and keeps the strict gate. Ground contact is separate from
[quest-driven character presence](docs/CHARACTER_STATES.md), which remains
incomplete. Dreamer startup visibility is a documented example.

For the Windows build and limited emulator result, see the
[current validation record](docs/VALIDATION-WINDOWS-2026-10-02.md). Method 1
retains synchronous loading behind the frozen-frame Loading... box; method 2
read-ahead remains experimental.

The reference target is **A1200 / AGA / PAL, 68040 + FPU + JIT, 2 MiB Chip and
16 MiB Z3 RAM**. Stock A1200 performance is unproven. Build with owned game
files using the [Linux instructions](docs/LINUX_BUILD.md). Converted game data
and ROMs stay private. Start a fresh character when moving from older content.

Shift+V cycles distance; `dbg aw hors 0` creates the Nord / Barbarian / The
Steed test character after Census; `dbg tp balmora` travels to Balmora and
supplies that character if absent. `dbg tp` opens the destination picker.

See [map and journal](docs/WORLD_MAP_AND_JOURNAL.md),
[world survey](docs/WORLD_SURVEY.md), [debug controls](docs/DEBUG_OVERLAYS.md),
[project state](docs/PROJECT_STATE.md), [font options](docs/PAPER_FONT_OPTIONS.md)
and [conversion lessons](docs/BALMORA_CONVERSION_LESSONS.md).

*For years, they thought the Nerevarine would never appear on the Commodore Amiga...*

*Well, those n'wahs were wrong! The prophecy said nothing about the frame rate.*

## About AmiWind

Created by **FlyingFathead a.k.a. Horstator**
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
this repository, not a second repository. See [repository layout](docs/REPOSITORY_LAYOUT.md).

**Original Morrowind game files are required. You must provide your own copy.**

> **AmiWind recommends the GOG GOTY edition of Morrowind.**
>
> AmiWind has been developed and tested primarily against the GOG Game of the Year
> release. The GOG installation includes additional loose TrueType (TTF) font assets
> that provide a better starting point for AmiWind's offline font conversion and
> rasterization.
>
> The Steam GOTY edition does not normally include these loose TTF font assets. When
> they are unavailable, AmiWind will fall back to Bethesda's original `.fnt` + `.tex`
> bitmap fonts and continue the build. This fallback is supported, but converted font
> quality and appearance may differ and may be inferior, particularly when fonts must
> be rendered at sizes different from the original bitmap assets.
>
> **For the best-tested and preferred AmiWind conversion path, use the GOG GOTY edition:**
>
> https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition

The Steam GOTY edition remains a supported fallback input when its required game data
passes AmiWind's validation.

The AGA runtime incorporates code from **id Software's Quake** and the
**AmiQuake** lineage, modified, extended and adapted for **AmiWind**. These
components are distributed under the **GNU GPL version 2**, with the original
copyright and licence notices preserved; individual v2-or-later grants remain
intact. AmiWind's host tools and original A500 runtime are separately
**GPL-3.0-only**; see [LICENSE](LICENSE). OpenMW is a reference for file formats
and behaviour; the current converters are standalone tools and bundle none of
its code. Earlier opening experiments used it for external captures. See
[licensing and credits](docs/LICENSING_AND_CREDITS.md) for component details.

Please also support [Cloanto / Amiga Forever](https://www.amigaforever.com/) for
licensed Amiga ROMs. Supply a suitable Kickstart ROM yourself; none is included
in the public repository. Public test records identify tested ROMs by checksum.

The setup model is similar to OpenMW: point the tools at your installed game
folder. Conversion runs locally and writes to a separate workspace. This
independent project is not an OpenMW release or an official Bethesda product.

> **Public source package  -  no commercial game data or ROMs.** No Quake or
> Morrowind game data, reusable game artwork, music, voices, game
> executables, Amiga Kickstart ROMs or Workbench files are included. This source
> package includes the selected development screenshots and a short clip for documentation, but
> contains no compiled AmiWind executable or assembly recovered
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

## Building and playing

**Native Windows entry point (experimental):** `build.cmd` or `build.ps1`.
Start with `.\setup-windows.cmd -Plan`, then `.\setup-windows.cmd -Yes`, and follow the
[Windows setup guide](docs/WINDOWS_BUILD.md). Windows and Linux share the Python
build pipeline. Native Windows full conversion and WinUAE game entry passed;
experimental reliability limits remain. The Docker helper/export also completed
the full v0.0.26 conversion and WinUAE game-entry check. Hosted Docker CI and
publication must follow hosted CI; see [release notes](docs/RELEASE-v0.0.26.md).

**Quickest way to compile on Ubuntu/Debian Linux (or Ubuntu under WSL):**

```sh
./build.sh --autoinstall
```

**Easiest way to build and run on Linux:** install [FS-UAE](https://fs-uae.net/),
then point the command at your own **A1200 Kickstart 3.1 ROM**:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file "/path/to/your/kickstart-3.1-a1200.rom"
```

Replace the example ROM path with your actual file or a directory containing ROMs. The builder checks FS-UAE
and the ROM before setup, fills both ROM and HDF paths in the
[documented preset](docs/FS-UAE-PLAYTESTING.md), and launches the finished image.
If you omit `--kickstart-file`, it checks `~/.roms/kickstart-3.1-a1200.rom` under
the current user's home directory, then checks files directly in `~/.roms/` for
the known SHA-256. If no ROM is selected, it **asks for a file or directory**.
Directory searches select a checksum match; an explicitly selected different
ROM warns that compatibility is unverified. Noninteractive runs exit with clear
instructions if no ROM is selected. ROMs are never downloaded or included.

Select your Morrowind installation and confirm the dependency proposal. The tool
reuses installed dependencies, fetches missing pinned SDK/map tools, builds the
reference QuakeC compiler when needed, uses its Python environment automatically,
and continues into the build. APT may also ask for your sudo password and package
confirmation. Use `--autoinstall --plan` to preview setup without installing.

Start with [Linux build instructions](docs/LINUX_BUILD.md) or
[Windows host options](docs/WINDOWS_BUILD.md). Native Windows/MSYS2 has completed a full
conversion and WinUAE game-entry smoke test; its reliability limits remain
[documented](docs/WINDOWS_BUILD_ROADMAP.md). The Linux Docker builder on WSL 2 has
also completed full conversion and verified HDF assembly. These are separate
host validation results; Linux remains the established build foundation.
The tool accepts your Morrowind installation root, checks required file sizes
and known SHA-256 hashes, and reports dependency versions. Build outputs default
to ignored `out/`.

```sh
./build.sh --install-dependencies --plan
./build.sh --versions
./build.sh --check
```

These commands preview setup and check prerequisites. Follow the linked build
guide to install the required tools and build the playable HDF.

### Run AmiWind in an emulator

Already have a playable HDF? Copy
[`AmiWind-FS-UAE-launcher.py`](tools/AmiWind-FS-UAE-launcher.py) beside it and run
`python3 AmiWind-FS-UAE-launcher.py`. It suggests the newest version, remembers
your ROM, checks its checksum and configures FS-UAE. Use `--yes` for immediate
subsequent launches. See the [launcher guide](docs/FS-UAE-LAUNCHER.md).

The FS-UAE autorun command above handles configuration and launch automatically.
For manual setup or WinUAE, use the guides and steps below.

| Emulator / official homepage | Host platforms | AmiWind setup | v0.0.26-rc1 configuration template |
| --- | --- | --- | --- |
| [FS-UAE](https://fs-uae.net/) | Linux, Windows, macOS | [FS-UAE guide](docs/FS-UAE-PLAYTESTING.md) | [Download/view `.fs-uae` preset](resources/emulators/AmiWind-v0.0.26-rc1-FS-UAE.fs-uae) |
| [WinUAE](https://www.winuae.net/) | Windows | [WinUAE guide](docs/WINUAE.md) | [Download/view `.uae` preset](resources/emulators/AmiWind-v0.0.26-rc1-WinUAE.uae) |

1. Build `AmiWind-v0.0.26-rc1.hdf` from your own Morrowind installation using the
   build guide above. The source ZIP contains the tools and templates, not a
   playable game image.
2. Install an emulator from its official homepage above and save a local copy
   of its AmiWind configuration template.
3. Follow the matching setup guide to select your licensed **A1200 Kickstart
   3.1 ROM** and the built HDF. WinUAE uses an RDB hardfile on the UAE controller;
   FS-UAE uses the ROM and HDF paths in the configuration file.
4. Start emulation and click inside the window to capture the mouse. Use
   **WASD** to move and the mouse to look; see [controls and setup](docs/AGA_BUILD.md).

The presets use A1200/AGA, 68040 with FPU, 2 MiB Chip and 16 MiB Z3 Fast RAM,
with JIT and maximum CPU speed. The v0.0.16 playable image was tested with
FS-UAE 3.1.66 on Linux. The Windows checkpoint reached the game in WinUAE 6.0.3
using this hardware profile; see the [test scope](docs/VALIDATION-WINDOWS-2026-10-02.md).
The public [dry-run build](docs/CI_DRY_RUN.md) contains no game assets or ROMs
and boots to a test notice; it is not the playable demo.

## Development

Current engineering priority: [reduce world-terrain build times and avoid
unnecessary recompilation](docs/BUILD_TOOLKIT_ROADMAP.md), starting with phase
profiling and verified reuse across builds. These improvements are planned.

[Project state](docs/PROJECT_STATE.md) Â· [Open bug reports](docs/BUGS.md) Â· [Roadmap](docs/ROADMAP.md) Â·
[Repository layout](docs/REPOSITORY_LAYOUT.md) Â· [Release workflow](docs/RELEASE_WORKFLOW.md) Â·
[Changelog](docs/CHANGELOG.md) Â· [Build dependencies](docs/BUILD_DEPENDENCIES.md) Â·
[Build/compiler toolkit roadmap](docs/BUILD_TOOLKIT_ROADMAP.md) Â·
[Licensing and credits](docs/LICENSING_AND_CREDITS.md)

Thanks to the Morrowind creators, the Amiga community, and the contributors whose
work made this experiment possible. The earlier A500 track, previous methods,
fonts and hand-rendering alternatives remain available in the source and history.

Development changes must follow the [project rules](docs/PROJECT_RULES.md), including required Linux and Windows compatibility.
