# Build AmiWind on Linux

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

## 1. Quickest setup and build

From the repository root, run:

```sh
./build.sh --autoinstall
```

Compilation and conversion default to a shared worker budget based on available
CPUs, affinity and Linux container quotas. `-j 4`, `--jobs 4` and `--j 4` set the
budget. `--single-thread` or `-j 1` runs the serial path. Independent engine, music
and dialogue stages can overlap the ordered scene pipeline. Scenery decoding,
scene previews and BSP model preparation use separate processes; shared files
are assembled in deterministic input order. Census VIS/LIGHT use the same limit.
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

Windows 11 users: see [Windows and WSL instructions](WINDOWS_BUILD.md). Native
Windows input inventory is supported by the Python entry point; the full native
build remains a Linux/WSL route and has not been validated on Windows/WSL yet.

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

For a smaller host-only terrain test with no native toolchain:

```sh
./build.sh --stage terrain --data-files '/games/Morrowind' --name terrain-test
```

This produces verified terrain packets, not an Amiga executable or HDF.

## 4. Boot your private image

Use the generated RDB HDF with the [documented emulator settings](WINUAE.md).
Provide a suitable licensed Kickstart ROM, available through
[Cloanto / Amiga Forever](https://www.amigaforever.com/). No ROM or Workbench
files are copied into the image. A ROM is needed to boot in an emulator, not
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

Run the separate [world survey](WORLD_SURVEY.md) for cell-density analysis and
the private atlas/terrain mesh. The usual production ground-contact gate still
applies; the diagnostic RC4 package does not turn its 23 open findings into a
passed production build.
