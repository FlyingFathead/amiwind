# Windows 11 and Morrowind installations

The first full-build route on Windows is Ubuntu under WSL2. The current AGA
build was verified on Linux x86_64, not yet on Windows/WSL. Native Windows
package provisioning and the complete native build are not validated. The input
checker uses Python's standard library and accepts Windows paths.

## Point at your installation

GOG commonly installs this edition to `C:\GOG Games\Morrowind\`. This is a
suggestion, never a requirement. Select your actual installation root; the tool
finds Data Files beneath it. Selecting Data Files directly also works. Quote
command-line paths containing spaces.

With Python 3.10+ installed, check inputs from PowerShell:

```powershell
py -3 tools\build.py --check-inputs --data-files 'C:\GOG Games\Morrowind'
```

Inside WSL Ubuntu, that Windows folder is usually mounted at
`/mnt/c/GOG Games/Morrowind`. Pasted Windows drive paths are translated with
WSL's `wslpath`, so either form can be supplied:

```sh
./build.sh --check-inputs --data-files 'C:\GOG Games\Morrowind'
./build.sh --check-inputs --data-files '/mnt/c/GOG Games/Morrowind'
```

Interactive mode detects WSL or native Windows, checks the default GOG location,
and compares Morrowind.esm/Morrowind.bsa sizes and SHA-256 hashes with the
reference. A matching installation is offered with `[Y/n]`. Decline to enter
another location. If no matching default is found, it asks for your folder.
Explicit `--data-files` always wins; noninteractive runs never guess. Accepting
the suggestion starts the full input check before conversion.

Reference sizes are 79,837,557 bytes for Morrowind.esm and 310,459,500 bytes for
Morrowind.bsa. Sizes alone are insufficient: both hashes must match too.
Different editions/languages may be valid without matching our current reference;
see [input comparison and overrides](BUILD_DEPENDENCIES.md).

## Install and build under Ubuntu/WSL

Install WSL/Ubuntu using [Microsoft's WSL guide](https://learn.microsoft.com/windows/wsl/install).
Keep the source checkout and build intermediates in the Linux filesystem when
practical; read the existing Windows game installation through its mount. There
is no need to run Morrowind.exe or copy the Windows executables.

```sh
./build.sh --install-dependencies --install-sdk --plan
./build.sh --install-dependencies --install-sdk
. ../amiwind-tools/venv/bin/activate
./build.sh --dry-run --sdk ../amiwind-tools/sdk --name first-test
```

This creates the asset-free notice image. For the playable scene, follow the
[full Linux guide](LINUX_BUILD.md) for ericw-tools and qcc, then supply the game
folder without `--dry-run`. Output defaults to `out/build/<name>/image/`; use
`--workspace` to choose another parent.

Compilation needs no Kickstart ROM. A separately supplied licensed ROM is needed
when booting the HDF in WinUAE or FS-UAE.

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
