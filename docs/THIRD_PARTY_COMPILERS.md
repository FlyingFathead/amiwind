# Third-party compilers and bundled QCC proposal

Status: design proposal recorded in v0.0.25-rc5, 1 October 2026. QCC is still
installed outside the repository. No bundled source provider, provider switch
or native Windows QCC patch is implemented in this checkpoint.

## Current behavior

`tools/fetch_native.py` downloads the id Software Quake-Tools source archive at
revision `c0d1b91c74eb654365ac7755bc837e497caaca73`, verifies nine selected files
by size and SHA-256, compiles QCC and runs `check_quakec()` against AmiWind's
actual QuakeC. The selection includes its headers and `COPYING`: 109,571 bytes
before archive compression. Those values were checked against the installed
reference source; the manifest is `QCC_FILES` in that tool.

The normal bootstrap reuses the managed `Quake-Tools/qcc-host` installation. It
does not clone the repository on every game build. The download serves a fresh
setup; `git clone` is a documented manual fallback. The existing `--qcc` option
selects an external compiler explicitly, with compatibility checks. Vendoring
would reduce fresh/offline setup dependencies and make host patches reviewable;
it would not materially accelerate the long world-conversion stages.

## Proposed source layout and provenance

Prefer a small, explicitly maintained source selection under
`third_party/quake-tools/qcc/`, with the original `COPYING` beside the source.
Keep an upstream record at `third_party/quake-tools/README.AmiWind.md`: repository
URL, exact revision, original file hashes, component licence, selected files,
build recipe and all local modifications. Keep host-portability patches under
`third_party/quake-tools/patches/` and apply them to an external build copy.
The patched files must carry dated modification notices as required by their
licence. Do not silently rewrite upstream files or discard their notices.

The existing release allowlist must explicitly include the selected source,
licence, provenance and patches. Preserve byte-exact upstream content with a
narrowly scoped, hash-verified vendored-source packaging rule where necessary;
do not disable whitespace or source-content checks for the rest of the project.
Compile the host executable outside the checkout. Public source releases would
contain the source and build material, not prebuilt compiler executables.

## Proposed switchable provider

These are proposed build-configuration choices, not current command-line flags:

| Provider | Intended behavior |
| --- | --- |
| `bundled` | Proposed default after validation: verify the bundled source and patches, then build or reuse a matching managed host compiler. No QCC source network fetch. |
| `external` | Use an explicitly selected executable, preserving the current `--qcc` override and compatibility test. |
| `download` | Optional explicit fallback using the same pinned upstream revision and source hashes. Never fetch an unpinned latest version. |

An explicit `--qcc` without a provider selection would select `external`.
Conflicting explicit settings must produce an error, not silently choose one.
A failed bundled-source hash check or compile must stop; it must not silently
switch compilers or download replacements. Setup should report the selected
provider, source/patch hashes, host compiler, flags and final executable hash.
Cache reuse should match those inputs plus host OS/architecture and runtime;
changing a Windows/Linux host, compiler recipe or patch invalidates the cache.

## Linux and native Windows; WSL2 fallback

Native Windows/MSYS2 is the first Windows target to investigate. WSL2 remains
an optional fallback if native integration proves troublesome; it would share
the Linux recipe. Native Windows needs a separately verified recipe for its
chosen compiler/runtime. MSYS POSIX GCC and MinGW/UCRT
GCC are different targets: the former may add an MSYS runtime dependency;
the latter uses native Windows CRT behavior. Record and ship any required
runtime dependencies appropriately if binaries are ever distributed.

Path translation only translates paths at a tool boundary. It does not repair
C API differences such as `mkdir(path, 0777)` versus Windows `_mkdir(path)`.
Start from the exact pinned source; use minimal, conditional host changes and
validate filesystem/binary I/O behavior, including paths with spaces. Keep
semantic compiler changes separate from host-portability changes.

Every provider must compile AmiWind's actual QuakeC and pass `check_quakec()`:
program version, system-variable CRC, bounds and supported opcodes. Compare
`progs.dat` from bundled and existing pinned compilers on Linux before changing
the default, and investigate any difference. Repeat on native Windows during
bring-up, and separately on WSL2 if that fallback is evaluated. QCC success
alone does not validate Amiga GCC, ericw,
asset conversion, image assembly or emulator playback.

## Licensing boundary

The pinned [QCC source notice](https://github.com/id-Software/Quake-Tools/blob/c0d1b91c74eb654365ac7755bc837e497caaca73/qcc/qcc.c)
grants GPL version 2 or later. Its
[COPYING](https://github.com/id-Software/Quake-Tools/blob/c0d1b91c74eb654365ac7755bc837e497caaca73/qcc/COPYING)
sets the redistribution conditions: retain copyright/warranty/licence notices,
include the licence, and mark modified files with their changes and dates.
A separate GPL compiler can be included with independent project components;
mere aggregation does not itself relicense them. Output is not automatically
GPL-covered just because QCC produced it; its content and source determine that.

If host compiler binaries are distributed later, provide their exact complete
corresponding source, modifications, interface files and compilation/installation
scripts with equivalent access at the same distribution location. A pointer to
some upstream revision alone is not the corresponding-source plan for a patched
binary. Review the actual selected files and any added dependencies before such
a binary release. QCC's licence does not license other SDK/assembler components
or Quake/Morrowind game assets; review each component on its own terms.
See [component licensing and credits](LICENSING_AND_CREDITS.md).

## Checkpoints before changing the default

1. Import and verify the minimal source/licence/provenance selection; update
   package rules and test source-patch application.
2. Implement provider selection and reproducible cache identity. Prove bundled
   QCC can build without network access when its host C compiler is installed.
3. Compile actual QuakeC, compare with the current reference, and exercise
   missing, corrupt and conflicting provider selections.
4. Validate Linux and native Windows separately with documented patches.
   Require a separate WSL2 result if that fallback is evaluated.
5. Only then make `bundled` the default for validated hosts. Keep explicit
   external selection available and report full-build results separately.

## Deferred compiler acceleration research

Optional bundled QCC could support controlled future experiments, including
GPU-assisted host compilation if actual profiling establishes a useful parallel
workload. Vendoring source alone does not provide CUDA support. The compiler
must still emit compatible Quake VM bytecode for the Amiga; CUDA-targeted output
would serve a different runtime. Measure QCC's share before prioritizing it over
asset conversion. See the separate [build and compiler toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md#deferred-possibility-gpu-assisted-qcc).
