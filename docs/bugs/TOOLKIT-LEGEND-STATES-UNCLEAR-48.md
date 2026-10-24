# TOOLKIT-LEGEND-STATES-UNCLEAR-48: the CHIM Progress Tracker legend is confusing (15 status buttons, open ocean labelled not in the game)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 22 October 2026, in v0.0.48-dev2 |
| Where | Toolkit World map legend and headline (amiwind-toolkit), tracker headline (tools/cell_progress.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | medium: the tracker reads wrong at a glance: settled sea looks like unfinished work and the headline names an old version; nothing is wrong in the game |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source c8a9cc8, engine c8a9cc8, CHIM world c8a9cc8 |
| CHIM engine version | CHIM 0.2.1, engine c8a9cc8, world format 0.7 |
| Platform or emulator | not in game (seen on the Toolkit World map, not in the game) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Status: 22 October 2026](#status-22-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 22 October 2026

Fixed for v0.0.48 on the branch v0.0.48-legend (commit 987de42a). Reported by the maintainer on 22 October 2026.

## Symptom

The CHIM Progress Tracker shows 15 status buttons in one row. Seven of them are always 0 (cell complete, maintainer-approved,
playtested, failing, not converted, nothing measured, hull policy pending). The biggest button after the land states reads
"open ocean, not counted as done (shared ocean chunk made, not yet placed)" for 769 cells, which is wrong on both counts: 19 of
those cells are in the shipped v0.0.47 world, and the other 750 are squares with no cell record in the game data that the edge
current keeps the player away from. The headline also said "eligible for v0.0.41" while v0.0.48 was in development. The
maintainer likes the button style; the meaning had to change so it stays sensible from now on.

## Where

The Toolkit World map legend and headline chips (amiwind-toolkit/chim-head.js, chim-legend.js, world-map.html) and the
tracker headline (tools/cell_progress.py).

## How it happened

The legend listed every audit bucket of the tracker, whatever its count, and the buckets describe how far a conversion got,
not where a cell stands today. The open ocean bucket came from an early ocean test run and was never set against the builds.
The eligible release came from a release plan that was no longer updated, with a fixed constant behind it.

## Why it was not caught

No check looked at the legend as a whole, and no check compared a cell's label with the newest ingested build or with the
game data's own cell records.

## Reproduction

Open the World map with the tracker data of the v0.0.47 release run and look at the chips above the map.

## Repair

The tracker sorts every cell into three groups against the newest ingested build: **In the game** (the land states and every
sea cell the build holds, "sea, in the game"), **Not in the game yet** (Solstheim named as such, problems, the work left) and
**Beyond the world's edge: settled** (no cell record in the game data, on no build; drawn faint grey with the hover text "No
cell exists here in the original game data. AmiWind's edge current turns the player back before this point, so there is
nothing to build."). Settled counts toward "accounted for", never toward the cells in the game. A state with no cells waits
in a "More states" fold-out and comes back by itself. The groups are worked out in tools/cell_progress.py (chim.group,
chim.state, headline groups and states), so the page, the generated cell tracker and `cell_progress.py status` agree. The
eligible release is the plan release, or the version in development when the plan is older.

On the v0.0.47 release data: in the game 1,409, not in the game yet 153 (all Solstheim), settled 755, accounted for 2,164 of
2,317.

## Verification

tests/test_legend_groups.py (classification, ingest, the Markdown tracker, status, the page and headline in Node) and the
updated tracker tests pass in the test container. The page was run headless against the real tracker data (DOM stubs, not a
rendered browser).

## Prevention

The legend is generated from the group lists, zero-count states fold away by themselves, and a test fails when a version
number is written into the tracker code.

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
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
