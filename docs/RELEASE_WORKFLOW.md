# AmiWind release workflow

Official project: https://github.com/FlyingFathead/amiwind/

Use one shared release number, currently **v0.0.16**. AmiWind remains a demo;
keep increments within `0.0.x`, with `-devN` for development iterations as needed.
The old separate Python pipeline numbering is historical. `pyproject.toml` is
the authoritative version; build and packaging tools read it through
`tools/project_version.py`. Python `.devN` maps to public `-devN` spelling.
Native boot/HUD/load strings must match or the build/source gate stops.

## Deliverables and structure

| Archive | Structure and purpose |
| --- | --- |
| `AmiWind-v0.0.16-public-source.zip` | Complete repository under `amiwind/`; extract from `~/NeuralNetwork/`. |
| `AmiWind-v0.0.16-public-source-incremental.zip` | Added/changed public files under `amiwind/`, since the exact preceding delivered source. |
| `AmiWind-v0.0.16-private-playable.zip` | Private package with `AmiWind-v0.0.16.hdf`, README and `build.json` at its root, plus `roms/`, `resources/emulators/`, `docs/`, `private-conversion/` and `evidence/`. |

Each ZIP has a same-name `.sha256` sidecar. The private package includes the
owner's supplied ROM as `roms/kickstart-3.1-a1200.rom`; it is never a GitHub asset.
The optional asset-free `AmiWind-v0.0.16-dry-run.zip` has a notice HDF and matching
source, contains no ROM/game data and does not replace the playable package.

The source repository has one root. Native AGA code is in `engine/aga/`, host
conversion code in `src/mwad/`, commands in `tools/`, documentation in `docs/`,
presets in `resources/emulators/`. Only core files and README belong at the root.
Keep compiled output in ignored `out/` or a chosen external workspace. Preserve
previous methods, fonts, hand variants and release archives.

## Incremental updates

Name the exact patch base and SHA-256 in `docs/PATCH-v0.0.16.json`. Include only
added/changed files and patch metadata. List deletions explicitly; unzip alone
cannot remove obsolete files. Verify a clean application reproduces the full
source tree, including its generated package manifest. Always provide the full
source alongside the patch.

This patch starts from `amiwind-0.12.1.dev1-source.zip`, SHA-256
`73b06b6189de15ad0baa9d43c47541de30fe2e07d83dfcb3e44fdebfd90423c4`.
That file contains newer consolidation work despite its misleading old pipeline
number. Users starting from the two-root v0.0.15-dev2 source should extract the
full v0.0.16 ZIP into a fresh `amiwind/` instead. Back up local edits first.

## Release gate

Candidates are written under `incoming/`, checked independently, then promoted
into immutable `releases/`. Validate ZIP paths, source allowlist, content hashes,
patch application, private image/ROM hashes, corresponding source and boot
behavior. Never overwrite a released ZIP or relabel an old executable as a new
build. Keep historical version strings in historical records accurate.

Update README, project state, changelog and validation notes before packaging.
Report the tests actually run and their limits. Public CI compiles without game
files or ROMs. Full conversion, Windows/WSL and physical Amiga behavior require
their own validation. The owner runs Git/GitHub commands; see FIRST_RELEASE.md
for one initialization/push/tag/release workflow. The repository starts private.

## Boot identity

Normal preflight and dry-run screens display their shared AmiWind version and:

```text
By FlyingFathead +- ChaosWhisperer
https://github.com/FlyingFathead/amiwind/
```

Public source excludes original/converted game data, reusable extracted fonts,
ROMs and private images. The five owner-approved README screenshots are a
documentation exception. Preserve component licence notices and keep complete
development recovery sets separate from playable packages.
