# BUILD-SCRATCH-DISK-GROWTH-32: Build scratch volumes grow the container disk image on the system drive

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Docker build scratch volumes on the development host |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Container disk image grew about 63 GiB in 40 minutes and is never returned to the drive. |
| Family | Development tooling, receipts and packaging (`tracker-tooling`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open (infrastructure). Found while running parallel build jobs on the development host.

## Symptom

Build scratch volumes grow the container disk image on the system drive; space freed inside
volumes is reused but never returned. During parallel jobs the container disk image grew about
63 GiB in 40 minutes: one build's scratch volume reached about 151 GB and another job's about
131 GB. Moving 64.6 GiB of other data off the system drive left its free space unchanged at about
50 GiB, because the disk image took the space.

## Where

Docker Desktop on Windows (WSL2): container volumes live in one virtual disk file on the system
drive. Affects full builds, image steps and any job that copies build trees into scratch volumes.

## How it happened

Each job copied its inputs and outputs into its own scratch volume, and earlier image attempts
were moved aside instead of removed. The virtual disk grows on demand and never shrinks: space
freed inside it is reused by later writes but returned to the system drive only by compaction,
which needs Docker stopped (an owner decision on this host).

## Why it was not caught

Free space was watched on the system drive, not the size of each job's scratch volume, and no job
had a scratch budget.

## Reproduction

Run two full build jobs in parallel with separate scratch volumes; compare the container disk
image size and the system drive's free space before and after, and after deleting files inside a
volume.

## Repair

Not yet: per-job scratch budgets; reuse of one scratch tree instead of new copies; cleanup of
moved-aside image attempts after delivery; compaction of the disk image only when the owner stops
Docker for it.

## Verification

Pending.

## Prevention

Each job declares a scratch budget and reports its volume size; the disk watch includes the
container disk image size and alerts on growth rate, not only on free space.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Development tooling, receipts and packaging (`tracker-tooling`). Receipts, packaging, development tools and the tracker itself. See [families](README.md#families).

- ACTOR-RECEIPT-01 (no report page): Windows actor-audit receipt hash did not match the CRLF-written file
- AW25-07 (no report page): Python FS-UAE launcher not executable after extraction
- [BUILD-MOJIBAKE-32](BUILD-MOJIBAKE-32.md): A builder error message contains mojibake
- [BUILD-NAME-MOJIBAKE-32](BUILD-NAME-MOJIBAKE-32.md): A builder error message shows mojibake
- BUILD-REPAIR-01 (no report page): Image-repair retry omitted region-ownership files
- BUILD-REPAIR-02 (no report page): Retry assertion rejected an empty failure list as a failure
- DOC-STATE-01 (no report page): Published release documentation retained stale candidate/current-version claims
- [DOCS-DEAD-ANCHORS-32](DOCS-DEAD-ANCHORS-32.md): Seven documentation links point at headings that no longer exist
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
