# Build AmiWind on Linux

rc10 adds [verified persistent NPC model reuse](NPC_MODEL_CACHE.md). Full gallery
coverage and protected model quality remain mandatory.

<!-- contents start -->
## Contents

- [Bitmap paper readability (integrated in dev8)](#bitmap-paper-readability-integrated-in-dev8)
- [1. Quickest setup and build](#1-quickest-setup-and-build)
- [Manual or partial setup](#manual-or-partial-setup)
- [2. External native tools](#2-external-native-tools)
- [3. Check, then build](#3-check-then-build)
- [4. Boot your private image](#4-boot-your-private-image)
- [Rebuilding only the first NPC slice](#rebuilding-only-the-first-npc-slice)
- [Repeatable conversion choices](#repeatable-conversion-choices)
- [World map and journal assets](#world-map-and-journal-assets)
- [Night lighting tables](#night-lighting-tables)
- [Completion summary](#completion-summary)
- [NPC gallery default](#npc-gallery-default)
- [World flora default](#world-flora-default)
- [Harvestable mushrooms default](#harvestable-mushrooms-default)
- [Shipped towns default](#shipped-towns-default)
- [Game heap size](#game-heap-size)
- [Disk layout limits](#disk-layout-limits)
- [MiniWind playtester build](#miniwind-playtester-build)
- [Quick test builds](#quick-test-builds)

<!-- contents end -->

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.

**First prerequisite: sufficient build capacity.** Before starting, verify
usable space for all required models/content, intermediates, staging copies,
temporary images, final outputs, verification copies and a safety margin. Check
the actual output filesystem and quota. RAM-backed scratch also consumes the
process/container memory budget; it is not extra independent disk capacity.
If space is insufficient, provide capacity before expensive conversion begins.
Do not skip NPC models or gallery creation to make the build fit.

**All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.**

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

The guided builder converts a bounded Seyda Neen proof of concept and builds
an experimental AGA HDF. It does not convert the complete game or promise stock
A1200 performance. The current reference needs 040/FPU, AGA, 2 MiB Chip and
16 MiB Fast RAM; see [AGA setup](AGA_BUILD.md) and [WinUAE](WINUAE.md).

**Please purchase Morrowind from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/)
and supply your installed game files. AmiWind's Morrowind demo cannot run
without converted data from your own copy.** An existing installation is fine.

**The GOG GOTY edition is the preferred AmiWind source installation.** The GOG
layout used for development includes loose `BookArt/*.ttf` TrueType fonts, which
are preferred for host-side rasterization at AmiWind's target sizes. Steam GOTY
normally lacks those loose TTFs. When they are absent, the builder reports that
explicitly and falls back to Bethesda's `Fonts/*.fnt` + `.tex` bitmap fonts. The
fallback is supported, but visual results may vary and may be inferior at scaled
or non-native sizes. Preferred edition: <https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition>.

There is no need to reinstall intact base files. GOG installers are not read
directly; AmiWind reads the installed game tree. Tribunal, Bloodmoon and mod load
orders are not used. The optional base-game Video/mw_intro.bik and Splash artwork
are converted when present.

See [installed game layout](GAME_INPUT_LAYOUT.md) for the generic GOG directory
topology, the master/archive files directly under `Data Files/`, and the
distinction between installed assets and private transfer ZIPs.

## Bitmap paper readability (integrated in dev8)

TTF remains the preferred source. When reading pages use the Bethesda bitmap
fallback, the approved stronger-coverage candidate is now the default. Dialogue,
normal menus and small character/menu text retain their existing coverage.

Use `--bitmap-paper-ink original` to opt out, or `--bitmap-paper-ink filled` to
select the candidate explicitly. The same setting is available in
`config/build-defaults.json` or an external `--build-config FILE.json`.
CLI settings override the selected JSON, which overrides the shipped defaults.
See [paper font options](PAPER_FONT_OPTIONS.md). This option changes bitmap reading-page ink;
TTF/FNT source selection is automatic and independent of the worker limit.

The exterior world pipeline is `--builder chim` (the default from v0.0.33, with
the CHIM areas Balmora and Seyda Neen from `config/build-defaults.json`; name
others with one or more `--chim-area TOWN`) or `--builder legacy` (every
exterior as region maps, as in v0.0.32 and earlier; still selectable and
tested). Startup screen: a CHIM build shows "RPG engine powered by CHIM" under
the logo, a legacy build the v0.0.32 lines. A CHIM build ships no
legacy exterior map of a CHIM area: the image step writes the town's CHIM frame
maps, removes its legacy region maps and fails the build if any is still in the
image (`build.json` `chim_world.legacy_check`). Extra towns that are not CHIM
areas (the Vivec Arena) are left out of a CHIM image; the open world ships with
the legacy builder's maps until it is on CHIM. A CHIM build with Seyda Neen
needs the recorded v0.0.31 Seyda Neen maps from your own v0.0.31 image
(`--seyda-recorded DIR`). `build-state.json` `chim_plan` lists the legacy
exterior stages a CHIM plan still runs and which later step reads each one
(details: [CHIM world format](chim/WORLD_FORMAT.md#a-chim-build-ships-no-legacy-exterior-maps)).

## 1. Quickest setup and build

From the repository root, run:

```sh
./build.sh --autoinstall
```

Compilation and conversion default to a shared worker budget based on available
CPUs, affinity, Linux container quotas and memory. `-j 4`, `--jobs 4` and `--j 4` set the
budget exactly: every stage, including the final image step, gets those workers,
never fewer because of the CPU count. A value above the usable CPU threads runs
as requested with one warning. `--single-thread` or `-j 1` runs the serial path. Independent engine, music
and dialogue stages can overlap the ordered scene pipeline. Scenery decoding,
scene previews and BSP model preparation use separate processes; shared files
are assembled in deterministic input order. Census VIS uses the same limit; map
lighting runs one thread per map so its output is reproducible.
FFmpeg and numerical-library threads are bounded to avoid nested oversubscription.
The pinned QBSP and final BSP/HDF assembly remain serial. See
[parallel build details and verification](PARALLEL_BUILD.md).

Choose your Morrowind installation. The tool validates its files, discovers
existing dependencies, proposes missing packages/downloads with their source
links, and asks before installing. It then continues the build in the same
invocation. No manual environment activation, SDK path, map-tool path or compiler
path is needed for dependencies installed by this setup. APT retains its own
confirmation and may require your sudo password.

Tools default to the sibling `../amiwind-tools/`: `venv/` for Python, `sdk/`,
`ericw/bin/` for map tools, and `Quake-Tools/qcc-host`. Explicit `--sdk`,
`--quake-tools` and `--qcc` settings win. At the proposal, choose `paths` to
supply tools already installed elsewhere. `--tools-dir` relocates managed tools.
Existing directories are reused when complete and never overwritten when
incomplete. If setup fails, completed installations remain for the next attempt.

For your external test workspace:

```sh
./build.sh --autoinstall --workspace ../amiwind-build-test
```

The easiest way to build and launch the completed HDF is FS-UAE autorun:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file "/path/to/your/kickstart-3.1-a1200.rom"
```

Replace the example with your owned A1200 Kickstart 3.1 ROM file or a directory
containing ROMs. Install [FS-UAE](https://fs-uae.net/) so `fs-uae` is on PATH.
Without an explicit path, the launcher checks
`~/.roms/kickstart-3.1-a1200.rom`, then files directly in `~/.roms/` for the
known SHA-256. Directory scans skip subdirectories and symlinks; filenames do
not matter. If nothing matches, interactive mode asks for a file or another
directory. An explicitly selected ROM with a different hash produces a warning.

These checks happen before setup/conversion. Missing FS-UAE exits with status 1;
a missing ROM in noninteractive mode also exits 1 with instructions. The launcher
fills both selected ROM and built HDF paths into the generated configuration.
The [FS-UAE guide](FS-UAE-PLAYTESTING.md) includes the exact preset and a command
for launching an already-built HDF without rebuilding. No ROM is downloaded.

`./build.sh --autoinstall --plan` previews dependency setup only, without
downloads, installation or conversion. `--autoinstall --check` may install after
confirmation but stops after input/tool checks. Plain `./build.sh` also offers
setup when run interactively on Linux; noninteractive builds never install
unless `--autoinstall` was explicitly supplied and its confirmation is answered.

## Manual or partial setup

On Ubuntu/Debian, preview the guided setup and then confirm it:

```sh
./build.sh --install-dependencies --plan
./build.sh --install-dependencies
. ../amiwind-tools/venv/bin/activate
```

`./build.sh --install-sdk` independently installs the pinned Linux x86_64 SDK;
it also works alongside `--install-dependencies`. Host setup displays packages,
commands and locations before asking
`[y/N]`; APT also asks before installing its resolved packages. Use `--tools-dir`
to relocate the tools. See [dependency details and reference versions](BUILD_DEPENDENCIES.md).

For manual host setup instead:

```sh
sudo apt-get update
sudo apt-get install python3 python3-venv python3-pip build-essential ffmpeg unzip xz-utils fonts-dejavu-core libgmp10 libmpfr6 libmpc3
python3 -m venv ../amiwind-tools/venv
. ../amiwind-tools/venv/bin/activate
python -m pip install 'setuptools>=68' 'PyFFI==2.2.3' 'numpy>=1.23' 'Pillow>=9.1' 'fast-simplification==0.2.0' 'scipy>=1.10' 'amitools==0.8.1'
```

Python 3.10+ is required. The virtual environment defaults outside the checkout;
`build.sh` uses Python from PATH, or `AMIWIND_PYTHON` when explicitly set. Nothing
is installed without confirmation. A managed environment is selected automatically;
`AMIWIND_PYTHON` keeps an explicit interpreter choice until a confirmed setup needs
to switch to its newly prepared environment. No game files or ROMs are downloaded.

Windows 11 users: use `setup-windows.cmd` / `setup-windows.ps1` and
`build.cmd` / `build.ps1` with the [Windows guide](WINDOWS_BUILD.md). The shared
pipeline has completed native Windows conversion, corrected image assembly and
WinUAE game entry at the [dated checkpoint](VALIDATION-WINDOWS-2026-10-02.md).
Native Windows remains experimental. Docker Desktop on WSL2 has separate build
evidence; ordinary Ubuntu-under-WSL2 is still a separately documented trial.

## 2. External native tools

Install these outside the source checkout and retain their own licence notices:

| Tool | Reference used by the project | What to supply |
| --- | --- | --- |
| [AmigaPorts GCC SDK](https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/tag/v16.2-rc11) | v16.2-rc11, compiler 16.2.0b20260825082934, Linux x86-64 | Extracted SDK root with `bin/` and NDK includes |
| [ericw-tools](https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1) | v0.18.1 Linux | Directory containing executable `qbsp`, `vis`, `light` |
| [id Quake-Tools](https://github.com/id-Software/Quake-Tools) | qcc from revision `c0d1b91` used in the reference build | Compiled host `qcc-host` executable |

For qcc, in an external Quake-Tools checkout's `qcc` directory:

```sh
cc -std=gnu89 -include unistd.h -O2 -fcommon -o ../qcc-host qcc.c pr_comp.c pr_lex.c cmdlib.c
```

The automatic setup fetches the pinned public source and runs this command for
you. On Ubuntu/Debian, `sudo apt-get install fteqcc` is another option; select it
with `--qcc /usr/bin/fteqcc`. Discovery also recognizes `fteqcc` on PATH.
`--autoinstall` provisions its managed reference compiler unless you explicitly
select another compiler. A new tools directory also gets a fresh Python venv and
managed map tools, even when equivalent tools exist elsewhere on PATH. It is reported as an alternative, never as
a version match to id's compiler. A temporary compile of AmiWind's own QuakeC
checks version 6, system-variable CRC 5927, section bounds and supported opcodes
before conversion. This check does not replace a runtime playtest.

The complete native engine is included in `engine/aga/` inside this repository.
No upstream engine archive download or patch application is needed. The builder
stages these sources into a new separate build directory and records their hashes.
The original upstream revision and old patch remain provenance records under
`docs/aga/`; they do not override checked-in source. OpenMW is not a dependency
of this current static-scene conversion path.

## 3. Check, then build

With tools installed, plain `./build.sh` prompts for the installation root and
discovers managed tools. For an explicit, repeatable invocation:

```sh
./build.sh --check \
  --data-files '/games/Morrowind' \
  --workspace ../amiwind-local \
  --sdk /tools/m68k-amigaos-gcc-16.2 \
  --quake-tools /tools/ericw/bin \
  --qcc /tools/Quake-Tools/qcc-host
```

Remove `--check` and add `--name first-town` to perform the build. `--plan`
prints the exact stage commands without running them. `--check` creates no retained
build outputs; guided dependency installation is possible only after confirmation.
It checks paths, tool versions, source presence, file sizes/SHA-256 and container
structure. Referenced asset decoding and native performance require later stages. `ffmpeg`, `xdftool` and `rdbtool` are found on
PATH; explicit flags can override them.

If the selected game folder has no core master/archive pair, the tool announces
a search through up to four subdirectory levels and 2,000 folders. Directory
symlinks are not followed. One candidate is checked automatically; multiple
candidates require a choice (or an explicit `--data-files` in noninteractive mode).
Only that installation is inventoried and hashed. Invalid inputs stop before
dependency installation. Ctrl+C exits cleanly; if a build stage was running, its
log and cancellation receipt remain in the separate output directory.

The full AGA build reports 23 stages, including both towns and their interiors,
world terrain, character assets, audio, native compilation and HDF assembly.
Independent stages can overlap within the shared worker budget. It stops at the
first failed stage and records the command, timing and log path in
`../amiwind-local/build/first-town/build-state.json`. Stage logs are in `logs/`.
Output HDFs are under that run's `image/` directory. Original files are read in
place. The default output parent is ignored `out/` in the checkout; the explicit
`--workspace ../amiwind-local` above selects an external parent instead. Neither
location is included in source packages. Each build uses `build/<name>/`.

Each run name is immutable. To retry, fix the reported dependency or conversion
problem and choose a new name; automatic resume is not implemented. Preserve a
successful image before experimenting. Disk conversion can be slow and requires
space for the installed inputs, SDK, intermediate scenes, staged payload and
final image at the same time. Keep build runs outside the source checkout and
allow several times the final payload size; see [storage profiles](STORAGE.md).

Development builds can skip work done before: `--reuse-from OLD_RUN` copies the
unchanged stages of one earlier run, and `--prerendered DIR` keeps finished
CHIM worlds, interiors and region maps in a store folder by version and area
and uses them in any later build whose stage fingerprints match. Both verify
every copied file; release candidates and finals are built from scratch. See
[Speed](chim/build_guide/SPEED.md#prerendered-store---prerendered-dir).

For a smaller host-only terrain test with no native toolchain:

```sh
./build.sh --stage terrain --data-files '/games/Morrowind' --name terrain-test
```

This produces verified terrain packets, not an Amiga executable or HDF.

## 4. Boot your private image

Use the generated RDB HDF with the [documented emulator settings](WINUAE.md).
Provide a suitable licensed Kickstart ROM, available through
[Cloanto / Amiga Forever](https://www.amigaforever.com/). No ROM or Workbench
files are copied into the image, except an FPU support library you select
yourself with `--amiga-libs` ([FPU support library](FPU_SUPPORT_LIBRARY.md)). A ROM is needed to boot in an emulator, not
to compile the source. The experimental AGA runtime requires Kickstart 3.x;
the preserved A500 branch has separate Kickstart 1.3 instructions.

Do not publish game-containing HDFs, converted audio, textures, meshes or game
records. The selected README screenshots are a specific documentation exception.
They remain derived game content. The source release contains source and
documentation; the separate asset-free dry-run image contains only compiled code
and original notice text. Dev7 runs `AmiWindCheck` first, keeps a successful report
visible for up to five seconds (Space/Enter skips), then shows the original dry-run
notice; see [content policy](CONTENT_POLICY.md).

## Rebuilding only the first NPC slice

After generating a matching `bsp-scene`, the guided AGA build automatically runs
`tools/prepare_npcs.py` into a separate `npc-scene`. To repeat that stage manually:

```sh
python tools/prepare_npcs.py --data-files '/external/Morrowind/Data Files' \
  --scene /external/run/bsp-scene --out /external/run/npc-scene-new
```

The output includes private models, skins, sound, response text and actor IDs.
Do not publish it. Existing outputs are never overwritten. Run `tools/prepare_hands.py` on this NPC scene, then use the resulting hands
scene as input to `tools/prepare_interior.py`, then pass that interior output
to `tools/build_aga.py image`; old checkpoint-011 scenes must be rebuilt for
the new standing hull. Installed PyFFI, NumPy, SciPy, Pillow, fast-simplification
and ffmpeg are required; the earlier installation command includes them.

Checkpoint-014 also exports an ordered private voice lookup beside the stages;
it is not loaded by the runtime yet. Manual NPC/hands/lookup commands are in
[AGA_BUILD.md](AGA_BUILD.md). All original/converted models, voices and lookup
JSON remain outside public source.

## Repeatable conversion choices

Use a fresh `--name` for each candidate. `--hands 3d` (default) and `--hands sprites`
select separate native builds; sprites currently cover Nord unarmed motions only.
The private `build-state.json` identifies the recipe, mode, commands, tool/source
checksums and checksums of all installed input files, including loose files.
Hashing runs once before conversion and may take time on a large installation.
Do not change source files or tool binaries during a run. The receipt aids
reproduction; it is not a hermetic environment or a promise of byte-identical HDF
timestamps. See [CONVERSION_RECIPES.md](CONVERSION_RECIPES.md).

## World map and journal assets

The native image stage now prepares the on-demand world map and journal
catalogue from `--data-files`, after the final UI palette is established. This
terrain-only path does not run the full scenery-density survey. If original
inputs are omitted, a matching converted `id1/world` directory and receipt must
already exist. The image builder rejects stale palette/content hashes. These
four world/journal assets participate in the save-content fingerprint.

## Night lighting tables

After the final map optimisation the image stage writes three tables into the
boot image's `id1/world/`, the ones the engine reads for night lighting:

| File | Contents | Made by |
| --- | --- | --- |
| `lamps.awl` | Every exterior lamp, torch, fire and candle of your own `Morrowind.esm`, by cell, with its colour class (AWL1) | `tools/light_sources.py lamp-table` |
| `night-windows.txt` | Per town map, the textures of window and lamp glass that glow at night | `tools/night_windows.py` |
| `fog-locations.txt` | Per place day and night fog distance (`dbg fog location`) | validated copy of `config/fog-locations.txt` |

The window table traces the final maps' textures back to the scenery they were
converted from: `--balmora-scenery` (Balmora cache `scenery/`, default
`--balmora-cache`/scenery), `--town-scenery` (Seyda Neen `prepare_scenery.py`
output, default the directory of `--town-flora-source-index`), the scene's
`opening-barrel-source` and the `--world-flora` overlay. The guided build
passes all of them (`--world-flora` unless `--no-tree-sprites`). A source that was not given is skipped and listed in
`image/night-lighting/night-lighting.json` and in `build.json`
(`night_lighting`, status `partial`); a town without its own scenery gets no
window line, so its glass stays dark instead of being guessed. Each table is
checked against the engine's format before it is written, and all three
participate in the save-content fingerprint. The per-map window report is
`image/night-lighting/night-windows-report.json`.

Run the separate [world survey](WORLD_SURVEY.md) for cell-density analysis and
the private atlas/terrain mesh. The usual production ground-contact gate still
applies; the diagnostic RC4 package does not turn its 23 open findings into a
passed production build.

## Completion summary

The builder prints start/end dates with timezone offsets, total build time,
compiler-warning lines, output filename, GiB/bytes and SHA-256 inside terminal-width
rules. Success is printed only after the stages and final output hashing pass.
The same information is saved in the external run's `build-summary.json`.
See [timing boundaries, warnings and failures](BUILD_OUTPUT.md).

## NPC gallery default

**Normal game builds MUST include the NPC gallery. Do not silently skip it for
conversion time, disk size, missing inputs or an earlier build's omission.**
All original NPCs/creatures and their required assets must be available to the
engine for a complete game; the gallery provides required inspection/regression
access. Missing gallery content fails the default build. See the
[explicit build contract](CHARACTER_MODEL_GALLERY.md).

Normal AGA builds include the original NPC/creature inspection gallery for
`dbg npcgallery`, debugging and regression checks. Missing required gallery files
fail the build. Use `--no-npc-gallery` only for exceptional, explicitly requested
debugging that requires isolating the gallery; this choice is recorded. Gallery conversion does not require recompiling
retained terrain. See [gallery build details](CHARACTER_MODEL_GALLERY.md).

A build made with `--no-npc-gallery` tells the player so: the image carries the
marker `id1/npc-gallery-disabled.txt` (also named in `build.json` under
`npc_gallery`), and every way into the gallery from the F10 console
(`dbg npcgallery`, `dbg gallery`, `dbg modelgallery`,
`dbg combattest`, `dbg torchtest npc ...`) prints instead:

```text
This build was made without the NPC gallery (quick playtest build).
To include it, build without --no-npc-gallery.
```

`dbg help` (and `dbg help <word>`) lists those commands with
"(not in this build)". Normal builds have no marker and behave as before.

**Warning: gallery omission is for debugging builds only. All NPCs and their
required assets remain necessary for a complete game. `--no-npc-gallery` skips
inspection-only conversion/packaging; it must never remove world NPC placements,
models, dialogue or other gameplay dependencies, or be advertised as a complete
content profile. Normal builds include the NPC gallery for debugging and
regression inspection. This requirement does not claim that every original
world NPC has already been converted or placed by the current demake.**

## World flora default

Normal AGA builds make the world flora: the original trees, grass and reeds as
sprites with collision (`world-flora-assets` and `world-flora` stages, then the
image's `--world-flora` overlay for the world and both towns). Every release
since v0.0.28 ships them. `--no-tree-sprites` leaves them out for debugging
only: the builder prints a warning, `build-state.json` and `build-summary.json`
record `world_flora` as `disabled by --no-tree-sprites`, and the image does not
match a release. Maps that place flora (such as Seyda Neen maps reused from a
release) then stop the image step with "World flora was not built".
`--tree-sprites`, the old opt-in, is still accepted and has no effect. The
measured Balmora layout repair (`--balmora-cache`) runs in every AGA build,
with or without flora. Asset-free `--dry-run` and `--stage terrain` builds make
no flora. `tests/test_build_defaults.py` fails if a feature the release ships
leaves the default build.

## Harvestable mushrooms default

Normal AGA builds make the harvestable mushrooms (shipped since v0.0.29): the
`harvest` stage (`tools/harvest_build.py prepare`) converts every exterior
small-mushroom model once into a shared model, against the palette the image
ends with, and records every original placement. The image step (`--harvest`)
then works on the maps it ships: it removes mushrooms a converter baked into a
map (Balmora) where a harvestable one goes, writes one catalogue per map that
covers plants (world maps from `world/regions.awr`, the Seyda Neen and Balmora
sub-cells from their region tables, the intro docks), runs the geometry gate on
the final maps and admits a map only when the repository heap check passes
with its catalogue. Details: [EXTERNAL_HARVEST_MODELS.md](EXTERNAL_HARVEST_MODELS.md#builder-step).
`--no-harvest` leaves them out for debugging only (a warning; `build-state.json`
records `harvest` as `disabled by --no-harvest`; mushrooms stay baked and
cannot be picked), and the image does not match a release.

## Shipped towns default

Normal AGA builds import every town after Seyda Neen and Balmora that a release
ships: the rows of `config/towns.json` with `shipped_since` and no `withdrawn`
reason, one `town-<id>` stage each, right after Balmora's interiors. The Vivec
Arena preview (shipped since v0.0.32) is withdrawn from v0.0.33 by owner
decision (CHIM-ARENA-MEMORY-33), so a default build no longer imports it;
`--extra-town vivec_arena` still builds it. `--extra-town <id>` adds a town that
is not shipped (or is withdrawn); naming a
shipped town there has no effect. `--no-extra-town <id>` (a shipped town) and
`--only-core-towns` (Seyda Neen and Balmora only) leave towns out for debugging
only: the builder prints a warning, `build-state.json` records the selection in
`extra_town_selection`, and the image does not match a release. Contradictory
town options stop the build before any work. Details: [TOWN_IMPORT.md](TOWN_IMPORT.md).

## Game heap size

The game heap (Quake's Hunk: maps, models and the CHIM zone) is 11 MiB by default,
which runs the whole game on an A1200 with 16 MiB of Fast RAM. `--heap-mb N` (or
`"heap_mb": N` in a `--build-config` file; the command line wins) builds with exactly
N MiB, like `--jobs N`: it is never refused. Above the size measured to run the whole
game on 16 MiB of Fast RAM (11 MiB), the build prints one warning and records it in
`engine-build.json` (`heap_mb`, `heap_mb_selected_by`, `heap_warning`), the boot check
prints a `Game heap: ... [!] WARN` row, and the engine says so at start. The boot
check asks for the heap plus 3 MiB of free Fast RAM, and the heap plus 16 bytes in
one block. The map heap gates measure against the build's own size. The start
argument `-heapmb N` overrides the built size for one start, with the same warning. What the heap
holds, the measured figures per map and what 12 MiB costs: [chim/build_guide/MEMORY.md](chim/build_guide/MEMORY.md).

## Disk layout limits

Every image the builder writes (full, MiniWind, release candidates and finals) passes one disk-layout
gate in the image step, for every drive: each partition starts below 2 GiB of its drive (Kickstart
3.1 does not mount a partition that starts later) and is below 2 GiB, each file is below 1 GiB (well
under the 2 GiB file limit of the Amiga file system), and each drive image is below 4 GiB. A
violation stops the build with the drive, partition or file, its offset or size, and the limit; the
measured layout is recorded as `disk_layout` in the image's `build.json`. `build.sh`, `build.cmd` and
`build.ps1` all run it, since they run the same image step.

The gate runs twice. First on the plan, before anything is written: each world partition before its
files are copied into it, then every drive (partition sizes, their offsets and the drive size, exactly
as the drives will be written) before the boot partition or any drive image exists, so a layout over a
limit costs no image writes. Then again on every drive as written and read back. The asset-free
`--dry-run` boot-notice image passes the same gate after its partition table is read back, and its
`dry-run-build.json` records `disk_layout` too.

To check the gate itself, run the self-test (no game data, a few seconds):

```sh
python3 tools/build.py --layout-selftest
```

It sends dummy payloads through the image step's own packing code and expects a refusal, with the
matching message, for a 2.5 GB file, a 2048 MiB partition, a partition starting past 2 GiB and a drive
over 4 GiB. The last two force a drive grouping the packer never makes, and the self-test also checks
that the packer's own grouping keeps those partitions legal. A layout just under every limit (a file of
1 GiB minus one byte, 1920 MiB partitions, a partition starting at 1920 MiB + 32 KiB, a 3840 MiB +
32 KiB drive) must pass, and a tiny payload is written end to end (partitions, drive, readback, gate).
The dummies are sparse files: several GiB in size, almost nothing on disk, never read, because a
refused plan stops before any image is written. They live in one scratch folder that is removed on
success, failure and Ctrl-C, and the run ends with `Disk layout self-test: cleaned N dummy files`. The
end-to-end case needs `xdftool` and `rdbtool` and writes about 256 MiB for a few seconds;
`python3 tools/layout_selftest.py --no-write` skips it, and `--scratch DIR` picks the scratch parent.
The test suite runs the same self-test (`tests/test_layout_selftest.py`).

## MiniWind playtester build

`--miniwind` selects the build type AmiWind "MiniWind" Playtester Build: a
quick PARTIAL-AREA test of Balmora only (the Balmora exterior on CHIM, the
Balmora interiors, engine, menus, UI, audio, fonts and music) that boots
straight into Balmora. Private `-devN` versions only, never a release;
`--miniwind-description TEXT` adds an "Included:" line to the startup screen.
Details: [MINIWIND_PLAYTESTER.md](MINIWIND_PLAYTESTER.md).

## Quick test builds

A development build (`VERSION` such as `0.0.33-dev1`) can leave whole content
groups out to reach a playable test image sooner: `--exclude GROUP[,GROUP...]`
or one option per group.

| Group | Option | Skips | In the game |
| --- | --- | --- | --- |
| `video` | `--exclude-video` | the media stage's videos and the intro movie | New Game goes straight to the ship |
| `music` | `--exclude-music` | the music stage and the soundtrack | silence, one console line |
| `voice` | `--exclude-voice` | the recorded dialogue library (`Sound/Vo`) | greetings and the intro lines stay |
| `npc-gallery` | `--exclude-npc-gallery` (or `--no-npc-gallery`) | the NPC gallery stage | the gallery commands say it is not in the build |
| `interiors` | `--exclude-interiors` | the Seyda Neen and Balmora room compiles | house doors say "Area unavailable" |
| `harvest` | `--exclude-harvest` (or `--no-harvest`) | the harvest stage | mushrooms stay, but cannot be picked |
| `unreferenced` | `--exclude-unreferenced [GROUPS]` | area builds only: what the area does not reference | only the area's NPCs, voices and sounds |

Dressing, flora and every other object with collision always stay. The image
is named `...-quick-test.hdf`, the receipts record the groups, and the game says
"This build was made without ... (quick test build)." where it would notice.
Release candidates and finals refuse every exclusion. Measured savings, the
reference closure and its receipt: the
[CHIM build guide](chim/build_guide/README.md), page
[Quick test builds](chim/build_guide/QUICK_TEST_BUILDS.md).
