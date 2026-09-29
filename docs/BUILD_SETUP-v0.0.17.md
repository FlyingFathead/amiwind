# v0.0.17 build setup and test history

This source snapshot is for a local clean setup/build test before publication.
The published v0.0.16 archives and tag remain unchanged. Do not run the old
`publish_first_release.py` helper: it is specific to the initial v0.0.16 release.

## Quickest build

```sh
./build.sh --autoinstall
```

Choose your Morrowind installation and confirm the dependency proposal. The tool
installs missing dependencies and continues into conversion and native/HDF
building. APT may also request your sudo password and package confirmation.
The game installation is read-only; no game files or ROMs are downloaded.

For a clean test, extract this source ZIP into a new parent directory. It creates
one `amiwind/` directory. From that extracted checkout run:

```sh
./build.sh --autoinstall --tools-dir ../tools --workspace ../output
```

Both directories should be new. This creates a fresh Python venv and managed
SDK, map tools and reference QuakeC compiler even if an unrelated active venv or
PATH already supplies similar dependencies. The prepared environment is used
automatically. Builds go to `../output/build/<name>/`; the playable image is
`image/AmiWind-v0.0.17.hdf`. Every run has a new name by default. Failed setup can
be retried with the same command; completed dependency installations remain.
Existing incomplete dependency directories are diagnosed and never overwritten.

`--autoinstall --plan` previews dependency setup without creating anything.
`--autoinstall --check` may install after confirmation and stops before game
conversion. The asset-free build is `--autoinstall --dry-run`, producing
`AmiWind-v0.0.17-dry-run.hdf` with a notice screen. It needs no game data or ROM.

## Changes

- One dependency proposal covers host packages, Python, the pinned Amiga SDK,
  ericw-tools and a locally compiled pinned id Quake-Tools qcc.
- `--install-sdk` also works independently; installed SDKs and native tools are
  discovered automatically. Explicit tool flags take precedence.
- Missing game files at the selected path trigger an announced search through
  at most four subdirectory levels and 2,000 folders. Directory symlinks are
  skipped. Multiple candidates require a choice before hashing.
- Invalid game inputs stop before tool setup. Ctrl+C exits without a traceback;
  interrupted build stages retain their logs and cancellation receipt.
- Relative tool paths are resolved before probes change working directory.
  FTEQCC is recognized as an alternative. Disk-tool availability uses `--help`,
  since xdftool/rdbtool have no version flag.
- QuakeC is compiled in a temporary directory before conversion. Its bytecode
  version, system-variable CRC, section bounds and opcodes are checked. The same
  output checks run when packaging the game image.
- Root `VERSION` supplies Python metadata, native generated C/assembly includes,
  boot/HUD/load text, the Amiga `$VER` tag, receipts and output filenames.
- Source ZIP timestamps use `SOURCE_DATE_EPOCH` when set, otherwise VERSION's
  modification time, instead of the old fixed 1980 date.
- The existing CI job now exercises uncached autoinstall of all public tools,
  then source tests and the asset-free image build. It skips documentation-only
  pushes/PRs and remains manually runnable. No proprietary inputs are installed.

## Progress and logs

Setup commands and build stages have terminal-width separators and report elapsed time.
APT, Python dependencies and native downloads have separate proposal sections.
The APT section lists the requested packages explicitly. Package checks handle
multiple architectures and require an installed native or architecture-independent
package; when none are missing, both APT update and install are skipped.
Status heartbeats pause during sudo/APT commands so they cannot interrupt input
prompts; the commands’ own output remains live. Downloads show transferred
MiB (and a percentage when the pinned size is known) every five seconds. Quiet
verification and build operations report that they are still running every
15 seconds. Converter/compiler output is shown live and retained in the run
folder’s `logs/` directory. Output stays visible when piped through `tee` or in CI.
A heartbeat indicates the operation is still running, not proof of forward progress.

## If a download fails

The downloader prints the exact source/release URL, expected version/hash where
applicable, extraction/build instructions and the flag to select a manual tool
installation. A checksum failure is never bypassed.

- SDK: [AmigaPorts v16.2-rc11](https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/tag/v16.2-rc11).
  Select the Linux x86_64 archive, verify the printed SHA-256, extract it and use
  `--sdk /absolute/path/to/m68k-amigaos-gcc-16.2`.
- Map tools: [ericw-tools v0.18.1](https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1).
  Extract the Linux ZIP including its shared libraries; use
  `--quake-tools /absolute/path/to/ericw-tools-v0.18.1-Linux/bin`.
- Compiler: [id Quake-Tools c0d1b91](https://github.com/id-Software/Quake-Tools/tree/c0d1b91c74eb654365ac7755bc837e497caaca73).
  The downloader provides the exact clone/checkout/compiler commands on failure.
  Use `--qcc /absolute/path/to/Quake-Tools/qcc-host` afterward. The optional Ubuntu
  FTEQCC package can be selected with `--qcc /usr/bin/fteqcc`.

Keep those flags on your original build command, including your chosen
`--tools-dir` and `--workspace`. See [Linux setup](LINUX_BUILD.md) for host/Python
package commands if APT or pip fails.

## Evidence and remaining checks

- Owner's Ubuntu machine: fresh SDK and ericw downloads matched the pinned
  SHA-256 hashes. The pinned qcc source was cloned and compiled successfully.
- Owner's compiler checks: original qcc produced 16,220 bytes, FTEQCC produced
  15,232 bytes; both reported version 6 and CRC 5927. This checks compilation and
  interface compatibility, not gameplay equivalence.
- Local verification: 139 host regression tests passed; empty-destination native-tool
  installation using retained reference archives, actual qcc compilation and
  ericw executable startup. Network downloading was not exercised in that test.
- Local native engine and boot checker compile with the new generated version
  includes. The engine's Amiga version tag and boot-checker banner contain 0.0.17.
- Bootstrap entry point starts without third-party Python packages. Python
  package metadata resolves VERSION to 0.0.17.
- Owner test-004 completed all 12 stages using the actual game installation,
  producing `AmiWind-v0.0.17.hdf`. This repaired and reused the tools downloaded
  during earlier test attempts; it is not a wholly fresh uninterrupted run.
- The owner subsequently confirmed test-006 works. A fresh uninterrupted setup
  after all fixes and updated hosted CI were not independently observed here.
  Native compiler warnings remain for review.

## Test-004 fixes

The owner’s test-003 run downloaded and verified the SDK, map tools and reference
QuakeC compiler, passed the compiler preflight and terrain conversion, then failed
at scenery because the fresh Python 3.12 environment lacked distutils.
The subsequent test-004 run completed the full game-data build, as recorded above.

Setup now installs setuptools for PyFFI, including when repairing an existing
managed venv. Preflight and asset-free CI execute a synthetic NIF write/read.
Each native download step repeats its source URL, temporary archive path,
installation destination and verification information. pip uses verbose output
to expose download source details. Existing tools remain reusable.

## Test-005: optional FS-UAE autorun

`--autorun-fs-uae` checks FS-UAE before installation or conversion. It uses your
owned `~/.roms/kickstart-3.1-a1200.rom`, or `--kickstart-file PATH`. If the default
is missing, interactive mode asks for a ROM path; noninteractive mode exits 1.
Both absolute paths are filled into the documented preset beside the completed
HDF. No usernames are hardcoded, and no ROM is downloaded or packaged.
Missing FS-UAE at startup exits 1; failure to launch after a successful build
warns and keeps the completed build. Checks/plans never launch. The standalone
`tools/run_fs_uae.py --image PATH` launches an existing HDF without conversion.
See [FS-UAE playtesting](FS-UAE-PLAYTESTING.md) for usage and checksum reporting.

Validation: launcher boundary tests cover early failure, ROM selection and
checksum reporting, paths containing spaces, config preservation, check/plan
modes, failed builds, and completed normal/dry-run builds. A harmless executable
stub exercises actual command invocation; this is not an emulator boot test.

## Test-006: cumulative candidate and default demo opening

The cumulative source patch includes all setup and FS-UAE changes through
test-005, plus `early_game_demo_start_1`, enabled by default. The new opening
loads the existing town-center spawn in Seyda Neen and selects track 04 before
normal exploration shuffle. See [opening selection](EARLY_GAME_DEMO_START.md).
The source ZIP and patch contain no game assets or ROMs.

Validation: 29 targeted build, native scene/spawn and music tests passed;
the updated 68040 Amiga engine and boot checker compiled. The actual production
music code was tested against synthetic audio, including first-track selection,
full-track transitions, history and missing-track fallback. The owner then
reported that test-006 works and requested publication. Earlier compiler
warnings have not been hidden or claimed resolved.

## Final source update

The launcher also accepts ROM directories, checks immediate candidate files by
SHA-256, and prompts for another location if no match is found. This host-side
change does not alter the engine tested in test-006. README and both Linux/WSL
guides now lead with `--autoinstall`, with FS-UAE autorun as the Linux play route.
Default bounded build parallelism is documented in [PARALLEL_BUILD](PARALLEL_BUILD.md).
See [final validation scope](VALIDATION-v0.0.17.md).
