# Development and source packaging

All documentation lives in `docs/`; keep the root limited to core project files.
Original/converted game content stays outside distributable source. Build output
uses ignored out/ or a selected external workspace.
The project owner handles all Git/GitHub pushes. No remote is configured by the
source package, and packaging does not commit, tag, push or publish anything.

## Source authority

There is one repository root, `amiwind/`. Edit native code directly in
`engine/aga/src/`; the builder compiles an external copy of that checked-in tree.
The old upstream patch under `docs/aga/` is historical and is never applied by
the current builder. Keep the existing immutable release archives as baselines.
See REPOSITORY_LAYOUT.md for the path mapping and RELEASE_WORKFLOW.md for the
single version shared by source, runtime and release packages.

## Tests

```sh
python -m unittest discover -s tests -v
```

Fixtures are generated into temporary directories using fictional data. No
Morrowind files are needed for tests. GCC or Clang enables the C reader test;
that test is explicitly skipped if neither compiler is available. The host
tests do not measure Amiga performance.

## Explicit release file list

`tools/release-files.json` lists the source files permitted in a source archive.
Add a path deliberately when adding distributable source. Review the content
policy first. The checker rejects unexpected files, missing files, source
symlinks, binary/oversized source entries and tracked files outside the list.
Ordinary Python caches, virtual environments and package metadata are excluded.

```sh
python tools/release.py --check
python tools/release.py --workspace "../morrowind-amiga-workspace"
```

The packer writes a candidate into external `incoming/`. A separate validation
pass checks archive paths, CRCs, hashes, sizes and source-byte equality before
promotion into `releases/`. The archive includes `docs/PACKAGE_MANIFEST.json`.
A SHA-256 sidecar is written beside it. Existing versioned releases are never
overwritten: bump `pyproject.toml` and update the changelog before the next release.
The generated package manifest is a receipt, excluded from Git and regenerated
when packaging a checkout extracted from a previous source archive.

Entries use fixed timestamps, sorted paths and fixed permissions for reproducible
packaging in the same toolchain. The source ZIP excludes `.git` and contains one
top-level `amiwind/` folder, ready to initialize as a Git repository.

Update `README.md`, `docs/PROJECT_STATE.md` and `docs/CHANGELOG.md` before a release.
Keep detailed format and design notes in their dedicated documents.

## Optional private development bundle

`tools/private_bundle.py` is a separate, explicit operation. It includes the
owner's configured original game folder, generated data and previews alongside
the validated source tree. It is not a public source release. For local use:

```sh
python tools/private_bundle.py --source-archive "../morrowind-amiga-workspace/releases/AmiWind-v0.0.16-public-source.zip" --workspace "../morrowind-amiga-workspace" --out "../morrowind-amiga-workspace/releases/AmiWind-v0.0.16-private-development.zip"
```

The source folder in that bundle is byte-identical to the public source package.
The original and converted data stay in a sibling workspace. The bundled setup
configuration omits machine-specific game paths; run `setup` after extraction.

For opening tests, install the optional `opening` dependencies (Pillow). The
historical checkpoint-005 host suite had 33 passing tests. Native checks are recorded in
CHECKPOINT_005_VALIDATION.md (earlier checks in OPENING_VALIDATION.md). `tools/package_opening.py` creates a compact private
opening bundle from `--source-archive`, `--build`, `--kickstart` and `--out`. It
validates the source archive, disk hashes and ROM checksum and uses a separate
candidate validation pass before writing a new, immutable ZIP. Supplying a ROM
to this explicit private operation includes it in that private package only.

## Preserve working features and alternatives

Do keep versioned checkpoints, original conversion recipes, previous font atlases,
and selectable implementation variants. Add experiments alongside the existing
path, compare them, and retain a documented fallback. This includes the readable
and retro fonts when adding an original-game-derived font, and 3D hands when
adding sprite hands. Store every derived commercial asset outside public source.

Do not destructively overwrite/remove a feature, asset recipe or alternative
merely to try an optimization or visual change. Keep this rule beyond the current
prototype. A deliberate future retirement needs an explicit migration decision,
not accidental replacement. Record what was actually tested and preserve failures.

Current acceptance at checkpoint-017:97 host tests passed with the actual native
source tree provided through AMIWIND_RUNTIME_SOURCE, plus the documented FS-UAE
checks. Earlier counts above belong to older checkpoints and are historical.

## Historical repository-consolidation checks

The complete native source is now included in engine/aga. Run the host suite with
`PYTHONPATH=src:tools python3 -m unittest discover -s tests -v` after installing
the documented dependencies. 113 tests passed locally. The ignored out/ directory
is never a source-release input. See CI_DRY_RUN.md for public CI and native test
compilation, BUILD_DEPENDENCIES.md for reference versions, and WINDOWS_BUILD.md
for Windows installation-path handling. Existing historical checkpoint evidence
is preserved; it is not replaced by the new test counts.

For current validation and first publication, see RELEASE-v0.0.16.md and
FIRST_RELEASE.md. The older private development bundle above is not the
required private playable package.
