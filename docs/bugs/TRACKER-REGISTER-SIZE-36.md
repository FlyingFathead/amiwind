# TRACKER-REGISTER-SIZE-36: The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | docs/bugs/bugs.json; tools/bug_register.py rotation; tests/test_bug_tracker.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev5 (last seen) |
| Severity | medium: Tooling: the register would hit the release preflight limit if left; no game impact |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine e74c9d2 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (register tooling) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 11 October 2026

Open. The same size problem as [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md) (the 1 MiB limit and the 75 %
warning came from it), now PERSISTING there with this report; this entry tracks the second archive. The warning
threshold for `bugs.json` is 85 % for now (temporary, coordinator decision on 11 October 2026); the
hard 1 MiB limit is unchanged. Planned right after the v0.0.36 release.

## Symptom

`tests/test_bug_tracker.py` (`test_tracker_files_fit_the_release_size_limits`) failed a gate. `bugs.json` was 789,008
bytes, over the 75 % warning line of its 1 MiB text limit (786,432 bytes). The integration head itself was at 784,191
bytes, 2.2 KB below the line.

## Evidence

The rotation rule, as it stands, frees almost nothing:

| Rotation rule | Bugs moved | Bytes freed |
| --- | ---: | ---: |
| fixed or closed, found in v0.0.33 or earlier (today) | already moved | 0 |
| found in v0.0.34 or earlier | 1 | 1,732 |
| found in v0.0.35 or earlier | 2 | 2,652 |
| Total today | | under 3 KB |

## Where

- `docs/bugs/bugs.json`
- `tools/bug_register.py` (`ARCHIVE`, `ARCHIVE_UP_TO`, rotation in `render`)
- `tests/test_bug_tracker.py`

## How it happened

v0.0.36 added many bugs with full facts, build records, platform fields and persisting report lines. The one frozen
archive takes only fixed or closed bugs found in v0.0.33 or earlier.

## Why it was not caught

The 75 % warning did its job: it caught the growth before the hard limit. No rotation step was planned for the
v0.0.36 line.

## Reproduction

Always, once the register passes 786,432 bytes.

## Repair

Planned:
- Add a second archive, `docs/bugs/archive/bugs-v0.0.34-v0.0.35.json`: fixed bugs first found in v0.0.34 and v0.0.35,
  moved by the same rotation tool.
- Update the tests and `tools/release-files.json`.
- Return the `bugs.json` warning threshold to 75 %.

## Verification

Not yet.

## Prevention

Plan an archive rotation at each release, before the register reaches the warning line.

## RC2 size recurrence and lossless representation, 13 October 2026

The exact RC2 full-suite snapshot stops after 402 tests because the live register is 896,776 bytes, above the existing 85% warning line (891,289.6 bytes) of its unchanged 1 MiB hard limit. Preserve that failed snapshot and receipt.

The current rotation rule already moved all eligible fixed/closed, non-persisting issues first found through v0.0.33. Only one additional fixed/non-persisting v0.0.34–v0.0.35 record is currently eligible for the planned second archive; moving it cannot solve this growth without changing the status or history of open issues. No open/persisting record is archived and the existing archive remains byte-identical.

Instead, the canonical live writer emits one complete issue object per line in the same JSON array. Only indentation/nesting whitespace changes: every field, value, array/issue order and report history round-trips unchanged. Readable status remains in the generated register and reports. Add a real save/load Unicode and nested-history regression, retain the size guard and hard limit unchanged, and require exact focused tracker/export/link checks. The archive remains on its existing format and rotation rule; future legitimate rotations remain separate work. This is a tooling source candidate, not game/maintainer acceptance.

## Focused validation, 13 October 2026

The isolated corrected snapshot passes 56 tracker/export tests with zero failures, errors or skips, including the actual size guard and save/load history regression. Its independently read-back source ZIP contains all 2,871 allowlisted files and the exact compact register bytes. Existing archive bytes remain unchanged. The earlier full-suite failure is retained; this focused result is not a full-suite, game build, native or maintainer acceptance claim. Final integrated source pin and its gates remain required.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-END-USER-LAUNCHERS-36](BUILD-END-USER-LAUNCHERS-36.md): Requested: the builder's simple mode writes a Python launcher, an FS-UAE config and a WinUAE config for the end user, matching the build
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- [CHIMPORT-DOOR-MARKER-AUDIT-36](CHIMPORT-DOOR-MARKER-AUDIT-36.md): The CHIMport door audit counted marker DOOR records (PrisonMarker) as missing door links: 6 cells failed door_links, Seyda Neen among them
- [CHIMPORT-STATUS-STALE-41](CHIMPORT-STATUS-STALE-41.md): The CHIM regions preflight refuses cells on old CHIMport audits without saying how old they are or how to measure them again
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-CELL-COUNTS-44](DOCS-CELL-COUNTS-44.md): Cell counts in the docs and tracker are stated without saying what they count
- [DOCS-CHANGELOG-STALE-39](DOCS-CHANGELOG-STALE-39.md): Maintained changelog stops at v0.0.35 while current development reaches v0.0.39-rc1
- [DOCS-CHIM-PROGRESS-STALE-38](DOCS-CHIM-PROGRESS-STALE-38.md): Main README CHIM progress map still shows the v0.0.36 snapshot
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
- [DOCS-RC1-PREFLIGHT-39](DOCS-RC1-PREFLIGHT-39.md): RC1 documentation changes omit export and generated-document requirements
- [DOCS-RELEASE-EVIDENCE-SCOPE-39](DOCS-RELEASE-EVIDENCE-SCOPE-39.md): Release notes conflate earlier image evidence and open bug identities
- [DOCS-ROADMAP-IMPLEMENTATION-39](DOCS-ROADMAP-IMPLEMENTATION-39.md): Roadmap retains obsolete implementation and coverage claims
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [PUBLIC-REFERENCE-SCREENSHOT-40](PUBLIC-REFERENCE-SCREENSHOT-40.md): Original-game reference screenshot included in the public source list
- [RELEASE-WORKING-VERSION-ISOLATION-39](RELEASE-WORKING-VERSION-ISOLATION-39.md): Publishing an earlier release reads the next development version record
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
- [TRACKER-AREA-CELLS-RUN-WIDE-42](TRACKER-AREA-CELLS-RUN-WIDE-42.md): The CHIM tracker gives every area of a build all of the build's cells: Balmora holds 811 cells, so an area or shipped-towns plan selector takes most of the island
- [TRACKER-CHIM-COUNT-STALE-44](TRACKER-CHIM-COUNT-STALE-44.md): The CHIM progress tracker still reports 1,193 of 1,436 cells after a build with every exterior cell: it counts audits over both islands, not what the build put on CHIM
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- [TRACKER-FIXED-LEFT-OPEN-36](TRACKER-FIXED-LEFT-OPEN-36.md): Fixed work whose bug entry stayed open (LAVA-NOT-IMPLEMENTED-33)
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-OCEAN-COUNTED-DONE-36](TRACKER-OCEAN-COUNTED-DONE-36.md): The tracker counts the 867 open-ocean cells as done, although the engine does not place the ocean chunk yet
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
