# Dependency checks and reference versions

The full AGA build has three kinds of dependency:

| Source | Dependencies | Purpose |
| --- | --- | --- |
| Ubuntu/Debian APT | Python 3.10+, python3-venv, python3-pip, build-essential, FFmpeg, unzip, xz-utils, fonts-dejavu-core | Host scripts, compilation, audio conversion, extraction and diagnostic text |
| Python virtual environment | setuptools (PyFFI distutils compatibility), PyFFI, NumPy, Pillow, SciPy, fast-simplification, amitools | Models, geometry, images and Amiga disk filesystems |
| Separate public tools | AmigaPorts GCC SDK/vasm, ericw-tools, id Quake-Tools qcc | Amiga executable, BSP maps and QuakeC |

The terrain-only converter needs Python and the owner's base game data. The
asset-free test image needs Make, the Amiga SDK/vasm and amitools; it does not
need game data, ROMs, FFmpeg, ericw-tools or qcc. See [CI and dry-run](CI_DRY_RUN.md).

## Confirmed installation

The quickest route installs missing dependencies and continues into the build:

```sh
./build.sh --autoinstall
```

It discovers existing tools, checks your selected game installation, shows the
missing-dependency proposal and asks for confirmation. The SDK and ericw-tools
downloads are pinned by size/SHA-256. Reference qcc source is pinned to commit
`c0d1b91c74eb654365ac7755bc837e497caaca73` with individual source-file hashes;
the setup compiles it locally and checks its output against AmiWind's VM format.
The source, licences and receipts remain beside each installed tool.

No manual shell activation is needed. Managed tools live in `../amiwind-tools/`
by default; `--tools-dir` relocates them. SDK, map tools and qcc are rediscovered
by subsequent builds and `--versions`. Explicit tool paths take precedence.
Choose `paths` at the proposal to supply existing tools elsewhere.
`--autoinstall --plan` previews dependency setup only and never installs.
`--autoinstall --check` installs only after confirmation, then checks without
game conversion. Plain interactive Linux builds/checks also offer setup.

For host/Python setup only (no automatic continuation):

```sh
./build.sh --install-dependencies --plan
./build.sh --install-dependencies
. ../amiwind-tools/venv/bin/activate
```

The first command only prints the proposed setup. The second shows missing APT
packages, Python requirements, commands and the environment location, then asks
`Run this dependency setup? [y/N]`. No installation or directory creation occurs
before confirmation. APT keeps its own confirmation, including resolved versions
and download sizes. It uses configured distribution repositories; pip uses the
configured Python package indexes. Existing suitable packages are reused.

Add `--install-sdk` to either command to include the pinned Linux x86_64 SDK
download. It is verified against its recorded byte size and SHA-256 before safe
extraction into `../amiwind-tools/sdk`. The SDK includes its own licence notices.
An existing SDK destination is never overwritten. Use `--tools-dir /chosen/path`
to relocate the environment and optional SDK. The SDK downloader needs Python
with `tarfile.data_filter` (Python 3.12+ is the straightforward choice).
`./build.sh --install-sdk` also works on its own, with no APT/pip setup;
`--install-sdk --plan` is a read-only preview. Complete SDKs are reused.

Activation puts Python, xdftool and rdbtool from the environment on PATH. It is
not necessary to install the AmiWind project into global Python. The shell
launcher delegates the actual work to Python under tools/.

Automatic host setup supports Ubuntu/Debian, including Ubuntu under WSL. Native
Windows package provisioning is not implemented. Python must already exist to
launch this checker. Ubuntu 22.04+ provides a sufficiently recent system Python.
The `--autoinstall` route handles ericw-tools and the reference qcc as well.
With a new tools directory it creates a fresh venv even if another active Python
environment already has the dependencies. It provisions managed map tools and
the reference qcc regardless of unrelated PATH entries; explicit tool flags win.
For CI, `--autoinstall --install-dependencies --yes` installs all conversion tools
without needing game files, then exits. `--yes` explicitly accepts setup and
APT confirmations. Normal interactive use does not require this flag.
The APT host list includes libgmp10, libmpfr6 and libmpc3 for the cross-compiler.

## Version comparison

```sh
./build.sh --versions
```

`tools/build-reference.json` records the environment used for checkpoint-017 and
the source 0.12.1.dev1 rebuild. The same report is printed before an AGA build
and saved in its receipt. `--versions` is an informational inventory, not a build
success gate. Missing required tools still block the relevant build mode.

| Label | Meaning |
| --- | --- |
| matching | Detected version equals the recorded reference; qcc uses the reference executable hash |
| newer / older | Numeric release differs from the reference |
| unknown | Unrecognized banner, failed probe, different same-release suffix, or unrecognized qcc executable |
| alternative | FTEQCC found; a different compiler family, not a version match to id qcc |
| available | xdftool/rdbtool responds to --help; its CLI has no version flag |
| missing | Package or executable was not found |

Matching version text alone does not imply identical binaries or successful
compilation. Vendor and prerelease suffix differences are not silently treated
as matching. Tool hashes are saved with actual builds. A locally rebuilt qcc may
be valid but differ from the reference binary; its SHA-256 will then be unknown.
The report shows resolved executable paths, including relative paths supplied
on the command line. The separate `amitools` package row describes the current
Python environment; it is not silently attributed to an executable from another
environment. QuakeC preflight compiles the selected hands variant in a temporary
directory and checks bytecode version, system-variable CRC, section bounds and
supported opcodes. Temporary files are removed; a runtime playtest is still needed.

Ubuntu/Debian provides `fteqcc` through APT. Discovery recognizes this executable;
`--qcc /usr/bin/fteqcc` selects it explicitly. `--autoinstall` builds a managed
reference compiler unless it is already present or an explicit `--qcc` choice
was made.

Recorded versions: Python 3.12.14, GNU Make 4.3, host GCC 13.3.0, Amiga GCC
16.2.0b 20260825082934, FFmpeg 6.1.1-3ubuntu5, ericw-tools 0.18.1, qcc source
revision c0d1b91, NumPy 2.5.3, SciPy 1.17.0, Pillow 12.3.0, PyFFI 2.2.3,
fast-simplification 0.2.0 and amitools 0.8.1. The earlier standalone assembler is
vasm 1.9d. The pinned SDK's vasm 2.0f also passed the source 0.12.1.dev1 engine,
boot-checker and dry-run notice compilation; the notice was boot-tested locally.
Neither version comparison nor CI replaces a full game conversion and playtest.

The installer uses the project's supported Python dependency constraints rather
than forcing all these environment versions onto another machine. Its results
can therefore differ and must be reported and tested. This is not a lockfile.

## Game inputs and editions

Select the installation root or Data Files itself. The checker walks the loose
file tree, checks all ESM record/subrecord boundaries and BSA entry ranges, checks
required asset groups, and compares known-file sizes and SHA-256 checksums.
`config/input-reference/` contains 7,197 filename/size/hash records from the
installation used for the reference build, with no asset content. The reference
edition/language is not independently certified yet; do not label it as a
universal GOG/Steam checksum database.

When no core pair is present directly or under Data Files, it announces a bounded
search: four directory levels, at most 2,000 folders, no directory symlinks.
It locates candidates before inventory or hashing. Multiple candidates require
an interactive choice or a specific `--data-files` argument. Missing or invalid
inputs stop before dependency installation. The game prompt includes GOG and
Steam store links. Ctrl+C cancels without a Python traceback.

The terrain stage compares the core master/archive. The AGA stage also compares
the reference Music and Sound files. Splash remains optional. AGA font conversion
now prefers the loose GOG GOTY `BookArt/*.ttf` sources and falls back per family to
Bethesda's `Fonts/*.fnt` + `.tex` pairs. At least one usable Magic Cards source is
required for the current UI. Missing preferred TTFs are warnings, not build errors,
when the bitmap fallback is complete. The warning identifies the Steam-typical
layout, recommends GOG GOTY, links its store page and notes that rasterized results
may vary or be inferior at scaled/non-native sizes. Additional files have no
reference checksum and are reported as unrecognized. Expansion/plugin load orders
are not applied. Videos, Windows executables and manuals are not required for the
current scene.

An unrecognized edition or intentional file modification stops by default.
`--allow-data-differences` explicitly permits checksum/missing-reference differences
while still enforcing container structure and required asset groups. This does
not certify that edition. Individual referenced models, textures and audio are
validated as conversion reaches them; a preflight cannot prove every decoder and
gameplay behavior is correct.

The GOG default-location suggestion checks both core sizes and SHA-256 hashes
before offering the folder. Full input checking still follows acceptance.

Package references: [Ubuntu Python setup](https://ubuntu.com/developers/docs/howto/python-setup/),
[AmigaPorts releases](https://github.com/AmigaPorts/m68k-amigaos-gcc/releases),
[ericw-tools](https://github.com/ericwa/ericw-tools),
[id Quake-Tools](https://github.com/id-Software/Quake-Tools).

Python 3.12 no longer includes distutils or installs setuptools in a new venv.
PyFFI 2.2.3 imports distutils, so the converter explicitly requires
`setuptools>=68`. Build preflight and CI exercise the actual TES3 NIF reader
with an in-memory synthetic write/read before conversion. This uses no game data.
See [Python 3.12 changes](https://docs.python.org/3/whatsnew/3.12.html#distutils).

## Original game inputs; remote-work archives are excluded

The Morrowind_*.zip and datafiles.zip packages supplied for remote work are not
GOG/Steam installation inputs. The builder never requires or extracts those ZIPs.
Select the installation root or Data Files directory; discovery finds the original
Morrowind.esm/Morrowind.bsa pair beneath it, then uses the original known asset
folders and subfolders (Video, Sound, Music, Meshes, Textures, Fonts, BookArt,
Icons and Splash). Name matching is case-insensitive. Only supported game asset
types enter validation and build input hashes. Personal archives stay untouched.
