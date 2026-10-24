# TRACKER-REGISTER-SIZE-33: The bug register outgrew the release text-file size limit

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 6 times; something has to be done

- Reported with v0.0.33 at 2026-10-09 (time not recorded): first: the register outgrew the 256 KiB release text limit (gate preflight)
- Reported with v0.0.36-dev5 at 2026-10-11 14:55 +0300: bugs.json 789,008 of 1 MiB passed the 75 % warning again; follow-up TRACKER-REGISTER-SIZE-36 (second archive)
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Moved from TRACKER-REGISTER-SIZE-36 (duplicate): RC2 suite caught the 896,776 B size warning; lossless canonical JSON plus 56 focused checks; fresh pin required.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Journal reached196510B,98B below its warning. Rotate133 older entries; preserve newer/CHIM entries, history, links and all limits. Unreleased documentation follow-up.
- Reported with v0.0.43-dev2 at 2026-10-18 15:28 +0300: Journal reached 196,648 B, 40 B past its warning. Rotated 130 entries of 11-16 October into the v0.0.37-v0.0.41 archive.
- Reported with v0.0.46-dev at 2026-10-20 09:12 +0300: The 2026-10-20 audit took the one archive to 232,832 B, 89 % of 256 KiB. Split into four found-in ranges and rotation to v0.0.35: archives 57-86 KB (22-33 %), bugs.json 688,666 B (66 %).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:preflight |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | release preflight (tools/release.py), docs/bugs/bugs.json and docs/BUGS.md |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Blocks the release preflight once the register passes 256 KiB; no effect on the game. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Journal headroom follow-up, 14 October 2026](#journal-headroom-follow-up-14-october-2026)
- [Focused journal validation, 14 October 2026](#focused-journal-validation-14-october-2026)
- [Journal rotation, 18 October 2026](#journal-rotation-18-october-2026)
- [Archive split by version range, 20 October 2026](#archive-split-by-version-range-20-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

_Last updated with AmiWind v0.0.43-dev2 (18 October 2026)._

## Status: 8 October 2026

Open. Repaired in source on v0.0.33-bug-fields (a named 1 MiB limit for the two register files),
not shipped at the time of writing. Found by the local gate's release preflight.

## Symptom

After the bug facts (reported by, first noticed, where, reproduction, duplicate, persistence,
severity, family, related bugs) were added to every register entry, the release preflight stopped
with "Unexpected binary or oversized source content: docs/bugs/bugs.json". The file had grown from
160,093 to 320,196 bytes; the generated `docs/BUGS.md` was 172,673 bytes.

## Where

`tools/release.py` (source content check: every text file at most 262,144 bytes), which the release
preflight and the source ZIP use. Affected: `docs/bugs/bugs.json`, and soon `docs/BUGS.md`. Other
text files are far below the limit.

## How it happened

The register is one JSON file that gains an entry with every bug, and the generated register table
grows with it. The 256 KiB limit was set for hand-written source files, before the register existed.
Without the facts the register would still have reached the limit at about 570 bugs.

## Why it was not caught

No check watched how close the register files were to the limit; the preflight only fails once a
file is over it.

## Reproduction

Always: run the release preflight on a tree whose `docs/bugs/bugs.json` is larger than 262,144 bytes.

## Repair

`tools/release.py` keeps the 256 KiB limit (`TEXT_LIMIT`) for every text file and names a larger
limit, 1 MiB, for exactly two files in `LARGE_TEXT`: `docs/bugs/bugs.json` and `docs/BUGS.md`.
Gate 256 on v0.0.33-bug-fields (9847b57): preflight, suite, host parity and engine all pass.

Alternative, not taken: split the register into one JSON file per version series (for example
`docs/bugs/bugs-32.json`), each under the common limit; the register tool and tests would read all of
them. Reconsider it if the register approaches 1 MiB.

## Verification

Gate 256 passes with the limit in place. Not yet in a release preflight of a shipped version.

## Prevention

`tests/test_bug_tracker.py` (`test_tracker_files_fit_the_release_size_limits`) fails when any
tracker file (register, journal, report pages) passes 75 % of its limit in `tools/release.py`, so
the next step is taken before the preflight fails.

## Journal headroom follow-up, 14 October 2026

The v0.0.40-dev2 source journal reached 196,510 bytes, leaving 98 bytes below
the existing 75% warning of 196,608 bytes. Continued short entries alone
would soon fail the tracker gate. The hard text limit and warning are unchanged.

Move 133 selected entries dated 9-11 October into the
[v0.0.35-v0.0.36 archive](../journals/BUG_JOURNAL-v0.0.35-v0.0.36.md).
Preserve every entry body and its order, changing only relative links for
the new directory. Keep newer entries and the latest ten CHIM summary
entries in the current journal. Existing frozen files remain unchanged.
Register IDs, issue states, repair history and acceptance fields do not change.

Validation must compare every moved entry with its original, verify prior
archive hashes and unchanged CHIM summary links, check the tracker and
documentation links, and confirm the archive is allowlisted and exported.
This is unreleased documentation maintenance, not a game repair.

## Focused journal validation, 14 October 2026

The rotated source passes all 36 tracker tests, the 806-issue register check,
1,051-document contents and anchor checks, and the 2,905-file source preflight.
All prior frozen archive hashes match and the generated CHIM tracker is
byte-identical. Every moved entry was checked against its original with only
relative-link relocation permitted. No text limit or warning was increased.
Full-suite, target and native results for the earlier game build do not
validate this later source. Shipment remains separate.

## Journal rotation, 18 October 2026

The v0.0.43-dev2 source journal reached 196,648 bytes, 40 bytes past the
75 % warning of 196,608 bytes, and the tracker test failed. The 130 entries
dated 11-16 October 2026 (the v0.0.37 to v0.0.41 releases) moved into the
[v0.0.37-v0.0.41 archive](../journals/BUG_JOURNAL-v0.0.37-v0.0.41.md), as in
the rotation of 14 October: entry bodies and order unchanged, only relative
links rewritten for the new directory, and links between the current journal
and the archive repointed to where each entry now lives. The current journal
is now about 28 KB (11 % of the limit) and keeps the entries from 17 October
on, which hold the latest ten CHIM summary entries. The hard text limit and
the warning are unchanged.

## Archive split by version range, 20 October 2026

Reported again with v0.0.46-dev. The register audit of 20 October 2026 closed
47 bugs; the fixed and closed ones first found in v0.0.33 or earlier rotated
into the single frozen archive `archive/bugs-v0.0.29-v0.0.33.json`, which
reached 232,832 bytes, 89 % of its 256 KiB limit, and the tracker size test
failed (gate 3323).

Repair, in `tools/bug_register.py` (`ARCHIVES`): the archive is now one file
per range of the version a bug was first found in, and the rotation reaches
v0.0.35 (the second archive planned on
[TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md)). `load()` reads
`bugs.json` and then every archive in range order; `render` writes each
rotated bug to the first range that covers it and removes the old single
file once its bugs are written; `check` reports a retired file that is still
there as stale. No record changed: the 930 records are identical before and
after, each ID once.

| File | Before | After | Share of its limit |
| --- | ---: | ---: | ---: |
| `bugs.json` | 746,571 | 689,209 | 66 % of 1 MiB |
| `archive/bugs-v0.0.29-v0.0.33.json` | 232,832 | removed | |
| `archive/bugs-to-v0.0.31.json` | | 75,110 | 29 % of 256 KiB |
| `archive/bugs-v0.0.32.json` | | 72,082 | 27 % |
| `archive/bugs-v0.0.33.json` | | 85,646 | 33 % |
| `archive/bugs-v0.0.34-v0.0.35.json` | | 57,908 | 22 % |
| `docs/BUGS.md` | 548,570 | 548,861 | 52 % of 1 MiB |

Every tracker file warns at 75 % again (the temporary 85 % for `bugs.json`
and the archive is gone); the hard limits are unchanged. If every open bug
first found in v0.0.33 or earlier were closed, the largest archive would
still stay under the warning line. A new test
(`test_rotation_into_several_archives_keeps_every_bug_once`) checks the
split, the load order, the removal of the retired file and that a second
save changes nothing. Not shipped.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- [ACTOR-MODEL-ERROR-UNNAMED-48](ACTOR-MODEL-ERROR-UNNAMED-48.md): The actor model decoder's stops name neither the model nor the refused field
- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-END-USER-LAUNCHERS-36](BUILD-END-USER-LAUNCHERS-36.md): Requested: the builder's simple mode writes a Python launcher, an FS-UAE config and a WinUAE config for the end user, matching the build
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-PY-AT-TEXT-LIMIT-49 (no report page): tools/build.py stands at 99.6 % of the 256 KiB release text limit: a 1.2 KB builder change failed the gate preflight
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- BUILD-STALE-BSP-CONFIG-48 (no report page): Docs and config still described things that ship as .chim as .bsp maps
- BUILD-SUMMARY-INTERIOR-COUNTS-48 (no report page): The build summary and the inclusion ledger do not say how many interiors a build includes
- [CHIMPORT-DOOR-MARKER-AUDIT-36](CHIMPORT-DOOR-MARKER-AUDIT-36.md): The CHIMport door audit counted marker DOOR records (PrisonMarker) as missing door links: 6 cells failed door_links, Seyda Neen among them
- [CHIMPORT-STATUS-STALE-41](CHIMPORT-STATUS-STALE-41.md): The CHIM regions preflight refuses cells on old CHIMport audits without saying how old they are or how to measure them again
- [DEBUG-TP-ROOM-ENTRANCE-50](DEBUG-TP-ROOM-ENTRANCE-50.md): dbg tp <room map> finds a batch room s entrance only in Balmora s door list: rooms entered from Seyda Neen, Vivec or a region frame say No converted entrance
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-CELL-COUNTS-44](DOCS-CELL-COUNTS-44.md): Cell counts in the docs and tracker are stated without saying what they count
- [DOCS-CHANGELOG-STALE-39](DOCS-CHANGELOG-STALE-39.md): Maintained changelog stops at v0.0.35 while current development reaches v0.0.39-rc1
- [DOCS-CHIM-PROGRESS-STALE-38](DOCS-CHIM-PROGRESS-STALE-38.md): Main README CHIM progress map still shows the v0.0.36 snapshot
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
- [DOCS-RC1-PREFLIGHT-39](DOCS-RC1-PREFLIGHT-39.md): RC1 documentation changes omit export and generated-document requirements
- [DOCS-RELEASE-EVIDENCE-SCOPE-39](DOCS-RELEASE-EVIDENCE-SCOPE-39.md): Release notes conflate earlier image evidence and open bug identities
- [DOCS-ROADMAP-IMPLEMENTATION-39](DOCS-ROADMAP-IMPLEMENTATION-39.md): Roadmap retains obsolete implementation and coverage claims
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DOOR-GRAPH-MWAD-SHADOW-48](DOOR-GRAPH-MWAD-SHADOW-48.md): tools/door_graph.py fails to start when PYTHONPATH names both src and tools
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [PUBLIC-REFERENCE-SCREENSHOT-40](PUBLIC-REFERENCE-SCREENSHOT-40.md): Original-game reference screenshot included in the public source list
- [REGISTER-ADD-NO-RELEASE-ROW-48](REGISTER-ADD-NO-RELEASE-ROW-48.md): bug_register.py add does not list a new report page in tools/release-files.json or write its contents list: the v0.0.48 final gate failed on both
- [RELEASE-WORKING-VERSION-ISOLATION-39](RELEASE-WORKING-VERSION-ISOLATION-39.md): Publishing an earlier release reads the next development version record
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [ROOM-RESIDENTS-NOT-CACHED-48](ROOM-RESIDENTS-NOT-CACHED-48.md): The room stages bake every resident again on every run: 26 s of a 39 s rerun with every room unit reused
- [TEST-CHIMPORT-POOL-COPY-MODE-48](TEST-CHIMPORT-POOL-COPY-MODE-48.md): test_chimport_pool's copy-mode reuse test fails in the gate container: the units are computed again
- TEST-TOOLKIT-LINE-TIED-VERSION-49 (no report page): The Toolkit fold test tied the Toolkit line (Last updated with AmiWind vX) to VERSION: the v0.0.50-dev1 bump failed gate 3840 although the Toolkit had not changed
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-LEGEND-STATES-UNCLEAR-48](TOOLKIT-LEGEND-STATES-UNCLEAR-48.md): The CHIM Progress Tracker legend is confusing: 15 status buttons, half of them always 0, and open ocean labelled not in the game for cells that are
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
- TOOLKIT-MONITOR-FOLLOW-NOT-DEFAULT-49 (no report page): The Toolkit Monitor did not follow the newest running build on a load or a reload: follow latest started off and the page link pinned the old run
- TOOLKIT-PAINT-SEA-CELLS-48 (no report page): Paint and the rectangle select on the World map skip sea cells, so their properties cannot be copied
- [TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48](TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48.md): The World map status dot says stale for finished ingested data
- TOOLKIT-TIMELINE-CORES-TOP-48 (no report page): Toolkit Monitor stage timeline: the top of the cores line ran into its label, so the peaks could not be seen
- [TRACKER-AREA-CELLS-RUN-WIDE-42](TRACKER-AREA-CELLS-RUN-WIDE-42.md): The CHIM tracker gives every area of a build all of the build's cells: Balmora holds 811 cells, so an area or shipped-towns plan selector takes most of the island
- [TRACKER-CHIM-COUNT-STALE-44](TRACKER-CHIM-COUNT-STALE-44.md): The CHIM progress tracker still reports 1,193 of 1,436 cells after a build with every exterior cell: it counts audits over both islands, not what the build put on CHIM
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- TRACKER-CHIM-PAGE-SIZE-48 (no report page): The generated CHIM tracker page reached 75 % of its 256 KiB release text limit
- [TRACKER-FIXED-LEFT-OPEN-36](TRACKER-FIXED-LEFT-OPEN-36.md): Fixed work whose bug entry stayed open (LAVA-NOT-IMPLEMENTED-33)
- [TRACKER-IN-GAME-SEA-LABELLED-OCEAN-48](TRACKER-IN-GAME-SEA-LABELLED-OCEAN-48.md): The cell tracker calls cells that are in the game ocean: cell -15,-8 stands alone in the sea on the World map
- [TRACKER-INCLUSION-NOT-RUN-SINCE-44-48](TRACKER-INCLUSION-NOT-RUN-SINCE-44-48.md): The inclusion ledger was not refreshed after v0.0.44-dev1 and the Toolkit headline still names v0.0.41
- [TRACKER-INTERIORS-NOT-SHOWN-48](TRACKER-INTERIORS-NOT-SHOWN-48.md): The CHIM Progress Tracker does not show the interiors: no room list, no counts per island and state, and 16 rooms with no entrance area left out of every batch
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-OCEAN-COUNTED-DONE-36](TRACKER-OCEAN-COUNTED-DONE-36.md): The tracker counts the 867 open-ocean cells as done, although the engine does not place the ocean chunk yet
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

Related bugs in other categories:

- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text

<!-- END GENERATED CATEGORY -->
