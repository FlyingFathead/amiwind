# BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64: The reuse report counts a stage's whole stored unit group as rebuilt even when the stage makes no units (world-flora: 1931 of 1931 while it converted 0 regions)

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.66-dev3 at 2026-11-15 01:54 +0200: Seen again on the v0.0.66-dev3 line: the unit check stopped world-scenery (2064 of 2064) and world-flora (1931 of 1931) as baking again, while neither converts a region (every region is a CHIM cell). Their stage keys moved only by the table of earlier unit keys; they are taken through PROVEN_EQUAL_SOURCES (BUILD-STAGE-KEY-EQUAL-EDITS-66), so the stop does not come up, but the count itself is unchanged.
- Reported with v0.0.66-dev3 at 2026-11-15 06:12 +0200: Seen again on the v0.0.66-dev3 line: the unit check of c0ab8f11 against the stopped v0.0.66-dev3 try2 run planned 46 of 48 stages for reuse, world-scenery and world-flora among them, yet stopped both for the 2,064 and 1,931 stored units of their caches: a stage that does not run is counted as baking again.
- Reported with v0.0.66-dev5 at 2026-11-15 12:29 +0200: Seen again on the v0.0.66-dev5 line: the unit check of 18eb63f1 stopped world-scenery (2,064 of 2,064) and world-flora (1,931 of 1,931) as baking again, while neither stage converts a region; the stored group of older key forms was counted. Each snapshot needed an allowance with a proof.
- Reported with v0.0.66-dev6 at 2026-11-15 14:23 +0200: Seen again on the v0.0.66-dev6 line: the unit check of 00dfab13 stopped world-scenery (2,064 of 2,064) and world-flora (1,931 of 1,931) although the first repair was in it. Cause found: the check planned the world terrain, scenery and flora commands without the exterior checklist the build binds to them, so the three stages read as changed and were counted as rebuilt; the build reused them.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 November 2026, in v0.0.64-dev3 |
| Where | the builder's reuse report (stage unit counts), world-flora stage |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.67-dev3 |
| Severity | high: Regressed in v0.0.67-dev2 (was medium): a wrong count hides which stages really rebuilt and sends the reuse review after work that never ran; the build outpu... |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Fix commit | `c534a39c` |
| Fixed on | 2026-11-18 |
| Planning item | `BUILD-REUSE-STOP-STORED-GROUP-FIX-66` |
| Came back (regression) | in v0.0.67-dev2 (fixed in v0.0.66-dev8 before) |
| Playtest version | 2026_11_10_v0.0.64-dev3_full-v0.0.64-dev3_bf2743f |
| From commit | source bf2743f, engine bf2743f, CHIM world bf2743f |
| CHIM engine version | CHIM unknown, engine bf2743f, world format unknown |
| Unknown because | a count in the reuse report; the CHIM version and format do not bear on it |
| Build note | the reuse report said world-flora rebuilt 1931 of 1931 units while the stage converted 0 regions: the count comes from the stored unit group, not from the units the stage made |
| Platform or emulator | not in game (a builder report count) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | developer | v0.0.67-dev2 (tools/reuse_all.py region_limits) | 2026-11-18 | when the terrain stage runs again, the limit comes from this build's exterior checklist, made before any stage: with no cell that gets an open-world map the region stages look up none of their stored units; tests/test_reuse_all.py holds the case and the cases that still count in full | the checklist already says what the terrain receipt will hold |
| shipped | a development build | v0.0.67-dev3 (a375b13f) | 2026-11-19 | the fix commit c534a39c (tools/reuse_all.py) is an ancestor of the delivered dev3 head a375b13f and not of the dev2 head | the dev3 build holds the stop that takes its limit from this build's exterior checklist when the terrain stage runs again |
| confirmed by a test | a test module | v0.0.67-dev3 (a375b13f) | 2026-11-19 | tests/test_reuse_all.py (the case of a terrain stage that runs again and the cases that still count in full) and tests/test_exterior_layer_cells.py, run by gate 11450 on a375b13f | a builder-only fix, so no play check applies: the tests fail on the earlier counting and pass on the fix |
| confirmed by a build | a development build | v0.0.67-dev3 (a375b13f) | 2026-11-19 | the check of the dev3 build 2026_11_19_v0.0.67-dev3_full-dev3_a375b13: "Reuse check (--check): passed (no reuse stop)", world terrain, world scenery and world flora planned as reused from the earlier build with no allowance | the stop did not come back on the build that holds the fix (that build's terrain stage was reused, so the test above carries the case of a terrain stage that runs again) |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-10: reported in v0.0.64-dev3
- 2026-11-15: Before the regression: fixed in source, v0.0.66-dev8 (56901b8d) (a gated commit; gate 10910 passed on 3a64d00e, which holds it: the build check plans the same commands as the build, so the unit stop counts only the regions a stage converts)
- 2026-11-15: Before the regression: shipped, v0.0.66-dev8 build 2026_11_15_v0.0.66-dev8_full-v0.0.66-dev8_3a64d00 (a numbered build; the delivered build: the build holds 56901b8d)
- 2026-11-15: Before the regression: confirmed by a build, v0.0.66-dev8 build 2026_11_15_v0.0.66-dev8_full-v0.0.66-dev8_3a64d00 (a numbered build; the build's reuse check of 3a64d00e: world terrain, scenery and flora were planned as reused from the ...
- 2026-11-15 01:54 +0200: seen again in v0.0.66-dev3: Seen again on the v0.0.66-dev3 line: the unit check stopped world-scenery (2064 of 2064) and world-flora (1931 of 1931) as baking again, while neither converts a region (every region is a CHIM cell).
- 2026-11-15 06:12 +0200: seen again in v0.0.66-dev3: Seen again on the v0.0.66-dev3 line: the unit check of c0ab8f11 against the stopped v0.0.66-dev3 try2 run planned 46 of 48 stages for reuse, world-scenery and world-flora among them, yet stopped both for the 2,064 and 1,931 stored units of ...
- 2026-11-15 12:29 +0200: seen again in v0.0.66-dev5: Seen again on the v0.0.66-dev5 line: the unit check of 18eb63f1 stopped world-scenery (2,064 of 2,064) and world-flora (1,931 of 1,931) as baking again, while neither stage converts a region; the stored group of older key forms was counted.
- 2026-11-15 14:23 +0200: seen again in v0.0.66-dev6: Seen again on the v0.0.66-dev6 line: the unit check of 00dfab13 stopped world-scenery (2,064 of 2,064) and world-flora (1,931 of 1,931) although the first repair was in it.
- 2026-11-18: came back in v0.0.67-dev2 (fixed in v0.0.66-dev8 before): Seen again in the check of a build that holds Mournhold's districts: their eleven rows in the region directory make the world terrain stage run again, so its receipt could not be read, and the plan counted all 2,064 stored world scenery ...
- 2026-11-18: fixed in source: developer, v0.0.67-dev2 (tools/reuse_all.py region_limits); when the terrain stage runs again, the limit comes from this build's exterior checklist, made before any stage: with no cell that gets an open-world map the region stages look up none of their stored units; tests/test_reuse_all.py holds the case and the cases that still count in full: the checklist already says what the terrain receipt will hold
- 2026-11-19: shipped: a development build, v0.0.67-dev3 (a375b13f); the fix commit c534a39c (tools/reuse_all.py) is an ancestor of the delivered dev3 head a375b13f and not of the dev2 head: the dev3 build holds the stop that takes its limit from this build's exterior checklist when the terrain stage runs again
- 2026-11-19: confirmed by a test: a test module, v0.0.67-dev3 (a375b13f); tests/test_reuse_all.py (the case of a terrain stage that runs again and the cases that still count in full) and tests/test_exterior_layer_cells.py, run by gate 11450 on a375b13f: a builder-only fix, so no play check applies: the tests fail on the earlier counting and pass on the fix
- 2026-11-19: confirmed by a build: a development build, v0.0.67-dev3 (a375b13f); the check of the dev3 build 2026_11_19_v0.0.67-dev3_full-dev3_a375b13: "Reuse check (--check): passed (no reuse stop)", world terrain, world scenery and world flora planned as reused from the earlier build with no allowance: the stop did not come back on the build that holds the fix (that build's terrain stage was reused, so the test above carries the case of a terrain stage that runs again)

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev8 (15 November 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Timeline](#timeline)
- [Status: 15 November 2026](#status-15-november-2026)
- [Symptom](#symptom)
- [Where](#where)
- [Cause](#cause)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 15 November 2026

Open. Both causes are fixed in source (the first on the v0.0.66-dev6 line, the second on the v0.0.66-dev8 line); fixed in
source, to be confirmed by the v0.0.66-dev8 unit check, which runs without the per-stage allowances for the world scenery
and world flora stages. The entry stays open until that check has run. Seen in v0.0.64-dev3, twice on the v0.0.66-dev3
line and again on the v0.0.66-dev5 and v0.0.66-dev6 lines (the reports above).

## Symptom

The builder's reuse report and its unit check count every unit stored in a stage's cache as baking again, even when the
stage makes no units at all:

- v0.0.64-dev3: the reuse report said world-flora rebuilt 1,931 of 1,931 units while the stage converted 0 regions.
- v0.0.66-dev3 line: the unit check stopped world-scenery (2,064 of 2,064) and world-flora (1,931 of 1,931) as baking
  again, while neither converts a region (every region is a CHIM cell).
- v0.0.66-dev3 head (c0ab8f11): the unit check against the stopped v0.0.66-dev3 build planned 46 of 48 stages for
  reuse, world-scenery and world-flora among them, and still stopped both for the 2,064 and 1,931 stored units of their
  caches.

A stage that does not run is counted as baking again, so the count sends the reuse review after work that never runs.
The build output itself is not wrong.

## Where

The builder's reuse report and unit check (stage unit counts), the world-scenery and world-flora stages.

## Cause

The unit stop (tools/reuse_all.py strict_problems) compares the units a stage's unit cache holds with the units found
under this build's key, for every stage the plan runs. For the world scenery and world flora stages the cache holds one
unit per region of every earlier key form (2,064 and 1,931 regions, stored while the regions were still converted),
but a region that is a CHIM region cell or a routing-only row gets no map from these stages
(`prepare_world_scenery.prepare`, `prepare_world_flora`: the regions to convert are those without a CHIM cell or routing
mark in the terrain stage's receipt). Every region is a CHIM cell on this line, so the stages convert none, and the stop
still counted the whole stored group as baking again. A stage that the plan takes from an earlier build is never in the
stop's list; the unit check of a snapshot nevertheless listed these two as running, so the count mattered every time.

Second cause (found 15 November 2026 on the v0.0.66-dev6 line): the check plans different commands from the build. The
build binds the exterior checklist to its world terrain, world scenery and world flora commands (`--exterior-plan`) and
the terrain folder to the image command (`--exterior-terrain`) before it prepares the stages (tools/exterior_plan.py
`bind_steps`); the check (tools/build.py `unit_stop_check`) built the same commands without that step. Against every
earlier build the three stages therefore read "changed: command", the check's plan ran them, and the unit stop counted
the units stored in the two region caches. The build itself bound the commands, matched the earlier keys and reused all
three. The first repair below also cut nothing in that check: its region count is read from the terrain stage's
receipt when the plan takes that stage from an earlier build, and in the check the terrain stage was itself planned to
run again, so the full stored count stayed. The reuse preflight line the check prints beside it ("46 of 48 stages
reusable") comes from a separate prediction made from the earlier build's own recorded commands, which is why it
disagreed with the plan.

## Repair

The unit report counts, for the world scenery and world flora stages, at most the regions the stage converts: when the
plan takes the terrain stage from an earlier build, its receipt is read there and the held and found counts are cut to
the regions without a CHIM cell or routing mark (`reuse_all.region_limits`, `unit_report(limits=...)`). With every
region a CHIM cell the stage has 0 units to bake and no stop; a stage that does convert regions, a terrain stage that
runs again or an unreadable receipt keeps the full count and the 5 % limit. Tested in tests/test_reuse_all.py
(StoredGroupOfRegionStages: the 2,064 and 1,931 unit case, a stage taken from an earlier build, a stage that makes
regions, a terrain stage that runs again).

Second repair: the check binds the exterior checklist to the same commands before it plans them, exactly as the build
does (`unit_stop_check` calls `exterior_plan.bind_steps` when the build has an exterior checklist), so its plan matches
the build's and the three stages read as reused. The whole output of the build check is also kept in a file beside the
result (`RUN.check.log`); the refusal and the result carry only its last 40 lines, which
had lost the plan line of a stopped stage. Tested in tests/test_check_unit_stops.py (the check plans the bound commands,
a check without a checklist plans them as they are, the whole output is kept).

## Verification

Replayed read only against the v0.0.66-dev5 build with the v0.0.66-dev6 source: before the second repair the check plans
43 of 48 stages for reuse (world terrain, world scenery and world flora rebuilt) and stops the two region stages; with
the bound commands it plans 46 of 48 (engine and image only) and passes with no allowance for either stage. Pending: the
unit check of v0.0.66-dev8 passes with no allowance, and its plan lines read "reused" for the three stages.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47](BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): The actor-library stage stopped at once: run as a script, tools/mwad.py hid the src/mwad package
- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CACHE-PROVENANCE-41](BUILD-CACHE-PROVENANCE-41.md): Some cache entries record no time or no versions: pool keys from CHIMport have empty versions and commit, world-terrain units and stage records have no creation time or version
- [BUILD-CACHE-PROVENANCE-GROWTH-54](BUILD-CACHE-PROVENANCE-GROWTH-54.md): chim-units/.provenance is one append-only 8.8 GB file; its growth per build is not measured
- [BUILD-CELL-PROGRESS-ENGINE-KEY-48](BUILD-CELL-PROGRESS-ENGINE-KEY-48.md): The tracker data stage (cell-progress) counted every engine source in its key: an engine-only edit rebuilt it
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHECK-READONLY-WORKSPACE-67](BUILD-CHECK-READONLY-WORKSPACE-67.md): tools/build.py --check cannot check the reuse plan of a workspace that is mounted read-only: its build preflight stops on the cache folders it cannot write before the reuse plan is made
- [BUILD-CHECK-UNIT-STOPS-MISSING-66](BUILD-CHECK-UNIT-STOPS-MISSING-66.md): The build check passes while the build itself stops at its first-minute unit-cache reuse stop
- [BUILD-CHIM-HEAP-KEY-LOADER-63](BUILD-CHIM-HEAP-KEY-LOADER-63.md): An engine model loader edit re-keys the whole CHIM world and its interiors
- [BUILD-CHIM-KEY-ARRIVAL-SPOT-REACH-67](BUILD-CHIM-KEY-ARRIVAL-SPOT-REACH-67.md): The converted world stage is keyed by the arrival search's Python mirror, so a change there would convert the whole outdoor world again (about 27 minutes)
- [BUILD-CHIM-KEY-ENGINE-FILE-WHOLE-54](BUILD-CHIM-KEY-ENGINE-FILE-WHOLE-54.md): chim_world.c is keyed whole into the CHIM world, so a diagnostic print re-keys the world
- BUILD-CHIM-KEY-ENGINE-SOURCES-49 (no report page): An engine source edit rebuilds the whole CHIM world: the CHIM stage imports project_version, whose engine check names engine/aga/src files
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-CHIM-KEY-VERSION-48](BUILD-CHIM-KEY-VERSION-48.md): The CHIM world and cell-progress stages key on VERSION, so a version-only bump (rc to final) rebuilds the whole CHIM world
- [BUILD-CHIM-LABEL-IN-KEYS-48](BUILD-CHIM-LABEL-IN-KEYS-48.md): The CHIM version label was in the stage keys: the x.x.1 release step rebuilt about 25 stages, the CHIM world among them
- [BUILD-CHIM-RECORD-COMPILER-INCOMPLETE-51](BUILD-CHIM-RECORD-COMPILER-INCOMPLETE-51.md): The chim stage's read record is always incomplete: it starts compilers with checkout paths, so it can never be reused when only its key's sources changed
- BUILD-CHIM-VIS-RECOMPUTED-48 (no report page): The CHIM stage recomputed every region frame's visibility (1 h 20 min on 24 cores)
- [BUILD-CREATURE-KEY-REASON-TEXT-66](BUILD-CREATURE-KEY-REASON-TEXT-66.md): The creature models' unit key counts the whole interior creature list, so a reworded reason text of one row re-keyed all 97 stored models
- [BUILD-CUTOFF-WHOLE-ANCESTOR-51](BUILD-CUTOFF-WHOLE-ANCESTOR-51.md): An interior light change reran exterior stages: the reuse cutoff refuses a stage when any earlier stage's whole output differs, not the files it reads
- [BUILD-DEV-GALLERY-SKIP-RC-REBUILD-48](BUILD-DEV-GALLERY-SKIP-RC-REBUILD-48.md): Development builds leave out the NPC gallery, so every release candidate builds all 3,551 faces fresh
- [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md): The cell-progress stage was never reusable: it reads the CHIM stage's statistics report, which counted as a forbidden diagnostic read
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-FLORA-RECEIPT-SECONDS-36](BUILD-FLORA-RECEIPT-SECONDS-36.md): The world flora receipt held the stage's wall time, so a rerun with the same inputs never wrote the same receipt
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- [BUILD-GAME-INPUT-KEY-BROAD-64](BUILD-GAME-INPUT-KEY-BROAD-64.md): Every stage that reads the game data was keyed by every game input, so an expansion file being present re-keyed the base world
- [BUILD-IMAGE-LAYOUT-SERIAL-49](BUILD-IMAGE-LAYOUT-SERIAL-49.md): The image step plans its disk layout and writes its partitions on about 1.6 of 24 cores for about three minutes
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
- [BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68](BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68.md): Since the CHIM source catalogue cache, the base world's CHIM stage is keyed by the expansions' masters and archives and their selection, so an expansion change rebuilds the whole base world
- [BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md): Adding a function to a shared module changed the key of every stage that imports it, although no stage runs the new code
- [BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68](BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68.md): One new row in the expansions' grounding id file re-keys the base world stage and the Mournhold module, though neither reads it
- BUILD-KEY-KEYED-REACH-WHOLE-51 (no report page): Code handed to an in-stage cache key counted whole in the stage key: a helper added to tools/map_files.py rebuilt the CHIM world
- [BUILD-KEY-MESH-TABLE-WHOLE-54](BUILD-KEY-MESH-TABLE-WHOLE-54.md): A per-mesh measured table is keyed whole: one new row of collision-standing-room.json re-keyed every room, resident and model unit
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- BUILD-KEY-RULE-NO-FORM-51 (no report page): A change of the stage key rules without a new key form rebuilt stages whose inputs did not change
- [BUILD-KEY-UNIT-RESTORED-CODE-52](BUILD-KEY-UNIT-RESTORED-CODE-52.md): A stage whose last real run restored its units from a cache was reused after the code those units come from changed: chim-room-batches kept actor models of the old animation tables
- [BUILD-MINIWIND-REUSE-STALE-57](BUILD-MINIWIND-REUSE-STALE-57.md): The MiniWind build launcher reused the v0.0.53 final run instead of the newest passed run
- [BUILD-MODULE-UNIT-CACHE-IN-KEY-67](BUILD-MODULE-UNIT-CACHE-IN-KEY-67.md): The stage of Mournhold's districts was keyed by its own unit cache folder: the units a run stored re-keyed the stage for the next run
- BUILD-MWSCRIPT-KEY-UNDERDECLARED-48 (no report page): The mwscript stage's reuse record is refused: the stage reads tools/mwscript/measure.py, which its fingerprint leaves out
- BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59 (no report page): The mwscript stage was reused after its compiler changed, so v0.0.59 ships compiled scripts of an older compiler
- [BUILD-NPC-BAKE-CACHE-KEY-40](BUILD-NPC-BAKE-CACHE-KEY-40.md): New NPC shell fallback dependencies are absent from the model cache key
- [BUILD-OUTPUTS-NOT-REPRODUCIBLE-33](BUILD-OUTPUTS-NOT-REPRODUCIBLE-33.md): A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt
- [BUILD-PASS-KEY-OVERBROAD-36](BUILD-PASS-KEY-OVERBROAD-36.md): Image-pass and unit cache keys changed with code no pass runs: a new function in a shared module and edits to the cache's own key code rekeyed every character head preview twice (Vivec stage A try2 and try3: 275 of 275 recomputed)
- [BUILD-PASS-KEY-RULE-NO-CARRYOVER-36](BUILD-PASS-KEY-RULE-NO-CARRYOVER-36.md): A pass key rule change carried no entries written by older trees: dev4 recomputed 2,372 optimizer maps and the exterior sky maps with code and outputs identical to dev3
- [BUILD-POOL-APPLY-READ-MISS-35](BUILD-POOL-APPLY-READ-MISS-35.md): In a pool-mode build every reused stage was refused as the next reuse source: the reuse step's read of tools/storage_pool.py counted as a stage input
- [BUILD-POOL-ARG-UNFINGERPRINTED-35](BUILD-POOL-ARG-UNFINGERPRINTED-35.md): The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- BUILD-PREFLIGHT-CELL-PROGRESS-VERSION-49 (no report page): The reuse preflight calls the tracker data stage (cell-progress) an unexpected VERSION-only rebuild, though its outputs name the release derived from VERSION
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-APPLY-SERIAL-49](BUILD-REUSE-APPLY-SERIAL-49.md): Reusing a stage links its cached files on about one core: 34,306 files took 1.4 minutes at the start of a version-only build
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-AUDIT-WITHOUT-REASON-36](BUILD-REUSE-AUDIT-WITHOUT-REASON-36.md): The reuse audit and preflight called a stage rerun because its old record was short a replaced file UNEXPECTED, although the reason explains it
- [BUILD-REUSE-CASCADE-36](BUILD-REUSE-CASCADE-36.md): A fix in CHIM-native town code made 23 of 36 stages rebuild: the interior stage reran with different outputs and 5 rebuilds were unexpected
- [BUILD-REUSE-CHAIN-ABSENT-STAGE-68](BUILD-REUSE-CHAIN-ABSENT-STAGE-68.md): A build that reuses a run rebuilds the stages that run had itself taken from an earlier run, because they are not stored in it
- [BUILD-REUSE-CUTOFF-MODE-36](BUILD-REUSE-CUTOFF-MODE-36.md): Early cutoff compared file modes with their write bits: a stage reused by hard link (read-only) never matched the same bytes written fresh, so 10 stages after dev3's bsp rerun were refused
- BUILD-REUSE-FOREIGN-DIRS-52 (no report page): A reused stage recreates, as empty folders, the folders another stage filled beside it: the area stage then stops on its own room folder
- [BUILD-REUSE-INTRO-CENSUS-REPLACED-48](BUILD-REUSE-INTRO-CENSUS-REPLACED-48.md): A reused MiniWind rooms build rebuilt the intro and census stages (replaced outputs) and its Balmora interiors (4 s to 1m21s)
- BUILD-REUSE-KEY-WALK-LISTED-51 (no report page): The read records of the CHIM world stages list almost every folder of the checkout, so a new bug page refuses their narrowed reuse
- [BUILD-REUSE-NEVER-READ-STOPS-66](BUILD-REUSE-NEVER-READ-STOPS-66.md): The reuse check stops stages whose key changed only in code they never ran or read, and redoes their stored units
- BUILD-REUSE-OUTPUTS-DIFFER-48 (no report page): Eight stages were rebuilt because their earlier outputs differed from their records (character, reading, world-ui, actor-contact, world-terrain and others)
- [BUILD-REUSE-PLAN-ENV-36](BUILD-REUSE-PLAN-ENV-36.md): The standalone reuse plan reports environment changes the real build does not have
- BUILD-REUSE-RC1-RECORDS-REFUSED-48 (no report page): Every stage that ran the idle-worker watcher or read the CHIM label module was marked not reusable: rc1-try2 had 24 unexpected rebuilds
- [BUILD-REUSE-RECORD-RETIRED-36](BUILD-REUSE-RECORD-RETIRED-36.md): Early cutoff and the reuse audit lost their records when an older run was retired: stages with byte-identical outputs counted as changed
- [BUILD-REUSE-REDUCED-RECORD-36](BUILD-REUSE-REDUCED-RECORD-36.md): A stage reused from a run that had itself reused it came back without the files a later stage replaced there, so that later stage failed when it ran again
- [BUILD-REUSE-SCHEDULER-TOP-45](BUILD-REUSE-SCHEDULER-TOP-45.md): A scheduler-only edit rekeys every stage, NPC gallery face and stair walk that reaches tools/build_parallel.py
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-REUSE-STOPPED-SOURCE-52](BUILD-REUSE-STOPPED-SOURCE-52.md): Reusing a build that stopped early reruns every stage it never reached, though the build it reused holds them
- [BUILD-REUSE-TMP-RECORDED-DELETED-48](BUILD-REUSE-TMP-RECORDED-DELETED-48.md): A reused stage removed another stage's reuse copies mid-copy: its record listed them as deleted (balmora-interiors stopped at os.replace)
- [BUILD-ROOM-ACTOR-FORECAST-WRONG-67](BUILD-ROOM-ACTOR-FORECAST-WRONG-67.md): The build check forecast every room actor fit from the unit cache; the image step then fitted 2,533 of 2,594 again, 22 min 44 s
- [BUILD-ROOM-ACTOR-INPUT-RECORD-67](BUILD-ROOM-ACTOR-INPUT-RECORD-67.md): The room actor fit's unit inputs leave out the room record's placements: a placement moved, turned or given another store model in a room whose map and store models are unchanged would take a stale fit from the unit cache
- BUILD-ROOM-BATCHES-KEY-UNDERDECLARED-48 (no report page): The room stage's reuse record is refused: it reads 17 repository files its fingerprint leaves out
- BUILD-ROOM-BATCHES-SCENE-RACE-48 (no report page): A reused build stopped in the room stage: it ran before the area stage had restored the scene map it reads (seyda.bsp)
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SEYDA-BOUNDED-RUN-PATHS-36](BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): The actor-contact stage wrote its run folder path into 67 Seyda Neen region records, so its outputs differed in every run folder
- [BUILD-SHARED-WRITES-UNATTRIBUTED-52](BUILD-SHARED-WRITES-UNATTRIBUTED-52.md): Stages running side by side write the same files, so their records are refused and they rebuild every time: the town carried-item models, the room door audio
- [BUILD-SPRITE-KEY-HASHLIB-47](BUILD-SPRITE-KEY-HASHLIB-47.md): The CHIM stage failed 45 minutes into a build: the sprite recipe key used hashlib without importing it
- BUILD-STAGE-KEY-CLIENT-H-58 (no report page): An engine declaration added to client.h re-converts the CHIM world and its interiors
- [BUILD-STAGE-KEY-EQUAL-EDITS-66](BUILD-STAGE-KEY-EQUAL-EDITS-66.md): A stage whose key moved only by edits that change none of its outputs ran again in full, about 31 minutes of CHIM world
- BUILD-STAGE-KEY-TEXT-DEFINES-59 (no report page): The CHIM world and CHIM rooms stages rebuild when tools/text_defines.py changes, although the world does not use the text macros
- [BUILD-STAGE-KEY-UNIT-STORE-63](BUILD-STAGE-KEY-UNIT-STORE-63.md): Five stage keys count the unit store code as a whole file, so one reuse table row rebuilds them
- BUILD-STAGE-KEY-WHOLE-CLASS-48 (no report page): A one-method edit in tools/actor_grounding.py rekeyed the CHIM stages: a class was import-time code of its module, so every stage importing the module hashed every method
- [BUILD-STAGE-READS-UNFINGERPRINTED-48](BUILD-STAGE-READS-UNFINGERPRINTED-48.md): Two stages read repository files their fingerprint leaves out, so their records are refused and they rerun on every reuse
- [BUILD-STAGE-WRITES-OTHERS-OUTPUT-63](BUILD-STAGE-WRITES-OTHERS-OUTPUT-63.md): A failed image step wrote into a file another stage owns, so resuming rebuilt Vivec city (11 min), the actor library (40 min) and the Vivec rooms (28 min)
- [BUILD-STAIR-KEY-BOOKKEEPING-36](BUILD-STAIR-KEY-BOOKKEEPING-36.md): Stair walk keys count the progress lines (stair_progress.py) and the record bookkeeping (stair_records.py): an edit to either rekeys every walk
- [BUILD-STAIR-PASS-NOT-KEPT-41](BUILD-STAIR-PASS-NOT-KEPT-41.md): A frame's passed stair walk is not reused when the build it ran in failed, and the walker key changes with converter code
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-TABLE-UNITS-REBAKE-63](BUILD-TABLE-UNITS-REBAKE-63.md): Every build bakes the dialogue and voice tables and the actor ground check again
- [BUILD-UNIT-KEYS-LAYER-BLIND-66](BUILD-UNIT-KEYS-LAYER-BLIND-66.md): Unit cache keys do not change with the selected expansion layers: an expansions-on build would reuse base-game units
- [BUILD-VERSION-GETATTR-TRACE-49](BUILD-VERSION-GETATTR-TRACE-49.md): The v0.0.49 final rebuilt the CHIM world: the lazy VERSION (a module __getattr__ in project_version) ran in the CHIM stage, its read trace recorded it and the key could not
- [BUILD-VISUAL-RECIPES-LAYER-ROWS-KEY-67](BUILD-VISUAL-RECIPES-LAYER-ROWS-KEY-67.md): An expansion's visual recipe or cell row re-keyed every base stage that reads the visual recipes: the file was keyed whole
- [CACHE-NO-PROVENANCE-36](CACHE-NO-PROVENANCE-36.md): Cache and pool entries were keyed by SHA-256 but did not record when, by which run, from which version and commit they were made, and some recorded no output hash
- [CHIM-COLLISION-UNION-FAIL-NOT-CACHED-48](CHIM-COLLISION-UNION-FAIL-NOT-CACHED-48.md): A collision union that fails is compiled again for every room that uses the same mesh packet
- [CHIM-INTERIORS-REUSE-MISS-48](CHIM-INTERIORS-REUSE-MISS-48.md): The CHIM rooms stage (chim-interiors) is never reused: it hashed the shared CHIM unit cache, which is past the 512 MiB folder limit
- [CHIMPORT-CELL-KEY-LAYERS-65](CHIMPORT-CELL-KEY-LAYERS-65.md): Selecting the expansion layers re-keys every CHIMport cell of the island
- [CHIMPORT-CELL-KEY-REQUEST-ID-67](CHIMPORT-CELL-KEY-REQUEST-ID-67.md): The CHIM import keys every cell by the master builder request that runs it
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [CHIMPORT-POOL-CROSS-MOUNT-36](CHIMPORT-POOL-CROSS-MOUNT-36.md): CHIMport run folder and the storage pool on two mounts of one volume: hard links fail across the mounts, so pooled units were copied, not linked
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- [CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68](CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68.md): A build module's world stage converts again every unit a CHIMport run already made for the same cells
- [DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68](DELIVER-RESUME-NEW-COMMIT-NO-SOURCE-68.md): A delivery resumed on an earlier finished build for a newer commit stops because that commit's source export does not exist
- [DOOR-CHECK-KNOWN-UNKEYED-54](DOOR-CHECK-KNOWN-UNKEYED-54.md): config/door-check-known.json is in no stage key: an edit to the known list never re-runs a passed image's door check
- [K-BACKUP-RUN-COPY-SYMLINKS-68](K-BACKUP-RUN-COPY-SYMLINKS-68.md): Archiving a superseded build run to the archive drive fails for runs that hold symbolic links
- [MESH-TABLE-LAYER-GROWS-67](MESH-TABLE-LAYER-GROWS-67.md): A row added to an expansion layer of a measured mesh table would re-key every unit recorded with that layer's earlier rows
- [MESH-TABLE-SECOND-LAYER-REKEY-67](MESH-TABLE-SECOND-LAYER-REKEY-67.md): A row of a second expansion in a measured mesh table would re-key every unit recorded with the first expansion's rows
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order
- [READY-STAGE-REACH-BY-RULE-68](READY-STAGE-REACH-BY-RULE-68.md): A merge note stated the build stages a change re-keys from the rules, not from the planner's measured key, and a later file-list probe over-stated it
- [REUSE-STOP-OLD-GROUPS-67](REUSE-STOP-OLD-GROUPS-67.md): The strict reuse check counts the units an older version of a bake left in its cache as work the build would redo, so a one-unit table with history stops a build that would reuse it

Related bugs in other categories:

- [UNIT-KEY-WHOLE-FILE-63](UNIT-KEY-WHOLE-FILE-63.md): The resident and room unit caches keyed every unit on the whole of their tool files, so an unrelated edit to tools/prepare_area.py re-keyed all 1,769 residents and every room, and the v0.0.63-dev1 build baked them all again

<!-- END GENERATED CATEGORY -->
