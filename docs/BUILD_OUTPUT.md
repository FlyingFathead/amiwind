# Build completion output

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

## Timing

`Compilation started:` is printed once after prerequisite checks and setup,
before input/tool/source provenance hashing. The reported elapsed time covers
that hashing, all build stages and final output hashing. It excludes dependency
installation, prerequisite/input checks and any subsequent emulator session.
Start/end use the host's local time with a UTC offset. Elapsed time uses a
monotonic clock and therefore does not depend on wall-clock corrections.
The terminal displays whole elapsed seconds; JSON retains milliseconds. Hours
continue beyond 24 instead of wrapping at midnight.

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
selected tool versions/hashes/paths, worker budget and stage scheduling mode.
It is saved atomically when the run directory exists.
If saving the receipt fails, the terminal reports that separately. The receipt
contains local paths: keep it with private build evidence outside the source
checkout. Public release documentation uses sanitized results only.

This does not alter the existing production image acceptance gates. Windows
execution remains untested; see [the Windows roadmap](WINDOWS_BUILD_ROADMAP.md).


Private diagnostic builds with explicitly accepted actor findings use the footer
`Private test image assembled; production actor gate DID NOT PASS`. They do not
print `Compilation finished without errors`. Their summary records
`validation: private-test-only` and includes the actor acceptance receipt; the
HDF name ends in `-private-test.hdf`. A completed execution status is distinct
from passing the production contact gate. The raw contact report stays failed.
