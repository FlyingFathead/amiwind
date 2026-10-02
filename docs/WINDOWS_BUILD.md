# Windows build entry points and WSL notes

**Linux is the established build baseline. Native Windows 11 building is
experimental.** A complete current-recipe conversion and verified HDF, followed by WinUAE game
entry, passed on 2 October 2026 after correcting/retrying image assembly.
See [the validation record](VALIDATION-WINDOWS-2026-10-02.md) for scope and timing.
Intermittent Python worker failures remain open; this success does not establish
that the Windows path is consistently reliable.
See [known issues and recovery limits](#windows-build-and-known-issues).

After a failed Windows run, preserve its logs and validated caches, then use a
fresh run name. Compatible model-cache entries can be reused; general resumption
of every completed stage is not implemented. Do not assume a retry rate or treat
repeated retries as a fix. Windows-specific development must preserve the Linux
build path and its validation gates.

`setup-windows.cmd` / `setup-windows.ps1` provision a native Windows environment.
`build.cmd` / `build.ps1` use the same `tools/build.py` pipeline as Linux.
Native Windows engine compilation and asset-free HDF creation passed locally
on 2 October 2026 with the reference SDK. The asset-free image also booted
to its expected notice in WinUAE. Full-game conversion, corrected image assembly and a prison-scene WinUAE smoke
test have now passed. The open issues and exact recovery scope remain below.

## Windows build and known issues

### Intermittent Python worker failure (unresolved, 2 October 2026)

Canonical record: [WIN-01 in the bug journal](BUG_JOURNAL.md#win-01-intermittent-geometry-worker-queue-failure--open-2-october-2026).

Native Windows full-conversion attempts have intermittently failed in Python's
`ProcessPoolExecutor`, while preparing interior, Balmora or Census BSP geometry:

```text
multiprocessing/queues.py: self._sem.release()
OSError: [WinError 6] The handle is invalid
concurrent.futures.process.BrokenProcessPool
```

This is a host asset-conversion failure. The Amiga engine compiler completed
successfully in the affected runs. Failures have occurred with 24- and 12-worker total budgets
(effective failing pools of 17 and 12 workers); excessive worker count has not been established as the cause. An
isolated 24-worker interior conversion, eight rounds of a 24-worker synthetic
geometry test, and five repetitions of the two affected Balmora regions at
12 workers passed. Those passes do not establish a fix or full-build success.

The root cause and a reliable workaround remain under investigation. A reduced
job count or a successful retry must not be described as a confirmed repair.
The later conversion and image-retry checkpoint reached the game in WinUAE,
as recorded in [validation](VALIDATION-WINDOWS-2026-10-02.md);
that is not comprehensive gameplay validation.

Preserve the failed run's `build-state.json`, `build-summary.json` and stage
logs. Keep validated model caches; use a fresh `--name` for a new full build.
After cancellation, check for remaining workers from that build: Windows
stage termination has left child Python processes alive during diagnosis.
Close only identified build descendants, not every Python process on the host.
Do not bypass content or image-validation gates to obtain a successful status.

Linux's existing launcher, scheduler, worker-count logic and engine build are
unchanged from the cloned v0.0.25 baseline during this investigation. Any
process-management workaround must be Windows-specific. Shared archive-name
and LF-output fixes preserve Linux's existing formats; changed converter source
hashes invalidate older model-cache entries and require their regeneration.

### Diagnostic interpretation and performance

The confirmed failure point is the Python worker's local queue semaphore, not
the Amiga compiler. Worker startup, handle duplication/closure and possible
native-library interactions remain hypotheses. The [bug journal](BUG_JOURNAL.md)
records the evidence and exact fix status for WIN-01 and the separate WIN-02
process-tree cleanup defect. Do not publish private diagnostic logs containing
local paths, usernames, machine identities or owned asset details.

Record actual pool sizes separately from the top-level `--jobs` budget. Pools
can be smaller because of task count or concurrent stage reservations. Stage
allocations are fixed at launch; an existing pool does not automatically grow
when another stage finishes. CPU graphs alone cannot establish throughput or
identify a failure. Compare stage wall times, fresh models/second, cache hits,
active worker count and memory headroom for comparable workloads. Preserve
complete content, quality and validation gates when optimizing the builder.

One completed Windows gallery diagnostic used twelve workers: 3,551 models,
790 validated cache hits, 2,761 fresh conversions, zero failed conversions,
and 988 seconds in model processing. Including dependency/cache checks took
1,051.828 seconds. Final catalogue and payload validation passed for 7,107
files. This is a gallery-stage measurement, not a cold full-game build time
or individual visual acceptance of every model.

## Automated setup

From PowerShell or Command Prompt in the checkout:

```powershell
.\setup-windows.cmd -Plan
.\setup-windows.cmd -Yes
.\build.cmd --versions
.\build.cmd --dry-run --jobs 4
```

The first command previews without requiring Python, downloads or writes.
`-Yes` explicitly authorizes installation. `-ToolsDir C:\AmiWind\amiwind-tools`
selects a different external tools folder; use a short local ASCII path without
spaces as recommended by MSYS2. The Amiga SDK installer may request Windows
administrator approval. Other than installer registration/shortcuts and normal
OS temporary/cache locations, tools and build data stay in the selected tree.
The script does not change firewall policy or global PATH.

Setup verifies cached/downloaded installers by size and SHA-256, checks the
Python Software Foundation signature during online installation, installs the
managed Python/MSYS2/SDK, provisions Python packages, installs map tools and
FFmpeg, and builds QCC from the same hash-pinned sources as Linux. It retains
licences, tests both QuakeC hands variants and the synthetic TES3 NIF reader,
then records tool hashes and versions in `TOOLS/windows-setup.json`.

### Version policy

`config/windows-toolchain.json` records **fresh-install defaults**, including
the tested SDK release, Python installer, Python package constraints and verified
download hashes. The SDK release matches Linux's `fetch_toolchain.SPEC`; QCC
revision/file hashes and dependency requirements are imported from shared code.
Update these defaults deliberately with both host checks, not floating URLs.

An existing Python environment satisfying the shared requirements is reused and
its actual package versions are cached; fresh environments use the tested defaults.
Existing tools are not rejected merely for being older or newer. Older versions
emit an explicit warning naming the original reference version. Newer/different
versions are reported; compatibility checks and actual builds determine whether
they work. Existing managed FFmpeg is reused, including a newer version; if
absent, a pinned build from Gyan (linked by FFmpeg's official download page)
is installed. This script uses direct verified downloads, **not winget**.
Existing managed SDK binaries that differ from the default produce a warning.
Unsupported Python (<3.10), missing files, corrupted downloads, incompatible
dependencies or failed checks still stop setup. Existing source/tool directories
are not overwritten to resolve a conflict.

The Windows Python default is 3.12.10, the conventional installer used for this
checkpoint; the Linux reference is 3.12.14. This difference is explicitly warned
about. This is a compatibility baseline, not a claim that 3.12.10 is the newest
security release. Likewise, MSYS2 packages are signed rolling packages, not a
globally reproducible lock: setup records their resolved versions and retains
their package cache. The tested source build reported 78 compiler warning lines.

### Offline use

After one successful online setup:

```powershell
.\setup-windows.cmd -Yes -Offline
.\build.cmd --dry-run --jobs 4
```

Keep `TOOLS/downloads` (installers, source archives, wheels and wheel checksums),
the provisioned `TOOLS/msys64` tree and its `var/cache/pacman/pkg` directory.
Offline setup verifies caches and installs Python dependencies using `--no-index`.
It never runs package-repository updates or downloads. It requires an already
provisioned MSYS2 tree; restoring a brand-new MSYS2 installation entirely from
cached packages is not implemented. Ordinary builds use installed tools offline.
Missing offline prerequisites fail with a specific path instead of accessing the
network. No game assets or ROMs are downloaded by setup.

## Native Windows launcher

Keep the checkout, tools and private game inputs separate under a common parent:

```text
C:\AmiWind\
  amiwind\          Git checkout
  amiwind-tools\    Python, venv, MSYS2, SDK and conversion tools
  builds\           Optional external build workspace
  GOG Games\        Owned installation (read-only build inputs)
```

From PowerShell in the checkout:

```powershell
.\build.cmd --help
.\build.cmd --host-plan
.\build.cmd --setup-python --plan
.\build.cmd --setup-python
.\build.cmd --dry-run --workspace 'C:\AmiWind\builds' --jobs 4
```

`--setup-python` explicitly installs packages using pip and then exits. Its
requirements come directly from the same `PYTHON_PACKAGES` tuple as Linux;
it creates `amiwind-tools/venv` without changing global Python packages.
`--plan` previews setup without writes. It does not install the native tools.
`--dry-run` actually compiles the engine and creates an asset-free notice HDF.
It needs the SDK and disk tools, but no game files, ROM, map tools or QCC.

You can invoke `build.ps1` directly if your PowerShell execution policy permits
local scripts. `build.cmd` uses Windows PowerShell with a process-local execution
policy and forwards its exit code; it does not change the saved execution policy.

### Required tools

1. **Official Windows CPython 3.10+**, including pip and venv. Start with the
   project's Python 3.12 series when evaluating package compatibility. Use a
   normal installation or `amiwind-tools/python/python.exe`. Do not use MSYS2's
   MinGW Python for the converter's Windows wheels. `AMIWIND_PYTHON` can select
   an explicit executable; otherwise the launcher checks the selected tools
   directory's venv/Python and then `py -3` or `python.exe` on PATH.
2. **[MSYS2](https://www.msys2.org/)** in `amiwind-tools/msys64`, or select its
   existing root using `--msys2 C:\msys64`. Complete its normal `pacman -Syu`
   update, reopening the terminal when requested, then install `make gcc` with
   `pacman -S --needed make gcc`. GNU make and its POSIX shell serve the shared
   engine Makefile; host GCC is for QCC. No global PATH edit is required.
3. **A Windows-hosted [AmigaPorts SDK](https://github.com/AmigaPorts/m68k-amigaos-gcc/releases)**.
   The Linux reference pins `v16.2-rc11`; select the corresponding Windows build
   if available and validate its layout. Set `--sdk PATH` or place it at
   `amiwind-tools/sdk`. Required files include `bin/m68k-amigaos-gcc.exe`,
   `bin/vasmm68k_mot.exe` and `m68k-amigaos/ndk-include/exec/exec_lib.i`, plus the
   SDK's linker, runtime libraries and any host DLLs. No Windows SDK archive
   or installer hash has been verified by this change. Do not use the Linux
   tarball on native Windows.
4. For a **full conversion**, provide ericw-tools 0.18.1 Windows `qbsp`, `vis`
   and `light` in `amiwind-tools/ericw/bin` (or use `--quake-tools`), Windows
   FFmpeg in `amiwind-tools/ffmpeg/bin` (or `--ffmpeg`), and DejaVuSansMono.ttf
   in `amiwind-tools/fonts` (or `--fallback-font`). Build the pinned reference
   QCC revision from the roadmap, including any documented portability patch,
   and select it with `--qcc`. Its bytecode must pass the shared VM checks.

After the asset-free compile and QCC checks succeed, the same pipeline accepts:

```powershell
.\build.cmd --data-files 'C:\AmiWind\GOG Games\Morrowind' --workspace 'C:\AmiWind\builds' --jobs 4
```

Use your actual installation path. `--jobs 4` is a conservative first trial,
not a measured recommendation for every machine. Keep all gallery/content
defaults and validation gates enabled. Test the resulting HDF separately in WinUAE.

### Linux and Windows parity

`.gitattributes` keeps text source files at LF on both hosts so source hashes
and shell scripts remain consistent, including when Git has `core.autocrlf=true`.

Build arguments, dependency requirements, conversion stages, image layout,
source version and validation gates remain shared. Windows adds only `--msys2`
and `--setup-python`; Linux retains `--autoinstall` and its APT/SDK provisioning.
Windows rejects Linux installation switches with a specific setup explanation; use `setup-windows.cmd -Yes` for Windows provisioning.
`--host-plan`, `--versions` and `--check-inputs` can run before MSYS2 is installed.

The CI host-contract matrix runs on Ubuntu and Windows, including real `.cmd`
and `.ps1` argument/exit-code tests on Windows. The existing Linux SDK/image CI
remains in place. This is launcher parity coverage, not evidence of a successful
Windows SDK compile, full game conversion or emulator boot.

## Preferred direction: native Windows/MSYS2

The Windows roadmap prioritizes native Windows/MSYS2 tooling around the shared
Python builder. Compiler, dependency and path integration still need validation.
For an initial read-only inventory, run `py -3 tools\build.py --host-plan`.
The inventory does not install dependencies or certify a working build.

WSL2 is an optional fallback if native Windows compilation proves troublesome.
This priority supersedes the rc5 proposal to try WSL2 first. Neither route has
an AmiWind performance measurement or a verified complete build.

## Fallback: Ubuntu under WSL2

Use these trial notes only when evaluating that fallback. WSL2 Ubuntu can reuse
the existing Linux dependencies and build recipes.
The notes below describe how to try the Linux builder inside WSL2. A complete
Windows/WSL build has not been validated. Linux validation is recorded per
checkpoint; see the [current release notes](RELEASE-v0.0.25-rc6.md) for its completed
stages and remaining limitations.

1. Install Ubuntu using [Microsoft's WSL guide](https://learn.microsoft.com/windows/wsl/install).
   Choose a named distribution with `wsl --list --online`. For an Ubuntu 24.04
   trial, from administrator PowerShell: `wsl --install -d Ubuntu-24.04`.
   Restart if requested, finish Ubuntu first-run setup, and check that
   `wsl --list --verbose` reports version 2 for that distribution.
2. Extract the public source ZIP into your Ubuntu home directory and open a
   terminal in its `amiwind/` directory. Keep tools and build outputs in the
   Linux filesystem; you can read your existing Windows game installation.
   For repeated builds, an owned input copy inside WSL also avoids repeated
   cross-filesystem reads. This follows [Microsoft's filesystem performance guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
3. Run:

```sh
./build.sh --autoinstall
```

Enter your installed Morrowind folder when asked. For example, a Windows install
at `C:\GOG Games\Morrowind` is normally `/mnt/c/GOG Games/Morrowind` in WSL:

```sh
./build.sh --autoinstall --data-files '/mnt/c/GOG Games/Morrowind'
```

The Linux builder is designed to locate nested Data Files folders, check game
inputs, propose missing APT/Python/native dependencies and continue after approved
installation. That automatic path still needs complete WSL validation. Progress,
commands and per-stage logs stay visible; download failures report manual setup
information.

Supply your own installed Morrowind files; buy the game from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).
The builder does not download the game or run its Windows executable.

Keep source, dependencies and generated output in separate sibling directories.
Use explicit `--tools-dir` and `--workspace` paths inside WSL; the final image is
`<workspace>/build/<run>/image/AmiWind-v<VERSION>.hdf`. `--autoinstall --plan` previews setup; `--autoinstall --dry-run`
builds only the asset-free notice image. See the [Linux guide](LINUX_BUILD.md)
for options and manual setup.

## WSL fallback resources and first checkpoint

Review [WSL Settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
(or `%UserProfile%\.wslconfig`) before a large build. The default RAM cap is 50%
of host RAM and is configurable; the default processor allocation includes all
Windows logical processors. This does not imply half the CPU or half the build
speed. Choose resource settings from available capacity and measured usage.
Memory, CPU and swap settings affect all WSL2 distributions. If
restarting with `wsl --shutdown`, finish all WSL work first: it stops every
running distribution. Use `free -h`, `nproc` and `df -h` inside Ubuntu, and also
check free space on the Windows volume holding the distro's virtual disk.
The [roadmap](WINDOWS_BUILD_ROADMAP.md#fallback-only-wsl2-ubuntu)
records the fallback conditions and remaining acceptance work.

From the source directory inside Ubuntu, first try a new asset-free run:

```bash
(
set -euo pipefail
bash build.sh --autoinstall --dry-run \
  --tools-dir "$HOME/amiwind-tools" \
  --workspace "$HOME/amiwind-tests" \
  --name "wsl-dry-run-$(date +%Y%m%d-%H%M%S)"
)
```

This requires no game assets or ROM. A passing result proves the selected
compile/test-image stages only. Then run the full conversion with the same tools
and an owned installation, a new name and no `--dry-run`. Record both results,
including the [completion summary](BUILD_OUTPUT.md). Native WinUAE testing is a
separate checkpoint; Windows FS-UAE autorun is not implemented by these commands.

## Run the result on Windows

Install [WinUAE](https://www.winuae.net/) and use the
[v0.0.25-rc6 WinUAE template](../resources/emulators/AmiWind-v0.0.25-rc6-WinUAE.uae)
with the [WinUAE setup guide](WINUAE.md). Copy the completed HDF from WSL to a
Windows folder, select that HDF and your own **A1200 Kickstart 3.1 ROM**, and
save the configuration. The template includes the accelerated AGA/68040/FPU
settings. Compilation itself needs no ROM.

Alternatively, if Linux FS-UAE and GUI support work in your WSL installation,
you can request automatic configuration and launch:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file '/mnt/c/path/to/your/kickstart-3.1-a1200.rom'
```

Replace that example with a real WSL-readable file or ROM directory. `fs-uae`
must be on the Linux PATH. The launcher accepts a file or searches immediate
files in a directory for the recorded SHA-256; if no ROM is selected it asks
interactively. It fills both ROM and HDF paths in the generated config.
Missing FS-UAE stops before installation/conversion. WSL GUI autorun is untested;
see the [FS-UAE guide](FS-UAE-PLAYTESTING.md). No ROM is downloaded or included.

## Input checks without a full build

With Python 3.10+ installed, check inputs from PowerShell:

```powershell
py -3 tools\build.py --check-inputs --data-files 'C:\GOG Games\Morrowind'
```

Within WSL, Morrowind drive paths can also be translated by `wslpath`. Explicit
`--data-files` wins over discovery. Other editions or languages may differ from
the reference; see [input comparison](BUILD_DEPENDENCIES.md).

## Share a checksum inventory without sharing game data

This optional PowerShell command hashes every installed file and writes a CSV to
the Desktop. It reads the game folder without modifying it. Change `$root` for
your installation. The CSV contains relative paths, byte counts and SHA-256,
not file contents. It can help add an explicitly identified edition reference.

```powershell
$root = (Resolve-Path -LiteralPath 'C:\GOG Games\Morrowind').Path.TrimEnd('\')
$report = Join-Path ([Environment]::GetFolderPath('Desktop')) "Morrowind-GOG-GOTY-$(Get-Date -Format yyyyMMdd-HHmmss)-SHA256.csv"

Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction Stop |
    Sort-Object FullName |
    ForEach-Object {
        [pscustomobject]@{
            Path   = $_.FullName.Substring($root.Length + 1).Replace('\', '/')
            Bytes  = $_.Length
            SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
        }
    } |
    Export-Csv -LiteralPath $report -NoTypeInformation -Encoding UTF8

Write-Host "Saved: $report"
```

### Full conversion passed; image packing needs bounded Windows commands

An instrumented v0.0.25 Windows-port run passed all pre-image stages, including
the complete gallery and all 2,526 terrain regions. It then failed at image
packing with WinError 206: the xdftool command exceeded the Windows process
argument limit. The Windows-only batching correction passed focused file-readback
and regression checks, then passed full HDF validation and WinUAE game entry.
See [the exact successful checkpoint](VALIDATION-WINDOWS-2026-10-02.md).
See [WIN-03](BUG_JOURNAL.md#win-03-windows-image-packing-command-exceeds-process-limit--validation-pending-2-october-2026).
The original failed receipt remains failed; an image-only retry records its own
result. WIN-01 was not observed in this run and remains unresolved.
