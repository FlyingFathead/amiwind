# Windows build roadmap

## v0.0.26-rc1 checkpoint

**Linux is the established foundation; native Windows 11 remains experimental.**
The complete current recipe converted on native Windows, produced a verified
HDF after correcting/retrying image assembly, and entered Jiub's prison scene
in WinUAE 6.0.3. See the [dated validation record](VALIDATION-WINDOWS-2026-10-02.md)
and [rc1 release notes](RELEASE-v0.0.26-rc1.md) for exact provenance and limits.
The tested full image used the v0.0.25 runtime identity; rc1 packages the port.

Windows setup/build entry points delegate to the same Python conversion pipeline
used by Linux. Official Windows CPython supplies the extension-module environment;
MSYS2 supplies POSIX tools and QCC. The [Windows guide](WINDOWS_BUILD.md) records
versions, offline limitations and commands. Existing tools are compared with
reference versions; version drift warns and actual checks decide compatibility.

## Remaining reliability and validation work

- **WIN-01, open:** intermittent ProcessPoolExecutor queue-handle failures during
  geometry conversion. Root cause is unknown; lowering worker count and a passing
  retry have not established a fix. Retain failed receipts/logs.
- **WIN-02, open:** cancellation has left worker descendants running. Integrate
  and validate Windows-specific cleanup without altering Linux process control.
- **WIN-03, fixed in this candidate:** oversized Windows xdftool command lines
  are split into bounded operation batches; final image readback passed.
- Exercise a new uninterrupted full run, broader gameplay, scene transitions,
  saves and audio. The smoke test confirms boot/game entry/basic input.
- Validate Linux on Linux/CI. Preserve its launchers, scheduler, engine source,
  file formats, full-content defaults and normal gates. Portable BSA identifiers
  use forward slashes; generated Amiga text uses LF on both hosts.

Use the [bug journal](BUG_JOURNAL.md) for symptoms, reproduction, evidence and
fix-versus-mitigation status. Fresh run names can reuse validated model caches;
there is no generic resume of every finished stage and no measured retry rate.

## Final v0.0.26: Docker next

Implement and validate the [Docker builder and input helpers](DOCKER_BUILD_ROADMAP.md)
around the existing Linux pipeline. Users supply their own game files through
read-only runtime mounts, with persistent outputs/caches outside the image.
Do not include original/converted game assets, HDFs or ROMs in image layers.
Start with a provisional 40 GiB free-space allowance and revise from measured
complete builds. Docker is absent from rc1 and is part of final-release scope.

Native Windows does not require WSL. A Linux container on Windows is a separate
host result; it cannot replace native Windows validation. WSL remains an optional,
unvalidated fallback described in the [Windows notes](WINDOWS_BUILD.md).

## Build performance

Measure complete wall time, individual stages, fresh conversions versus verified
cache hits, effective worker counts, CPU/RAM and peak storage. The successful
terrain stage processed 2,526 regions in 572.34 seconds with a 24-worker budget;
that is not a cold whole-build timing. Preserve useful local intermediates.
Improve throughput without omitting content or relaxing quality/validation.
See the [toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) and
[compiler roadmap](THIRD_PARTY_COMPILERS.md) for further work.
