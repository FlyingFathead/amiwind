# Dependency checks and reference versions

The full AGA build has three kinds of dependency:

| Source | Dependencies | Purpose |
| --- | --- | --- |
| Ubuntu/Debian APT | Python 3.10+, python3-venv, python3-pip, build-essential, FFmpeg, unzip, xz-utils, fonts-dejavu-core | Host scripts, compilation, audio conversion, extraction and diagnostic text |
| Python virtual environment | PyFFI, NumPy, Pillow, SciPy, fast-simplification, amitools | Models, geometry, images and Amiga disk filesystems |
| Separate public tools | AmigaPorts GCC SDK/vasm, ericw-tools, id Quake-Tools qcc | Amiga executable, BSP maps and QuakeC |

The terrain-only converter needs Python and the owner's base game data. The
asset-free test image needs Make, the Amiga SDK/vasm and amitools; it does not
need game data, ROMs, FFmpeg, ericw-tools or qcc. See [CI and dry-run](CI_DRY_RUN.md).

## Confirmed installation

From the repository root:

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

Activation puts Python, xdftool and rdbtool from the environment on PATH. It is
not necessary to install the AmiWind project into global Python. The shell
launcher delegates the actual work to Python under tools/.

Automatic host setup supports Ubuntu/Debian, including Ubuntu under WSL. Native
Windows package provisioning is not implemented. Python must already exist to
launch this checker. Ubuntu 22.04+ provides a sufficiently recent system Python.
ericw-tools and qcc remain explicit setup steps for full game conversion.

## Version comparison

```sh
./build.sh --versions --sdk ../amiwind-tools/sdk
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
| missing | Package or executable was not found |

Matching version text alone does not imply identical binaries or successful
compilation. Vendor and prerelease suffix differences are not silently treated
as matching. Tool hashes are saved with actual builds. A locally rebuilt qcc may
be valid but differ from the reference binary; its SHA-256 will then be unknown.

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

The terrain stage compares the core master/archive. The AGA stage also compares
the reference Music and Sound files. Missing/different optional Fonts and Splash
files do not block the current build. Additional files have no reference checksum
and are reported as unrecognized. Expansion/plugin load orders are not applied.
Fonts, videos, Windows executables, manuals and GOG extras are not required for
the current scene. The original-font conversion experiment remains separate.

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
