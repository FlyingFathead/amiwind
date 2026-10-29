# Building and playing

_Last updated with AmiWind v0.0.55 (29 October 2026)._

How to build AmiWind from your own Morrowind copy and run it in an emulator. The short version is in the [README](../README.md#build-it-from-your-own-morrowind).

**Native Windows entry point (experimental):** `build.cmd` or `build.ps1`.
Start with `.\setup-windows.cmd -Plan`, then `.\setup-windows.cmd -Yes`, and follow the
[Windows setup guide](WINDOWS_BUILD.md). Windows and Linux share the Python
build pipeline. Earlier native Windows full conversion and WinUAE game-entry
checks passed; experimental reliability limits remain. The published v0.0.27
passed Linux/Windows launcher CI, Docker builder CI and the source/asset-free
build job. See the [release notes](releases/notes/RELEASE-v0.0.27.md) for the scope of each
check; these results do not certify a full v0.0.27 gameplay run on either host.

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

Every finished build also writes, beside the HDF, `AmiWind-FS-UAE-launcher.py`
(run it: it asks for your ROM once and starts FS-UAE), `AmiWind-v<version>-FS-UAE.fs-uae`
and `AmiWind-v<version>-WinUAE.uae`. Without `--kickstart-file` the two configs carry a
placeholder ROM setting to fill in; see [WinUAE setup](WINUAE.md) and the
[FS-UAE launcher](FS-UAE-LAUNCHER.md).

The example ROM path stands for your own ROM file, or for a directory that
contains ROMs. The builder checks FS-UAE and the ROM before setup, fills in the
ROM and HDF paths of the [documented preset](FS-UAE-PLAYTESTING.md), and
launches the finished image. Without `--kickstart-file`, it looks for
`~/.roms/kickstart-3.1-a1200.rom` in your home directory, and then for a file
directly in `~/.roms/` with the known SHA-256. If it still has no ROM, it
**asks for a file or directory**. In a directory it picks the file whose
checksum matches; a different ROM chosen by name is accepted with a warning
that compatibility is unverified. A run without a terminal stops with
instructions when no ROM is selected. ROMs are never downloaded or included.

Next, the tool asks for your Morrowind installation and shows the dependencies
it proposes to install. Once you confirm, it reuses what is already installed,
fetches the missing pinned SDK and map tools, builds the reference QuakeC
compiler if needed, sets up its own Python environment and carries on into the
build. APT may also ask for your sudo password and to confirm packages.
`--autoinstall --plan` shows the setup steps without installing anything.

Start with [Linux build instructions](LINUX_BUILD.md) or
[Windows host options](WINDOWS_BUILD.md). Native Windows/MSYS2 has completed a full
conversion and WinUAE game-entry smoke test; its reliability limits remain
[documented](WINDOWS_BUILD_ROADMAP.md). The Linux Docker builder on WSL 2 has
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

**Build speed:** `--jobs N` sets the exact worker count. While a build runs,
`./build.sh status out/build/NAME` shows its progress, the cores in use and an
ETA; afterwards `./build.sh profile report|compare|optimize out/build/NAME`
shows where the time went and what to parallelize next. Development rebuilds can
reuse unchanged stages with `--reuse-from`. See
[performance options](BUILD_PROFILE.md#performance-options). `--clean` builds the
way a first-time user does (no earlier run, an empty cache), and `--public-defaults`
refuses options a public user would not have: see
[clean builds](BUILD_CACHE.md#clean-builds-and-public-defaults). The numbers of
every build and gate can be kept in one database for comparisons across runs:
[perf database](PERF_DATABASE.md).

**Disk space:** every build keeps its run folder and adds to the build cache, so
the workspace grows with each release you build. When the build disk is 80 % full
or more, the build prints a `[disk] WARNING` line naming the garbage collector:
`python tools/build_gc.py plan out` lists what it would remove (old release
series, finished scratch, cache objects nothing uses any more) and deletes nothing;
add `--delete` to remove exactly what it lists as expired. See
[free disk space](BUILD_CACHE.md#free-disk-space).

A normal build includes everything the release ships; no extra option is
needed. From v0.0.33 the default builder is CHIM, with Balmora and Seyda Neen on
CHIM, both converted from your own data (from v0.0.35 the recorded v0.0.31
Seyda Neen maps, `--seyda-recorded DIR`, are optional and NOT RECOMMENDED since v0.0.31:
the default converts Seyda Neen from your data; which Seyda Neen an image holds:
[docs/LINUX_BUILD.md](LINUX_BUILD.md#which-seyda-neen-is-in-my-build); what fills the disk images and
where their size is going: [docs/IMAGE_SIZE.md](IMAGE_SIZE.md)), and `--builder legacy`
still builds the old way (see
[builder types](chim/build_guide/BUILDER_TYPES.md)). The Vivec Arena preview
of v0.0.32 is withdrawn from v0.0.33 (`--extra-town vivec_arena` still builds it
for testing). Options that leave shipped content out are for debugging only and
say so; see [shipped towns](LINUX_BUILD.md#shipped-towns-default).
For a quick Balmora-only playtest image (a private test, never a release), add
`--miniwind` or a ready-made sandbox such as `--miniwind-balmora-exterior`; see
[MiniWind: the test ground](MINIWIND.md) and the
[build type reference](MINIWIND_PLAYTESTER.md).
For quick test builds of one spot (fewer videos, voices, rooms or NPCs), see the
[CHIM build guide](chim/build_guide/README.md).

Update (v0.0.44): the default CHIM areas are Balmora, Seyda Neen and the whole city of Vivec, and the exterior cells
between them are CHIM region frames; every exterior cell of Vvardenfell is on CHIM since v0.0.43.

**FPU support library (optional, your own copy):** a real 68040 or 68060 needs
`68040.library` or `68060.library` for the rare FPU cases its hardware does not
handle. Add `--amiga-libs DIR` with a folder from your own Workbench or
accelerator installation; the builder copies the library into `LIBS:` on the
boot disk and opens it at start-up. Without it the build continues and the boot
check shows a warning. AmiWind never includes the library; see
[FPU support library](FPU_SUPPORT_LIBRARY.md).

### Run AmiWind in an emulator

Already have a playable HDF? Copy
[`AmiWind-FS-UAE-launcher.py`](../tools/AmiWind-FS-UAE-launcher.py) beside it and run
`python3 AmiWind-FS-UAE-launcher.py`. It suggests the newest version, remembers
your ROM, checks its checksum and configures FS-UAE. Use `--yes` for immediate
subsequent launches. See the [launcher guide](FS-UAE-LAUNCHER.md).

The FS-UAE autorun command above handles configuration and launch automatically.
For manual setup or WinUAE, use the guides and steps below.

| Emulator / official homepage | Host platforms | AmiWind setup | v0.0.48 preset |
| --- | --- | --- | --- |
| [FS-UAE](https://fs-uae.net/) | Linux, Windows, macOS | [FS-UAE guide](FS-UAE-PLAYTESTING.md) | [Download/view `.fs-uae` preset](../resources/emulators/AmiWind-v0.0.48-FS-UAE.fs-uae) |
| [WinUAE](https://www.winuae.net/) | Windows | [WinUAE guide](WINUAE.md) | [Download/view `.uae` preset](../resources/emulators/AmiWind-v0.0.48-WinUAE.uae) |

1. Build the current source from your own Morrowind installation using the guide
   above. Keep every HDF listed in the build summary together. The source ZIP
   contains tools and templates; playable images are private build outputs.
2. Install an emulator from its official homepage above. Prefer the matching
   configuration generated beside your HDFs: it lists every required disk. The
   v0.0.48 presets above provide a starting point for manual setup.
3. Follow the matching setup guide to select your licensed **A1200 Kickstart
   3.1 ROM** and all the built HDFs. WinUAE uses RDB hardfiles on the UAE
   controller; FS-UAE uses the ROM and HDF paths in its configuration file.
4. Start emulation and click inside the window to capture the mouse. Use
   **WASD** to move and the mouse to look; see [controls and setup](AGA_BUILD.md).

The presets use A1200/AGA, 68040 with FPU, 2 MiB Chip and 32 MiB Z3 Fast RAM, the
safe minimum for the whole game (since 23 October 2026; 128 MiB from 21 October, 16 MiB
before; more is used automatically; 16 MiB still starts with a warning and loads more
often, see [Fast RAM](FS-UAE-LAUNCHER.md#fast-ram)), with JIT and maximum CPU speed. The v0.0.16 playable image was tested with
FS-UAE 3.1.66 on Linux. The Windows checkpoint reached the game in WinUAE 6.0.3
using this hardware profile; see the [test scope](history/validation/VALIDATION-WINDOWS-2026-10-02.md).
The public [dry-run build](CI_DRY_RUN.md) contains no game assets or ROMs
and boots to a test notice; it is not the playable demo.

The presets of the newest release are
[`AmiWind-v0.0.48-FS-UAE.fs-uae`](../resources/emulators/AmiWind-v0.0.48-FS-UAE.fs-uae) and
[`AmiWind-v0.0.48-WinUAE.uae`](../resources/emulators/AmiWind-v0.0.48-WinUAE.uae).
