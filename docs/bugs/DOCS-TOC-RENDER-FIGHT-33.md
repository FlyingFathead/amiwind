# DOCS-TOC-RENDER-FIGHT-33: The contents-list writer and the bug register renderer move each other's blocks on bug pages

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:doc-toc |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | tools/doc_toc.py contents placement vs tools/bug_register.py fact table on bug pages |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The full gate fails on one of two doc checks; no effect on the game or builds. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.33-dev, not shipped at the time of writing. Found when the contents-list
work (v0.0.33-doc-toc) and the bug fact fields (v0.0.33-bug-fields) were merged on v0.0.33-dev; each
branch was consistent on its own.

## Symptom

On a long bug page, `python tools/doc_toc.py write` put the contents list right under the title,
above the generated fact table; `python tools/bug_register.py render` then put the fact table back
right under the title, above the list; the next `doc_toc.py check` failed again. Eight pages
(BALMORA-TEMPLE-GEOMETRY-29, QC-AW-FLAME-SPAWN-32, VIVEC-ARENA-ACTORS-32 and five more) never
settled, so one of the two checks of the full gate always failed.

## Where

`tools/doc_toc.py` (`_insert_at`, where the list goes) and `tools/bug_register.py`
(`rendered_page`, which writes the fact table directly under the title).

## How it happened

The contents-list rule places the list after the title and its first intro paragraph; a generated
HTML comment block is not an intro, so the list went right after the title. The fact table rule
places the table right after the title. The two rules were written on separate branches.

## Why it was not caught

Neither branch had the other's generator, and the tests of each tool used only its own blocks.

## Reproduction

On v0.0.33-dev before the repair: `python tools/doc_toc.py write`, then
`python tools/bug_register.py render`, then `python tools/doc_toc.py check` (fails on the eight
pages).

## Repair

A generated block directly under the title counts as part of the title: the contents list goes
after it. `bug_register.py` is unchanged.

## Verification

`tests/test_doc_toc.py`: a page with a generated fact table under the title gets its list after
the table, and a bug page passed through `rendered_page`, then `doc_toc.render`, then
`rendered_page` again is unchanged. Both repository checks pass after write and render in either
order.

## Prevention

The two cross-tool tests above run in the full suite; any generator that writes a block under a
document title must keep the other generators' output a fixed point.

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
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
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
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
