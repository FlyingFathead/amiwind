# DOCS-RELEASE-EVIDENCE-SCOPE-39: Release notes conflate earlier image evidence and open bug identities

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 13 October 2026, in v0.0.39-dev1 |
| Where | Release notes for v0.0.38 and v0.0.39-dev1 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.39-dev1 (last seen) |
| Severity | low: Release readers could mistake earlier image evidence for current validation and a fixed bug for an open issue. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 7565ada |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Documentation review; no new game or emulator failure observed.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Shipment-status recurrence, 14 October 2026](#shipment-status-recurrence-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

14 October 2026: Final v0.0.39 source packaging authorized from delivered RC2. README and release notes distinguish RC2 checks from final-source validation. No individual issue acceptance, new cell coverage or final artifact shipment is inferred.

## Symptom

The v0.0.38 notes described full-image checks without identifying that they
belonged to the preceding image, although a corrected compact image was still
pending. The v0.0.39-dev1 notes linked a fixed opponent-visibility bug as the
example for unrelated open third-person equipment and animation issues.

## Where

`docs/releases/notes/RELEASE-v0.0.38.md` and `docs/releases/notes/RELEASE-v0.0.39-dev1.md`.

## How it happened

An earlier validation checklist survived the packaging correction. A broad
third-person summary reused an issue link without checking its current state
and precise symptom in the canonical register.

## Why it was not caught

Syntax, link and source-export checks cannot prove that prose refers to the
right image or that an issue is an appropriate example of the stated symptom.

## Reproduction

Compare the notes' final-image claims with their pending compact-image gates.
Compare the dev1 known-issue link with the fixed register entry for
CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36 and the distinct open player torch,
readied-pose and jump reports.

## Repair

Name the preceding image explicitly and retain the corrected image's pending
gates. Explain the release around lava, Tel Uvirith and actual CHIM coverage.
Link the separate open animation reports. Keep published source, candidate
repairs, image observations and delivery distinct. No engine change or bug
reopening follows from this editorial correction.

## Verification

The first editorial candidate also changed the required known-issues heading.
The release validator rejected it; the exact `Known in this build` heading and
ID-labelled bullets were restored before packaging. Preserve that parser
contract when editing prose.

The wording was compared against the canonical register and the existing
coverage and build receipts. Source checks for the corrected documentation and
future package validation are separate gates; no new runtime result is claimed.

## Prevention

For each release claim, identify the source/image and the check it passed.
Read open-issue identities from the register, and keep historical evidence
labelled when an image is replaced. Do not infer native acceptance from a
planned map count or a source-only correction.

## Shipment-status recurrence, 14 October 2026

The main README and progress guide retained held/preparation wording after
final v0.0.39 delivery finalized at 07:15:35 UTC. The obsolete lines survived
because link, syntax and prior scoped scene checks did not compare current
release prose against the completed shipment record.

The documentation correction names that finalization and labels preceding
RC1/RC2 scene diagnostics as historical. Renewed
[third-person punching](PLAYER-PUNCH-THIRDPERSON-39.md),
[movement with fists drawn](PLAYER-READY-MOVEMENT-39.md),
[blocking](COMBAT-BLOCKING-36.md) and
[swimming](WATER-GAMEPLAY-PARITY-38.md) remain open.
Shipment, independent fresh-download verification and maintainer gameplay
acceptance are distinct. No coverage count or runtime source changes.

The correction is prepared for integration; this report's historical pending
statements describe their dated checkpoints. Current status remains in the
canonical register. Prevention: reconcile README, progress guide, release
notes and issue status against the exact finalization receipt before each
handoff, then check generated records and affected links.

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
- [DOCS-ROADMAP-IMPLEMENTATION-39](DOCS-ROADMAP-IMPLEMENTATION-39.md): Roadmap retains obsolete implementation and coverage claims
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DOOR-GRAPH-MWAD-SHADOW-48](DOOR-GRAPH-MWAD-SHADOW-48.md): tools/door_graph.py fails to start when PYTHONPATH names both src and tools
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- EVIDENCE-STAMPS-TYPED-53 (no report page): Evidence script headers carried hand-typed times instead of copies of the stamp tool
- GATE-NUMBER-RACE-53 (no report page): Two workers started gate 4074 at the same moment: the gate scripts number-is-free check is not atomic
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- MONITOR-WARNINGS-ROW-54 (no report page): Requested: the Toolkit build monitor gathers every warning of a build in one yellow row, Warnings: N with a view of the lines
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
- TOOLKIT-COPY-ONE-CELL-57 (no report page): The world map's copy-cells button is disabled when only one cell is clicked
- [TOOLKIT-CULL-DIAGNOSTICS-38](TOOLKIT-CULL-DIAGNOSTICS-38.md): Collision-only diagnostics disable terrain culling preview
- [TOOLKIT-LEGEND-STATES-UNCLEAR-48](TOOLKIT-LEGEND-STATES-UNCLEAR-48.md): The CHIM Progress Tracker legend is confusing: 15 status buttons, half of them always 0, and open ocean labelled not in the game for cells that are
- [TOOLKIT-MAP-SCALING-36](TOOLKIT-MAP-SCALING-36.md): The CHIM Progress Tracker map scales badly: a small box in the middle with inner scrollbars, controls far away, the island cropped
- [TOOLKIT-MONITOR-BLIND-PHASES-36](TOOLKIT-MONITOR-BLIND-PHASES-36.md): The Toolkit Monitor shows nothing during silent build phases: no activity, no phases, no time since the last log line
- TOOLKIT-MONITOR-FOLLOW-NOT-DEFAULT-49 (no report page): The Toolkit Monitor did not follow the newest running build on a load or a reload: follow latest started off and the page link pinned the old run
- TOOLKIT-MONITOR-NO-MEMORY-55 (no report page): Requested: the Toolkit build monitor shows the build's memory: RAM used and available, a memory curve beside the cores, the peak
- TOOLKIT-PAINT-SEA-CELLS-48 (no report page): Paint and the rectangle select on the World map skip sea cells, so their properties cannot be copied
- TOOLKIT-RELOAD-WORLD-55 (no report page): A reload of the Toolkit always opened the World tab instead of the tab that was open
- TOOLKIT-RESULTS-NO-OPEN-55 (no report page): Requested: a build in the monitor's Recent builds and gates list opens that run with one click
- TOOLKIT-SERVE-SOCKET-BUFFER-57 (no report page): The Toolkit server stops for good on one transient socket error while heavy builds run
- [TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48](TOOLKIT-STALE-DOT-FOR-INGESTED-DATA-48.md): The World map status dot says stale for finished ingested data
- TOOLKIT-TIMELINE-CORES-TOP-48 (no report page): Toolkit Monitor stage timeline: the top of the cores line ran into its label, so the peaks could not be seen
- [TRACKER-AREA-CELLS-RUN-WIDE-42](TRACKER-AREA-CELLS-RUN-WIDE-42.md): The CHIM tracker gives every area of a build all of the build's cells: Balmora holds 811 cells, so an area or shipped-towns plan selector takes most of the island
- [TRACKER-CHIM-COUNT-STALE-44](TRACKER-CHIM-COUNT-STALE-44.md): The CHIM progress tracker still reports 1,193 of 1,436 cells after a build with every exterior cell: it counts audits over both islands, not what the build put on CHIM
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
- TRACKER-SEA-CELL-LAND-GREEN-57 (no report page): The world map paints in-game sea cells land-green in its build view: a lone tile at -15,-8 looks like leftover land
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
