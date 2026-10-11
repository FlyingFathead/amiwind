# Perf database

<!-- contents start -->
## Contents

- [Rules](#rules)
- [What it reads](#what-it-reads)
- [Tables](#tables)
- [Commands](#commands)
- [Running it in a container](#running-it-in-a-container)
- [Rebuilding the database](#rebuilding-the-database)
- [Dumps](#dumps)
- [After every gate and build](#after-every-gate-and-build)

<!-- contents end -->

`tools/perf_db.py` keeps every build's and every gate's measurements in one
SQLite database, intact and comparable across runs. A build folder holds its
own reports (`build-state.json`, `build-profile.json`, the CHIM heap and stair
reports, the image sizes), but run folders are deleted when a run is retired,
and comparing one number across a dozen runs means opening a dozen folders.
The database reads those files once, records each file's SHA-256 next to the
rows it produced, and answers the comparison in one command:

```text
python3 tools/perf_db.py --db perf.db compare --metric heap.peak --frame frames/x-03/y-02
```

Python 3.10 or newer, standard library only (`sqlite3`), no game data. It never
changes a build; it only reads the files a build or a gate wrote.

## Rules

- **Rows are append-only.** No row is ever updated or deleted; triggers in the
  database refuse `UPDATE` and `DELETE` on every table. A measurement, once
  recorded, stays as it was measured.
- **Every input is identified by its SHA-256.** A file already read with the
  same SHA-256 is skipped (reading it again adds nothing). The same path with
  different bytes is refused and reported, never overwritten.
- **Ledgers grow, they are not rewritten.** A JSON-lines ledger is read in
  segments: only complete lines, and on the next read only what was appended.
  The part already read must still have the SHA-256 recorded for it, otherwise
  the read is refused.
- **Runs are read when they have finished.** A run folder whose
  `build-state.json` still says `running` is skipped (and read on a later
  pass); a state that says `running` but has not been written for six hours
  (`--stale-hours`) belongs to a stopped build and is read as it is.
- **Same inputs, same rows.** With a content store the database can be rebuilt
  from exactly the bytes it read, and two rebuilds have the same canonical
  SHA-256 (see [Rebuilding the database](#rebuilding-the-database)).

## What it reads

`ingest` takes any mix of these, and folders of them:

| Input | Recognised by | Becomes |
| --- | --- | --- |
| A run folder | `build-state.json`, `build-summary.json`, `build-progress.json` or `build-profile.json` in it | The files listed below, under `runs/<run>/...` |
| A retired run's archive | `<run>.tar.gz`, `.tgz` or `.tar` holding those files | The same `runs/<run>/...` paths, so a run read from its folder and later from its archive is recognised by SHA-256 |
| A master builder result | a `.json` file with `"schema": "aw-result-1"` ([AW.md](AW.md)) | `aw-results/<name>` |
| A ledger | its file name: `build-ledger.jsonl`, `gate-ledger.jsonl`, `reuse-ledger.jsonl`, `samples.jsonl`, `optimizer-list.jsonl`, `TRIALS.jsonl`, `aw-trials.jsonl` | `ledgers/<name>`, in appended segments |

From a run folder (files over 32 MiB are left out; the per-map image heap and
stair dumps can pass 100 MB):

| File | Rows |
| --- | --- |
| `build-state.json` | run (version, commit, source tree hash, builder options and their SHA-256, start, result, failed stage, reuse source); one stage row per step (status, reused, wall, CPU, cores, jobs, peak RSS, I/O, fingerprint) |
| `build-profile.json` | stage rows from the profiler (CPU, mean jobs, peak tree RSS, host load); the run's wall-weighted host load |
| `build-progress.json` | expected seconds per stage and their basis |
| `build-summary.json` | start and finish times, reuse counts, compiler warnings, image size and SHA-256 |
| `chim-world/chim-heap.json` | one heap row per CHIM frame |
| `chim-world/chim-stairs.json`, `image/stair-walk.json` | one stair row per frame plus a `*` row for the whole walk |
| `chim-world/chim-timing.json` | CHIM build sections, unit counts (built / reused) |
| `chim-world/chim-validate.json` | CHIM world bytes by record kind, visibility numbers |
| `chim-world/chim-receipt.json` | CHIM world bytes per frame, per file class and per record kind |
| `image/chim-frame-heap.json` | heap rows of the image step (with the map name) |
| `image/world-partitions.json` | partition sizes |
| `image/heap-watcher.json` | the heap watcher's estimate |

## Tables

Every measurement table has the columns `id`, `source_id` (the file it came
from, in `source_files`), `seq` (row number within that file), `origin` (which
kind of file), `rank` (lower = closer to the measurement) and `line` (the
ledger line, for ledger rows).

| Table | One row per | Main columns |
| --- | --- | --- |
| `source_files` | file (or ledger segment) read | `path`, `kind`, `sha256`, `size`, `byte_offset`, `first_line`, `lines`, `file_sha256` (whole ledger up to this segment), `run`, `via` (archive), `stored`, `ingested_at`, `row_count`, `error` |
| `runs` | run, per file describing it | `run`, `kind` (build, gate, miniwind), `version`, `commit_hash`, `tree_hash` (SHA-256 hash tree of the source files), `flags`, `flags_sha256`, `requester`, `reason`, `started`/`finished` (as written, with zone) and `started_utc`/`finished_utc`, `wall_s`, `result`, `failed_stage`, `reuse_from`, reuse counts, `compiler_warnings`, `host_load` |
| `stages` | stage of a run, per file | `status`, `reused`, `wall_s`, `cpu_s`, `cores`, `jobs`, `jobs_mean`, `peak_rss_bytes`, `read_bytes`, `write_bytes`, `expected_s`, `expected_basis`, `fingerprint` |
| `gates` | gate | `gate` (number), `commit_hash`, `status`, `tests_run`, `failures`, `errors`, `skipped`, `engine_warnings`, `wall_s`, `suite_s`, `queue_wait_s`, `staging_s`, `parts` (exit codes and part times) |
| `heap` | CHIM frame of a run | `frame` (e.g. `frames/x-03/y-02`), `map`, `peak_bytes`, `budget_bytes`, `headroom_bytes`, `positions`, `positions_over`, `ring_models`, `ring_chunks`, `ring_textures`, load ring peak and headroom, `breakdown` (what fills the worst position, when the report has it) |
| `stair` | frame of a run's stair walk (`*` = the whole walk) | `steps`, `passed`, `covered`, `failed`, `untestable`, `gating_failures`, `advisory_failures`, `walked`, `reused`, `sampled`, `seconds`, `by_kind` |
| `sizes` | sized item of a run | `item` (`image/<file>`, `partition/<volume>`, `chim/total`, `chim/frame/<frame>`, ...), `class`, `bytes`, `count`, `sha256` |
| `metrics` | any other number | `scope`, `name`, `value` or `value_text` |
| `reuse` | stage of a reuse audit | `stage`, `class`, `cause` |
| `optimizer` | optimizer list item | `stage`, `reason`, `detail`, `recoverable_s` |
| `cpu_samples` | host or container CPU sample | `t` (as the sampler wrote it), `container`, `cpu_pct`, `cores`, `mem` |

`python3 tools/perf_db.py schema` prints the full schema.

### Merged views

Several files describe the same run, stage or frame (the build state and the
profiler both time a stage; a retired run may also have ledger rows). The views
`run_view`, `stage_view`, `heap_view`, `stair_view`, `gate_view` and
`size_view` give one row per key; each column comes from the best-ranked row
that has a value, and `origin` names the file kind of the best row. The tables
keep every row as read; the views only choose.

## Commands

```text
perf_db.py --db FILE [--store DIR] ingest PATH [PATH ...] [--strict] [--stale-hours H]
perf_db.py --db FILE compare --metric M (--frame F | --stage S | --item I) [--runs A B ...]
perf_db.py --db FILE stage-history --stage S [--like PATTERN]
perf_db.py --db FILE gate-summary [--day YYYY-MM-DD]
perf_db.py --db FILE run RUN
perf_db.py --db FILE sources [--run RUN]
perf_db.py --db FILE export --csv DIR | --table NAME
perf_db.py --db FILE canonical
perf_db.py --db FILE dump --sql OUT.sql.gz
perf_db.py --store DIR rebuild --out NEW.db
perf_db.py schema
```

`--db` and `--store` can also come from `AMIWIND_PERF_DB` and
`AMIWIND_PERF_STORE`. Query commands open the database read-only.

- `compare` metrics: `heap.peak`, `heap.headroom`, `heap.budget`,
  `heap.median`, `heap.positions_over`, `heap.load_peak`, `heap.ring_models`,
  `heap.ring_chunks`, `heap.ring_textures`, `stage.wall`, `stage.cpu`,
  `stage.cores`, `stage.rss`, `stair.steps`, `stair.failed`, `stair.gating`,
  `size.bytes`. Runs are listed in start order (or in the `--runs` order), each
  with the difference to the first, and runs named in `--runs` but missing from
  the database are listed as such.
- `--strict` (used before a run folder is deleted): exit 1 unless every path
  gave at least one file, none is still running and every file parsed.
- `--json` and `--csv-out` print the query tables as JSON or CSV.
- A file that cannot be parsed is still recorded (with its SHA-256 and the
  error) and its bytes are kept in the store; fix the parser, then rebuild.

## Running it in a container

The database is meant to live next to the builds, in the build volume, and to
be touched only by throwaway containers. Any image with Python 3.10 or newer
works; the builder image has it:

```text
docker run --rm --pull never --network none --user 1000:1000 \
  --mount type=volume,src=BUILD_VOLUME,dst=/vol,readonly \
  --mount type=volume,src=BUILD_VOLUME,dst=/perf,volume-subpath=perf \
  -v "$PWD/tools:/tool:ro" \
  -e AMIWIND_PERF_DB=/perf/perf.db -e AMIWIND_PERF_STORE=/perf/store \
  BUILDER_IMAGE python3 -I /tool/perf_db.py ingest /vol/build
```

The build volume is mounted read-only; only the `perf` folder in it (a volume
sub-path, Docker 26 or newer) is writable. Create that folder once (as the
build user) before the first run. Ledgers or results kept outside the volume
are mounted read-only the same way (`-v DIR:/in:ro`, then `ingest /in/...`).
Queries need no write access at all: mount `/perf` with `readonly` too.

## Rebuilding the database

With `--store DIR` every file read is also kept, compressed, under its SHA-256
(`DIR/sha/<ab>/<sha>.gz`, read back and checked before it counts), and every
read is listed, in order, in `DIR/MANIFEST.jsonl` (path, SHA-256, size, segment,
time read). `rebuild` creates a new database file from that store alone, in the
recorded order and with the recorded times; it never overwrites a file. Every
stored file is checked against its SHA-256 as it is read back.

`canonical` prints the SHA-256 of the database content: every row of every
table, in a fixed order, as JSON lines (the creation time left out). The same
inputs give the same rows, so two rebuilds, and a rebuild and the database it
was rebuilt from, print the same canonical SHA-256 - which also proves the
rebuild saw the same inputs. A newer parser (the `parser` value in `meta`)
reads files differently by design; a rebuild with it re-reads every stored file
with one parser.

## Dumps

`dump --sql OUT.sql.gz` writes a gzip SQL text dump of the whole database (no
time stamp in the gzip header: the same database gives the same bytes) and
`OUT.sql.gz.sha256` next to it. It never overwrites an existing dump. A dump
restores with `gzip -dc OUT.sql.gz | sqlite3 restored.db`. To keep wear low,
write a new dump only when `canonical` changed since the last one.

## After every gate and build

The master builder runs a configured command after it writes each gate or build
result ([AW.md](AW.md#perf-database-step)), so new results, run folders and
ledger lines reach the database without anyone asking for it.
