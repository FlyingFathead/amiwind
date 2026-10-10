# BUILD-IMAGE-STALE-PYTHONPATH-35: Builder container images put an old builder copy on PYTHONPATH

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | Builder container images (recipe in tools/build_docker.py); tools/build.py entry |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: Any container run of another source tree without its own PYTHONPATH could import old builder code silently; a job read the wrong VERSION from it. |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 6dcb10e |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Repair in v0.0.35 development (not shipped).

## Symptom

A job ran Python in a builder container against a newer, mounted source tree and read the version
0.0.26 instead of the source's own. Nothing failed or warned.

## Where

- The builder image recipe (`tools/build_docker.py`) copies the source into `/opt/amiwind` and sets
  `PYTHONPATH=/opt/amiwind/src:/opt/amiwind/tools`. Every image derived from such an image keeps that copy
  and that path, long after the copy is old.
- `tools/build.py` and `tools/chimport.py`: no check of where the builder modules they load come from.

## How it happened

`tools/build.py` puts its own `src/` first on the module path, and a script's own folder comes first
anyway, so a normal build of a mounted source loaded none of its modules from the old copy (checked: 0
modules). But any other Python run in such a container without its own `PYTHONPATH` (a one-off check, a
helper script, a module the source no longer has, a stage process importing a removed module) silently
loaded the old copy's code.

## Why it was not caught

The builds themselves were right, so no build or gate failed. Nothing checked where the loaded builder
code came from, and the old copy carried the same module names as the current source.

## Reproduction

Run `python -c "import build_aga; print(build_aga.VERSION)"` from any folder other than a source tree's
`tools/` in an image built from an old source: it prints the old version.

## Repair

- Import guard on every build (`tools/entry_check.py`): a builder module loaded from outside the source
  tree being built, or any module loaded from another AmiWind builder tree, stops the build and names the
  module; entries of `PYTHONPATH` that point into another builder tree are dropped before any stage
  starts. No other change to a default build.
- `tools/build.py --check-entry`: the read-only entry check for anyone starting work (working version,
  module sources, integration head, storage pool); `tools/chimport.py run|cell|world` run it too.
- `tools/build.py --developer-mode` (`--devmode`): the same checks before any stage, a refused build on a
  version mismatch or a missing integration head, plus the run name and the reuse preflight; recorded in
  `build-state.json`. See [BUILD_CACHE.md](../BUILD_CACHE.md#entry-check).
- Local images: new tags derived from the old ones without the old copy on the path.

## Verification

`tests/test_entry_check.py`: a version mismatch is refused (and accepted with a reason), an old-tree
module is refused by name, an old tree on `PYTHONPATH` cannot shadow a removed module, the right setup
passes, a default build prints no developer block but still runs the guard, `--check-entry` output and
exit status, and `chimport.py` refuses before converting. The full gate passes in the clean images.

## Prevention

The guard runs on every build; the entry check is the first step of every worker
(`build.py --check-entry`) and of every development build (`--developer-mode`).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- [BUILD-OUTPUTS-NOT-REPRODUCIBLE-33](BUILD-OUTPUTS-NOT-REPRODUCIBLE-33.md): A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt
- [BUILD-POOL-APPLY-READ-MISS-35](BUILD-POOL-APPLY-READ-MISS-35.md): In a pool-mode build every reused stage was refused as the next reuse source: the reuse step's read of tools/storage_pool.py counted as a stage input
- [BUILD-POOL-ARG-UNFINGERPRINTED-35](BUILD-POOL-ARG-UNFINGERPRINTED-35.md): The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
