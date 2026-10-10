# Bug tracking

One system, three parts. A test (`tests/test_bug_tracker.py`) checks that they
agree; a mismatch fails the build.

<!-- contents start -->
## Contents

- [Rules](#rules)
- [Facts](#facts)
- [Report template](#report-template)
- [Found in build](#found-in-build)
- [CHIM bugs](#chim-bugs)
- [Screenshots](#screenshots)
- [Duplicates and similar bugs](#duplicates-and-similar-bugs)
- [Families](#families)

<!-- contents end -->

| Part | File | Holds |
| --- | --- | --- |
| Register | [`bugs.json`](bugs.json) (schema: [`bugs.schema.json`](bugs.schema.json)), shown as [`docs/BUGS.md`](../BUGS.md) | Every bug exactly once: ID, title, state (open/fixed/closed), fixed in, owner accepted, current status, report link, the [facts](#facts) (who reported it, when and in which version, where, reproduction, duplicate, persistence, severity, family, related bugs) and optional tags (`performance`: listed together below the table; add with `--tag performance`). The only place for current status. Edit the JSON, or use `tools/bug_register.py add` / `set`, then `tools/bug_register.py render`; never edit generated parts by hand (the register in BUGS.md, the fact table and the "Bugs in the same category" section of each page, the [families](#families) table below). |
| Families | [`families.json`](families.json) | The categories bugs are grouped in: key, title and the shared cause or rule. |
| CHIM Engine tracker | [`CHIM_TRACKER.md`](CHIM_TRACKER.md) | Every [CHIM bug](#chim-bugs) by part, open first, with the build it was found in and the latest journal changes. Generated whole with the register. |
| Report | `docs/bugs/<ID>.md` | The full record of one bug (template below). Required for every bug found from v0.0.30 on, and for an older bug when it is worked on again. |
| Journal | [`docs/BUG_JOURNAL.md`](../BUG_JOURNAL.md) | Dated, short entries as things happen: reported, cause found, fixed, shipped, accepted. Each entry starts with the bug ID. |

Frozen history (read-only; current status is in the register):
[journal before 7 October 2026](../journals/BUG_JOURNAL-v0.0.29.md),
[earlier register notes](../journals/BUGS-NOTES-v0.0.29.md),
[v0.0.29-rc1 tracker](../BUGS-v0.0.29-RC1.md),
[v0.0.29-rc2 checkpoint](../RC2_ISSUE_CHECKPOINT.md).

## Rules

- **ID:** `AREA-WHAT-NN`, where `NN` is the version series in which it was
  found (`-30` for v0.0.30). Never reuse or rename an ID.
- **ID suffix and `found_in` answer different questions.** The suffix is the version series under
  development when the bug was registered; `found_in` is the build in which it was first observed.
  They differ when a bug is found in an older shipped build: an audit of the shipped v0.0.31 image
  during v0.0.32 work registers `...-32` with `found_in: v0.0.31`, and a fault found on the v0.0.32
  line in data that v0.0.31 already shipped can carry a `-31` ID registered at the time. Neither is
  renamed or corrected to match the other.
- **New bug:** add it to `bugs.json` (`tools/bug_register.py add ID --title ... --found vX --reported-by WHO
  --where ... --severity S --severity-reason ... --family KEY`), a journal entry and the report page in the
  same change, as soon as it is found, even if the cause is unknown; then `tools/bug_register.py render`
  writes the fact table and the category section into the page. A bug found from v0.0.30 on without
  every fact fails the tracker test.
- **Fixed** (`state: fixed` with `fixed_in`) means a correction shipped in a named version and was verified.
  A candidate, mitigation or source-only change is not fixed, and a development line
  (`v0.0.32-dev`) is never a `fixed_in` value; numbered builds (`v0.0.31-dev2`) are. Keep reported,
  source-checked, packaged, native-verified and owner-accepted distinct, and
  set `owner_accepted` only when the owner has played the fixed build.
- **Wording for unshipped repairs:** write "fixed in source on <branch> (<commit>), not shipped at the time of
  writing". Statuses describe the state when they were written; say so instead of "not yet shipped".
- **Regressions** get their own ID, linked to the older bug they resemble.
- Old IDs keep their records; their register row is updated when their status
  changes.

## Facts

Every bug found from v0.0.30 on (ID suffix 30 or higher) carries these fields in `bugs.json`; older
bugs carry them where the record allows. A value that the evidence does not give is `unknown`, never
a guess.

| Field | Values | Meaning |
| --- | --- | --- |
| `reported_by` | `owner`, `developer`, `review`, `audit`, `test`, `build`, `ci`, `gate:<name>`, `unknown` | Who first reported it: the owner in play, work on the code or data, an independent review, a data audit or measurement, a test, a build run, hosted CI, or a named gate or validator (`gate:stair-walk`). |
| `found_date` | `YYYY-MM-DD` or `unknown` | When it was first noticed (not when it was fixed). |
| `found_in` | a version (`v0.0.32-dev3`, `v0.0.31`, or a development line such as `v0.0.32-dev` for source work) or `unknown` | The build or line it was found in. |
| `where` | one line, at most 100 characters | Place or component: a map and spot, a builder stage, an engine part. |
| `reproduction` | `always`, `sometimes`, `once`, `unknown` | Every time (data, source and build faults are `always`), intermittently, seen once, or not known. |
| `duplicate_of` | an ID or `null` | Set only on a duplicate, which is then `closed` (see below). |
| `persists_in` | a list of versions, `unknown`, or `fixed in vX` | Versions in which it was observed, oldest first, the last one being the last seen. A fixed bug says `fixed in <fixed_in>`. Add the version each time it is seen again. |
| `severity`, `severity_reason` | `critical`, `high`, `medium`, `low`, plus one line | How bad it is, and why in one line (see below). |
| `family` | a key from [`families.json`](families.json) | Its category: the bugs that share its cause or area ([families](#families)). |
| `related` | a sorted list of IDs | Bugs in other families that share a mechanism with it. Links go both ways (`set ID --related X` writes both); bugs of the same family are linked by the family and are not listed here. |
| `chim` | `streaming`, `format`, `builder`, `stairs`, `rendering`, `performance` | Marks a [CHIM bug](#chim-bugs) and names its part. |
| `build` | an object (see [found in build](#found-in-build)) | The build it was found in: playtest version, source, engine and world commits, CHIM version and world format. |

**Choosing the severity.** Judge the effect on the player or on the release, not the effort to fix.

- `critical`: a crash, freeze or hang; data loss; the game cannot start or be played on; the builder
  cannot produce the game; anything that blocks a release.
- `high`: a major fault a player meets in normal play (stuck, falling through the world, major
  content missing, a major visual break, severe slowness), or a builder fault that silently ships
  wrong or missing content.
- `medium`: a visible or measurable fault with a workaround or a limited reach; performance and
  build-speed problems; a gate or test gap that could hide a regression.
- `low`: cosmetic or debug-only faults; tooling, messages, documentation and receipts; measurement
  method problems.

Raise the severity when new evidence shows a wider reach (and say so in the journal); never lower it
to make a release look better.

**Generated parts of a page.** `render` writes the facts as a two-column table under the page title
(rows Reported by, First noticed, Where, Reproduction, Duplicate of, Persists in, Severity, Family; then
CHIM for a CHIM bug, and Playtest version, From commit, CHIM engine version, Unknown because and Build note
when a `build` record exists)
and, after Prevention, the section "Bugs in the same category" listing the other bugs of the family
and the related bugs, each as its ID and title. Both sit between marker comments; the test fails when
they differ from `bugs.json`. A hand-written fact table directly under the title is replaced by the
generated one; `tools/bug_register.py backfill FILE` merges facts from a JSON list of records (missing
facts only, unless `--overwrite`); with `--pages` it also reads hand-written fact tables, which win over
the file.

## Report template

```markdown
# <ID>: <short title>

(fact table: generated by tools/bug_register.py render)

## Status: <date>

<Open / fixed in vX / owner-accepted in vX>. Present in <versions>.

## Symptom

What was seen, where (map, position, version), by whom.

## Where

Files, maps or components affected, and what is known to be unaffected.

## How it happened

The cause, step by step.

## Why it was not caught

Which check was missing or did not cover it.

## Reproduction

Exact steps or data comparison that shows the fault.

## Repair

What changed, and the gates on the result.

## Verification

What was run on which build, and what remains (for example owner playtest).

## Prevention

The check or gate added so it cannot recur unnoticed.

(Bugs in the same category: generated by tools/bug_register.py render)
```

---

## Found in build

Owner requirement (9 October 2026): a bug says exactly which build it was found in. The `build` record
is required for every [CHIM bug](#chim-bugs) and for every bug found from v0.0.30 on in a numbered build
(`found_in` such as `v0.0.32-dev3`, `v0.0.30-rc1` or `v0.0.32`); the tracker test fails without it.

| Key | Values | Meaning |
| --- | --- | --- |
| `name` | one line, at most 60 characters | The playtest version with its number as the build calls itself: `CHIM Preview 1`, `v0.0.33-dev1`, `MiniWind v0.0.33-dev1`; `source` when it was found in source, tests or gates on a development branch rather than in a playtest build. |
| `source_commit` | a commit (7 to 40 hex digits) or `unknown` | The source the build (its image) was made from; for `source`, the commit it was found at. |
| `engine_commit` | a commit or `unknown` | The commit the engine binary was compiled from (the source commit for a repository build). |
| `world_commit` | a commit, `unknown`, or `null` for a legacy-engine build | The commit of the builder that wrote the CHIM world. A preview can carry a world from an earlier run than its engine, so both are kept. |
| `chim_version`, `chim_format` | `0.1.0` and `0.4`, `unknown`, or `null` for a legacy-engine build | CHIM's own version and the world format the build carries. A CHIM bug never has `null` here. |
| `unknown_reason` | one line | Required when any value is `unknown`: why it is not known (older receipts did not record commits). |
| `note` | one line, optional | Anything a reader needs, for example an earlier sighting in a development run. |

Fill it from the build's receipt, which names only versions and commits:
`tools/bug_register.py set ID --from-build <playtest folder>/build.json` (it also reads the
`PLAYTEST-MANIFEST.json` beside it); single values with `--build-name`, `--source-commit`,
`--engine-commit`, `--world-commit`, `--chim-version`, `--chim-format` (`none` for null),
`--unknown-reason` and `--build-note`. `add` takes the same options. The register's "Found in" column
names the build when it differs from `found_in`; the page's fact table shows every value.

## CHIM bugs

The [CHIM Engine tracker](CHIM_TRACKER.md) lists every bug of the CHIM engine (its streaming and
memory, world format, builder stage, stairs and collision on CHIM worlds, rendering and performance).
The rule:

- A bug is a CHIM bug when its `chim` field names its part: `streaming` (engine streaming and memory),
  `format` (world format), `builder`, `stairs` (stairs and collision on CHIM worlds), `rendering`
  (rendering and visibility) or `performance`.
- Every ID that starts with `CHIM-` and every bug of the `chim-streamer` family is a CHIM bug. `render`
  marks such a bug automatically when it lacks a part (from its title and place; it prints the choice,
  which `set ID --chim PART` corrects), so bugs registered on other branches appear after a merge and
  one render. `add` does the same.
- Any other bug joins with `set ID --chim PART` when its cause or repair lies in CHIM (for example a
  stair fault that only CHIM worlds show). Legacy bugs that CHIM is meant to remove stay off the page.
- A CHIM bug carries its [found-in-build](#found-in-build) record with a CHIM version and world format.

`tools/bug_register.py render` writes the page together with the register; the tracker test fails when
the page is stale, when a CHIM bug is missing from it, or when a `CHIM-` ID lacks its part. The page
header gives the CHIM version (from `CHIM_VERSION`), the open, fixed and closed counts per part, and the
last 10 journal entries that name a CHIM bug, newest first, so a journal entry that names a CHIM bug
is followed by a render like any other register change.

## Screenshots

Evidence frames on a bug page follow the project's documentation image convention; there is no
separate image folder for bugs:

- One file per frame in `docs/images/`, named `amiwind-v<version>-<name>.png` after the build it shows
  (`amiwind-v0.0.33-chim-specks-bridge.png`); short clips as `.gif`. PNG at most 1 MiB, GIF at most
  4 MiB (the release limits in `tools/release.py`). Optimise (palette PNG, maximum compression) and crop
  to the game view; one large frame per point (2x nearest-neighbour scaling) rather than small contact
  sheets. Never edit, brighten or repaint a frame.
- Each file is listed in `tools/release.py` (`DOCUMENTATION_IMAGES`, or `DOCUMENTATION_CLIPS` for a
  GIF), in `tools/release-files.json`, and re-included in `.gitignore` with its own line
  (`!/docs/images/<file>`).
- The page shows it with a caption naming the build (playtest version and commit), the place and pose
  (map, position, view angle, `dbg` command if any), the game time and whether the headlamp was on, for
  example:

  ```markdown
  ![Specks, CHIM Preview 1 (engine 0d8bf4f), Balmora bridge, noon, headlamp off](../images/amiwind-v0.0.33-chim-specks-bridge.png)
  ```

- The tracker test fails when a page links a frame outside `docs/images/`, a missing file, a wrong
  name, a file over the limit, or one not listed in all three places. The CHIM Engine tracker marks a
  bug whose page has frames with a link to its first frame.

## Duplicates and similar bugs

**Duplicates.** A report that turns out to be the same fault as an existing one keeps its ID (IDs are never
reused or deleted). It is closed with the status "duplicate of <ID>" and a link, `duplicate_of` names that ID, and its
evidence moves to the original. Example: BUILD-SEYDA-PRIVATE-STAGES-31, closed as a duplicate of BUILD-SEYDA-REGEN-30.

**Similar bugs.** Bugs that share a cause or a mechanism stay separate entries (each has its own symptom,
place and verification), but they share one `family` and every page lists the others (generated), and a repair is checked
against the whole family, not only the bug that prompted it. Fix the shared layer once rather than each
instance; a family that keeps growing is a sign the shared rule or gate is missing.

## Families

Generated from [`families.json`](families.json) and the `family` field in [`bugs.json`](bugs.json); each
family links to its list in the register.

<!-- BEGIN GENERATED FAMILIES: edit docs/bugs/families.json and bugs.json, then run tools/bug_register.py render -->

| Family | Key | Bugs (open of total) | Shared cause or rule |
| --- | --- | --- | --- |
| [Vivec preview frame and its joins to the world](../BUGS.md#vivec-preview-frame-and-its-joins-to-the-world-vivec-frame-edge) | `vivec-frame-edge` | 7 of 7 | The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. |
| [Collision shapes and climbing (stairs, ramps, walkways)](../BUGS.md#collision-shapes-and-climbing-stairs-ramps-walkways-stairs-collision) | `stairs-collision` | 21 of 21 | Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. |
| [Distance drawing (horizon, fog, sky, far edges)](../BUGS.md#distance-drawing-horizon-fog-sky-far-edges-distance-drawing) | `distance-drawing` | 13 of 13 | Far-plane fog, the skyline fill, distant sprites and resident ground. |
| [Seyda Neen recorded stage](../BUGS.md#seyda-neen-recorded-stage-seyda-recorded) | `seyda-recorded` | 6 of 8 | Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. |
| [Content silently missing from a build](../BUGS.md#content-silently-missing-from-a-build-build-content-missing) | `build-content-missing` | 13 of 14 | Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. |
| [Builder breaks and reproducibility](../BUGS.md#builder-breaks-and-reproducibility-builder-from-scratch) | `builder-from-scratch` | 21 of 25 | The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. |
| [Build speed](../BUGS.md#build-speed-build-speed) | `build-speed` | 40 of 40 | Every stage on the shared worker pool; per-stage time and CPU in the build profile. |
| [Build reuse keys and output attribution](../BUGS.md#build-reuse-keys-and-output-attribution-build-cache-reuse) | `build-cache-reuse` | 21 of 22 | A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. |
| [Console, keyboard and mouse input](../BUGS.md#console-keyboard-and-mouse-input-console-input) | `console-input` | 13 of 14 | The console line editor, qualifier keys and the emulator key path. |
| [Music and sound](../BUGS.md#music-and-sound-audio) | `audio` | 20 of 23 | The mixer must stay fed through loads and scene changes; music starts after loads settle. |
| [Lighting, lamps and night](../BUGS.md#lighting-lamps-and-night-lighting-night) | `lighting-night` | 30 of 33 | Morrowind lights become Quake light entities baked by the light compiler and animated with lightstyles; night tables and dynamic lights follow the original. |
| [First-person hands and torch](../BUGS.md#first-person-hands-and-torch-torch-hands) | `torch-hands` | 7 of 10 | First-person hands, punches and the carried torch. |
| [Map heap and memory budget](../BUGS.md#map-heap-and-memory-budget-heap-memory) | `heap-memory` | 17 of 21 | The heap model must match what the loader actually allocates; strict heap gate, hard ceiling always fatal. |
| [Engine table limits](../BUGS.md#engine-table-limits-engine-limits) | `engine-limits` | 26 of 29 | Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. |
| [Mesh converter geometry](../BUGS.md#mesh-converter-geometry-converter-geometry) | `converter-geometry` | 24 of 28 | Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. |
| [World storage and duplication](../BUGS.md#world-storage-and-duplication-world-storage) | `world-storage` | 7 of 7 | Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. |
| [Loading and disk reads](../BUGS.md#loading-and-disk-reads-disk-loading) | `disk-loading` | 8 of 9 | Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. |
| [Rendering cost and visibility](../BUGS.md#rendering-cost-and-visibility-render-performance) | `render-performance` | 12 of 12 | Read the visibility data and renderer counters before any performance claim. |
| [CHIM world streamer](../BUGS.md#chim-world-streamer-chim-streamer) | `chim-streamer` | 49 of 49 | The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. |
| [FPU and CPU behaviour (68040/68060)](../BUGS.md#fpu-and-cpu-behaviour-6804068060-fpu-cpu) | `fpu-cpu` | 8 of 8 | Results must not depend on the FPU; unimplemented instructions trap on a real 68040 without a support library. |
| [Emulator measurement method](../BUGS.md#emulator-measurement-method-benchmark-method) | `benchmark-method` | 7 of 7 | Emulator numbers are relative until a hardware number exists; same-session runs with a drift control. |
| [Disk images, partitions and launchers](../BUGS.md#disk-images-partitions-and-launchers-disk-image-layout) | `disk-image-layout` | 8 of 11 | Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. |
| [Morrowind editions, archives and inputs](../BUGS.md#morrowind-editions-archives-and-inputs-game-data-editions) | `game-data-editions` | 9 of 9 | The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. |
| [Object placement and in-game geometry](../BUGS.md#object-placement-and-in-game-geometry-placement-geometry) | `placement-geometry` | 5 of 9 | Placed objects match the original (OpenMW A/B at the same pose). |
| [Actors and NPCs](../BUGS.md#actors-and-npcs-actors-npc) | `actors-npc` | 17 of 19 | Actor placement, models and behaviour; the actor placement gate. |
| [Harvestable plants](../BUGS.md#harvestable-plants-harvest) | `harvest` | 10 of 10 | Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. |
| [Town and interior import](../BUGS.md#town-and-interior-import-town-import) | `town-import` | 7 of 8 | The town importer converts every town and interior within engine limits; doors lead somewhere. |
| [Scene changes, arrivals and handoffs](../BUGS.md#scene-changes-arrivals-and-handoffs-transitions-arrivals) | `transitions-arrivals` | 9 of 13 | Cell, region and scene changes keep the player, view, equipment and sound intact. |
| [Menus, HUD, map screen and text](../BUGS.md#menus-hud-map-screen-and-text-ui-text) | `ui-text` | 17 of 21 | Menus, HUD, map screen, fonts and messages. |
| [Debug commands and remote control](../BUGS.md#debug-commands-and-remote-control-debug-commands) | `debug-commands` | 13 of 15 | dbg commands, teleports, debug map loads and the remote console. |
| [Boot and engine start-up](../BUGS.md#boot-and-engine-start-up-boot-startup) | `boot-startup` | 8 of 10 | The boot check and engine start-up report problems clearly and never stop the game silently. |
| [Game logic (QuakeC) and saves](../BUGS.md#game-logic-quakec-and-saves-game-logic) | `game-logic` | 19 of 22 | QuakeC entities, saves and game state. |
| [Gates, CI and tests](../BUGS.md#gates-ci-and-tests-tests-ci) | `tests-ci` | 26 of 31 | A check that is skipped, tests the wrong tree or depends on the host is not a check; skips fail loudly. |
| [Development tooling, receipts and packaging](../BUGS.md#development-tooling-receipts-and-packaging-tracker-tooling) | `tracker-tooling` | 15 of 22 | Receipts, packaging, development tools and the tracker itself. |

<!-- END GENERATED FAMILIES -->

Add a family to `families.json` when a new shared cause or area appears; a bug that fits none gets the
closest family until a better one exists.
