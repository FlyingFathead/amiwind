# One AmiWind repository

Official project home: https://github.com/FlyingFathead/amiwind

**`amiwind/` is the only repository root.** Open or initialize that directory as
the repository. Its README.md, pyproject.toml and build.sh are at that root.
Every path in the public source ZIP starts with `amiwind/`. Extract the ZIP from
the parent directory. The source ZIP filename includes the version; the directory
inside does not. No second source directory needs to be copied or published.

## Contents

| Path relative to amiwind/ | Purpose |
| --- | --- |
| README.md | Project entry point and official URL |
| src/mwad/ | Host conversion library |
| tools/ | Build, conversion, inspection and release commands |
| engine/aga/src/ | Complete authoritative native AGA C/header source |
| engine/aga/Makefile | Native engine build rules |
| engine/aga/boot/ | 68000 hardware/RAM preflight source |
| engine/aga/qc/ | Native gameplay/scene QuakeC source |
| runtime/ | Preserved older A500 runtime and terrain reader |
| tests/ | Host and native-source regression fixtures |
| docs/ | Development, provenance, validation and roadmap |
| resources/emulators/ | Public emulator presets |
| out/ | Ignored local build outputs; never included in source ZIP |
| .github/workflows/ | Source tests and asset-free Amiga compilation |

Game assets, original/converted fonts, ROMs, toolchains, compiled binaries, HDFs
stay outside distributable source. Build outputs default to ignored `out/`,
with `--workspace` available for an external location. Only the five selected
README screenshots are approved documentation images. Component licence notices
remain distinct: host/A500 code uses the root licence; the AGA engine retains its
own COPYING and upstream notices. Consolidation does not relicense code.

## Why the old ZIP had two roots

The v0.0.15-dev2 ZIP combined the main `morrowind-amiga-demake/` project with
`amiwind-runtime-v0.0.15-dev2-source/`, a separately assembled corresponding-source
snapshot. The main project held AGA additions and a patch against an external
upstream archive. That was a two-package source bundle, not one clean checkout.

The pre-release source snapshot 0.12.1.dev1 merged them. Duplicate native additions and QuakeC were compared
byte-for-byte before keeping one copy. The selected complete native tree now lives
under engine/aga/. The unified v0.0.16 release carries that work forward with
one shared version, boot credits, blue water tint and the 540 fog default.

## Build source authority

The engine builder copies engine/aga/ into a new build directory named runtime/
and compiles there. Native edits made in this checkout are therefore the actual
build input. The receipt records source hashes. No upstream archive or patch is
needed. Legacy --archive/--upstream-archive arguments remain optional provenance
checks and never replace the checked-in source.

The historical baseline source manifest and upstream patch are under docs/aga/.
They identify checkpoint-017, are not current source manifests, and are not
applied automatically. Current source contents are declared in
`tools/release-files.json`; each packaged version generates
`docs/PACKAGE_MANIFEST.json`. Additions must be explicit.

Fresh build output: `<external-output>/runtime/build/AmiQuakeGCC`, with the
AmiWindCheck preflight program alongside it. The guided build's image stage uses
that path. Existing older build outputs and release packages remain unchanged.

The Python distribution/release name is now amiwind; the import package and
existing `mwad` command remain unchanged. Existing external workspaces bearing
the legacy project identifier are still accepted. Both old and new source trees
remain protected against placing private game data beneath them.

## Historical repository-consolidation validation

The results below describe the original consolidation checkpoint. Current
source/build/publication evidence is in [v0.0.27 release notes](RELEASE-v0.0.27.md).

At that checkpoint, 113 host tests passed, including dependency-consent, reference-checksum, WSL-path,
corruption and output-boundary cases. Native engine/preflight compilation passed
with the reference GCC and both standalone vasm 1.9d and SDK vasm 2.0f. The
asset-free HDF passed filesystem/payload readback and booted to its notice in
FS-UAE with a privately supplied ROM. All 7,197 reference data hashes matched.

At that checkpoint, GitHub-hosted execution, a clean-machine package setup,
a fresh full scene conversion and Windows/WSL execution had not been performed.
The consolidation itself did not change gameplay. See [v0.0.16](RELEASE-v0.0.16.md)
for the subsequent tint/default changes. Later Windows, Docker and hosted CI
results are recorded separately; those early unperformed checks are historical.
