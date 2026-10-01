# AmiWind v0.0.25-rc4 — build-host groundwork and Windows roadmap

Source checkpoint retaining rc3's interior-window repair. Native Windows/MSYS2
remains an untested target; this is not a Windows-support release.

## Changes

- Centralize host-specific `.exe` and Python virtual-environment discovery.
- Add `--host-plan`, a read-only inventory that does not install dependencies,
  execute native tools or inspect game inputs. Windows automatic setup and SDK
  downloads remain unimplemented, with explicit diagnostic messages.
- Pass the builder's selected Python interpreter into the native engine's GNU
  make invocation. Quote it for a POSIX recipe shell, including literal dollars.
- Accept `--fallback-font`, check a managed tools font before the Linux system
  fallback, forward the selected font to the scene converter and hash it in
  build provenance. No font binaries are included.
- Add a single-path `cygpath` helper. It is not yet integrated into a Windows
  QCC source-build recipe. Path translation does not adapt C runtime APIs.
- Expand the potential Windows roadmap with MSYS/MinGW distinctions, exact-QCC
  compatibility checks and separate compile/conversion/image acceptance gates.

## Verification and limits

A fresh Linux-hosted AGA 68040 engine and boot checker compile passed with rc4
version identity. Engine C/assembly/QuakeC sources are unchanged from rc3.
This invocation reports 36 compiler warnings; no runtime warning fixes or
suppressions were added. This is not a warning-free result.
All 345 source tests pass with external qbsp enabled, and the actual Linux QCC
passes the QuakeC compatibility check. Explicit/default Linux console-font
selection produces identical glyph pixels. C test fixtures now use the
Python-selected temporary directory, avoiding hardcoded system-temporary
storage; their assertions are unchanged.
Host tests exercise Windows path-selection logic by simulation. They do not
prove execution on Windows. See the [validation receipt](validation/rc4-source.json)
for exact test results, hashes and limitations.

The prior rc3 Linux full rebuild passed 21 stages, including the repaired area
conversion, then failed with `ENOSPC` while copying world-terrain BSPs into the
final scene. Its world-terrain stage did not pass, and image assembly was not
reached. rc4 has no completed full conversion/HDF/boot result. The unchanged
production image gate still has 23 historical actor-contact findings; none is
waived by this checkpoint.

Deliverables contain public source, updater and checksums only. Original game
inputs, converted assets, ROMs, compiled executables and playable images are
excluded. Published rc3 and earlier archives/tags remain immutable.

See [Windows roadmap](WINDOWS_BUILD_ROADMAP.md),
[local checkpoint instructions](LOCAL-RC4.md) and
[release workflow](RELEASE_WORKFLOW.md).
