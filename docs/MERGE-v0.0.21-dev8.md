# Reconciled dev8 source record

Date: 29 September 2026. Target: v0.0.21-dev8 source prerelease.

## Exact inputs

Base: `amiwind-2026-09-29_025822.zip`, SHA-256
`a4a660e8cad92e554cbc45c07b42b935cf3aadc36ab6aac04ceeba688a0309c3`. This is the owner's dev7 working snapshot;
its uncommitted boot/launcher work is authoritative for this merge.

Paper changes: `AmiWind-v0.0.21-dev6-paper-002-public-source.zip`, with the
published dev5 tree as the three-way ancestor. The paper checkpoint's dev6
number did not replace the separate boot-work dev6/dev7 history. Dev8 combines
the branches without retagging either earlier release.

Only the paper checkpoint's changed code/config/tests were added to dev7.
LINUX_BUILD.md merged cleanly against the common dev5 ancestor. Current README,
version, changelog and release-state documents were reconciled explicitly. Both
sets of historical records remain. Existing dev6/dev7 emulator presets are
preserved; new dev8 presets use the same settings and new versioned image names.
The additional CPU-helper change guards an OSError from process_cpu_count().

## Preserved newer files

These files are byte-identical to the uploaded dev7 snapshot:

| File | SHA-256 |
| --- | --- |
| `engine/aga/boot/bootcheck.asm` | `4ab8332c37bc56b93aef8ef896aa08227f4bd298cdc8f3dcdabc916f3583dba0` |
| `tests/test_fs_uae_launcher.py` | `94f3174bc87af065c5e15822efa5a4db1f594bb29448e9dfb3d76798fb6d21f2` |
| `tests/test_project_version.py` | `bf3e305c86d285ff3938ddfe91fd89d11dfa70ec21133a2aab2e36e01053c922` |
| `tools/AmiWind-FS-UAE-launcher.py` | `db566c9e0605d50d6e2026babc074a8f80ec2f24f839340f6a6c2bf2dcc6d54b` |
| `tools/build_dry_run.py` | `8f040b1a722fe7eb29aa042e5846bc7b08c3147958b230129b49b26fd3b1f3f5` |
| `tools/project_version.py` | `381a0e64bda7af41aa91adbb7256e3df4ef02bef81ec0fb2cc11c01807df155a` |

The root VERSION changes generated version strings only when actually rebuilt.
No previously built binary/image was renamed to imply a dev8 rebuild.

## Validation boundary

The reconciled host suite ran 237 tests: 234 passed, two skipped and one errored.
The sole error is ModuleNotFoundError for fast_simplification in this sandbox;
the package is already declared by the project. The two skips concern absent
optional geometry dependencies. No test was weakened or given a dummy replacement.
The CPU-query error from the older run is fixed; all three CPU-job tests pass.
These counts are not a claim of a clean fully provisioned host run.

The supplied apply/release helper selects the owner's existing sibling
amiwind-tools/venv by default and requires the dependencies and full host suite
to pass before it edits the checkout or publishes. It does not silently install
packages, skip failing tests or overwrite conflicting newer local source.

The public allowlist gate passes. Full and incremental ZIPs are checked against
the source bytes and each other. Source-only diagnostics and compiled host C UI
tests are not a new Amiga build or emulator playtest. The source merge includes
neither an HDF nor the pending whole-pipeline parallelization implementation.

The approved font preview and earlier source-font measurements are historical
checkpoint evidence, retained in CHECKPOINT-v0.0.21-dev6-paper-002.md. The owner's
complete dev5 Steam build is also historical, not a new dev8 test.
