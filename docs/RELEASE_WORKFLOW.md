# AmiWind release workflow

_Last updated with AmiWind v0.0.64-dev4 (10 November 2026)._

<!-- contents start -->
## Contents

- [Overview](#overview)
- [Development snapshots, release candidates and finals](#development-snapshots-release-candidates-and-finals)
- [The release commit](#the-release-commit)
- [Checks before and after the build](#checks-before-and-after-the-build)
- [Delivery and the maintainer's kit](#delivery-and-the-maintainers-kit)
- [After the push](#after-the-push)
- [The trackers](#the-trackers)
- [Where release files go](#where-release-files-go)
- [Mandatory change records](#mandatory-change-records)
- [Release gate: the build tool must match the release](#release-gate-the-build-tool-must-match-the-release)
- [Game version and engine version](#game-version-and-engine-version)
- [Release gate](#release-gate)
- [Boot identity](#boot-identity)
- [Amiga limitations](#amiga-limitations)
  - [FFS partition capacity and hardfile capacity are different](#ffs-partition-capacity-and-hardfile-capacity-are-different)
  - [Preferred partition contents and performance](#preferred-partition-contents-and-performance)
  - [Legacy filesystem names: 30 bytes per component](#legacy-filesystem-names-30-bytes-per-component)
  - [Traceable original-to-target mapping](#traceable-original-to-target-mapping)
  - [AmiQuake's limitations](#amiquakes-limitations)
- [Palette and skin-tone consistency](#palette-and-skin-tone-consistency)
- [Source ZIP portability](#source-zip-portability)

<!-- contents end -->

Official project: https://github.com/FlyingFathead/amiwind/

This page describes how a release is made today. The maintainer pushes, tags and publishes to GitHub from a Linux
machine; the project builds, checks and verifies everything before that. The previous text of this page, written before
every exterior ran on the CHIM engine, is kept as
[history](history/superseded/RELEASE_WORKFLOW-v0.0.54.md).

## Overview

A release is a chain of checked steps. Each step validates its input before it starts and its output before the next
step uses it, and a refusal at any step is final: it is fixed at its cause, never passed over.

1. Work happens on branches, one gate per commit. A commit is built or merged only after its gate passed.
2. Development snapshots (`devN`) are built from the development line, checked in the emulator and handed to the
   playtest server. They are for testing and need the same 32 MB of Fast RAM the game requires.
3. The release is one commit that carries the version bump, the documentation and the release presets.
4. A release candidate or final image is built from that commit, checked, packaged and delivered.
5. The maintainer's Linux kit is built from the same commit. He applies it, pushes, and the project watches the hosted
   checks to the end.
6. After the push the project's own line is connected to GitHub's main and the records are brought up to date.

## Development snapshots, release candidates and finals

- **Snapshots** are numbered `X.Y.Z-devN`. The version file, the emulator presets and the release notes of a snapshot
  carry that name. A snapshot's notes say "in development" and list what is new, what is known and what is not yet
  checked in game. A fix in a snapshot is not yet marked fixed in the register: that needs a numbered release build and
  a verification, and a source-only fix does not count either.
- **A release candidate** (`-rcN`) is a snapshot that is a candidate for the final; it is only built when something
  needs a separate look before the final.
- **The final** is usually the last snapshot built again with its release version number. A change of the version
  number alone must rebuild only what shows the version (the engine and the image), never the converted world: caches
  are keyed by content, so a snapshot, a candidate and a final of unchanged content reuse each other's results. The
  from-scratch build of the release line, with nothing reused, is its own check and runs before a final.

## The release commit

One commit carries everything that must agree before the build:

- **The version.** `VERSION` changes together with `resources/emulators/AmiWind-v<VERSION>-FS-UAE.fs-uae` and
  `AmiWind-v<VERSION>-WinUAE.uae` and their entries in `tools/release-files.json`; older presets are kept. The
  emulator-config, keyboard-port and launcher tests run against the new version before the commit is pinned
  ([BUILD-VERSION-EMULATOR-PRESETS-38](bugs/BUILD-VERSION-EMULATOR-PRESETS-38.md)). The presets default to 32 MB of Fast
  RAM.
- **The records**, see [the change records](#mandatory-change-records): register, README, changelog, release notes,
  roadmap, the generated indexes.
- **The progress pages.** Every version commit renders the current state of the scripting tracker and of the
  [CHIM progress tracker](chim/PROGRESS_TRACKER.md) for its own version, the newest build first: after the tracker
  ingest, `python3 tools/cell_progress_state.py snapshot --from <tracker data>/cell-progress.json`, then
  `python3 tools/cell_progress_state.py render` and `python3 tools/doc_toc.py write`; beside it
  `python3 tools/mwscript_features.py measure --data-files <game data> --version <VERSION>` for the
  [MWScript features](MWSCRIPT_FEATURES.md). The preflight refuses a version whose progress page block differs from a
  fresh render, and a page that the release notes or the changelog link to when only its last-updated line changed and
  its generated block lags (`python3 tools/release_linked_pages.py list` prints those pages for the docs review).
- **The release notes** `docs/releases/notes/RELEASE-v<version>.md`, with the title word for word as the maintainer
  gave it, a "Known in this build" section whose entries link register pages, and the whitespace baseline
  `docs/releases/patches/PATCH-v<version>.json`.
- **Measured inputs of the release image**, such as the disk footprint, and the Toolkit's own version and its
  "Last updated" line whenever a Toolkit file changed.
- **Limits**: a new setting that uses resident memory raises the resident budget in the same commit, and a deferral that
  expired is renewed or lifted in the register.
- **The CI time budget.** The release preflight projects each hosted job's run time from the last recorded runs and
  raises the job's time limit in the release commit when the projection reaches 80 % of it, never after a push.

## Checks before and after the build

1. **The release preflight** takes minutes and lists every problem with its fix: the release guard, the persisting bugs,
   the version records, the previous tag, the patch file, the notes' bug pages, the reuse plan of the build, the CI time
   budget and a quiet machine.
2. **The release guard** is run first and is the fast-failing gate around the rest. It checks the manifest schema, the
   title (data, never code: no quotes, dollar signs, backticks, `@` or line breaks, tested with hostile titles), every
   kit template with the real title, the version at the commit against the manifest and the working version, the
   notes' format, the test list, privacy words in changed public files, the gate receipt of the same commit, the pinned
   previous release and size baseline, the from-scratch ledger for a final, and that the delivered image run is known
   to the progress tracker.
3. **The gate** runs the full suite on the exact commit: source checks, tests, the engine build, the launcher parity
   and a boot smoke whenever engine code is touched. A release gate runs without a queue and without early stop, and a
   gate number is never reused. Every gate log is kept.
4. **The build** is requested through the master builder ([aw](AW.md)), reusing the last good run of unchanged stages.
   Its start-up plan is read in its first minute; an unexplained rebuild stops it. A build runs only from a gated commit
   that contains the integration line.
5. **The boot smoke.** Nothing is delivered without an emulator run of that exact image that boots, loads a map and
   plays about ten seconds (the JIT preset, a fresh play copy, 32 MB of Fast RAM). Smaller sizes are recorded as below
   the requirement and never block. The smoke runs the map change three times, so an intermittent load stall has three
   chances to show.
6. **The teleport hops.** The release smoke hops through Seyda Neen, Balmora, Vivec, the Arena Pit, Ald'ruhn and Khuul;
   every hop must change the map and have its picture and frame time.
7. **The readback and the package.** Every file of the image is read back from the disk image, then the playtest ZIP is
   built and read back member by member against its manifest, with its SHA-256 checked.
8. **The records of the world.** The CHIM progress tracker and cell tracker ingest the image run, and the CHIM
   inclusion ledger is written for a release.

## Delivery and the maintainer's kit

- **Playtest delivery.** A verified snapshot goes to the private playtest server with the public source ZIP of the
  exact commit, through one wrapper that validates its input first (version form, files and checksums, one playtest and
  one source ZIP, the smoke passed, the guard passed for a candidate or final) and its output after. The server keeps the
  current and one previous version; each push says which one drops out. A snapshot that was not smoke-tested is not
  pushed.
- **The Raspberry Pi stick.** The image of every delivered build and of every final is also copied onto the Raspberry
  Pi 4B boot stick (Amiberry). It is the project's performance yardstick and a second smoke: the same image must reach
  the main menu and load the game the smoke loads. A difference in behaviour between the two emulators is a finding;
  slower boots and lower frame rates on the Pi are expected, and Pi numbers are only compared with earlier Pi numbers.
- **The Linux kit.** The kit is one ZIP built from the exact release commit by the project's kit tool: the guard first,
  the public-source ZIP, the suite record of the exact tree, the kit validation in a Linux container. The maintainer
  extracts it, runs the one command in its README, reviews the diff and answers the yes or no prompts before the commit
  and push. There is no second file beside the kit, and its scripts stop on local changes or a divergence from GitHub.
  A kit for a snapshot (a pre-release patch) is made the same way from a snapshot's configuration.
- **A docs review.** Right after the release commit, the release notes, README, changelog, roadmap and the kit README are
  read against the register, the work list and the plan: false known issues, claims of features that moved, missing
  features, numbers, links and the public-text rules. Findings are fixed in the release commit before the kit.

## After the push

1. The hosted checks of the pushed commit are watched to the end; a red job is reported with its name and failed step,
   and a release is not done until the run on main passes. The tag run holds only the from-nothing bootstrap, not the
   suite again. The job times are recorded for the next preflight.
2. The trees are compared (the maintainer's commit and the project's have the same tree and different hashes), the main
   checkout follows GitHub's main, and the project's line is merged with GitHub's main.
3. **Connect the release fully, in one go:** the previous-release pin, the size baseline and the pinned payload size in
   the size-ledger test, then a gate. The guard fails when the pin is not the newest published tag.
4. The Pi stick is updated if it was not already, and its boot banner is checked.
5. The whitespace baseline is refreshed from the tag.

## The trackers

The records change in the same step as the work, not later.

- **The bug register** (`docs/bugs/bugs.json`, rendered into [BUGS.md](BUGS.md) and the report pages, with the
  [journal](BUG_JOURNAL.md)) is always current: every finding is registered the same day; an issue seen again is
  reported on its entry as persisting, never filed again; a fix is marked fixed only when it shipped in a numbered
  release build and was verified, with the version it was fixed in. See [the register's readme](bugs/README.md).
- **The roadmap** ([ROADMAP.md](ROADMAP.md)) lists the open work of each version and says what a release moved on.
- **The changelog** ([CHANGELOG.md](CHANGELOG.md)) has an entry for each release, and an "in progress" entry for the
  current one that is filled as work merges.
- **The release notes** and the index pages ([releases](releases/README.md), the documentation index) are generated or
  written per release.
- **The measurements** of builds and in-game frame times are kept in [docs/performance](performance/) with the build and
  settings that produced them; an unchanged path is not measured again.

## Where release files go

Since v0.0.55 a release writes its notes to `docs/releases/notes/RELEASE-v<version>.md` (dev and rc notes beside
them), its whitespace baseline to `docs/releases/patches/PATCH-v<version>.json`, adds its row to
[releases](releases/README.md) and regenerates the [documentation index](README.md)
(`python3 tools/docs_index.py write`). One-off records (checkpoint validations, local release candidates, feedback,
investigations, per-version validations, plans, merges) go to `docs/history/<kind>/`, journals to `docs/journals/`.
Nothing is written at the docs/ root except topic documents, and nothing in docs/ is deleted: a document that is
replaced moves to `docs/history/superseded/` with a line naming its replacement. The gate refuses a per-version file
at the docs/ root and any relative link that names no file (tests/test_docs_layout.py).

## Mandatory change records

Changelog, bug tracking and CHIM coverage maintenance are required parts of
development, integration and release preparation. A change is incomplete
until its affected records agree with the code and actual verification.

1. Update [CHANGELOG.md](CHANGELOG.md) in the same change as a fix, feature,
   regression or confirmed finding, under the current version and date. State
   the player-visible result or build effect and link the issue ID. Keep
   implemented changes separate from findings and unfinished work.
2. Update [bugs.json](bugs/bugs.json), the issue report and [BUG_JOURNAL.md](BUG_JOURNAL.md)
   together; render the generated register and related pages. The register
   alone owns current status. Record regressions immediately. Source-only
   work does not set shipped/fixed or maintainer-accepted status.
3. Update the [CHIM cell tracker](chim/PROGRESS_TRACKER.md) whenever conversion,
   audits, native checks or package inclusion change. Bind each state to its
   source/build and receipt. Keep failed, excluded and held cells, original
   reference types, deferred actors and unimplemented gameplay explicit.
   Converted, audited, native-checked and packaged are separate states;
   planned cells do not count as included cells.
4. When coverage changes, regenerate the sanitized reference, cell-tracker
   page and progress map together and update their captions/date/counts. Keep
   the served tracker current from the same evidence. Do not expose private
   receipts or source assets, edit historical releases or invent acceptance.
5. Before freezing source or preparing a handoff, reconcile the changelog,
   linked release notes, register, roadmap and coverage snapshot. Include
   every new report/document in the public source allowlist. Check links,
   generated sections, whitespace and the actual exported source, not only
   the working directory. Missing or contradictory records block the handoff.
6. At verification and delivery, update the affected records using exact
   results and version IDs. Preserve historical entries and failed receipts.
   Rerun checks affected by changes; reuse unchanged valid evidence. Never
   turn an old image's successful check into acceptance of a new image.

## Release gate: the build tool must match the release

The repository's builder (`tools/build_aga.py`, `build.sh`, `build.cmd`, `build.ps1` and every converter they call)
must produce everything the release contains, from the builder's own Morrowind data, with no separate patch-up step.
Every change that went into a snapshot (world tables, map compiler settings, engine and data changes) is in the builder,
tested and documented before the release notes are written, and the shipped build uses only machine settings
(workspace, jobs, reuse, tools and data directories). A clean build with the repository builder must reproduce the
release payload's file list and contents, apart from documented build-time stamps; any other difference blocks the
release. The builder option `--seyda-recorded DIR`, which ships recorded Seyda Neen maps instead of converting them,
is optional and NOT RECOMMENDED since v0.0.31: the default converts Seyda Neen from your data. See
[Which Seyda Neen is in my build?](LINUX_BUILD.md#which-seyda-neen-is-in-my-build).

## Game version and engine version

The game and its engine carry separate version numbers. The streaming engine and its builder are the **CHIM engine**,
with its own semantic version: the major number changes when the world format changes (the engine refuses a world
built for another major version with a clear message instead of a crash), the minor number for new engine features, the
patch number for fixes. The CHIM builder has the same version as the engine it builds for. Every release states both:
"AmiWind vX / Running on CHIM Engine vY" in the release notes and the README, the short form in the boot checklist and
the engine console, and both numbers with the world format version in every build receipt. CHIM 1.0.0 is the release in
which the whole island runs on it.

## Release gate

**Check for trailing whitespace before any push or publish script is handed over.** `tools/release.py --check`,
candidate creation and candidate validation reject trailing spaces and tabs, whitespace-only lines, space-before-tab
indentation and blank lines at the end of new or modified text files. Only byte-identical inherited files under
`engine/aga/` and `docs/aga/` are exempt, listed by hash in the whitespace baseline of the last published release; a new
`VERSION` needs no extra file. After a release is published the list is refreshed from its tag
(`python3 tools/release.py --whitespace-baseline v<VERSION>`); it can only shrink. Before delivery,
`git diff --no-index --check` also runs on clean extracted source trees of the base and the candidate.

Candidates are written to a staging area, checked independently, then promoted. ZIP paths, the source allowlist,
content hashes, patch application, image hashes, corresponding source and boot behaviour are validated; a released ZIP
is never overwritten and an old executable is never relabelled as a new build. Public CI compiles without game files or
ROMs; full conversion and physical Amiga behaviour need their own validation. The source repository and source releases
are public; playable images, converted game files and supplied ROMs stay private and are never release assets.

## Boot identity

NPC placement is a release gate: follow [NPC_GROUND_CONTACT.md](NPC_GROUND_CONTACT.md)
on fresh scene loads, sub-cell/door re-entry and save restoration. Keep original
reference IDs in the report, investigate non-grounded residents and document
intentional airborne/scripted exceptions. A floor correction is not proof that
the final packaged runtime passes the audit.

Transition experiments follow the numbered-method protocol in
[PERSISTENCE_AND_STREAMING.md](PERSISTENCE_AND_STREAMING.md): preserve current
method 1, measure loading phases and heap separately, and compare any new method
2 before making it a default. Do not replace the existing loader during research.


Normal preflight and dry-run screens display their shared AmiWind version. The
preflight also repeats the version in its pass/fail footer so screenshots always
identify the runtime under test. Guest-visible hardware is reported by
`AmiWindCheck`; FS-UAE-only settings are validated by the portable host launcher.
The boot identity also includes:

```text
By FlyingFathead
https://github.com/FlyingFathead/amiwind/
Special thanks to: ChaosWhisperer
```

Public source excludes original/converted game data, reusable extracted fonts,
ROMs and private images. The explicitly allowlisted maintainer-approved README screenshots are a
documentation exception. README/gameplay images must show AmiWind itself;
OpenMW screenshots are private reference material and must never enter public
source or documentation assets. Preserve component licence notices and keep complete
development recovery sets separate from playable packages.

Public documentation and release assets use generic example paths. Keep maintainer
usernames, machine names and local directory layouts in private handoff material.

## Amiga limitations

### FFS partition capacity and hardfile capacity are different

For the current Kickstart 3.1 / DOS1 FFS compatibility profile, plan partitions
**below 2 GiB** and keep the complete device's addressed range **below 4 GiB**.
One RDB `.hdf` can contain several such partitions; a 2 GiB partition bound is
not a 2 GiB limit on the complete multi-partition hardfile. Verify the actual
ROM, filesystem and device path, including native reads at the highest used
offsets. These planning bounds do not certify arbitrary physical controllers.

The older `build_aga.py` **1 GiB boot-partition cap was a project build setting**,
not the FFS format limit. Do not describe it as an Amiga filesystem restriction.
Keep that smaller boot partition only when its payload fits; use the available
partition capacity deliberately when building the combined terrain image.

Measure the converted runtime payload before deciding its disk layout. Original
Morrowind installation size is not the converted-image size: overlapping BSPs
duplicate terrain, collision and visibility tables, and converted audio/textures
have different storage costs. Record payload bytes, partition sizes, free-space
allowance and highest used device offset in the build receipt. Check avoidable
duplication before expanding storage. Distinguish decimal GB from binary GiB
(2 GiB = 2,147,483,648 bytes). See [storage profiles](STORAGE.md).

### Preferred partition contents and performance

If capacity eventually requires two larger partitions, prefer **partition 1 for
the main Morrowind game**, including frequently visited interiors and shared
resources, plus boot files, configuration and saves. Prefer **partition 2 for
future Bloodmoon/Tribunal content, videos and less frequently used assets**.
Move selected base-game interiors only if needed; shops, guilds and quest hubs
are not inherently rare. Keep expansion assets together for play within that
expansion, and retain one copy of shared resources.

This is the maintainer's future placement preference. The present v0.0.25-rc1 image
uses two 1,664 MiB partitions with base-game terrain balanced between them; no
expansion conversions are included. Its measured payload exceeds one 2 GiB
partition, so further reductions or selective overflow are necessary before all
main-game content can occupy partition 1. Two exactly 2 GiB partitions plus RDB
space would exceed 4 GiB; keep both partitions and the complete image below their
respective planning bounds.

Two partitions do not cause operating-system swapping on the plain KS 3.1
baseline, and partition 2 in the same HDF has no inherent speed advantage.
Extra filesystem buffers/handler state consume RAM, and filesystem work costs
CPU time. Our current fallback search also checks primary paths before opening
second-volume files. Once open, reads use that file handle. A future direct
asset-to-volume index can avoid those failed lookups; it is not implemented.
Scene reloads may pause on either partition. Measure load time, RAM, frame stalls
and audio refill behavior before claiming a performance gain or no overhead.
See [content placement and costs](STORAGE.md#preferred-future-content-placement).

### Legacy filesystem names: 30 bytes per component

The RC1 HDF build rejected `scene-doors-bmhlaalucouncil.txt`: 31 ASCII
characters/bytes exceed the selected legacy Amiga OFS/FFS limit of **30 bytes
for each filename or directory component, including the extension**. A name
that works in the host workspace can therefore fail during Amiga packaging.
This is a constraint of our legacy target format; do not assume that newer
Amiga filesystems or a host-directory emulator mount behave identically.

Use stable abbreviations, shorthands, numbering or bounded identifiers when
needed. Reserve room for prefixes, suffixes and extensions. Do not silently
truncate: different originals can then collide. Keep target names ASCII where
possible, case-insensitively unique, and independent of display labels.

The door converter now emits `doors-bmhlaalucouncil.txt` (25 bytes). Runtime
loading prefers `doors-<map>.txt` and retains the older-name fallback. The
payload preflight `tools/amiga_fs.py:check_payload_names` runs before HDF
packing and rejects overlength components, unsupported characters and
case-insensitive path collisions. Validate the complete staged payload, not
only the examples that originally failed.

### Traceable original-to-target mapping

Every shortening must retain a reverse lookup. `config/seyda_area.json` and
`config/balmora_interiors.json` keep original cell names beside stable runtime
map IDs. `tools/prepare_doors.py` additionally generates private
`asset-name-map.json`: source master SHA-256, original cell, runtime map ID,
BSP path, current/previous door-bank filename, and each original door's record
ID, placed reference number, cell/grid, mesh path and destination. RC1 has
60 scene entries and 185 placed door records. Keep exact source spellings;
never replace them with the shortened target name.

| Original Morrowind cell | Runtime map | Generated door bank |
| --- | --- | --- |
| Balmora, Hlaalu Council Manor | `bmhlaalucouncil` | `doors-bmhlaalucouncil.txt` |
| Balmora, Caius Cosades' House | `bmcaius` | `doors-bmcaius.txt` |
| Balmora, Guild of Mages | `bmmages` | `doors-bmmages.txt` |

That JSON covers scene/BSP and door-bank naming. Other asset families retain
source-to-output receipts: `balmora-interiors.json` links NPC record IDs,
appearance part meshes and authored greeting paths to hashed MDL/WAV names;
`door-audio.json` links source samples and hashes to short WAV names. Original
placed geometry and transforms remain in `interior-reference.json`, while
room conversion reports identify selected meshes. These are complementary
records, not a claim that a single JSON covers every texture and sound in the
game. Keep the reports with private conversion evidence and include new asset
families as they are introduced. A one-to-many conversion must list every
output; reused outputs must preserve every relevant source identity.

For recurrence: trace the rejected path to its converter; choose a stable
short name; update producer and consumer together; emit the mapping; run the
payload preflight; rebuild the HDF; read files back and boot the packed image.
Do not fix only a local staging copy or rely solely on a host-directory boot.

### AmiQuake's limitations

AmiWind's engine is AmiQuake, so every converted map also lives inside Quake's
own limits. Numbers below are read from `engine/aga/src` (`bspfile.h`,
`client.h`, `progs.h`, `quakedef.h`, `model.c`, `common.c`) and the converter
(`tools/prepare_mesh_bsp.py`). Several are AmiWind extensions of the BSP29
format: indices stock Quake reads as signed 16-bit numbers are read unsigned.

| Limit | Value | Where it bites | Notes |
| --- | ---: | --- | --- |
| Map format | BSP29 only | every map | `BSPVERSION 29`; BSP2 is not supported. |
| Texture mappings (texinfo) per map | 65,535 | dense Vivec cantons | AmiWind reads the 16-bit face field unsigned (VIVEC-TEXINFO-31); the converter shares identical mappings. ericw vis v0.18.1 crashes and ericw light leaves faces unlit above 32,767, so run them only on maps below it (ERICW-TEXINFO-SIGNED-31). |
| Faces per map | 65,535 | big towns and interiors | `MAX_MAP_FACES`. |
| Faces listed in leaves (marksurfaces) | 65,535 | moving building faces into the world | 16-bit leaf lists, read unsigned with bounds checks (MODEL-MARKSURF-SIGNED-31). |
| Planes referenced by faces | 65,535 | large converted scenes | AmiWind reads face plane indices unsigned. |
| Surface extents | 256 texels per face | grid-exact mesh faces | The engine computes texture coordinates in double precision after every operation (as ericw light); the converter splits faces with a 1/16-texel guard, sizes lightmaps from the stored values and checks extents under double, single and extended rounding (`tools/surface_grid.py`). |
| BSP nodes | 32,767 | dense maps | negative values mean leaf contents. |
| Collision clipnodes | 65,520 | caves, shrines, mines | AmiWind extension (stock: 32,767). |
| Vertices / edges / surface edges | 65,535 / 256,000 / 512,000 | large meshes | `MAX_MAP_VERTS`, `MAX_MAP_EDGES`, `MAX_MAP_SURFEDGES`. |
| Leaves | 8,192 | vis splits | `MAX_MAP_LEAFS` (tool limit). |
| Inline models per map | 256 (AmiWind budget 220) | rooms with many objects | `MAX_MODELS` is sent as a byte; AmiWind keeps headroom. |
| Entities on the server | 600 | crowded scenes | `MAX_EDICTS`. |
| Leaves an entity is linked to | 16 | brush models of buildings | `MAX_ENT_LEAFS`; an entity in more leaves is treated as visible everywhere. See [Town visibility](performance/TOWN-VISIBILITY.md). |
| Static entities | 512 | dressed scenes | `MAX_STATIC_ENTITIES`. |
| Animated flames | 128 per map | fire-heavy interiors | `STATIC_FLAME_MAX`. |
| Dynamic lights at once | 32 | torches, guard torches, night lamps | `MAX_DLIGHTS`. |
| Light styles | 64 | switchable and flickering lights | `MAX_LIGHTSTYLES`. |
| Lightmaps per face | 4 styles | overlapping animated lights | `MAXLIGHTMAPS`. |
| Particles | 2,048 | fire, embers | `MAX_PARTICLES`. |
| Surface extent | 256 texels | large flat faces | Checked at load; the 68040's wide floating-point intermediates can round a face that sits exactly on the 16-texel grid one block larger than a 32-bit check predicts. |
| Coordinates | about +/-4,096 units | town and region size | sent as 16-bit numbers in 1/8 units; why towns are split into frames and sub-cells. |
| Sounds / models per level | 256 each | | sent over the network as bytes. |

Heap per map comes on top of all of these: see the map memory profile and
the builder's heap budget. A future builder limits check is planned to report
every one of these per map, as a warning or a failure.

## Palette and skin-tone consistency

Before packaging, run `ui_palette.sync_lookups(game, check=True)` against the
final game directory. The production image builder enforces this check. Palette
reservation must update the dependent lighting and fog columns, including when
reopening a previously converted payload. Retain the resulting table hashes in
the private receipt. Use a pale-skinned resident as a native visual sentinel;
check both nearby daylight and normal world lighting/fog. See the
[ashen-face investigation](IMPLEMENTATION_JOURNAL.md#j027--pale-faces-mapped-back-to-sky-grey).
This catches colour-table drift; it does not certify every face or texture seam.

## Source ZIP portability

When rebundling an audited source tree, preserve file bytes and each
entry's Unix executable modes. Validate paths before extraction: reject
absolute paths, parent traversal, symlinks, case collisions, Windows
device names, alternate-stream colons and trailing dots or spaces.
Hash checks do not establish executable-mode or pathname portability.
