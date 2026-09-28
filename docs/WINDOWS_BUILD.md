# Build AmiWind on Windows with WSL

## Quickest route: Ubuntu under WSL2

Use Ubuntu under WSL2 to run the same one-command builder as Linux. Native
Windows dependency installation and full Windows/WSL builds have not yet been
validated; the owner has confirmed the Linux build and FS-UAE launch work.

1. Install Ubuntu using [Microsoft's WSL guide](https://learn.microsoft.com/windows/wsl/install).
   From an administrator PowerShell terminal: `wsl --install -d Ubuntu`.
   Restart if requested, open Ubuntu, and finish its first-run setup.
2. Extract the public source ZIP into your Ubuntu home directory and open a
   terminal in its `amiwind/` directory. Keep tools and build outputs in the
   Linux filesystem; you can read your existing Windows game installation.
3. Run:

```sh
./build.sh --autoinstall
```

Enter your installed Morrowind folder when asked. For example, a Windows install
at `C:\GOG Games\Morrowind` is normally `/mnt/c/GOG Games/Morrowind` in WSL:

```sh
./build.sh --autoinstall --data-files '/mnt/c/GOG Games/Morrowind'
```

The builder locates nested Data Files folders, checks game inputs, displays the
missing APT/Python/native dependencies, asks before installing, and continues
conversion and compilation. No manual venv activation, SDK, ericw-tools or qcc
setup is needed. Progress, commands and stage logs stay visible. If a download
fails, it prints the source link and manual setup instructions.

Supply your own installed Morrowind files; buy the game from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).
The builder does not download the game or run its Windows executable.

Tools default to `../amiwind-tools/`; output defaults to
`out/build/<run>/image/AmiWind-v0.0.17.hdf`. Use `--tools-dir` and `--workspace`
to relocate them. `--autoinstall --plan` previews setup; `--autoinstall --dry-run`
builds only the asset-free notice image. See the [Linux guide](LINUX_BUILD.md)
for options and manual setup.

## Run the result on Windows

Install [WinUAE](https://www.winuae.net/) and use the
[v0.0.17 WinUAE template](../resources/emulators/AmiWind-v0.0.17-WinUAE.uae)
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
