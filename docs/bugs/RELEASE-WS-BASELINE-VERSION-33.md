# RELEASE-WS-BASELINE-VERSION-33: Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:preflight |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | release preflight whitespace check (tools/release.py check_source_whitespace) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Blocks the preflight of every new version and branch until a hand-made file exists; no effect on the game. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Fixed in source on v0.0.33-ws-baseline, not shipped at the time of writing. Found by the local
gate's release preflight, again and again.

## Symptom

Each time `VERSION` changed (0.0.32, 0.0.33-dev1, and a side branch with its own version string),
the release preflight stopped with "Source whitespace check failed", listing "trailing whitespace"
and "blank line at EOF" in files nobody had touched: original id Software and AmiQuake engine
sources, QuakeC, an upstream patch and a licence text. It passed again only after someone made a
`docs/PATCH-v<VERSION>.json` by hand.

## Where

`tools/release.py`, `check_source_whitespace`, used by `tools/release.py --check`, candidate creation
and candidate validation (and so by the local gate's preflight and the source ZIP).

## How it happened

Unchanged inherited files may keep their historical formatting; the check recognised them by the
`base_files` hashes of `docs/PATCH-v<VERSION>.json`, the manifest of the incremental update for the
version being worked on. That file only exists once a release is being prepared. For any other
`VERSION` the baseline was empty, so every inherited file was checked strictly: 77 files of the
published v0.0.32 fail a strict scan (72 under `engine/aga/` and `docs/aga/`, plus five of our own
files, four of them Python files with extra blank lines at the end).

## Why it was not caught

The tests only covered a fixture whose patch file matched its `VERSION`; no test changed the version
without adding a patch file. Each failure was repaired by making the file, not by asking why the
whitespace baseline depended on the version string.

## Reproduction

Always: set `VERSION` to a value without a matching `docs/PATCH-v<VERSION>.json` and run
`python3 tools/release.py --check`.

## Repair

- The baseline is `docs/WHITESPACE-BASELINE.json`: the published release it was taken from
  (`release`, `commit`) and the SHA-256 of every inherited text file of that release that has
  whitespace defects. It does not depend on `VERSION`.
- Only files under `engine/aga/` and `docs/aga/` (inherited code, upstream patches and licence
  texts) can be exempt, and only while byte-identical. A file we edit is checked in full, including
  its old lines. Our own files are never exempt, whatever the baseline lists.
- `python3 tools/release.py --whitespace-baseline v<VERSION>` writes the file from the tag of a
  published release and refuses a commit that the tag `v<VERSION>` does not point to. Run it after a
  release is published; a newer release can only shrink the list, so a stale file is never wrong,
  just longer than needed.
- When the file is missing, the check fails on the first inherited defect and prints the command to
  run.
- The four project files with blank lines at the end (`src/mwad/audit.py`, `src/mwad/preview.py`,
  `src/mwad/verify.py`, `tests/test_barrier_conversion.py`) were cleaned in the same change.
- `docs/PATCH-v*.json` stay as they are: the incremental update and its apply/verify tooling still
  use them. They are no longer read by the whitespace check.

## Verification

Baseline written from the published v0.0.32 tag (72 inherited files). `tools/release.py --check`
passes on v0.0.33-ws-baseline; a copy with every `docs/PATCH-v*.json` removed and `VERSION` set to
an unreleased value passes the whitespace check. Full gate before the commit.

## Prevention

`tests/test_release.py`:

- `test_new_version_needs_no_patch_file_for_unchanged_inherited_files`: three versions, no patch
  file, inspection and a candidate ZIP pass.
- `test_new_whitespace_in_our_own_file_still_fails` and
  `test_baseline_never_exempts_project_authored_files`: our own files stay strict.
- `test_edited_inherited_file_is_checked_in_full` and
  `test_engine_file_exemption_and_full_check_after_edit`: an edited inherited file reports its old
  defects too.
- `test_patch_file_is_not_a_whitespace_baseline_and_missing_baseline_says_what_to_run`.
- `test_repository_baseline_is_keyed_to_a_published_release`: the repository's file names a final
  release, lists only inherited paths, and (with git and the tag present) equals a fresh write from
  that tag.
- `test_baseline_record_requires_the_published_tag_and_lists_only_inherited_defects` and
  `test_baseline_writer_writes_lf_json_and_reports_the_release` (no git needed, so they run in the
  offline gate image too).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
