# DOCS-DEAD-ANCHORS-32: Seven documentation links point at headings that no longer exist

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32 |
| Where | seven #anchor links in five public docs (AGA_BUILD, DEBUG_OVERLAYS, HIDDEN_IN_DIRT and two more) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29, v0.0.30, v0.0.31, v0.0.32 (last seen) |
| Severity | low: Navigation only; the linked pages still open. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |
| Playtest version | v0.0.32 |
| From commit | source and engine 0f467e4 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on v0.0.33-doc-toc (ef3c33c), not shipped at the time of writing.

## Symptom

Seven links with a `#section` part led to the top of their target page because the section they
named had been renamed or removed. 295 other same-repository `#anchor` links resolved.

## Where

| Link in | Pointed at | Now points at |
| --- | --- | --- |
| AGA_BUILD.md | ROADMAP.md, "TODO soon: static asset gallery and cell-by-cell scenery" | "Follow-up: static asset gallery and remaining scenery" |
| HORSTATORS_MUSINGS_2026-09-29.md | ROADMAP.md, "Future: world-coordinate HUD (investigate first, not v0.0.24 work)" | "World-coordinate HUD" |
| DEBUG_OVERLAYS.md | TORCH.md, "Guard torches and the clock — implementation in progress" | "Guard torches and the clock — scoped native verification passed" |
| HIDDEN_IN_DIRT.md (2), TERRAIN_VISUAL_CULL.md (2) | DAY_NIGHT_AND_SKY.md, "Existing renderer background and sky enclosure geometry" | "Shared exterior background sky: implementation candidate" |

The old heading texts are reconstructed from the anchors. Text outside these link targets is
unchanged.

## How it happened

Headings were renamed as work progressed (a TODO became a follow-up, "in progress" became
"verification passed"), and one sky section was replaced by the shared exterior sky section.
Links elsewhere kept the old anchors. GitHub does not report a missing anchor: it opens the page
at the top.

## Why it was not caught

No check followed `#anchor` links. The bug tracker test checks anchors only in links from the bug
register.

## Reproduction

On a commit before ef3c33c, run `tools/doc_toc.py check` from ef3c33c: it prints the seven links
as `file:line: target: no heading or anchor with this name` and exits 1.

## Repair

The seven links point at the current sections (table above). `tools/doc_toc.py check` follows
every Markdown link with a `#fragment` (inline and reference links, link text wrapped over lines,
not code) from the public documents to a Markdown file in the repository, and fails when no
heading or `<a id/name>` anchor there has that name. Anchors follow GitHub's rules, the same ones
the contents lists use. Frozen history is not checked as a source: it keeps its links as written.

## Verification

`tools/doc_toc.py check` passes on 514 documents (about 1,700 anchor links, including the
generated contents lists). `tests/test_doc_toc.py`: `AnchorLinkTests` (a dead anchor, a renamed
heading and a reference link are reported; live, encoded, explicit-anchor, code, image, web,
missing-file, non-Markdown and frozen-source links are not) and
`RepositoryTests.test_every_anchor_link_resolves`, which failed on the seven links before the
repair. Full gate on the branch.

## Prevention

The repository test fails as soon as a heading rename leaves a link behind; the message names
the file and line.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- [BUILD-SCRATCH-DISK-GROWTH-32](BUILD-SCRATCH-DISK-GROWTH-32.md): Build scratch volumes grow the container disk image on the system drive
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-TOC-RENDER-FIGHT-33](DOCS-TOC-RENDER-FIGHT-33.md): The contents-list writer and the bug register renderer move each other's blocks on bug pages
- [DRYRUN-LIBS-LABEL-32](DRYRUN-LIBS-LABEL-32.md): A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only
- [ESTIMATE-EVR-BELOW-CUR-31](ESTIMATE-EVR-BELOW-CUR-31.md): World estimate: "everything" comes out below "current content" in some regions
- HANDOFF-WRAPPER-01 (no report page): Source handoff wrapper reused an existing extraction directory
- PACKAGE-PORTABILITY-28 (no report page): Rebundled ZIPs lost exec modes; Windows path aliases accepted
- [PKG-STALE-RUNTIME-32](PKG-STALE-RUNTIME-32.md): The sealed v0.0.31 playtest contains a stale launcher preset folder
- [RELEASE-WS-BASELINE-VERSION-33](RELEASE-WS-BASELINE-VERSION-33.md): Every new VERSION failed the whitespace preflight until a docs/PATCH-v<VERSION>.json was made by hand
- [TOOLING-HEADLESS-BROWSER-31](TOOLING-HEADLESS-BROWSER-31.md): No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker
- [TRACKER-CHIM-LINK-MERGE-33](TRACKER-CHIM-LINK-MERGE-33.md): A merge dropped the CHIM Engine tracker link from the register; the integration head fails a tracker test
- [TRACKER-MAP-BLANK-31](TRACKER-MAP-BLANK-31.md): World progress map vanished when the mouse moved over it
- [TRACKER-REGISTER-LINK-MERGE-33](TRACKER-REGISTER-LINK-MERGE-33.md): An integration merge dropped the CHIM Engine tracker link from the bug register
- [TRACKER-REGISTER-SIZE-33](TRACKER-REGISTER-SIZE-33.md): The bug register outgrew the release text-file size limit
- WIN-02 (no report page): Cancelled Windows stage leaves child workers alive

<!-- END GENERATED CATEGORY -->
