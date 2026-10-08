# Development and source packaging

All documentation lives in `docs/`; keep the root limited to core project files.
Original/converted game content stays outside distributable source. Build output
uses ignored out/ or a selected external workspace.
The project owner handles all Git/GitHub pushes. No remote is configured by the
source package, and packaging does not commit, tag, push or publish anything.

## Source authority

There is one repository root, `amiwind/`. Edit native code directly in
`engine/aga/src/`; the builder compiles an external copy of that checked-in tree.
The old upstream patch under `docs/aga/` is historical and is never applied by
the current builder. Keep the existing immutable release archives as baselines.
See REPOSITORY_LAYOUT.md for the path mapping and RELEASE_WORKFLOW.md for the
single version shared by source, runtime and release packages.

## Mandatory rule: the repository builds the whole game from scratch

The repository's builder (`build.sh`, `build.cmd`, `build.ps1`,
`tools/build_aga.py` and the converters they call) must be able to build the
entire game from the builder's own Morrowind data, from scratch: no private
stage, no reused image, no hand-applied patch. This is checked regularly, before
every release and after any builder or converter change, by a from-scratch
build compared file by file with the latest release image; every difference is
a bug in the [register](BUGS.md). Known gap as of v0.0.31:
[BUILD-SEYDA-REGEN-30](BUG_JOURNAL.md#build-seyda-regen-30-public-build-cannot-regenerate-seyda-neen-7-october-2026); the
release gate in [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md) applies from v0.0.32.

## Mandatory build rule: ALWAYS CHECK COMPILER WARNINGS

For every native build, capture the complete compiler output and inspect every
warning. Successful compilation alone is not acceptance. Fewer unresolved
warnings is the goal; do not let the count become an ignored background number.

- Compare warnings against the preceding matching toolchain/configuration. Keep
  count, category, affected function and actual diagnostic text in the build
  evidence; a lower total must not conceal a new warning elsewhere.
- Investigate new warnings before packaging. Prioritize bounds/undefined
  behavior, uninitialized values, lifetime/dangling pointers, format overflows,
  dangerous conversions and misleading control flow in C on the Amiga target.
- Fix confirmed defects and exercise the affected behavior. Use host sanitizers
  where practical, then rebuild the actual m68k target. A host pass does not
  establish Amiga memory safety or explain an unrelated intermittent crash.
- Rebuild after corrections and compare again. Never suppress a warning, weaken
  warning flags or change toolchains merely to make the total look smaller.
- Release notes/handoff must state the count, what changed, any new unresolved
  warning and why existing warnings remain. Keep remaining substantive warnings
  in the follow-up work until reviewed and resolved; do not call a warning-bearing
  build warning-clean. Any explicitly deferred new warning needs a concrete
  reason and tracked follow-up before a release can be accepted.

The v0.0.20 maintenance comparison is 95 -> 93 with no new warnings under the
same GCC 16.2-rc11 configuration. Two array-row bounds violations were reproduced
and fixed. The other 93 warnings remain work, not a clean-bill-of-health claim.
This rule applies to later builds too, including character creation and save/load.

## Efficiency rule #1: parallelize

Every independent piece of work runs in parallel: builder stages, converters, checks and gates
use the shared worker pool (`tools/build_parallel.py`) or separate processes wherever the order
does not matter. A stage that leaves most cores idle is a bug: the image step once ran on one of
24 threads for about 23 minutes per pass
([BUILD-IMAGE-SERIAL-32](bugs/BUILD-IMAGE-SERIAL-32.md)). Serial work says why it must be serial,
and parallel results stay byte-identical to serial ones (a regression test checks it).
`--jobs N` is exact and reaches every stage and pool; see [Parallel host builds](PARALLEL_BUILD.md).

## Mandatory map rule: EVERY MAP MUST LET QUAKE'S VIS DO ITS JOB

Quake only skips what its `vis` data says cannot be seen, and `vis` only uses
structural world brushes as walls. Brush entities (`func_wall`, every converted
building, interior wall, floor and rock today) are drawn and collide but never
hide anything. Measured on the v0.0.31-dev5 maps: interiors 100 % visible from
everywhere, Balmora 84-89 %, Seyda Neen 59-76 %, the open world 69-85 %; hidden
houses and the NPCs behind them were processed every frame
([Town visibility](performance/TOWN-VISIBILITY.md),
[TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md)).

- Measure before changing the visibility structure. In the 8 October 2026
  prototypes, skip occluders inside houses (with and without hints) and
  building faces in the world model gave negligible benefit with the current
  town partitioning (589 of 590 bm019 building models still sent; at most about
  5 % less face work, with format limits broken). Further town occlusion work
  waits for evidence of a better partitioning or culling approach; meanwhile
  town frame rate is sought from drawing less at a distance and cheaper
  per-model work.
  Interiors (rooms behind thick walls) still need the occluder test.
- Every map build reports its visibility share (leaves visible from an average
  leaf) and the faces in the world vs in brush entities; a map that regresses
  past its limit fails the build.
- No performance conclusion without the visibility numbers and a matched
  in-game frame-rate A/B: before saying "nothing more can be culled", read the
  map's visibility data.
- The same applies to anything else placed as an entity: NPCs and creatures are
  only skipped when the visibility data puts them out of sight.

## Tests

```sh
python tools/run_tests.py            # parallel; same tests as the serial command below
python -m unittest discover -s tests -v
```

`tools/run_tests.py` discovers exactly what `unittest discover -s tests` finds,
then runs every test module in a fresh process of its own across `--jobs N`
workers (default: the builder's automatic CPU and memory budget). Long modules
start first, from the recorded seconds in `tests/module-timings.json`; a long
module without module- or class-level fixtures is split into shards of its own
tests (`--split-above SECONDS`, 0 disables). Each worker checks that it loads
the same test IDs that discovery found. One merged report lists failures,
errors, skips with reasons and per-module times; the run fails on any failure,
error, unexpected success, crashed or timed-out module (`--module-timeout`).
`--skip-allowlist FILE` (lines `test id | exact reason | why`) also fails on any
other skip. `--record-timings tests/module-timings.json` refreshes the records,
`--json FILE` saves the report and `--list` prints the discovered test IDs.
Tests must not depend on running in the same process as another module, and
must keep temporary files under unique temporary directories, because modules
run at the same time.

Fixtures are generated into temporary directories using fictional data. No
Morrowind files are needed for tests. GCC or Clang enables the C reader test;
that test is explicitly skipped if neither compiler is available. The host
tests do not measure Amiga performance.

## Explicit release file list

`tools/release-files.json` lists the source files permitted in a source archive.
Add a path deliberately when adding distributable source. Review the content
policy first. The checker rejects unexpected files, missing files, source
symlinks, binary/oversized source entries and tracked files outside the list.
Ordinary Python caches, virtual environments and package metadata are excluded.

```sh
python tools/release.py --check
python tools/release.py --workspace "../morrowind-amiga-workspace"
```

The packer writes a candidate into external `incoming/`. A separate validation
pass checks archive paths, CRCs, hashes, sizes and source-byte equality before
promotion into `releases/`. The archive includes `docs/PACKAGE_MANIFEST.json`.
A SHA-256 sidecar is written beside it. Existing versioned releases are never
overwritten: bump `VERSION` and update the changelog before the next release.
A host-tool/documentation packaging follow-up may instead use an explicitly
numbered archive revision while retaining the existing runtime version and HDF.
Give it new filenames/checksums, preserve the prior artifacts, and state clearly
which code and validation changed. It is not a new native build.
The generated package manifest is a receipt, excluded from Git and regenerated
when packaging a checkout extracted from a previous source archive.

Entries use fixed timestamps, sorted paths and fixed permissions for reproducible
packaging in the same toolchain. The source ZIP excludes `.git` and contains one
top-level `amiwind/` folder, ready to initialize as a Git repository.

Update `README.md`, `docs/PROJECT_STATE.md` and `docs/CHANGELOG.md` before a release.
Keep detailed format and design notes in their dedicated documents.

## Optional private development bundle

`tools/private_bundle.py` is a separate, explicit operation. It includes the
owner's configured original game folder, generated data and previews alongside
the validated source tree. It is not a public source release. For local use:

```sh
python tools/private_bundle.py --source-archive "../morrowind-amiga-workspace/releases/AmiWind-v0.0.16-public-source.zip" --workspace "../morrowind-amiga-workspace" --out "../morrowind-amiga-workspace/releases/AmiWind-v0.0.16-private-development.zip"
```

The source folder in that bundle is byte-identical to the public source package.
The original and converted data stay in a sibling workspace. The bundled setup
configuration omits machine-specific game paths; run `setup` after extraction.

For opening tests, install the optional `opening` dependencies (Pillow). The
historical checkpoint-005 host suite had 33 passing tests. Native checks are recorded in
CHECKPOINT_005_VALIDATION.md (earlier checks in OPENING_VALIDATION.md). `tools/package_opening.py` creates a compact private
opening bundle from `--source-archive`, `--build`, `--kickstart` and `--out`. It
validates the source archive, disk hashes and ROM checksum and uses a separate
candidate validation pass before writing a new, immutable ZIP. Supplying a ROM
to this explicit private operation includes it in that private package only.

## Preserve working features and alternatives

Do keep versioned checkpoints, original conversion recipes, previous font atlases,
and selectable implementation variants. Add experiments alongside the existing
path, compare them, and retain a documented fallback. This includes the readable
and retro fonts when adding an original-game-derived font, and 3D hands when
adding sprite hands. Store every derived commercial asset outside public source.

Do not destructively overwrite/remove a feature, asset recipe or alternative
merely to try an optimization or visual change. Keep this rule beyond the current
prototype. A deliberate future retirement needs an explicit migration decision,
not accidental replacement. Record what was actually tested and preserve failures.

Current acceptance at checkpoint-017:97 host tests passed with the actual native
source tree provided through AMIWIND_RUNTIME_SOURCE, plus the documented FS-UAE
checks. Earlier counts above belong to older checkpoints and are historical.

## Historical repository-consolidation checks

The complete native source is now included in engine/aga. Run the host suite with
`PYTHONPATH=src:tools python3 -m unittest discover -s tests -v` after installing
the documented dependencies. 113 tests passed locally. The ignored out/ directory
is never a source-release input. See CI_DRY_RUN.md for public CI and native test
compilation, BUILD_DEPENDENCIES.md for reference versions, and WINDOWS_BUILD.md
for Windows installation-path handling. Existing historical checkpoint evidence
is preserved; it is not replaced by the new test counts.

For current validation and first publication, see RELEASE-v0.0.16.md and
FIRST_RELEASE.md. The older private development bundle above is not the
required private playable package.


## Static scene walkability audit

Run the offline scanner against the converted BSP before native playtesting:

```sh
python tools/audit_walkability.py /path/to/census.bsp \
  --bounds 80 180 144 248 --height 75 --spacing 4 --drop 20 \
  --seed 128 208 --probe 127 206 75 --out /path/to/private/room-audit.json
```

Coordinates are native player origins, not raw TES3 coordinates or floor heights.
Scan one height band per floor. Probes return exit code2 when unsupported,
blocked or too steep; the JSON keeps all sample/reference evidence. The optional
seed follows supported neighbors within the step limit, checks intervening hulls,
and lists reachable fall/boundary candidates. Inspect doors and intentional
stairs before labeling those edges defects. This test excludes actor/script
states and visible mesh coverage; keep native walk and visual checks as gates.


## Geometry optimization principle: remove unnecessary runtime work

High-priority owner requirement: eliminate proven redundant or obstructing
geometry during conversion so the Amiga does not repeatedly transform, clip and
rasterize it. A visual layering fix alone does not meet this performance goal.
The first reference case is both exterior Census doors, including Seyda Neen
XYZ396,-171,39, yaw170,pitch-3: create a bounded, oriented door-shaped cut-out in
intruding wall geometry while preserving the aperture, frame and collision.

Keep the baseline and changed-face/reference report; measure native frame work
before claiming a speedup. This principle is recorded as journal J021, bug
AW-20260928-21, and high-priority graphics/culling roadmap work. The proposed
conversion option/tool is not yet implemented.

Planned doorway-assistance configuration: `door_priority=true` by default after
implementation/validation, false for baseline comparisons. Keep a safety margin
beneath the frame. Simplify concealed wall depth to a wall-coloured plane only
where this does not seal a revealed opening. No active switch is claimed yet.
Only the patch concealed by the door/frame may be reduced to the wall's base
colour or texture. Keep the visible wall's material, UVs and shape intact; do not
blank the surrounding wall. Confirm concealment from both sides and every
supported door state before removing geometry from the runtime asset.


## Something akin to Nanite, but on these old pieces of gear

Recovered post-dev4 research note. Treat this as an optimization experiment, not
a promised renderer feature.

AmiWind should prefer expensive **offline** analysis and cheap runtime choices.
Where useful, conversion may generate hierarchical/clustered geometry and several
immutable representations of the same terrain or structure. Runtime selection
may use distance, projected size, altitude, fog/visibility bounds and measured
resource budgets, but it must remain simpler than the work it avoids.

Do not add runtime mesh simplification to the Amiga. Preserve the unsimplified
source/baseline, deterministic conversion inputs, per-candidate change reports,
material/UV/silhouette constraints and collision independence. Distant detail may
become simplified geometry, baked texture detail, silhouettes or be omitted only
when the measured visual error and gameplay constraints allow it.

AmiQuake already provides strong BSP/frustum/edge machinery. Reuse that machinery
first. Any extra hierarchy, visibility hint or LOD selector needs matched native
profiling that includes its own bookkeeping, memory and cache cost. The proposed
`dbg fly 1` whole-world observer is the intended stress harness for these trials.

## Tables, tables, we need more tables

Owner requirement, 28 September 2026, 20:41 Helsinki: maintain a cross-system
catalogue of the parameters and conditional rules needed for the game. This is
planned coverage work, not a claim that all mechanics have been enumerated.

| Domain | Parameters and relationships to catalogue |
| --- | --- |
| Character | Race/sex/class/birthsign, base attributes, skills, derived statistics, current values and progression. |
| Effects and actions | Attribute/skill modifiers, duration, stacking/removal, action permissions, effect sources and recalculation dependencies. |
| Quests and scripts | Journal indices, globals, script locals, branch conditions, one-time outcomes, rewards and completion semantics. |
| NPCs and dialogue | Stable actor identity, placement, inventory, disposition, AI/action state, dialogue eligibility, speech/schedule timers and quest dependencies. |
| Containers and items | Base contents, placed-instance changes, loot/leveled-list rules, depletion/restocking, ownership, counts and moved/dropped item identities. |
| Doors and world references | Enable/disable state, locks, destinations, motion/collision state, moved/removed references and source-cell membership. |
| World and time | Clock, cell/region metadata, water/weather data, unloaded-state behavior and elapsed-time rules. |
| Persistence | Save-wide versus per-reference state, schema/content versions, limits, migration and load/recovery behavior. |

Each catalogue entry needs a stable key and source provenance; type, units,
range and default; who reads/writes it; trigger/condition/formula dependencies;
and whether it is immutable, derived, transient or saved. Record base-record
versus placed-reference scope explicitly. Unknown rules need a verification
entry, not an invented default presented as original behavior.

Cross-check owned source records/scripts and implementation references before
locking the schema. Keep original facts separate from compact runtime encoding
and UI stages. Generate lookup tables on the host where useful, budget resident
tables on the Amiga, and define bounded paging for larger catalogues. Reference
the same field definitions from conversion, game logic, save/load and tests so
container resets, repeated rewards or stale modifiers cannot arise from several
conflicting versions of the same state.


## Town import

Towns are converted from config files, not code: `tools/import_town.py --town
<id>` (Balmora, Vivec's Arena; `tools/prepare_balmora.py` is the unchanged
Balmora command line). The engine reads towns from the generated table
`engine/aga/src/aw_town_table.h`; regenerate it with `tools/town_table.py
--write` after changing `config/towns.json` or a town config. Every build
imports the towns a release ships (`shipped_since` in `config/towns.json`: the
Vivec Arena since v0.0.32); the builder adds a town not shipped yet with
`--extra-town <id>` and selects the vis pass with
`--vis {fast,full}` (vis threads follow `--jobs`). See
[TOWN_IMPORT.md](TOWN_IMPORT.md), [PARALLEL_BUILD.md](PARALLEL_BUILD.md#vis-threads-and-vis-mode)
and [performance/TOWN-VISIBILITY.md](performance/TOWN-VISIBILITY.md).

## World estimate

`tools/build_aga.py estimate --data-files <Morrowind> --out <dir>` (or
`./build.sh --data-files <Morrowind> --estimate-world <dir>`) estimates every
interior cell and exterior region of a whole-world import from your own files:
BSP sizes, heap, entities and every limit ratio, with charts, without
converting. `--sample-convert N` converts N maps to measure its error;
`estimate-calibrate` refits its coefficients from those conversions. See
[WORLD_ESTIMATE.md](WORLD_ESTIMATE.md).

## Mandatory delivery gate

ALWAYS CHECK FOR TRAILING WHITESPACE BEFORE POSTING AN AUTOMATED PUSH/PUBLISH
SCRIPT. Check the exact distributed helper, all changed/new source, and the
reconstructed archive. Run `git diff --check` and `git diff --cached --check`
before commit. Do not bypass a failed check. Preserve immutable issued archives;
use a new revision for a correction. The owner runs publication.

## Terrain coverage workflow

LAND/topomap alone is insufficient where placed rocks or structures cover the
ground. Audit source references, complete transforms and low-poly coverage before
patching a hole. Follow [What are rocks?](WHAT_ARE_ROCKS.md), including native
before/after views, compound-rotation tests and separate collision checks.

## Collision meshes

Morrowind keeps a model's collision inside its NIF: a `RootCollisionNode` under the root node,
otherwise the visible triangles, with root string flags for no collision (`NC`), camera-only
collision (`NCC`) and editor markers (`MRK`). Before changing collision or stairs, read
[Morrowind collision meshes](COLLISION_MESHES.md): the exact rules (OpenMW as reference),
measured counts, the stair findings, and which converter uses which collision source.

## Further terrain/detail direction — planned, not starting now

Continue the present conversion approach and add finer runtime sub-cell division
as measured high-cost regions, especially settlements, require it. Mark failing
heap/headroom regions and profile the actual payload before splitting; preserve
visibility/collision overlaps and gameplay continuity.

Future content follows a deliberate [world-detail/topology ladder](WORLD_DETAIL_LADDER.md):
rocks/mushrooms, trees/roots/stumps, marsh vegetation, early Seyda Neen shorelines,
terrain formations, paths/roads, natural entrances and regional sets. Keep
interactive micro-clutter separate. This is a future TODO, not current expansion
work; current release targets and heap/transition acceptance remain in force.

## Compiler diagnostics requirement

Add explicit configuration options for troubleshooting and record their effective
settings in build evidence. See [Compiler Troubleshooting](COMPILER_TROUBLESHOOTING.md)
for implemented tools, proposed controls and the production acceptance boundary.


## Emulator development access

See [FS-UAE development access](FS-UAE-DEVELOPMENT.md) for guest memory and
register inspection, breakpoints, serial-terminal access, save-state/capture
limits and a proposed repeatable testing workflow. Stock interfaces and optional
patched backends are distinguished; unattended runtime validation is pending.

## Headless development container

See [FS-UAE in Docker](FS-UAE-DOCKER.md) for a persistent container,
private virtual display, screenshots, console debugger and backup steps.
