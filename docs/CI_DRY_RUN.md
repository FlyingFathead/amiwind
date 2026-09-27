# Asset-free compilation and boot image

The GitHub Actions workflow `.github/workflows/source-check.yml` runs on pushes,
pull requests and manual dispatch. It uses an Ubuntu 24.04 runner and Python 3.12,
installs public host/Python dependencies, checks the source allowlist, runs the
synthetic tests (including host-compiled native harnesses), fetches the pinned
Amiga SDK, compiles the engine/preflight program and builds a small boot-notice HDF.

No Morrowind installation, game assets, Kickstart ROM, Workbench files or private
recovery archives are inputs to this workflow. It does not run an emulator or
claim full gameplay validation. Action dependencies are pinned by commit, and
the SDK archive is pinned by URL, size and SHA-256. New versions require an
intentional reference update. The first hosted run remains to be performed after
the owner publishes the repository; local compilation/image checks have passed.

## Local use

```sh
./build.sh --install-dependencies --install-sdk
. ../amiwind-tools/venv/bin/activate
./build.sh --dry-run --sdk ../amiwind-tools/sdk --name first-dry-run
```

Here `--dry-run` means an actual asset-free test compile and image build. Add
`--plan` to preview the two stage commands without executing them, or `--check`
to stop after prerequisites. It never accepts a game path. The normal full build
uses no `--dry-run` flag. Both modes use the runtime VERSION in tools/build_aga.py.

Default output is under ignored `out/build/<name>/`. `--workspace /other/path`
chooses another output parent. Names are immutable; retry under a new name.

| Build | Image name |
| --- | --- |
| Normal, with locally converted game data | AmiWind-v0.0.16.hdf |
| Asset-free test compile | AmiWind-v0.0.16-dry-run.hdf |

The test disk has an 8 MiB FFS partition in an RDB image. Its startup-sequence
runs a tiny 68000 notice program using the ROM's console/font. It shows the
runtime version, explains that this is a test compile without game files, asks
the reader to obtain Morrowind and rebuild with their installation, and points
to https://github.com/FlyingFathead/amiwind. It sleeps after displaying the text.
The compiled engine is included for inspection but is not launched without data.

To boot locally, attach the image as an RDB hard drive and supply your own
licensed Kickstart 3.1 ROM. The local verification used FS-UAE 3.1.66,
A1200/AGA, 68040/FPU, 2 MiB Chip and 16 MiB Fast. This only verifies the notice
screen. The ROM is not included in any public image or artifact.

## Public artifact

```sh
python tools/package_dry_run.py --image-dir out/build/first-dry-run/image --out out/artifacts
```

This creates `AmiWind-v0.0.16-dry-run.zip` and a checksum sidecar. The ZIP
contains the exact HDF matching the asset-free build receipt, the receipt,
README, native licence, and the corresponding versioned source ZIP. The nested
source ZIP extracts into `amiwind/`. Normal game-containing HDFs cannot be passed
to this packaging route without the matching asset-free receipt.

CI uploads only that ZIP and checksum, with 14-day retention, and never uploads
the general working directory. It creates no release, tag or commit. There are
no private assets in the CI checkout. Uploading the artifact tests packaging;
booting and performance remain separate checks.
