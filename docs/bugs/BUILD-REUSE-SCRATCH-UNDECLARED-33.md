# BUILD-REUSE-SCRATCH-UNDECLARED-33: A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | Stage output recorder (tools/build_cache.py RUN_PRIVATE, Recorder.after) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.33 |
| Severity | high: Every reuse of a run made since the scratch folder: the first stages and every stage after them run again (about 1,427 s of conversion in the rc1c rerun). |
| Family | Build speed (`build-speed`) |
| Playtest version | v0.0.33-rc1 builds rc1b and rc1c |
| From commit | source a266a40, engine a266a40, CHIM world a266a40 |
| CHIM engine version | CHIM 0.1.0, engine a266a40, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-reuse-scratch, not shipped at the time of writing.

Provenance: found reading the stage-cache records of the v0.0.33-rc1 builds rc1b (source 27058ec) and rc1c
(source a266a40, built with `--reuse-from` rc1b and `--allow-release-reuse`).

## Symptom

rc1c was a rerun of rc1b after a one-file fix in the image step. Its build state listed one reused stage
(setup) and "old outputs not reusable: created run-folder entries outside every declared stage path: scratch"
for terrain, dialogue-lookup, world-survey, world-scenery-assets and music. Every stage after them was then
refused because "an earlier stage it depends on ran again and its outputs differ from the old run". The whole
conversion ran again: about 1,427 s before the image step started.

## Where

`tools/build_cache.py`: `RUN_PRIVATE` (run-folder entries that belong to no stage) and `Recorder.after`,
which marks a stage non-reusable when a new top-level run-folder entry belongs to no declared stage path.

## How it happened

BUILD-TMP-SCRATCH-33 gave every stage the scratch folder RUN/scratch (`build_scratch.stage_environment`).
It is created by the first stage that needs scratch space, so it appears in the window of every stage running
at that moment; the recorder counted it as their undeclared output. Those stages were recorded non-reusable,
and a later build cannot use them or prove that a rerun made the same outputs (BUILD-CACHE-NO-CUTOFF-33),
so every dependent stage ran again too. The outputs themselves were identical: terrain 8 of 8 files, music
19 of 19 and media 7,185 of 7,185 match between rc1b and rc1c.

## Why it was not caught

The scratch helper and the reuse recorder were tested apart: no test started a stage with the builder's
stage environment and then checked its manifest. The reuse tests ran without RUN/scratch, and the rc builds'
reuse counts were not compared with the expected stage list.

## Reproduction

Build once, then build again with `--reuse-from` that run: the stages that ran when RUN/scratch first
appeared are listed as not reusable, and every stage after them runs again.

## Repair

RUN/scratch is run-private (`RUN_PRIVATE`). Records written by the old code are read through
`build_cache.requalify`: a manifest whose only reason not to be reused is exactly the scratch entry is
reusable again; its fingerprint and the same-output checks apply as for any other stage, and any other
reason still refuses reuse. Read against the real records: rc1b 33 of 33 conversion stages reusable (7
requalified), rc1c 33 of 33 (2 requalified); the image step is always assembled again.

## Verification

`test_the_builder_scratch_folder_is_not_an_undeclared_output` (fails without the repair) and
`test_old_records_refused_only_for_scratch_are_reusable` in tests/test_build_cache.py.

Measured on the v0.0.33 release builds (`--reuse-from`, same workspace): before the repair the release
candidate reruns reused 17, 18 and 25 of 34 stages, and every conversion stage that ran after the scratch
folder appeared was refused even when its outputs were byte-identical. A read-only re-check of those records
with the repaired loader finds all 33 conversion stages reusable. The v0.0.33 final image, built with the
repair from the last release candidate, reused 30 of 34 stages; the four that ran: `engine` (compiled with
the Amiga SDK, whose files are not fingerprinted, about 15 s), `harvest` and `chim` (their sources include
`tools/release-files.json` and `VERSION`, which the version change touches) and `image` (always assembled
and verified from the stage outputs).

## Prevention

The first test takes the scratch folder's name from `build_scratch.stage_environment` itself, so a moved or
renamed scratch folder fails it. A related open finding: BUILD-SURVEY-NOT-REPRODUCIBLE-33.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
