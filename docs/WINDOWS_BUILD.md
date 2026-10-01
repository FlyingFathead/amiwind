# Windows build status and WSL notes

rc4 adds experimental host discovery and a read-only `--host-plan` inventory.
It does not add Windows automatic installation or establish a passing build.

**Native Windows/MSYS2 is an untested proposal, not a supported AmiWind build
host.** See the [potential Windows build roadmap](WINDOWS_BUILD_ROADMAP.md).
AmiWind's current setup is Linux-first. Availability of individual Windows
tools does not establish that the complete pipeline works on Windows.

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
