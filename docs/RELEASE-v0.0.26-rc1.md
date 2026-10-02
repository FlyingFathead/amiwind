# AmiWind v0.0.26-rc1

This prerelease packages the native Windows 11 port and the fixes used to build
the complete current AmiWind recipe and enter the game in WinUAE. Linux remains
the established build foundation; native Windows is experimental. **Docker is
next and is planned for the final v0.0.26 release; rc1 does not include it.**

## Changes

- Native Windows setup and build entry points: .cmd, PowerShell and the shared
  Python pipeline. Setup records actual tool versions, warns about differences
  from known reference versions and supports reuse of provisioned offline tools.
- Portable forward-slash BSA identifiers and explicit LF output for Amiga text.
  These match Linux's existing formats. Linux launchers, scheduler and engine
  source are unchanged from cloned v0.0.25 commit
  3433922c40a48ffd20a0362ed58407298221686a.
- Windows-only xdftool batching fixes WIN-03's deterministic command-length
  failure during large image assembly. Linux tool invocation stays unchanged.
- Windows/Ubuntu host regression coverage, setup documentation, public defect
  records, measured performance/storage observations and a Docker implementation
  plan with Windows/Linux helpers for user-supplied inputs.

## Demonstrated Windows result

All 25 pre-image stages passed, including 3,551 NPC gallery models and all
2,526 world terrain regions. The original run failed at final image assembly;
after fixing WIN-03, a separately recorded image-stage retry reused validated
conversions and passed every normal image gate. No gallery, model-quality or
actor-ground waiver was used. Readback verified 8,974 DH0 files and 1,651 DW0
files in the 3.25 GiB HDF.

WinUAE 6.0.3 with owned Kickstart 3.1, AGA/PAL, 2 MiB Chip, 16 MiB Z3,
68040/FPU/JIT and fastest CPU reached the main menu, played the opening movie,
rendered Jiub's prison scene, accepted keyboard/name input and returned cleanly
to AmigaDOS. This is a limited game-entry smoke test, not full playthrough proof.

The full image was built before the release-name bump and displayed **v0.0.25**.
Its historical receipts and hash remain unchanged. rc1 packages that Windows
port/fix checkpoint under the new source version; do not relabel the old image
as a separately tested rc1 full-game build. See
[the detailed record](VALIDATION-WINDOWS-2026-10-02.md) for timings, versions,
image hash and recovery provenance.

## rc1 source/version checks

On Windows, 38 focused host/setup, archive-format, batching, release and version
tests passed; two POSIX-only checks were skipped. The rc1-versioned Amiga engine
and asset-free HDF compiled in 5.531 seconds with 78 warning lines, and image
readback passed. Its 8,421,376-byte HDF SHA-256 is
4fdf74a34079a9eda65fd59397e47d6f2eb2e7f9b7a884a496051592fceaf892.
This separate test image is not playable and was not launched again in WinUAE.
Protected Linux source and its existing CI job match the cloned baseline;
11 portable conversion/packing files passed structural comparison after
accounting for equivalent formats and Windows-only branches.
See [the source validation receipt](validation/v0.0.26-rc1-source.json).

## Known limitations and next work

- WIN-01: intermittent Python geometry-worker queue-handle failure; cause unknown.
- WIN-02: cancellation can leave Windows worker descendants running; cleanup
  integration remains pending. Check the failed build's workers before retrying.
- Preserve failed logs and validated model caches, then start a fresh run.
  General stage resume is not implemented; retry frequency is unmeasured.
- This Windows host has not supplied a fresh Linux test result. Run Linux source,
  regression and asset-free compile checks before publishing from Linux.
- Docker image and input helpers remain to be implemented and validated for
  final v0.0.26. They must ship only source/tools and use owned game-data mounts.

See [Windows setup](WINDOWS_BUILD.md), [known bugs](BUG_JOURNAL.md),
[Linux builds](LINUX_BUILD.md) and [Docker roadmap](DOCKER_BUILD_ROADMAP.md).
The release archive contains public source and existing selected documentation
media only; no original game data, converted payload, HDF, ROM or private notes.
