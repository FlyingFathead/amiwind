# TRACKER-CHIM-COUNT-STALE-44: The tracker counts audits, not what the ingested build put on CHIM

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | tracker ingest and status (tools/cell_progress.py), docs/chim/CELL_TRACKER.md, Toolkit map |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | high: the public tracker contradicts the release: every exterior cell is on CHIM since v0.0.43 |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5-try6_793d7c14 |
| From commit | source 793d7c1, engine 793d7c1, CHIM world 793d7c1 |
| CHIM engine version | CHIM 0.2.1, engine 793d7c1, world format 0.7 |
| Platform or emulator | build |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 19 October 2026](#status-19-october-2026)
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

## Status: 19 October 2026

Open. Repaired in source on the v0.0.44-tracker line (tools/cell_progress.py, tools/cell_progress_md.py, the Toolkit
world map), with tests; not shipped at the time of writing. Reported by the maintainer the same day.

## Symptom

After the v0.0.44-dev1 build was ingested, the tracker still printed "CHIM cells: 1193 / 1436 (83.08%)", the same
figure as before, although that build carries every exterior cell of Vvardenfell on CHIM. Only the page timestamp
changed, so the tracker looked stale.

## Where

`tools/cell_progress.py ingest` and `status` (the printed headline), the generated page docs/chim/CELL_TRACKER.md and
the CHIM line of the Toolkit world map.

## How it happened

The ingest did read the build: its digest of the v0.0.44-dev1 CHIM world lists 1,409 cells its frames own (1,348
region cells, of them 1,132 land, 197 seabed and 19 open-ocean cells, plus 61 cells inside the Balmora, Seyda Neen and
Vivec town frames). The printed line was a different measure: cells whose audits passed, divided by the land cells of
every island. Three things kept it at 1,193 of 1,436:

- the 144 land cells of Solstheim were in the denominator, although no build covers that island yet;
- 99 seabed cells with a LAND record were measured as empty sea by an earlier CHIMport run; that result sets the cell
  to "not converted, empty sea", so the build carrying the cell did not count;
- the 98 seabed cells whose LAND record has no heights and the 19 open-ocean cells the build carries are not land, so the line
  could never show them.

The figure had stood at 1,193 since v0.0.43-dev1, the first build with every Vvardenfell land cell, so new builds did
not move it. Nothing in the tracker said, per build, how many cells that build put on CHIM; per cell it kept the last
source that measured the cell, often a CHIMport result rather than the build.

## Why it was not caught

The tests checked the audit buckets and the per-island "done" figures (Vvardenfell already showed 1,390 of 1,390
done), not a per-build count. The printed line had no island and no build in it, so it read like "on CHIM".

## Reproduction

Always: ingest any build that carries seabed or ocean cells, with a Solstheim census, and read the printed line.

## Repair

The ingest now records, per cell, the newest build whose CHIM world owns it (`on_chim_build`) and every such build
(`on_chim_builds`), apart from the audit bucket. The headline gains `on_chim` (the newest ingested build) and
`on_chim_builds` (every ingested build, newest first): cells on CHIM, land and sea, and per island land cells on CHIM
of that island's land cells. A sea cell a build carries is given an island like the other sea cells. The printed
lines, the page and the Toolkit world map show this first; the audit figure stays, labelled "audit progress, all
islands". The older inputs (CHIMport results, audit files, the legacy progress table) are read as before.

## Verification

The real ingest of the v0.0.44-dev1 world (tracker commit of this repair) prints: on CHIM 1,409 cells, Vvardenfell
land 1,292 of 1,292 (100 %) plus 117 sea cells, Solstheim 0 of 144. 1,292 is every Vvardenfell cell with a LAND
record that has terrain heights (1,132 region land cells, 61 town-frame cells, 99 empty land cells under the sea);
117 = 98 seabed cells whose LAND record has no heights and 19 open-ocean cells (corrected 19 October 2026,
[DOCS-CELL-COUNTS-44](DOCS-CELL-COUNTS-44.md); every count: [what we count](../chim/CELL_TRACKER.md#what-we-count)). Earlier builds read 1,253 (v0.0.43-dev2), 1,215 (v0.0.43-dev1) and
1,171 (v0.0.42) land cells. New tests in tests/test_cell_progress.py (`OnChimTests`): a synthetic build with 25 CHIM
cells counts 25 (24 land, 1 sea; the second island is not mixed in), a cell an older CHIMport run called empty sea
still counts when the build carries it, and the page shows the build figure.

## Prevention

The tracker's "on CHIM" figure is computed from the ingested build's world, never from audit buckets, and is tested
with a synthetic build. Every ingest prints it first, so a build that adds cells moves the first line.

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
- EVIDENCE-STAMPS-TYPED-53 (no report page): Evidence script headers carried hand-typed times instead of copies of the stamp tool
- GATE-NUMBER-RACE-53 (no report page): Two workers started gate 4074 at the same moment: the gate scripts number-is-free check is not atomic
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- PLAYTEST-KNOWN-ISSUES-STALE-54 (no report page): The v0.0.54 playtest package's KNOWN-ISSUES list was made from the register of the build commit, older than the release's register
- PREFLIGHT-DISK-FIGURE-53 (no report page): The release preflight does not check the shipped disk figure, so the final commit failed its gate on it (gate 4078)
- PREFLIGHT-PERSISTING-PARSE-53 (no report page): The release preflight counted only persisting bugs whose line ended in NOT SCHEDULED, so lapsed deferrals printed 0 bugs and half a list
- [PUBLIC-REFERENCE-SCREENSHOT-40](PUBLIC-REFERENCE-SCREENSHOT-40.md): Original-game reference screenshot included in the public source list
- [REGISTER-ADD-NO-RELEASE-ROW-48](REGISTER-ADD-NO-RELEASE-ROW-48.md): bug_register.py add does not list a new report page in tools/release-files.json or write its contents list: the v0.0.48 final gate failed on both
- REGISTER-DEFERRAL-EXPIRES-53 (no report page): A maintainer deferral naming a release (deferred to v0.0.52) still counted as a reason inside that release, so deferrals never expired
- REGISTER-REGRESSION-HANDLER-52 (no report page): Requested: a bug that comes back after it was fixed or closed must be found and reopened as a regression, never registered again as new
- [RELEASE-WORKING-VERSION-ISOLATION-39](RELEASE-WORKING-VERSION-ISOLATION-39.md): Publishing an earlier release reads the next development version record
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [ROOM-RESIDENTS-NOT-CACHED-48](ROOM-RESIDENTS-NOT-CACHED-48.md): The room stages bake every resident again on every run: 26 s of a 39 s rerun with every room unit reused
- SESSION-AW-VIEW-IN-SOLID-54 (no report page): The session tooling's aw_view puts the camera outside the room or inside a wall without a warning
- SMOKE-START-ENTER-MENU-52 (no report page): An engine smoke script started with START enter can stay in the main menu: its Return skipped the intro movie instead
- [TEST-CHIMPORT-POOL-COPY-MODE-48](TEST-CHIMPORT-POOL-COPY-MODE-48.md): test_chimport_pool's copy-mode reuse test fails in the gate container: the units are computed again
- TEST-TOOLKIT-LINE-TIED-VERSION-49 (no report page): The Toolkit fold test tied the Toolkit line (Last updated with AmiWind vX) to VERSION: the v0.0.50-dev1 bump failed gate 3840 although the Toolkit had not changed
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-LEGEND-STATES-UNCLEAR-48](TOOLKIT-LEGEND-STATES-UNCLEAR-48.md): The CHIM Progress Tracker legend is confusing: 15 status buttons, half of them always 0, and open ocean labelled not in the game for cells that are
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
- TOOLKIT-MONITOR-FOLLOW-NOT-DEFAULT-49 (no report page): The Toolkit Monitor did not follow the newest running build on a load or a reload: follow latest started off and the page link pinned the old run
- TOOLKIT-MONITOR-NO-MEMORY-55 (no report page): Requested: the Toolkit build monitor shows the build's memory: RAM used and available, a memory curve beside the cores, the peak
- TOOLKIT-PAINT-SEA-CELLS-48 (no report page): Paint and the rectangle select on the World map skip sea cells, so their properties cannot be copied
- TOOLKIT-RELOAD-WORLD-55 (no report page): A reload of the Toolkit always opened the World tab instead of the tab that was open
- TOOLKIT-RESULTS-NO-OPEN-55 (no report page): Requested: a build in the monitor's Recent builds and gates list opens that run with one click
- [TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48](TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48.md): The World map status dot says stale for finished ingested data
- TOOLKIT-TIMELINE-CORES-TOP-48 (no report page): Toolkit Monitor stage timeline: the top of the cores line ran into its label, so the peaks could not be seen
- [TRACKER-AREA-CELLS-RUN-WIDE-42](TRACKER-AREA-CELLS-RUN-WIDE-42.md): The CHIM tracker gives every area of a build all of the build's cells: Balmora holds 811 cells, so an area or shipped-towns plan selector takes most of the island
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- TRACKER-CHIM-PAGE-REPORT-LINKS-55 (no report page): The generated CHIM Engine tracker page links its report pages as bugs/bugs/<ID>.md: 45 links name no file
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
