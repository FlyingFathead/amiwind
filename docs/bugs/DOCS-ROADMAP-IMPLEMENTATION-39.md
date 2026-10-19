# DOCS-ROADMAP-IMPLEMENTATION-39: Roadmap retains obsolete implementation and coverage claims

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | docs/ROADMAP.md gameplay and exterior coverage; animation-kit reference |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | low: Readers could mistake implemented controls for missing work or a coverage plan for shipped content. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine d40fa70 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Documentation/source comparison; no new runtime failure.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

## Symptom

The roadmap calls the noclip-bob setting unimplemented even though it is in
published v0.0.38 source. It also groups the existing music console switch
with future settings work and says v0.0.38 will include every green map zone,
which was a plan rather than a package inclusion receipt.

## Where

`docs/ROADMAP.md`, gameplay and exterior coverage sections. The animation-kit
reference also needs to distinguish the new player-only jump candidate from
the established NPC profiles.

## How it happened

Older plans remained in prose after source implementation or a narrower
release selection. The roadmap was not reconciled with the source, canonical
issues and actual package evidence when the implementation advanced.

## Why it was not caught

Link, syntax and format checks do not establish whether a future-tense
statement still agrees with implementation or whether a coverage plan shipped.

## Reproduction

At published commit d40fa70b4787da09b8a6d5006f46ef6fb7e56c6f, compare the
roadmap's noclip entry with `view.c` and `config/debug-commands.txt`. Compare
the music entry with `aw_music.c` and ENGINE-MUSIC-NO-OFF-SWITCH-36. Compare
the old green-zone promise with the separately recorded release inclusion.

## Repair

Describe the existing noclip and console music controls accurately, retain
the unfinished music settings work, and mark the old coverage promise as a
historical target. Preserve the distinction between the CHIM world container
and the still-planned native CHIM frame-map header. Explain that player jump
code is a candidate, not completed NPC or equipment-animation coverage.
No engine or map content changes follow from this documentation correction.

## Verification

Compared published and current source and the canonical music report on
13 October 2026. Documentation correction prepared; delivery and documentation
gates remain separate. No new build, native acceptance or performance result.

## Prevention

When a feature advances, reconcile the active roadmap paragraph and feature
reference against exact source and release evidence. Keep historical targets
explicit and link current issue status to the canonical register. Do not
convert source presence, conversion progress or an earlier package into
acceptance of a later image.

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
- [TRACKER-REGISTER-SIZE-36](TRACKER-REGISTER-SIZE-36.md): The live register bugs.json reached 75 % of its 1 MiB release text limit; the size warning was raised to 85 % until a second archive rotation
- [TRACKER-RELEASE-HEADROOM-MISSING-42](TRACKER-RELEASE-HEADROOM-MISSING-42.md): The CHIM tracker keeps no memory headroom per cell from a full build, and older CHIMport results replace a newer full build's audits: every headroom figure dates from the v0.0.36-v0.0.40 builders
- [TRACKER-SEA-CELL-SET-36](TRACKER-SEA-CELL-SET-36.md): The CHIM tracker's island view leaves out 37 land cells that hold only terrain and sea; one is labelled Solstheim
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

Related bugs in other categories:

- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image

<!-- END GENERATED CATEGORY -->
