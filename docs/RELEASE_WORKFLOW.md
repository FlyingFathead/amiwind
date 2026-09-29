# AmiWind release workflow

Official project: https://github.com/FlyingFathead/amiwind/

Use one shared release number. The current public source release is **v0.0.22**;
see [release notes and validation](RELEASE-v0.0.22.md). Earlier releases remain immutable.
AmiWind remains a demo. Public GitHub releases use plain `0.0.x` version numbers;
development checkpoints after v0.0.22 use **v0.0.23-dev1**, then dev2, dev3, and so on.
Use a new dev suffix for each delivered checkpoint; retain prior artifacts unchanged.
The old separate Python pipeline numbering is historical. Root `VERSION` is the
only maintained version number. Build and packaging tools read it through
`tools/project_version.py`; Python package metadata reads the same file.
The native Makefile generates C and assembly version includes in the build tree.
Boot/HUD/load text, the Amiga `$VER` identifier, receipts and output filenames
therefore use that number. A value such as `0.0.17-dev1` normalizes to
`0.0.17.dev1` in Python package metadata. Historical release records keep their
original numbers. The current delivery set is v0.0.23-dev1.

## Deliverables and structure

| Archive | Structure and purpose |
| --- | --- |
| `AmiWind-v0.0.23-dev1-public-source.zip` | Complete repository under `amiwind/`; extract from `/path/to/downloads/`. |
| `AmiWind-v0.0.23-dev1-public-source-incremental.zip` | Added/changed public files under `amiwind/`, since the exact uploaded v0.0.22 workspace. |
| `AmiWind-v0.0.23-dev1-private-playable.zip` | TTF-present private playtest: HDF, launcher, README and `build.json` at its root, plus ROM, presets, conversion receipts and evidence. |
| `AmiWind-v0.0.23-dev1-bitmap-private-playable.zip` | Separate bitmap-only private playtest with the same structure and filled paper ink. |

Each ZIP has a same-name `.sha256` sidecar. The private package includes the
owner's supplied ROM as `roms/kickstart-3.1-a1200.rom`; it is never a GitHub asset.
Asset-free dry-run images contain no ROM/game data and do not replace playable
packages. No separate dry-run archive is delivered for dev1.

The source repository has one root. Native AGA code is in `engine/aga/`, host
conversion code in `src/mwad/`, commands in `tools/`, documentation in `docs/`,
presets in `resources/emulators/`. Only core files and README belong at the root.
Keep compiled output in ignored `out/` or a chosen external workspace. Preserve
previous methods, fonts, hand variants and release archives.

## Incremental updates

Name the exact patch base and SHA-256 in `docs/PATCH-v0.0.23-dev1.json`. Include only
added/changed files and patch metadata. List deletions explicitly; unzip alone
cannot remove obsolete files. Verify a clean application reproduces the full
source tree, including its generated package manifest. Always provide the full
source alongside the patch.

The dev1 patch starts from `amiwind-2026-09-29_124939.zip`, SHA-256
`d01d1bf130e4072dc794417f4127a3d7e62469861a85b3b3d146ff5d1baad568`.
Its base manifest identifies the actual uploaded source bytes. Do not overwrite
newer local changes with the incremental archive. Check the base first or unpack
the complete source into a separate directory for comparison.

## Release gate

**ALWAYS CHECK FOR TRAILING WHITESPACE BEFORE POSTING AN AUTOMATED PUSH/PUBLISH
SCRIPT.** Check all delivered files before posting or packaging. This check
belongs to package preparation, before the owner downloads or applies anything.
Passing tests and an archive allowlist do not replace it.

`tools/release.py --check`, candidate creation and candidate validation all reject
trailing spaces/tabs, whitespace-only lines, space-before-tab indentation and
blank lines at EOF in new or modified text files. Only byte-identical historical
base files are exempt; the current patch's base hashes identify them. This also
covers files that are untracked or extracted without Git metadata. Before
delivery, additionally run `git diff --no-index --check BASE_TREE CANDIDATE_TREE`
on clean extracted source trees and retain the result. Keep the owner's
`git diff --check` as a final check, not the first place defects are discovered.

Candidates are written under `incoming/`, checked independently, then promoted
into immutable `releases/`. Validate ZIP paths, source allowlist, content hashes,
patch application, private image/ROM hashes, corresponding source and boot
behavior. Never overwrite a released ZIP or relabel an old executable as a new
build. Keep historical version strings in historical records accurate.

Update README, project state, changelog and validation notes before packaging.
Report the tests actually run and their limits. Public CI compiles without game
files or ROMs. Full conversion, Windows/WSL and physical Amiga behavior require
their own validation. The owner runs Git/GitHub commands; see FIRST_RELEASE.md
for the historical first-release workflow. The source repository and source
releases are public. Playable images, converted game files and supplied ROMs
remain private and must never become GitHub release assets.

## Boot identity

Normal preflight and dry-run screens display their shared AmiWind version. The
preflight also repeats the version in its pass/fail footer so screenshots always
identify the runtime under test. Guest-visible hardware is reported by
`AmiWindCheck`; FS-UAE-only settings are validated by the portable host launcher.
The boot identity also includes:

```text
By FlyingFathead
https://github.com/FlyingFathead/amiwind/
Special thanks to: ChaosWhisperer
```

Public source excludes original/converted game data, reusable extracted fonts,
ROMs and private images. The five owner-approved README screenshots are a
documentation exception. Preserve component licence notices and keep complete
development recovery sets separate from playable packages.

Public documentation and release assets use generic example paths. Keep owner
usernames, machine names and local directory layouts in private handoff material.
