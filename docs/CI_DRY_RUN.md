# Asset-free compilation and boot image

_Last updated with AmiWind v0.0.54 (27 October 2026)._

The GitHub Actions workflow `.github/workflows/source-check.yml` runs on pushes,
pull requests, tags, a weekly schedule and manual dispatch. It uses Ubuntu 24.04
runners and Python 3.12, installs public host/Python dependencies, checks the
source allowlist, runs the synthetic tests (including host-compiled native
harnesses), fetches the pinned Amiga SDK, compiles the engine/preflight program
and builds a small boot-notice HDF.

From v0.0.53 the work is split into jobs that run side by side (before, one job
did all of it in a row and outgrew its time limit):

| Job | What it does |
| --- | --- |
| `tools` | Bootstraps every public tool into an empty directory (`tools/build.py --autoinstall --install-dependencies`) when anything the installer reads has changed, and keeps that directory in the Actions cache. Otherwise it restores the kept copy and checks it file by file. |
| `source-checks` | The source allowlist, the NIF reader check and the setup plan. |
| `tests` | The whole test suite, in parallel jobs (`tools/run_tests.py --shard I/N`), shown as `Test suite part 1 of 6` to `Test suite part 6 of 6` ([CI.md](CI.md)). |
| `dry-run` | After the tests pass: the engine compile, the boot-notice image and its package. |
| `tools-from-nothing` | On tags, every Monday and on request: the bootstrap into an empty directory with no cache, then the dry-run image built with those fresh tools. |
| `host-launcher-parity`, `docker-builder` | The host launcher checks on Linux and Windows, and the Linux container builder. |

**The tools cache.** Its key (`python tools/ci_tools.py key`) is a hash of the
installer's own code: the modules the setup imports, found from their import
statements, which also hold the pinned versions and download lists of the SDK,
the map tools, the QuakeC source, the Python packages and the host packages. The
key also names the runner image and its Python version. Any change to one of
these bootstraps again from nothing in that same run. A finished bootstrap
writes a manifest of every file (SHA-256, size, executable bit, link target);
each job that uses a restored copy checks it against that manifest before
anything runs, then runs the same installer, which only adds host packages the
runner lacks. `python tools/ci_tools.py inputs` lists the files the key covers.
One import is left out on purpose: after building the reference QuakeC compiler,
the installer test-compiles our QuakeC with it (`build_aga.check_quakec`); that
checks the compiler and adds nothing to the tools, and the tests compile the
same sources again.

**The test shards.** `tools/run_tests.py --shard I/N` runs whole test modules,
spread over the N shards by the recorded module times in
`tests/module-timings.json`, longest first to the lightest shard. The split
depends only on the commit, so all shards of one run agree on it, and the runner
checks that every module is in exactly one shard before it starts.
`--list --shard I/N` prints the tests of one shard.

**The time limits.** Each job has its own `timeout-minutes`, kept so that the
slowest recorded run stays under 80 % of it. The first run of the split layout
(v0.0.53) bootstrapped the tools from nothing in 28 minutes 15 seconds, so from
v0.0.54 `tools` has 40 minutes and `tools-from-nothing` (that bootstrap plus an
uncached dry-run) has 60. The slowest test shard took 19 minutes of its 30.

No Morrowind installation, game assets, Kickstart ROM, Workbench files or private
recovery archives are inputs to this workflow. It does not run an emulator or
claim full gameplay validation. Action dependencies are pinned by commit, and
the SDK archive is pinned by URL, size and SHA-256. New versions require an
intentional reference update. The first hosted run remains to be performed after
the maintainer publishes the repository; local compilation/image checks have passed.

## Local use

```sh
./build.sh --autoinstall --dry-run --name first-dry-run
```

Here `--dry-run` means an actual asset-free test compile and image build. Add
`--plan` without `--autoinstall` to preview the two stage commands once tools
are installed. `--autoinstall --plan` previews dependency setup only. Use `--check`
to stop after prerequisites. It never accepts a game path. The normal full build
uses no `--dry-run` flag. Both modes use the runtime VERSION in tools/build_aga.py.

Default output is under ignored `out/build/<name>/`. `--workspace /other/path`
chooses another output parent. Names are immutable; retry under a new name.

| Build | Image name |
| --- | --- |
| Normal, with locally converted game data | AmiWind-v0.0.17.hdf |
| Asset-free test compile | AmiWind-v0.0.17-dry-run.hdf |

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

This creates `AmiWind-v0.0.17-dry-run.zip` and a checksum sidecar. The ZIP
contains the exact HDF matching the asset-free build receipt, the receipt,
README, native licence, and the corresponding versioned source ZIP. The nested
source ZIP extracts into `amiwind/`. Normal game-containing HDFs cannot be passed
to this packaging route without the matching asset-free receipt.

CI uploads only that ZIP and checksum, with 14-day retention, and never uploads
the general working directory. It creates no release, tag or commit. There are
no private assets in the CI checkout. Uploading the artifact tests packaging;
booting and performance remain separate checks.
