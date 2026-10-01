# AmiWind v0.0.25-rc5

Source checkpoint: build completion timing, output size and checksums.

The shared builder now prints `Compilation finished without errors` only after
all selected stages and final output hashing succeed. Terminal-width rules
surround start/end timestamps with timezone offsets, hours/minutes/seconds,
engine compiler-warning lines, output filename/path, GiB/exact bytes and SHA-256.
A JSON summary is saved with the external build logs. Failures and cancellation
have separate wording and never advertise partial output as completed.
See [output semantics](BUILD_OUTPUT.md).

All 353 source tests pass. A fresh Linux build compiles the versioned 68040/FPU
engine and preflight, assembles an asset-free 8,421,376-byte HDF and checks every
payload readback. Its final digest matches an independent SHA-256 calculation.
That serial run reports 78 compiler-warning lines; this change does not suppress
or fix them. The first parallel native attempt failed at make's output capture
on a host with an exhausted system filesystem. Even a one-line echo recipe
failed with parallel output synchronization there; the fresh `--jobs 1` run
passed. The failed attempt is not recorded as successful.

Full game conversion/image acceptance is still incomplete; the prior rc3 full
run exhausted disk space during world-terrain assembly. The 23 historical actor
contact findings and production gate remain unchanged. No emulator boot or
Windows/MSYS2/WSL full build was performed for rc5. The [Windows roadmap](WINDOWS_BUILD_ROADMAP.md)
and rc4 host groundwork are retained. WSL2 Ubuntu is now documented as the
first proposed Windows-host experiment, without claiming a WSL pass. The
[third-party compiler proposal](THIRD_PARTY_COMPILERS.md) describes bundled
pinned QCC and provider selection; neither is implemented in rc5. Detailed evidence: [rc5 receipt](validation/rc5-source.json).

The incremental patch requires the rc4 source baseline. Full source, patch,
standalone updater and SHA256SUMS are supplied. Previous archives and tags remain
unchanged. Public source contains no HDF, converted game data or ROMs; no private
playable package is delivered.
