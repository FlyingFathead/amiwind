# BUILD-REUSE-KEYS-TOO-BROAD-35: A whole build reused no stage, and the cost was not visible before the build started

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | Stage reuse planning and the NPC gallery model cache key (tools/build_cache.py, gallery_cache.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | medium: A build after a large merge reran every stage with no warning before it started, and the gallery model cache key left out modules its converter runs. |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 901f8e9 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
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

## Status: 10 October 2026

Repair in v0.0.35 development (not shipped).

## Symptom

The first v0.0.35 development build (source 901f8e9) ran with `--reuse-from` the v0.0.34 build and
`--reuse-mode pool`. It reused 0 of 35 stages, and the per-model NPC gallery cache reused 0 of 3,551
models. The build did not say so before it started: the per-stage reasons appeared only in
`build-state.json`, and the build log printed one rebuild line per stage with no summary.

## Where

- `tools/build_cache.py` and `tools/build.py`: no check of the reuse plan before the first stage, and
  no loud warning when (almost) nothing is reused.
- `tools/gallery_cache.py`: each gallery model's key held the whole-file SHA-256 of a fixed list of six
  source files.

## How it happened

Measured against the two runs' recorded fingerprints: every stage's own key changed, not only through
the stages it depends on. Sources changed in 35 of 35 stages (105 changed files from twelve merged
branches; the reached code of the converters changed, e.g. a new shared data-reader helper in
`src/mwad/esm.py` that every reader calls). Game inputs changed in 28 stages: the input lock now
lists the Tribunal and Bloodmoon masters and archives (the data-reader fixes widened what counts as a
game input). Environment changed in 21 stages: new settings (lava, the NPC root rule, the stair walk)
that new code reads. Every one of these is a real input change, so no stage could safely be reused,
and the early cutoff that already exists (BUILD-CACHE-NO-CUTOFF-33: a stage whose own key is
unchanged is reused when the stages before it write the same outputs again) had nothing to work on.

The gallery model key had two faults. It was too broad: an edit anywhere in `src/mwad/audit.py` or
`src/mwad/paths.py` changed every model's key, even where the converter never runs the edited code.
It was also too narrow: it left out modules the converter does run (`src/mwad/esm.py`,
`src/mwad/npc.py`, `tools/nif_common.py` and others), so an edit made only there would have reused
stale models.

## Why it was not caught

The reuse audit (`tools/reuse_report.py`) runs after a build. Nothing compared the plan with the
source diff before the expensive stages started. The gallery key was a hand-written file list with no
test against the converter's real reach.

## Reproduction

`tools/build.py --reuse-plan OLD_RUN` with a checkout that differs from OLD_RUN's source in a shared
data-reader module: every stage is listed as rebuilt, each with the changed files that touch it.

## Repair

- Reuse preflight (`tools/reuse_report.py` `preflight`, run by `tools/build_cache.py` `prepare`):
  with `--reuse-from`, before any stage runs, the builder compares the reuse source's recorded source
  tree (`source_sha256` in its `build-state.json`) with the checkout, then prints every stage that is
  not reused, its reason and the changed files that touch it. If a stage would be rebuilt for a source
  key change that no changed file explains, or only for files no output can depend on, the build stops
  before the first stage. `--accept-rebuild` builds anyway, and says so. A plan that reuses nothing,
  or less than half of the reusable stages, prints a "check" line.
- `tools/build.py --reuse-plan OLD_RUN` runs the same preflight alone. It is read only, reads no game
  data and takes about 10 seconds.
- Gallery model key (`tools/gallery_cache.py` `converter_sources`): the code the converter can reach
  from `tools/prepare_gallery.py`, scope `units` (the same reach analysis as the stage fingerprints),
  plus the data files that code names. The rc9 seed import keeps the file list it compared before.
  The key format changes once, so the gallery models are converted once more on the first build with
  this change.

## Verification

- `tests/test_reuse_report.py`: rebuilds explained by the source diff or by a real input change are
  EXPECTED and list the changed files; a source key that changed with no file changed is UNEXPECTED
  and stops the build; a plan that reuses nothing is loud.
- `tests/test_build_cache.py`: the preflight stops a build before any stage runs, `--accept-rebuild`
  continues, `--reuse-plan` gives the same verdict, and a real edit is explained and named. The
  existing early-cutoff tests (identical outputs keep later stages; changed outputs rebuild them) still
  pass.
- `tests/test_gallery_cache.py`: a model key keeps its value for an unreached edit, changes for a
  reached edit in a module the old list never named, and covers the converter's real modules.
- The preflight against the real v0.0.34 run and source 901f8e9: 0 of 35 stages reused, 2 by policy,
  0 unexplained (every rebuild names its changed files).

## Prevention

The preflight runs on every build with `--reuse-from`, so the cost of a change is visible before any
stage runs, and a key that is too broad stops the build. The gallery key is derived from the code
the converter reaches, not maintained by hand.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-PER-WORKSPACE-33](BUILD-CACHE-PER-WORKSPACE-33.md): Per-file caches live in each build workspace, so a build on a new volume with --reuse-from converts everything again (MiniWind media 1,195 s instead of seconds)
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-STAIR-WALK-SLOW-33](BUILD-STAIR-WALK-SLOW-33.md): The image step's stair walk spent most of its time in interpreted collision traces and brute-force headroom tests (1,751 s of the rc1c image step)
- [BUILD-STORAGE-DUPLICATES-33](BUILD-STORAGE-DUPLICATES-33.md): Build storage keeps full duplicate copies of images, stage outputs and packages, and nothing removes them
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [MINIWIND-NOT-MINUTES-33](MINIWIND-NOT-MINUTES-33.md): A reused MiniWind build took about two hours instead of minutes
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
