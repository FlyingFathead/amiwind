# Build completion output

rc10 adds [verified persistent NPC model reuse](NPC_MODEL_CACHE.md). Full gallery
coverage and protected model quality remain mandatory.

## HDF capacity versus installed content

The final HDF's byte size is its virtual disk capacity, including filesystem
metadata and free space. It is not a count of converted game assets. The current
full-world layout creates as many world partitions as needed, each sized from its
payload plus approximately 20 percent and 16 MiB of headroom, then rounded up
to a 128 MiB boundary. Each partition stays below 2 GiB; the combined legacy
hardfile stays below 4 GiB. When the complete partition set will not fit,
additional HDFs are created automatically and recorded in `hdf_files`.
All drives must remain mounted together.

The reported rc7 image is 3,221,258,240 bytes: two 1.5 GiB partitions plus
32 KiB of disk-layout space. Its exact free space must be read from that build,
not estimated from the container size. `image/build.json` records total
`payload_bytes`, and per-partition `bytes`, `payload_bytes`, `free_bytes` and
file counts after readback of the completed HDF. Capacity minus payload also
includes filesystem overhead; use the recorded bitmap free bytes for available
space. Allocated host-disk blocks, compressed download size and runtime RAM are
different measurements again.

## Completion footer

From v0.0.25-rc5, `build.sh` / `tools/build.py` print a completion footer after the
selected pipeline finishes. The first and last lines are dashes matching the
terminal width (80 columns when no width is available). Long paths/checksums
remain complete even if the terminal wraps them.

A successful image build reports:

```text
Compilation finished without errors
AmiWind v<version> | AGA conversion and image
Started: <local date and time, including UTC offset>
Finished: <local date and time, including UTC offset>
Elapsed: <hours> hrs <minutes> mins <seconds> secs
Python: <detected version>
Python environment packages (not all required by every recipe):
  <package>: <installed version>
Selected compiler/toolkit versions and identities (captured before build):
  <tool>: <detected version or identity explanation>
    Binary SHA-256: <recorded binary digest>
Worker budget: <count> | stage scheduling: <mode>
Compiler warning lines: <count> (engine log)
Warning details: <run>/logs/22-engine.log
File: AmiWind-v<version>.hdf
Path: <run>/image/AmiWind-v<version>.hdf
Size: <GiB> GiB (<exact bytes> bytes)
SHA-256: <64 hexadecimal digits>
Summary: <run>/build-summary.json
```

The success sentence appears only after all selected stages return successfully
and the completed output is readable and checksummed. A missing output or a
hashing failure makes the build fail. The HDF is read in 1 MiB chunks; hashing
does not load the whole image into RAM. A detected change to the file during
hashing also rejects success. The digest identifies the complete file, including
filesystem metadata; it is not a promise of reproducible bytes across builds.

## HDFs and emulator runners

From v0.0.27-rc2, full and asset-free image assembly generates both configuration
formats beside the HDFs. Each configuration mounts every required disk from the
verified layout; the boot drive comes first. An optional owned Kickstart path
is applied locally. Without it, select your own ROM before starting the emulator.
Docker exports also receive configurations with host-local paths.

The final terminal-width footer includes:

```text
--------------------------------------------------------------------------------
Your .hdf file(s):
1. <output>/AmiWind-v<version>.hdf
2. <output>/AmiWind-v<version>-world-01.hdf

FS-UAE and WinUAE runners:
1. FS-UAE: <output>/AmiWind-v<version>-FS-UAE.fs-uae
2. WinUAE: <output>/AmiWind-v<version>-WinUAE.uae
--------------------------------------------------------------------------------
```

Only disks actually required are listed. Saved build summaries include the same
artifact paths; `image/build.json` retains per-drive size, SHA-256, partitions
and readback results. Local paths and ROMs are not public release payloads.

## Timing

`Compilation started:` is printed once after prerequisite checks and setup,
before input/tool/source provenance hashing. The reported elapsed time covers
that hashing, all build stages and final output hashing. It excludes dependency
installation, prerequisite/input checks and any subsequent emulator session.
Start/end use the host's local time with a UTC offset. Elapsed time uses a
monotonic clock and therefore does not depend on wall-clock corrections.
The terminal displays whole elapsed seconds; JSON retains milliseconds. Hours
continue beyond 24 instead of wrapping at midnight.

The footer ends with the build profile: wall and CPU time, average cores
against the job budget, the critical path, the slowest stages and idle-core
warnings, and any stages reused from an earlier run. Per-stage detail is in
`build-profile.json`; see [BUILD_PROFILE.md](BUILD_PROFILE.md).

## Compiler and toolkit inventory

From rc6 the footer repeats the pre-build observations for the tools selected
by the current recipe: GNU make, Amiga GCC, vasm, QCC, ericw map tools, FFmpeg and
amitools commands where selected. Python and installed conversion-package
versions are shown separately as environment information. An asset-free build
does not claim to use all the tools or packages of the full conversion pipeline.

Detected versions are never replaced with the recorded reference versions.
QCC is identified by its binary SHA-256 where no reliable version is recorded;
amitools commands report that their CLI lacks a version flag, alongside the
installed amitools package version. Other unknown/failed probes remain labelled
as such. Binary hashes identify the selected executable bytes, not all shared
libraries or the complete SDK. The JSON also retains selected executable paths.
No extra version probes run at completion. A failed build still lists the
selected environment; this is an inventory, not proof that every tool ran.

The footer also names four content selections, all recorded in
`build-summary.json` (`build_environment`) and the run's `build-state.json`:
`NPC gallery selection` (`enabled` unless `--no-npc-gallery`),
`World flora (trees and grass)` (`enabled` unless `--no-tree-sprites`),
`Harvestable mushrooms` (`enabled` unless `--no-harvest`) and `Extra towns`
(the shipped towns, `vivec_arena (shipped by default)`, plus any `--extra-town`;
`--no-extra-town` and `--only-core-towns` are named as left out); `asset-free` for
`--dry-run`, `not applicable (terrain stage)` for `--stage terrain`. Any
opt-out marks a debugging build that does not match a release; see
[LINUX_BUILD.md](LINUX_BUILD.md#world-flora-default). After an image, the
footer line `Harvestable mushrooms in the image` gives the maps admitted by the
heap check, the plants and the shared models (`harvest` in `build-summary.json`
and the image's `build.json`; details in `image/harvest/harvest-staging.json`).

## Warnings

Warnings are listed separately from success/failure. The footer counts recognized
`warning:` / `warning <number>:` diagnostic lines in the engine stage log; it
is not a count of unique defects. When the count is nonzero, it prints the log
path. Full compiler messages remain in that log and the live build output.
Other conversion/tool warnings remain in their own stage logs. A zero engine
count is not a claim that every stage was warning-free. Missing/unreadable
engine logs are reported as not counted. No compiler warnings are suppressed,
promoted to errors, or repaired by this reporting change.

## Failures, modes and saved results

A caught build failure or cancellation gets its own title and timing, with
`Output: no completed output verified`. A partial HDF is not labelled complete
and is not assigned a final checksum. Existing error messages and exit statuses
remain. Failures before the build starts keep their existing prerequisite/setup
messages. An uncatchable process termination or machine failure cannot print a
footer.

`--dry-run` is explicitly labelled an asset-free, non-playable build; it compiles
the engine/preflight and packages a test HDF. It does not validate game conversion.
Terrain-only output is a directory, so it reports total file bytes and marks a
single-file SHA-256 as not applicable. Check/plan/setup-only modes create no
build-completion receipt. A successful compile/image result does not establish
native runtime or playtest success. Optional emulator launch follows the footer
and retains its separate result.

`build-summary.json` contains the status, mode, version, both timestamps,
`elapsed_seconds`, human-readable elapsed time, output identity and compiler
warning count/log paths. `build_environment` records the interpreter, packages,
selected tool versions/hashes/paths, worker budget, stage scheduling mode and
`jobs_warning`: the one warning printed at the start when an explicit `--jobs N`
exceeds the usable CPU threads (otherwise null; the build still runs N workers).
It is saved atomically when the run directory exists.
If saving the receipt fails, the terminal reports that separately. The receipt
contains local paths: keep it with private build evidence outside the source
checkout. Public release documentation uses sanitized results only.

This does not alter the existing production image acceptance gates. Native
Windows build/image output passed at the [dated checkpoint](VALIDATION-WINDOWS-2026-10-02.md);
v0.0.27 also passed hosted Windows launcher parity. Those results do not certify
every build mode or full-game reliability; see the remaining limits in
[the Windows roadmap](WINDOWS_BUILD_ROADMAP.md).


Private diagnostic builds with explicitly accepted actor findings use the footer
`Private test image assembled; production actor gate DID NOT PASS`. They do not
print `Compilation finished without errors`. Their summary records
`validation: private-test-only` and includes the actor acceptance receipt; the
HDF name ends in `-private-test.hdf`. A completed execution status is distinct
from passing the production contact gate. The raw contact report stays failed.

The NPC stage heading reads `npc-gallery (pre-baking in-game character models...)`
in both serial and parallel builds, including image recovery. The saved stage
identifier and log filenames remain `npc-gallery` for recovery and cache compatibility.

NPC gallery progress reports cumulative `reused`, successfully `converted`,
`failed`, and `remaining` model counts, plus elapsed conversion seconds. The
initial dependency/cache scan is reported separately. Completion counts reflect
finished jobs immediately, rather than input-order results waiting on slow models.
