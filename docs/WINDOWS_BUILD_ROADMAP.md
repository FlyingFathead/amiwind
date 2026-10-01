# Potential Windows build roadmap

Status: untested Windows target; native Windows/MSYS2 prioritized, WSL2 fallback only, 1 October 2026.

The rc6 roadmap supersedes the WSL2-first proposal in the rc5 documentation.
This planning decision does not establish a successful Windows build.

**Native Windows/MSYS2 has not been tested with AmiWind.** This document records
a possible direction and the work needed to evaluate it. It is not a working
installation recipe, a support commitment or evidence of a successful build.

The goal would be one conversion/build pipeline with host-specific setup and
tool discovery for Linux and native Windows. Running the pipeline without WSL
or a Linux VM is a goal to investigate, not a capability established by rc4.
The existing [Windows/WSL notes](WINDOWS_BUILD.md) describe a separate route;
that route also lacks a verified complete build.

## Project priority before Windows bring-up

World-terrain build time and avoiding repeated compilation are now the top
engineering priority; see the [build/compiler toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md).
Windows portability remains planned after those measured build-time checkpoints.
The order below governs the Windows workstream when it resumes.

## Windows build priority

1. **Native Windows/MSYS2 first.** Develop and validate the Windows setup and
   toolchain around the shared Python builder. This is the preferred Windows 11
   route for the CPU-, memory- and storage-intensive conversion pipeline.
2. **WSL2 Ubuntu as a fallback.** Consider the existing Linux workflow under WSL2
   if native compiler, dependency or path integration proves troublesome. WSL2
   is optional; it is not a prerequisite for the native Windows roadmap.

No native Windows or WSL2 performance result exists for AmiWind. Prioritizing
native Windows does not establish a measured speed advantage. Keep the Linux
workflow available as the reference while bringing up the Windows toolchain.

## Why investigate MSYS2?

The upstream [Amiga GCC project](https://github.com/AmigaPorts/m68k-amigaos-gcc)
documents Windows/MSYS2 prerequisites and an absolute-path caveat when building
its toolchain. This makes MSYS2 a plausible candidate for investigation. It does
not validate AmiWind's SDK selection, converters, packaging or runtime.

AmiWind's `build.sh` is a small POSIX shell wrapper around `tools/build.py`.
Most orchestration already lives in Python. A Windows port would still need to
resolve tool provisioning, paths, subprocess behavior and dependency versions;
changing the shell alone would not establish support.

## Candidate arrangement to evaluate

One option is official Windows CPython with compatible Windows wheels for the
conversion libraries, native Windows executables for the SDK/map tools/FFmpeg,
and MSYS2 for GNU make and POSIX shell utilities. PowerShell could still be the
user-facing entry point into `tools/build.py`; the internal make recipes would
need a deliberately configured MSYS2 environment. This combination has not
been tested. The exact Python version, MSYS2 environment and package versions
remain decisions to validate, not an installation list.

The existing Python requirements include minimum version ranges. They record
the project's dependencies, not a tested Windows package set. Record the actual
resolved versions and hashes when evaluating this arrangement.

## What rc4 implements

`tools/build_host.py` centralizes OS-specific executable and virtual-environment
paths. `tools/build.py --host-plan` produces a read-only inventory without
installing packages, executing native tools or opening game inputs. It is usable
for gathering an initial Windows report, not certifying a working environment:

```powershell
py -3 tools\build.py --host-plan --tools-dir 'C:\AmiWindTools'
```

The builder recognizes explicit `.exe` tool paths and managed SDK/map/QCC
executables. It distinguishes official Windows Python's `Scripts/python.exe`
from MinGW Python's `bin/python.exe`. The engine build now passes the selected
Python interpreter into GNU make, quoting it for a POSIX recipe shell and
preserving literal dollar signs. Linux checks exercise spaces, quotes and
dollar signs in the interpreter path; Windows make/shell behavior is still
untested. Direct Makefile use retains its `python3` default.

`--fallback-font` selects the console graphics font explicitly; the selected
path reaches the converter and its hash enters build provenance. Discovery
also checks `--tools-dir/fonts/DejaVuSansMono.ttf`, then the existing Linux
system path. No font is downloaded or bundled by this change.

## Remaining integration work

| Area | Current implementation | Work to evaluate |
| --- | --- | --- |
| Automatic setup | Ubuntu/Debian APT and Linux environment provisioning. Windows receives an explicit unsupported-setup message. | Implement a Windows setup backend and dependency consent flow. |
| Amiga SDK | Downloads remain pinned to Linux x86-64; manual discovery recognizes `.exe`. | Select and verify a Windows SDK, including assembler and NDK. |
| Map tools and QuakeC | Executable discovery handles `.exe`; download/build recipes remain unchanged. | Verify Windows ericw archives; build and validate the exact pinned QCC. |
| Python environment | Host-specific layout helpers exist; automatic creation remains Linux-only. | Verify the chosen Python distribution and compatible compiled dependencies on Windows. |
| Make recipes | Selected Python reaches make; recipes use POSIX utilities. | Select and test GNU make plus MSYS2 shell, including SDK/source/output paths with spaces. |
| Console font | Explicit/managed font path supported; Linux default retained. | Provision a licensed, hash-recorded DejaVu font and compare generated graphics. |
| Worker budget | Memory/cgroup detection remains Linux-specific; otherwise CPU count is used. | Add Windows available-memory detection; use explicit conservative `--jobs` during bring-up. |
| Paths and processes | Single-path `cygpath` helper exists; QCC integration is pending. | Test drive paths, argument conversion, permissions, multiprocessing and child-process-tree cancellation. |
| Full build and launch | No Windows end-to-end result exists. | Complete conversion, all image gates and emulator boot/playtesting. |

MSYS2's [Python documentation](https://www.msys2.org/docs/python/) explains that
its MinGW Python cannot use the same compiled-extension wheels as official
Windows CPython. The investigation must choose a consistent environment and
verify NumPy, SciPy, Pillow, PyFFI, fast-simplification and amitools. Mixing
package sources without checking binary compatibility is not a build recipe.

MSYS2-provided POSIX tools and MinGW/UCRT native Windows tools must not be
assumed interchangeable. For example, the pinned QCC source uses POSIX calls
including `mkdir(path, 0777)`. The presence of `unistd.h` does not establish that
every call compiles with the selected compiler/runtime. Build that exact QCC
revision, record any required portability patch, and validate its generated
`progs.dat` before using it for a full build.

Likewise, a Windows download URL is only part of integrating a tool package.
Verify its actual archive layout, size, SHA-256, executable names and runtime
DLL dependencies. Windows ericw-tools packages and an equivalent SDK remain
items to select and test; this roadmap does not endorse an unverified filename
or hash. Manually passing `--sdk` alone does not fix the remaining host checks.

## Path translation and QCC

Use filesystem path translation at a known command boundary. Native Python can
retain Windows paths; commands that require MSYS2 paths can receive a `cygpath`
conversion. The rc4 helper translates exactly one argument, calls the tool
without a shell, and propagates failures:

```powershell
py -3 tools\build_host.py 'C:\AmiWind Work\Quake-Tools' --cygpath 'C:\msys64\usr\bin\cygpath.exe' --style unix
```

The helper is not yet wired into a Windows QCC source-build recipe. MSYS2's
[path documentation](https://www.msys2.org/docs/filesystem-paths/) explains its
automatic argument/environment conversion as well as explicit `cygpath` use.
Audit each boundary; do not rewrite every argument or globally disable all
conversion. Compiler flags and path lists need separate handling.

Path translation cannot adapt C APIs. There are two QCC options to test:
MSYS-runtime GCC may handle the POSIX source but introduces an MSYS DLL
dependency; MinGW/UCRT targets native Windows and may need a small compatibility
patch for `mkdir(path, 0777)` and other CRT differences. Build pinned revision
`c0d1b91c74eb654365ac7755bc837e497caaca73`, retain any patch in source control,
and run `check_quakec()` on AmiWind's actual QuakeC. Require program version 6,
system-variable CRC 5927, valid section bounds and supported VM opcodes.
Neither compiler route has been tested on Windows for this checkpoint.

## Proposed checkpoints

Each checkpoint would need recorded evidence before proceeding. Windows acceptance remains
open for every checkpoint; Linux helper tests do not establish Windows support.

1. **Select the environment.** Evaluate an MSYS2 environment and Python
   distribution; record the Windows version, tool versions and dependency
   sources. Confirm that all required packages can coexist.
2. **Compile without game inputs.** Build the Amiga engine, assembler components
   and QuakeC program. Retain the program-version, system-variable CRC and
   opcode checks in `tools/build_aga.py`. Record and review compiler warnings.
3. **Integrate host setup.** Add Windows-specific provisioning and discovery
   behind the shared Python entry point. Keep the existing Linux defaults and
   command-line options. Test quoted paths, interpreter selection, managed
   fonts, virtual environments, memory-aware parallelism, subprocess failure
   reporting and cancellation of the entire child-process tree.
4. **Exercise conversion.** Run source checks and focused regressions, then
   conversion using an owned installation. Use the actual
   [game input layout](GAME_INPUT_LAYOUT.md), including `Data Files`, loose
   assets and the base-master ESM/BSA. Compare structural validation results
   and relevant outputs with the same inputs on Linux.
5. **Complete and validate the image.** Finish every required stage with the
   normal validation gates enabled. Record elapsed time, worker count, peak
   memory and disk use. Boot the resulting image in a Windows emulator using
   an owned ROM, then check the opening route, input, audio and scene changes.
6. **Document demonstrated support.** Only after the complete build and runtime
   checks pass, publish an exact Windows setup recipe and validation record.
   Redact personal paths and machine identifiers from public receipts. Add
   Windows source/toolchain CI where practical; keep owned game data private.

Cross-host comparison should include BSP structure and contents, QuakeC output,
Amiga executable format and behavior, and the HDF's extracted payload. Record
hashes, investigate differences, and distinguish documented metadata changes
from geometry, collision, bytecode or asset changes. Neither byte-for-byte
identity nor acceptable differences can be assumed before that comparison.

## Fallback only: WSL2 Ubuntu

Evaluate WSL2 Ubuntu only if native Windows/MSYS2 bring-up proves troublesome.
It can reuse the Linux SDK, pinned Linux QCC recipe, APT setup and Linux Python
dependencies. That compatibility makes it a fallback worth investigating; it
does not establish a passing AmiWind build or acceptable performance.

[Microsoft's installation guide](https://learn.microsoft.com/en-us/windows/wsl/install)
describes running Linux tools under WSL. Install a named Ubuntu release to keep
the host version deliberate, then verify version 2 with `wsl --list --verbose`.
Ubuntu 24.04 is a reasonable initial comparison host; this checkpoint has no
complete WSL build receipt for it.

Keep source, SDK, Python environment and generated work in WSL's Linux filesystem.
[Microsoft recommends that placement for Linux tool performance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
Reading an existing game installation under `/mnt/c` is possible, but many small
reads can make it slower. An owned input copy inside WSL is preferable for timing
comparisons. Copy the completed HDF to Windows for native WinUAE testing.

[WSL resource settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
control memory, processors and swap. By default, WSL2 has a configurable cap
of 50% of Windows host RAM and access to all Windows logical processors. The
RAM default does **not** mean half the CPU allocation or half the build speed.
It is a resource limit, not a benchmark result.

If this fallback is tried, set the memory budget deliberately while leaving
headroom for Windows. Inspect available memory, CPU allocation and swap before
choosing the worker count; there is no measured AmiWind-specific setting to
recommend yet. Swap does not guarantee that a memory-heavy build finishes.

The distro's virtual disk consumes real host storage. Check Linux `df -h` and
free space on its backing Windows volume: a large virtual capacity is not free
physical space. See [WSL disk management](https://learn.microsoft.com/en-us/windows/wsl/disk-space).
Default WSL also mounts Windows drives and permits Windows-process interoperation;
it must not be treated as an isolated disposable VM with no workstation access.

The acceptance sequence is: inventory versions and capacity; asset-free compile
and HDF/readback; full owned-data conversion and all image gates; then Windows
emulator testing. Retain each result separately. Use the new
[build summary](BUILD_OUTPUT.md) to compare elapsed times with the same source,
inputs and build scope. Compare payload identity and structural checks as well
as whole-HDF hashes, since filesystem metadata can change the latter. No speedup
or completion-time estimate is established until those measurements exist.
Detailed trial commands are in [the WSL notes](WINDOWS_BUILD.md).

## Scope

The rc4 helpers are initial groundwork, not a completed Windows backend. This
roadmap promises no completion date or performance gain. The current build pipeline has no GPU-acceleration path;
GPU access is not a justification for claiming faster AmiWind conversion.
Native Windows emulator availability is separate from build-host validation.
Compiler success alone would not certify a complete or playable image.

## Bundled QCC as a possible default

The [third-party compiler plan](THIRD_PARTY_COMPILERS.md) proposes bundling the
pinned QCC source and licence, with minimal recorded Windows patches, a managed
external build cache and explicit compiler-provider selection. This could make
fresh setup less dependent on upstream downloads. It remains a proposal; path
translation alone does not solve C API/runtime differences. Linux, WSL2 and
native Windows require separate compiler and full-build evidence.

## Build performance is a separate workstream

The [build and compiler toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) proposes
per-phase region profiling, measured CPU/storage improvements and optional GPU
asset-conversion experiments. It also records GPU-assisted QCC as deferred
research. None of those backends is implemented or required for this Windows
portability roadmap. Prefer evidence from the actual complete pipeline over
hardware specifications or isolated-kernel speedup claims.
