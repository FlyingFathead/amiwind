# TRACKER-REGISTER-SIZE-33: The bug register outgrew the release text-file size limit

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.33 at 2026-10-09 (time not recorded): first: the register outgrew the 256 KiB release text limit (gate preflight)
- Reported with v0.0.36-dev5 at 2026-10-11 14:55 +0300: bugs.json 789,008 of 1 MiB passed the 75 % warning again; follow-up TRACKER-REGISTER-SIZE-36 (second archive)
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Journal reached196510B,98B below its warning. Rotate133 older entries; preserve newer/CHIM entries, history, links and all limits. Unreleased documentation follow-up.

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

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
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
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

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
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- [TRACKER-FIXED-LEFT-OPEN-36](TRACKER-FIXED-LEFT-OPEN-36.md): Fixed work whose bug entry stayed open (LAVA-NOT-IMPLEMENTED-33)
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-OCEAN-COUNTED-DONE-36](TRACKER-OCEAN-COUNTED-DONE-36.md): The tracker counts the 867 open-ocean cells as done, although the engine does not place the ocean chunk yet
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

Related bugs in other categories:

- [RELEASE-PATCH-SIZE-33](RELEASE-PATCH-SIZE-33.md): The release preflight refuses the whitespace baseline of v0.0.33-dev1 as oversized text

<!-- END GENERATED CATEGORY -->
