# CHIMPORT-NO-SHARED-POOL-35: The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | tools/chimport.py run units and cell outputs; tools/chim/units.py UnitCache |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: Store-once rule broken for the island conversion: a second run folder or workspace converts and stores every unit and cell again; no stored-vs-linked figures |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.35 integration line |
| From commit | source e998ca3, engine e998ca3, CHIM world e998ca3 |
| CHIM engine version | CHIM 0.1.0, engine e998ca3, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped. The new options are off by default.

## Symptom

`tools/chimport.py` stored every converted unit (meshes, model variants, textures, terrain chunks, visibility
rows) in its own cache, `RUN/units/`, and every cell output in its run folder. The builder's shared,
content-addressed storage pool (`tools/storage_pool.py`) was not used. A second run folder (for example one per
region worker) or another workspace converted and stored every unit again, and no run reported how many bytes
were stored and how many were shared.

## Where

`tools/chimport.py` (`run`, `cell`, `world`), the CHIM unit cache `tools/chim/units.py` (`UnitCache`), and the
storage pool (`tools/storage_pool.py`, keys in `tools/file_cache.py`).

## How it happened

The CHIMporter was written before the storage pool existed and kept the content-keyed unit cache of the CHIM
builder, which lives in one folder. When the pool arrived it was wired into `tools/build.py` only
(`--storage-pool`, `--reuse-mode pool`), and its folder was fixed to `WORKSPACE/cache/asset-pool-v1`, so the
CHIMporter, which has no workspace, could not name it.

## Why it was not caught

No check compares the stores a tool writes with the shared pool; the pool's tests cover the builder only.

## Reproduction

Run two CHIMport run folders over the same cells: each converts and stores every unit itself.

## Repair

- `tools/chimport.py run|cell|world` take `--storage-pool auto|on|off` (default off: unchanged),
  `--reuse-mode copy|hardlink|pool` and `--storage-pool-dir DIR` (else `AMIWIND_STORAGE_POOL`, else
  `--workspace W`).
- Units: `chim.units.PooledUnitCache` keeps the run's `units/` folder and adds the pool: a unit missing there is
  looked up by its fingerprint (key file `keys/chim-unit/<kind>/`) and linked (or copied); a built unit is stored
  once by a hard link and its key recorded.
- Cells: a cell key hashes the cell and its frame settings, the game inputs (the run's input lock), the palette,
  the qbsp binary, the engine sizes, every converter file, the `AMIWIND_*` switches and the Python and numpy
  versions. A cell's outputs are stored once with a manifest under that key; the same key in any run links the
  whole cell. The source stage (`work/`), `result.json` and `cell.log` are never shared. Before a cell is built
  again, read-only shared links in its folder are removed (the bytes stay in the pool).
- Every run prints and records the bytes stored and linked and the cells and units reused, computed and failed.
- `--storage-pool-dir` for `tools/build.py` too (and the build config key `storage_pool_dir`), resolved once in
  `tools/storage_pool.py`; the default folder is unchanged and a named pool keeps every stage key. When the pool
  and the run cannot be hard-linked, one warning is printed and recorded and files are copied: the build never
  fails because of the pool. `tools/build_gc.py plan --pool DIR` collects a named pool, and cell manifests name
  their objects.
- Also: `RUN/run.lock` refuses a second `run` on the same folder (two would overwrite each other's
  `state.json`), and `--region NAME` selects a region's cells from `plan.json`.

## Verification

`tests/test_chimport_pool.py`: a unit in the pool is linked, not recomputed, byte-identical and one inode; a cell
in the pool is linked whole, and converted again when an input changes; the cell key changes with every input and
not with the pool's place; the default options leave the cell command and the conversion unchanged; a second
writer is refused; `--region` selects the right cells; a named pool is used and the default is unchanged; a pool
on another file system falls back to copies with one warning; the collector keeps objects a manifest names.

## Prevention

The storage pool's folder is resolved in one function for every tool, and the tests above run in the full suite.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
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
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
