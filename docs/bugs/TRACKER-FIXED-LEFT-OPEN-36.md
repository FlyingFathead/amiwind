# TRACKER-FIXED-LEFT-OPEN-36: Fixed work whose bug entry stayed open (LAVA-NOT-IMPLEMENTED-33)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | docs/bugs/bugs.json register entries of work merged on other branches |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.36-dev5 (last seen) |
| Severity | low: a shipped feature read as missing in the register and was nearly scheduled again |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source e423498, engine e423498, CHIM world e423498 |
| CHIM engine version | CHIM 0.1.0, engine e423498, world format 0.5 |
| Build note | register review |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 11 October 2026](#status-11-october-2026)
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

## Status: 11 October 2026

Fixed for this entry: LAVA-NOT-IMPLEMENTED-33 is now recorded as fixed in v0.0.35. The check that would catch the next case is
still to be written.

## Symptom

[LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md) still read "open: liquid conversion, damage and tint in progress" on
11 October 2026, although the liquid lava (Quake liquid, damage, red tint, sound, CHIM glow) was merged into the v0.0.35 line
(7cb28f4, from 20335c6) and is in the v0.0.35 release notes ("Lava burns"). A plan for the next work started from the open
entry and nearly scheduled the shipped feature again.

## Where

docs/bugs/bugs.json: the register entry of a bug whose repair was merged on another branch.

## How it happened

The repair branch registered and fixed the work in its own commits; the merge into the release line did not carry a register
change that closed the entry, and nobody compared the release notes with the open register entries.

## Why it was not caught

The register tests check that entries are well formed and linked, not that an open entry's feature is absent from shipped
release notes.

## Reproduction

Read the register entry and the v0.0.35 release notes side by side.

## Repair

The entry is closed with its repair commits and release.

## Verification

The register shows LAVA-NOT-IMPLEMENTED-33 fixed in v0.0.35.

## Prevention

Proposed: the release flow lists every open register entry whose ID appears in the previous release notes' "What's new" or
"Fixed" sections, for a person to confirm before the freeze.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- [ACTOR-MODEL-ERROR-UNNAMED-48](ACTOR-MODEL-ERROR-UNNAMED-48.md): The actor model decoder's stops name neither the model nor the refused field
- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- [AW-CHIMPORT-ONE-NEGATIVE-CELL-68](AW-CHIMPORT-ONE-NEGATIVE-CELL-68.md): A CHIM import request for one cell whose coordinate starts with a minus sign is refused: the converter reads the cell as an option
- [AW-CHIMPORT-REGION-NO-PALETTE-66](AW-CHIMPORT-REGION-NO-PALETTE-66.md): aw chimport-region passes a palette, qbsp and SDK the builder image does not hold: every cell fails in seconds
- [AW-CHIMPORT-REGION-PASSED-ALL-FAILED-66](AW-CHIMPORT-REGION-PASSED-ALL-FAILED-66.md): aw chimport-region reports passed when every cell of the run failed
- [AW-CHIMPORT-REGION-POOL-COPY-67](AW-CHIMPORT-REGION-POOL-COPY-67.md): aw chimport-region copies the units it reuses from the shared pool instead of linking them
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-END-USER-LAUNCHERS-36](BUILD-END-USER-LAUNCHERS-36.md): Requested: the builder's simple mode writes a Python launcher, an FS-UAE config and a WinUAE config for the end user, matching the build
- [BUILD-FAILURE-NO-DETAILS-66](BUILD-FAILURE-NO-DETAILS-66.md): Requested: a failed build shows its failure details: the monitor showed only the percentage done and the word failed, and the failed stage's error line came without its traceback
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-PY-AT-TEXT-LIMIT-49 (no report page): tools/build.py stands at 99.6 % of the 256 KiB release text limit: a 1.2 KB builder change failed the gate preflight
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-RESIDENT-BUDGET-CAPS-DROPPED-64](BUILD-RESIDENT-BUDGET-CAPS-DROPPED-64.md): Raising the resident registry budget dropped the command cap block and its note from the budget file
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- [BUILD-STALE-BSP-CONFIG-48](BUILD-STALE-BSP-CONFIG-48.md): Docs and config still described things that ship as .chim as .bsp maps
- BUILD-SUMMARY-INTERIOR-COUNTS-48 (no report page): The build summary and the inclusion ledger do not say how many interiors a build includes
- [CELL-PROGRESS-SOURCE-UNREADABLE-SILENT-67](CELL-PROGRESS-SOURCE-UNREADABLE-SILENT-67.md): The CHIM Progress Tracker's result and ingest steps write the tracker data without any remembered input they cannot read, with no error: a step run without one of those inputs drops the mapping quality, the limits, the place names, the build history or the rooms in the game
- [CENSUS-DISTRICT-CONTAINERS-AS-ROOMS-67](CENSUS-DISTRICT-CONTAINERS-AS-ROOMS-67.md): The container count still reads a Mournhold district as a room: its 171 containers would be counted as having no row once their rows are keyed outdoors
- [CHIMPORT-CLI-MWAD-SHADOW-66](CHIMPORT-CLI-MWAD-SHADOW-66.md): chimport.py run stops on a fresh run folder: stair_walk puts tools/ first, so tools/mwad.py loads in place of the package mwad
- [CHIMPORT-DOOR-MARKER-AUDIT-36](CHIMPORT-DOOR-MARKER-AUDIT-36.md): The CHIMport door audit counted marker DOOR records (PrisonMarker) as missing door links: 6 cells failed door_links, Seyda Neen among them
- [CHIMPORT-LAYER-CELL-EMPTY-67](CHIMPORT-LAYER-CELL-EMPTY-67.md): CHIM import counts a cell only an expansion holds as empty: it is built as flat ground with nothing placed
- [CHIMPORT-STATUS-STALE-41](CHIMPORT-STATUS-STALE-41.md): The CHIM regions preflight refuses cells on old CHIMport audits without saying how old they are or how to measure them again
- [DEBUG-TP-ROOM-ENTRANCE-50](DEBUG-TP-ROOM-ENTRANCE-50.md): dbg tp <room map> finds a batch room s entrance only in Balmora s door list: rooms entered from Seyda Neen, Vivec or a region frame say No converted entrance
- DELIVER-OUTPUT-NAMES-LATE-59 (no report page): deliver_dev.py checks that its output names are free only after the smoke and hops
- [DELIVER-RESUME-OWN-OUTPUT-66](DELIVER-RESUME-OWN-OUTPUT-66.md): A resumed delivery stopped on the package outputs of its own failed try
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOC-TOC-BLANK-LINE-AT-EOF-67](DOC-TOC-BLANK-LINE-AT-EOF-67.md): The contents list added to a long report page that has only generated sections ends the file with a blank line, which the whitespace check of every commit refuses
- [DOCS-BUGS-FOLDER-OVER-1000-64](DOCS-BUGS-FOLDER-OVER-1000-64.md): The bug report folder holds more than 1,000 files, so the GitHub folder view leaves some out
- [DOCS-CELL-COUNTS-44](DOCS-CELL-COUNTS-44.md): Cell counts in the docs and tracker are stated without saying what they count
- [DOCS-CHANGELOG-STALE-39](DOCS-CHANGELOG-STALE-39.md): Maintained changelog stops at v0.0.35 while current development reaches v0.0.39-rc1
- [DOCS-CHIM-PROGRESS-STALE-38](DOCS-CHIM-PROGRESS-STALE-38.md): Main README CHIM progress map still shows the v0.0.36 snapshot
- [DOCS-CHIMPORT-EXPANSIONS-67](DOCS-CHIMPORT-EXPANSIONS-67.md): The CHIMport page described the base game only: how the expansions' cells are read, checked and crossed was missing
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
- [DOCS-PROGRESS-TRACKER-STALE-64](DOCS-PROGRESS-TRACKER-STALE-64.md): The CHIM Progress Tracker page carried the newest version in its last-updated line while its current state stopped at v0.0.48 and listed its builds oldest first
- [DOCS-RC1-PREFLIGHT-39](DOCS-RC1-PREFLIGHT-39.md): RC1 documentation changes omit export and generated-document requirements
- [DOCS-RELEASE-EVIDENCE-SCOPE-39](DOCS-RELEASE-EVIDENCE-SCOPE-39.md): Release notes conflate earlier image evidence and open bug identities
- [DOCS-ROADMAP-IMPLEMENTATION-39](DOCS-ROADMAP-IMPLEMENTATION-39.md): Roadmap retains obsolete implementation and coverage claims
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DOOR-GRAPH-CELL-TEST-AS-TELEPORT-67](DOOR-GRAPH-CELL-TEST-AS-TELEPORT-67.md): The door graph marks two Tribunal cells as reached by script because a script tests the player's cell name, although nothing moves the player there
- [DOOR-GRAPH-MWAD-SHADOW-48](DOOR-GRAPH-MWAD-SHADOW-48.md): tools/door_graph.py fails to start when PYTHONPATH names both src and tools
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- EVIDENCE-STAMPS-TYPED-53 (no report page): Evidence script headers carried hand-typed times instead of copies of the stamp tool
- [EXPANSION-COUNTS-MISS-FRAME-STORES-68](EXPANSION-COUNTS-MISS-FRAME-STORES-68.md): The build's record of the expansions' actors and the script tracker leave out what the frame stores of the image hold: actors there count as not placed, Solstheim's built cells as missing, its attached scripts as outside the image, and scripts that only declare dialogue variables as not attached
- GATE-NUMBER-RACE-53 (no report page): Two workers started gate 4074 at the same moment: the gate scripts number-is-free check is not atomic
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- IMAGE-HDF-COPY-SPARSE-JDRIVE-59 (no report page): Copying a padded HDF from the build volume onto a mounted folder fails with Permission denied
- [MESH-EXPORT-FULL-67](MESH-EXPORT-FULL-67.md): tools/mesh_export.py writes no texture names in its material file and no texture coordinates
- MONITOR-WARNINGS-ROW-54 (no report page): Requested: the Toolkit build monitor gathers every warning of a build in one yellow row, Warnings: N with a view of the lines
- [MWSCRIPT-TRACKER-MAIN-INERT-63](MWSCRIPT-TRACKER-MAIN-INERT-63.md): The script tracker called Main named by nothing, although the game always starts it and AmiWind carries its work
- [PACKAGE-PORTABILITY-28](PACKAGE-PORTABILITY-28.md): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PERF-DB-CHIMPORT-NO-WALL-67](PERF-DB-CHIMPORT-NO-WALL-67.md): The performance database records the master builder's CHIM import runs without their times, so it cannot answer how long such a run takes
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [PLAYTEST-KNOWN-ISSUES-STALE-54](PLAYTEST-KNOWN-ISSUES-STALE-54.md): The v0.0.54 playtest package's KNOWN-ISSUES list was made from the register of the build commit, older than the release's register
- PREFLIGHT-DISK-FIGURE-53 (no report page): The release preflight does not check the shipped disk figure, so the final commit failed its gate on it (gate 4078)
- PREFLIGHT-PERSISTING-PARSE-53 (no report page): The release preflight counted only persisting bugs whose line ended in NOT SCHEDULED, so lapsed deferrals printed 0 bugs and half a list
- [PUBLIC-REFERENCE-SCREENSHOT-40](PUBLIC-REFERENCE-SCREENSHOT-40.md): Original-game reference screenshot included in the public source list
- [REGISTER-ADD-NO-RELEASE-ROW-48](REGISTER-ADD-NO-RELEASE-ROW-48.md): bug_register.py add does not list a new report page in tools/release-files.json or write its contents list: the v0.0.48 final gate failed on both
- [REGISTER-CONCURRENT-WRITE-LOST-67](REGISTER-CONCURRENT-WRITE-LOST-67.md): Two register writes at the same time in one checkout lose an entry: the later writer saves the register from a copy read before the earlier writer's change
- REGISTER-DEFERRAL-EXPIRES-53 (no report page): A maintainer deferral naming a release (deferred to v0.0.52) still counted as a reason inside that release, so deferrals never expired
- [REGISTER-REGRESSION-HANDLER-52](REGISTER-REGRESSION-HANDLER-52.md): Requested: a bug that comes back after it was fixed or closed must be found and reopened as a regression, never registered again as new
- [REGISTER-REPORT-PERSISTS-STALE-64](REGISTER-REPORT-PERSISTS-STALE-64.md): bug_register.py report records a new sighting but leaves the versions the bug persists in unchanged
- [REGISTER-STEP-RENDERS-ALL-PAGES-68](REGISTER-STEP-RENDERS-ALL-PAGES-68.md): Every single closure step or field change in the bug register rewrites all of its generated pages, so a batch of steps for a handful of entries takes half an hour
- [RELEASE-WORKING-VERSION-ISOLATION-39](RELEASE-WORKING-VERSION-ISOLATION-39.md): Publishing an earlier release reads the next development version record
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [ROOM-RESIDENTS-NOT-CACHED-48](ROOM-RESIDENTS-NOT-CACHED-48.md): The room stages bake every resident again on every run: 26 s of a 39 s rerun with every room unit reused
- [ROUTE-UPLOAD-AFTER-PUSH-67](ROUTE-UPLOAD-AFTER-PUSH-67.md): The release route's upload to the download site is refused when the release was published on the code host first
- [SESSION-AW-VIEW-IN-SOLID-54](SESSION-AW-VIEW-IN-SOLID-54.md): The session tooling's aw_view puts the camera outside the room or inside a wall without a warning
- [SMOKE-START-ENTER-MENU-52](SMOKE-START-ENTER-MENU-52.md): An engine smoke script started with START enter can stay in the main menu: its Return skipped the intro movie instead
- [STUCK-WATCH-NIGHT-BY-HOUR-ONLY-68](STUCK-WATCH-NIGHT-BY-HOUR-ONLY-68.md): The stall watcher judged night only by the clock, so an alert the session had not yet acknowledged still reached the maintainer after night mode was switched on in the evening
- [TEST-CHIMPORT-POOL-COPY-MODE-48](TEST-CHIMPORT-POOL-COPY-MODE-48.md): test_chimport_pool's copy-mode reuse test fails in the gate container: the units are computed again
- TEST-TOOLKIT-LINE-TIED-VERSION-49 (no report page): The Toolkit fold test tied the Toolkit line (Last updated with AmiWind vX) to VERSION: the v0.0.50-dev1 bump failed gate 3840 although the Toolkit had not changed
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- TOOLKIT-COPY-ONE-CELL-57 (no report page): The world map's copy-cells button is disabled when only one cell is clicked
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-ELIGIBLE-RELEASE-STALE-64](TOOLKIT-ELIGIBLE-RELEASE-STALE-64.md): The CHIM Progress Tracker headline says eligible for a release six versions old
- [TOOLKIT-HEADLINE-EXPANSIONS-NOT-STARTED-67](TOOLKIT-HEADLINE-EXPANSIONS-NOT-STARTED-67.md): The Toolkit headline calls Mournhold and Solstheim not started while the view switch above the map shows 89 of 96 Mournhold rooms and 99 of 101 Solstheim rooms in the game
- [TOOLKIT-HEADLINE-ROWS-INLINE-64](TOOLKIT-HEADLINE-ROWS-INLINE-64.md): The CHIM Progress Tracker headline shows its rows for each land and the build as one run-on line in Firefox
- [TOOLKIT-HEADLINE-ROWS-OVERFLOW-64](TOOLKIT-HEADLINE-ROWS-OVERFLOW-64.md): The CHIM Progress Tracker headline rows run off the right edge and its summary cannot be folded
- [TOOLKIT-HELP-BUTTON-INERT-64](TOOLKIT-HELP-BUTTON-INERT-64.md): The round question mark in the Toolkit header does nothing when clicked
- [TOOLKIT-INSPECTOR-EXPORT-VERSION-64](TOOLKIT-INSPECTOR-EXPORT-VERSION-64.md): The Polycount inspector JSON copy names program version 0.0.38 on every later release
- [TOOLKIT-LEGEND-STATES-UNCLEAR-48](TOOLKIT-LEGEND-STATES-UNCLEAR-48.md): The CHIM Progress Tracker legend is confusing: 15 status buttons, half of them always 0, and open ocean labelled not in the game for cells that are
- [TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67](TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67.md): On a CHIM cell in the game, the Toolkit offers no map: the World tab says the Local view is 2D only, the Local tab asks for its terrain file (island-cells.json) by hand, its map list is empty and its Show in 3D button does nothing
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
- TOOLKIT-MONITOR-FOLLOW-NOT-DEFAULT-49 (no report page): The Toolkit Monitor did not follow the newest running build on a load or a reload: follow latest started off and the page link pinned the old run
- TOOLKIT-MONITOR-NO-MEMORY-55 (no report page): Requested: the Toolkit build monitor shows the build's memory: RAM used and available, a memory curve beside the cores, the peak
- [TOOLKIT-PAINT-SEA-CELLS-48](TOOLKIT-PAINT-SEA-CELLS-48.md): Paint and the rectangle select on the World map skip sea cells, so their properties cannot be copied
- [TOOLKIT-PROGRESS-FILE-REFETCHED-64](TOOLKIT-PROGRESS-FILE-REFETCHED-64.md): The World Map fetches and parses the whole 109 MB tracker file every 10 seconds
- TOOLKIT-RELOAD-WORLD-55 (no report page): A reload of the Toolkit always opened the World tab instead of the tab that was open
- TOOLKIT-RESULTS-NO-OPEN-55 (no report page): Requested: a build in the monitor's Recent builds and gates list opens that run with one click
- TOOLKIT-SERVE-SOCKET-BUFFER-57 (no report page): The Toolkit server stops for good on one transient socket error while heavy builds run
- [TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48](TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48.md): The World map status dot says stale for finished ingested data
- [TOOLKIT-STATUS-STALE-BY-CLOCK-64](TOOLKIT-STATUS-STALE-BY-CLOCK-64.md): The World Map status strip says stale for data that covers the newest delivered build
- TOOLKIT-TIMELINE-CORES-TOP-48 (no report page): Toolkit Monitor stage timeline: the top of the cores line ran into its label, so the peaks could not be seen
- [TOOLKIT-VERSION-CHECK-NO-GIT-64](TOOLKIT-VERSION-CHECK-NO-GIT-64.md): The Toolkit version check passes in a source tree without git history, so the gate lets a stale Toolkit version line through and the dev delivery stops after the build
- [TOOLKIT-WORLD-MAP-FRAME-LOOP-64](TOOLKIT-WORLD-MAP-FRAME-LOOP-64.md): The World Map vanished in Firefox after the frame was sized to its own content
- [TOOLKIT-WORLD-MAP-NESTED-SCROLL-64](TOOLKIT-WORLD-MAP-NESTED-SCROLL-64.md): The World Map scrolls as separate boxes: the headline stays while the map frame scrolls, and the wheel over the map never scrolls the page
- [TRACK-FIXED-STEPS-WHOLE-HOME-68](TRACK-FIXED-STEPS-WHOLE-HOME-68.md): Recording a fix of one register entry through its planning item marks every other entry of that item as fixed by the same commit
- [TRACK-FIXED-UMBRELLA-STEPS-ALL-67](TRACK-FIXED-UMBRELLA-STEPS-ALL-67.md): Marking one fault fixed through the tracker intake marked every fault of its plan item fixed when that item groups many
- [TRACK-UPDATE-MOVED-ITEM-FIRST-68](TRACK-UPDATE-MOVED-ITEM-FIRST-68.md): Updating a work item whose id also exists as a moved copy in an older version file wrote the note into the old moved copy instead of the live item
- [TRACKER-AREA-CELLS-RUN-WIDE-42](TRACKER-AREA-CELLS-RUN-WIDE-42.md): The CHIM tracker gives every area of a build all of the build's cells: Balmora holds 811 cells, so an area or shipped-towns plan selector takes most of the island
- [TRACKER-CHIM-COUNT-STALE-44](TRACKER-CHIM-COUNT-STALE-44.md): The CHIM progress tracker still reports 1,193 of 1,436 cells after a build with every exterior cell: it counts audits over both islands, not what the build put on CHIM
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- TRACKER-CHIM-PAGE-REPORT-LINKS-55 (no report page): The generated CHIM Engine tracker page links its report pages as bugs/bugs/<ID>.md: 45 links name no file
- TRACKER-CHIM-PAGE-SIZE-48 (no report page): The generated CHIM tracker page reached 75 % of its 256 KiB release text limit
- [TRACKER-DISTRICTS-COUNTED-TWICE-67](TRACKER-DISTRICTS-COUNTED-TWICE-67.md): The progress tracker counts Mournhold's five districts twice: as their open-terrain cells in the game and again as rooms not started
- [TRACKER-ENTRIES-WITHOUT-PAGES-67](TRACKER-ENTRIES-WITHOUT-PAGES-67.md): Half of the live bug entries have no report page: the category lists and links name them without a page to open (643 of 1307, 517 of them open, 207 from v0.0.66 and v0.0.67)
- [TRACKER-GUARD-SHIPPED-STEP-68](TRACKER-GUARD-SHIPPED-STEP-68.md): The tracker write guard counts the delivery chain's step that records what a build shipped as a write outside the intake
- [TRACKER-IN-GAME-SEA-LABELLED-OCEAN-48](TRACKER-IN-GAME-SEA-LABELLED-OCEAN-48.md): The cell tracker calls cells that are in the game ocean: cell -15,-8 stands alone in the sea on the World map
- [TRACKER-INCLUSION-NOT-RUN-SINCE-44-48](TRACKER-INCLUSION-NOT-RUN-SINCE-44-48.md): The inclusion ledger was not refreshed after v0.0.44-dev1 and the Toolkit headline still names v0.0.41
- [TRACKER-INTERIORS-IN-GAME-COUNT-64](TRACKER-INTERIORS-IN-GAME-COUNT-64.md): The tracker data counts 59 of 1,123 Vvardenfell interior rooms as in the game on CHIM rooms, while the builds since v0.0.48 convert almost all of them
- [TRACKER-INTERIORS-NOT-SHOWN-48](TRACKER-INTERIORS-NOT-SHOWN-48.md): The CHIM Progress Tracker does not show the interiors: no room list, no counts per island and state, and 16 rooms with no entrance area left out of every batch
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-OCEAN-COUNTED-DONE-36](TRACKER-OCEAN-COUNTED-DONE-36.md): The tracker counts the 867 open-ocean cells as done, although the engine does not place the ocean chunk yet
- [TRACKER-OPEN-ENTRIES-STALE-41](TRACKER-OPEN-ENTRIES-STALE-41.md): Register entries stayed open after their fixes shipped: 738 of 842 entries open before the audit of 16 October 2026
- [TRACKER-PRESENTED-CELLS-UNKNOWN-67](TRACKER-PRESENTED-CELLS-UNKNOWN-67.md): The CHIM tracker knew none of Mournhold's presented cells: with no LAND record and no census row they were not in its data, and their conversion results were ignored
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-ROOM-MAPS-NOT-READY-67](TRACKER-ROOM-MAPS-NOT-READY-67.md): The progress tracker counts the two opening rooms (the prison ship and the Census and Excise Office) as not ready although both are in the game
- TRACKER-SEA-CELL-LAND-GREEN-57 (no report page): The world map paints in-game sea cells land-green in its build view: a lone tile at -15,-8 looks like leftover land
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- [TRACKER-STAMP-BLOCKS-WORKER-GATES-68](TRACKER-STAMP-BLOCKS-WORKER-GATES-68.md): After the main line takes a new development version, every other branch's pre-check is refused until that version is published
- [TRACKERS-COUNT-MOURNHOLD-OUT-67](TRACKERS-COUNT-MOURNHOLD-OUT-67.md): The script tracker and the CHIM progress tracker still count Mournhold as not in the game: 187 Tribunal scripts are listed as add-on only and Mournhold's exterior shows 0
- [WIN-02](WIN-02.md): Cancelled Windows stage leaves child workers alive

Related bugs in other categories:

- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked

<!-- END GENERATED CATEGORY -->
