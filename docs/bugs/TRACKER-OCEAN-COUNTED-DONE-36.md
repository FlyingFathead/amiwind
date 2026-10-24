# TRACKER-OCEAN-COUNTED-DONE-36: The tracker counts the 867 open-ocean cells as done, although the engine does not place the ocean chunk yet

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | CHIM Progress Tracker headline, Done line, island totals, Toolkit and generated page |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36-dev5 |
| Severity | medium: the done figure overstated the conversion by the ocean cells; the maintainer reads it as game progress |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 6c29a23 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Status: 11 October 2026

Fixed in v0.0.36-dev5 (branch v0.0.36-tracker-plan). Reported by the maintainer (message of 09:53); verified in the browser on 11 October 2026 (about 10:16) by the project coordinator: open ocean is silver and the Done line reads 1,021 of 1,292.

## Symptom

The "Done: N of M" line, the island totals, the eligible figure and the release tables counted every open-ocean cell (a map cell without a LAND record that references the one shared ocean chunk) as done, in the same blue family as the sea around the coast. The figure read as game progress.

## Where

`tools/cell_progress.py` (headline, island headlines, the eligible set), `tools/cell_progress_md.py` (the generated page), `amiwind-toolkit/chim-legend.js`, `chim-head.js` and `world-map.html`.

## How it happened

The ocean chunk was made and stored, so the open-ocean status was counted like empty sea (done). The engine does not place the chunk until the open-world frames read it, so none of those cells is in the game yet.

## Why it was not caught

The cell tracker measured the conversion output, not what the engine uses; the release notes said the chunk is not placed yet, but nothing tied that statement to the count.

## Reproduction

Always: ingest any result file with open-ocean cells and read the Done line.

## Repair

Open ocean is drawn silver (a clear grey-blue that no status or plan colour uses), has its own legend row ("Open ocean: shared ocean chunk made, not yet placed in the game") with its count, and its own TOTALS row in the release plan table. It is no longer part of done, eligible, the island's cells and percent, or the compare ranks; the headline keeps the count (`ocean`, `map_cells`). When the engine places the chunk, the count moves back to done by one decision in one place (`DONE_SEA` in the ingester).

## Verification

Python tests for the headline, island totals, the eligible sets and the generated page; Node tests for the silver colour, its distinctness from the gold plan colours, the eligible preset and the totals row.

## Prevention

A bucket counts as done only when the engine uses its output; the definition table says so for every bucket.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- [ACTOR-MODEL-ERROR-UNNAMED-48](ACTOR-MODEL-ERROR-UNNAMED-48.md): The actor model decoder's stops name neither the model nor the refused field
- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-END-USER-LAUNCHERS-36](BUILD-END-USER-LAUNCHERS-36.md): Requested: the builder's simple mode writes a Python launcher, an FS-UAE config and a WinUAE config for the end user, matching the build
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- BUILD-STALE-BSP-CONFIG-48 (no report page): Docs and config still described things that ship as .chim as .bsp maps
- BUILD-SUMMARY-INTERIOR-COUNTS-48 (no report page): The build summary and the inclusion ledger do not say how many interiors a build includes
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
- [DOOR-GRAPH-MWAD-SHADOW-48](DOOR-GRAPH-MWAD-SHADOW-48.md): tools/door_graph.py fails to start when PYTHONPATH names both src and tools
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [PUBLIC-REFERENCE-SCREENSHOT-40](PUBLIC-REFERENCE-SCREENSHOT-40.md): Original-game reference screenshot included in the public source list
- [RELEASE-WORKING-VERSION-ISOLATION-39](RELEASE-WORKING-VERSION-ISOLATION-39.md): Publishing an earlier release reads the next development version record
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [ROOM-RESIDENTS-NOT-CACHED-48](ROOM-RESIDENTS-NOT-CACHED-48.md): The room stages bake every resident again on every run: 26 s of a 39 s rerun with every room unit reused
- [TEST-CHIMPORT-POOL-COPY-MODE-48](TEST-CHIMPORT-POOL-COPY-MODE-48.md): test_chimport_pool's copy-mode reuse test fails in the gate container: the units are computed again
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-LEGEND-STATES-UNCLEAR-48](TOOLKIT-LEGEND-STATES-UNCLEAR-48.md): The CHIM Progress Tracker legend is confusing: 15 status buttons, half of them always 0, and open ocean labelled not in the game for cells that are
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
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
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
