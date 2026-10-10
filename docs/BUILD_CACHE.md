# Build cache: resuming and reusing work safely

How the builder avoids doing work twice: after a failure it continues from the last
finished unit, and after a small change it rebuilds only what the change reaches.
This page states the rules every stage follows and why reuse is safe. The stage
profiler and the stage cache commands are in [BUILD_PROFILE.md](BUILD_PROFILE.md).
Storing every output once (the shared storage pool), the retention policy (the
garbage collector) and leased workspaces (the work pool) are further down this page.

<!-- contents start -->
## Contents

- [The rule](#the-rule)
- [Units](#units)
- [Why reuse is safe](#why-reuse-is-safe)
- [Early cutoff](#early-cutoff)
- [Reuse preflight](#reuse-preflight)
- [Run names](#run-names)
- [Entry check](#entry-check)
- [Developer mode](#developer-mode)
- [Fail fast](#fail-fast)
- [Hierarchical output hashes](#hierarchical-output-hashes)
- [Selective rebuilds](#selective-rebuilds)
- [Stage hashes and reference checksums](#stage-hashes-and-reference-checksums)
- [End summary](#end-summary)
- [Largest unit](#largest-unit)
- [Planned (v0.0.35 line)](#planned-v0035-line)
- [Shared storage pool: store once](#shared-storage-pool-store-once)
- [One pool for several workspaces and the CHIMporter](#one-pool-for-several-workspaces-and-the-chimporter)
- [Garbage collector: one retention policy](#garbage-collector-one-retention-policy)
- [Work pool: leased workspaces](#work-pool-leased-workspaces)

<!-- contents end -->

Status: the rules below are in force. Items marked *planned* are the next steps
(v0.0.35 line).

## The rule

A failure forces the builder to rebuild only the minimum, within safe limits:

- every unit of work (a stage, a map, a region, a cell, a partition) has a **key**:
  the content hash of all its inputs (input files, the outputs of the units it
  reads, the code that makes it, its options and the `AMIWIND_*` settings that
  code reads);
- a unit is rebuilt only when its key changed, or when its stored output is
  missing or damaged (every reused output is checked against its recorded
  SHA-256);
- a key never leaves an input out. A missed input would let a wrong result be
  reused, so keys err on the side of more inputs; an input that no output
  depends on only costs time, and is a bug to fix;
- outputs are byte-reproducible: the same inputs give the same bytes. Wall time,
  worker counts, cache hit counts and folder paths go to logs and the build
  profile, never into an output another unit reads.

## Units

| Level | Unit | Key | Where |
| --- | --- | --- | --- |
| Stage | one builder stage | stage fingerprint (code it can run, data files it names, game inputs, tools, settings, the stages it depends on) | `tools/build_cache.py`, `--reuse-from` |
| Image step | one map in one per-map pass (sky, hidden-surface cull, BSP optimizer, stair walk) | the map's bytes, the pass options, the pass's sources | `tools/pass_cache.py` `PassCache` |
| Stage units | one region of world scenery or world flora | the region record, its input bytes, every shared input by content, the sources, the settings | `tools/pass_cache.py` `UnitCache` |
| Stage units | one interior room (Balmora interiors, the area rooms, town interiors), one town region (Balmora and the other towns), one character head preview | the room or region record, the game data (the build's input lock), the palette, the map compilers by content, the shared town inputs by content, the sources, the settings | `prepare_area.build_room_cached`, `import_town`, `prepare_character` |
| Stage units | one world terrain map, one NPC gallery model, one CHIM unit, one sound or movie | each stage's own content-addressed cache (a gallery model: its appearance record, the bytes of its meshes and textures, the palette, and the code its converter can reach) | `world-terrain-v1`, `npc-gallery-v1`, `chim-units`, `asset-pool-v1` |

Development builds (`-devN`) use every cache. Release candidates and finals use
them only with `--allow-release-reuse`, which says the from-scratch reference
build runs separately on the same commit and is compared with the result; without
it a release build runs every unit.

## Why reuse is safe

1. **Keys cover every input.** The stage fingerprint follows the code a stage can
   reach and the data files that code names; the read trace (a hook in every
   stage's Python processes) lists the repository files the stage really opened,
   and a file the fingerprint left out makes the stage not reusable. Folders put on
   the import path (`sys.path.insert(0, str(ROOT / 'tools'))`) are where Python
   looks for modules, not reads; the modules themselves are followed.
2. **Outputs are checked on reuse.** Every reused file is compared with the
   SHA-256 recorded when it was made, before the build starts and again while it
   is copied; a damaged or partial entry is rebuilt, never used.
3. **Outputs are credited to their writer.** A stage's outputs are the files that
   changed under its run-folder paths while it ran. When two stages run at the
   same time and both saw a file change, the write trace decides: a file only one
   of them wrote is that stage's output; with an unknown writer (a map compiler) or
   two writers, neither stage is reused.
4. **Diagnostics are not compared, and never read.** Tool logs (`*.log`) and the
   reports `chim-stats.json`, `chim-timing.json`, `gallery-cache.json` and
   `world-terrain-cache.json` carry timings; a rerun stage whose outputs differ
   only in these still "wrote the same outputs" for the stages after it. A stage
   that reads another stage's diagnostic is not reused.
5. **The from-scratch build is the final check.** A release image is reproduced by
   a build without any reuse and compared file by file; any difference blocks the
   release.
6. **Every refusal is reported.** `tools/build.py --reuse-report RUN` lists each
   stage a `--reuse-from` run did not reuse, with the recorded reason, as EXPECTED
   (a real input change, the image step, a stage that never reuses) or UNEXPECTED
   (an over-broad key, a refused record, outputs that differ although the inputs
   did not). It exits 1 on any UNEXPECTED rebuild.

## Early cutoff

A stage whose own inputs are unchanged, but which follows a stage that runs again, is
planned as reused "if the stages before it write the same files again". When it starts,
every stage before it that ran in this build must have written exactly the files (SHA-256
and mode), links and deletions it wrote in the reuse source; then it is reused, otherwise
it runs. A code change that leaves a stage's outputs byte-identical therefore costs that
stage's run, not the rest of the build. A stage whose own key changed (its reached code,
the game inputs it reads, the settings its code reads) always runs: whether its outputs
would come out the same cannot be known without running it.

## Reuse preflight

With `--reuse-from`, the builder checks the reuse plan before any stage runs:

- it compares the reuse source's recorded source tree (`source_sha256` in its
  `build-state.json`) with the checkout;
- it prints every stage that will not be reused, with its reason (the changed parts of
  its key) and the changed files that touch it, and one line on how many stages are
  reused; a plan that reuses nothing, or less than half of the reusable stages, prints a
  "check" line;
- a stage rebuilt for a source key change that no changed file explains, or only for
  files no output can depend on (the release file list, prose, tests), is a key that is
  too broad: the build stops before the first stage. `--accept-rebuild` builds anyway and
  says so.

`tools/build.py --reuse-plan OLD_RUN [--json FILE]` runs the same preflight alone, read
only, against OLD_RUN's own commands and game inputs: no game data read, about 10
seconds. The build itself also checks outputs, so it can only reuse fewer stages than the
plan says. Example: the first v0.0.35 development build against the v0.0.34 build printed
0 of 35 stages reused, 2 by policy, every other one explained by changed sources, game
inputs or settings.

## Run names

A build run folder is named

    YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort>

for example `2026_10_10_v0.0.35-dev1_full_901f8e9`: the host's date, the source's
VERSION (with its `-devN` or `-rcN` suffix), the purpose (`full`, `miniwind-<town>` with
`-debug` and `-quick` where they apply, `dry-run`, or the stage of a partial build), `-tryN`
when a run of that name already exists, and the source commit. The commit is read from
the checkout's git files, else from `--source-commit` or `AMIWIND_SOURCE_COMMIT` (an
exported source tree), else it is `nogit`. An explicit `--name` must contain the source
version; `--any-run-name` allows any name with a warning. The parts are recorded in
`build-state.json` (`run_name`). `tools/run_name.py` implements the scheme.

## Entry check

Every build first checks that it runs the code it was asked to build. A builder module
(from `tools/` or `src/`) loaded from outside the source tree being built, or any module
loaded from another AmiWind builder tree, stops the build with the module's name and file
(BUILD-IMAGE-STALE-PYTHONPATH-35: older container images put an old builder copy on
`PYTHONPATH`). Entries of `PYTHONPATH` that point into another builder tree are dropped
before any stage starts, so stage processes cannot load old code either; the build prints
which entries it dropped. Nothing else changes for a build without `--developer-mode`.

    python3 tools/build.py --check-entry [--working-version FILE] [--workspace WS] [--name RUN] [--json]

is the same check as a read-only command for anyone starting work on a checkout (seconds,
no game data): (a) the working version, (b) the source of every loaded builder module,
(c) the integration head, (d) the storage pool (exists, writable; hard links are not
probed by this read-only command), and with `--name` (e) the run name. Exit status 0 =
ok, 1 = refused. `tools/chimport.py run|cell|world` run the same check before any cell
(`--working-version`, `--accept-version-mismatch`); `run` prints it and passes the record
to its cells.

The working-version record is a JSON file such as
`{"working_version": "0.0.35-dev1", "integration_head": "6dcb10e"}`. It is looked up in
this order, the first that exists wins:

1. `--working-version FILE`;
2. the environment variable `AMIWIND_WORKING_VERSION` (a file path);
3. `WORKSPACE/../WORKING_VERSION.json` (the top folder of a shared build volume whose
   workspaces sit side by side);
4. `WORKING_VERSION.json` in the storage pool folder, then in its parent
   (`WORKSPACE/cache`).

No record found is a warning, not a refusal.

## Developer mode

`tools/build.py --developer-mode` (alias `--devmode`) runs the entry check before any stage
of a build and prints one block:

- (a) working version: the source `VERSION` must equal the record's `working_version`;
  a mismatch refuses the build unless `--accept-version-mismatch REASON` says why;
- (b) source: every loaded builder module comes from the source tree (refused otherwise);
- (c) integration head: when the record names one, the source must contain it
  (`git merge-base --is-ancestor`); not containing it refuses. Without a git program the
  checkout's HEAD read from its `.git` files proves the equal case, and an exported tree
  matches it against `--source-commit`; anything that cannot be checked is a warning;
- (d) storage pool: exists, writable by the build's user, and hard links work (a tiny
  probe file is linked and removed); otherwise a loud warning: outputs then stay in the
  run instead of being linked (a cache problem never fails a build);
- (e) the run name follows the naming rule above (a warning otherwise);
- (f) with `--reuse-from`, the reuse preflight summary (stages reusable, rebuilt,
  unexpected, keys too broad).

The result is recorded in `build-state.json` as `developer_mode`. `--working-version` and
`--accept-version-mismatch` need `--developer-mode`. `tools/entry_check.py` implements both.

## Fail fast

The image step runs its payload preflight as soon as the payload is staged (in
its first minute): every read-only payload check, in parallel, all errors listed
together, including the harvest catalogues the step will write later, planned
from the harvest source. `tools/build.py --check-payload RUN` runs it alone on a
failed run, so a fix can be checked in seconds without rebuilding.

## Hierarchical output hashes

Every stage's outputs form a tree (`tools/unit_tree.py`): **units** (one map, region,
room, head preview or catalogue file), grouped into **segments** (a town's maps, a
block of 100 open-world regions, the rooms, the character heads), and one **stage
hash** over the segment hashes. Each level's hash covers the level below, so two runs
compare a stage in one step and drill down only on a mismatch, to the segments and
units that differ. Logs and timing reports are left out. The tree is stored in every
stage's output record, used by the "wrote the same outputs" check, named by the reuse
audit ("census: 1 units differ (scene/census.txt changed)"), and recorded per segment
in the release reference checksums, so a build that differs from a release is told
which stage and which segments first differ. Measured on the v0.0.33 rc1 records:
world terrain (12,664 files, 5,067 units, 54 segments) builds its tree in 0.04 s and
compares in 0.1 ms.

The image step's packing is not split by segment: the world partitions are written in
parallel in about 28 s and the whole disk assembly takes about 4 minutes, under the unit
ceiling, while caching packed partitions would store gigabytes per build.

## Selective rebuilds

`--rebuild-stage NAME[,NAME]` (with `--reuse-from`) runs the named stages again
although they could be reused. Nothing stale passes: every stage after them is
still decided by its key, and is reused only if the forced stages wrote the same
outputs as before; otherwise exactly the affected stages run. Forced stages are
recorded in the build state and listed by the reuse audit. Release candidates and
finals follow the same rules as `--reuse-from` (`--allow-release-reuse`).

`--rebuild-unit UNIT:NAME[,UNIT:NAME]` builds single stage units again although they
are cached (`interior-room:bmtemple`, `town-region:bm003`, `world-scenery-region:vf0123`,
or `UNIT:*` for every unit of that kind); the new result replaces the stored one.
`python tools/pass_cache.py list WORKSPACE/cache/image-passes [UNIT]` lists the stored
units with their names, keys, file counts and sizes. Units that read game data are
cached only when the build has an input lock (the game data identity); a unit whose
receipt does not survive a JSON round trip unchanged is never cached, so a cached unit
returns exactly what a built one would.

## Stage hashes and reference checksums

Every build records, per stage, the hash of its outputs (the SHA-256 of its
sorted per-file hashes without diagnostics) in `build-summary.json`, so two
builds can be compared stage by stage even when the disk image wrapper differs.
A release's reference file, `checksums/v<VERSION>.json`, holds per game edition
those stage hashes, the per-file payload hashes and the drive hashes; the release
tooling writes it from the release build (`python tools/build_reference.py write
RUN`). At the end of a build the builder compares itself with the reference of
its VERSION and prints one line: no reference yet, a match with the official
release image, or how many stages match and which stage first differs. This is a
report only: it never stops or changes a build. The file holds hashes and the
build's own output names only, no game content and no local paths.

## End summary

The build's last section, "Reuse and reference", lists the stages reused and
rebuilt with their causes (a warning for any unexpected rebuild), the time reuse
saved, the stage hashes recorded, the reference check and the payload
preflight's result; the same figures are in `build-summary.json`.

## Largest unit

Target: no single unit takes more than **5 minutes** to rebuild at the release
worker budget. A unit over it is split into smaller keyed units. Steps that cannot
be split (the final disk layout and drive assembly, which depend on every file)
are kept as cheap as possible: they only copy and verify finished parts.

## Planned (v0.0.35 line)

- **One content store for every cache.** Two tables shared by every build and
  worktree: unit key to output hashes, and output hash to bytes, stored once,
  written atomically, never changed in place, with a size cap and least-recently
  used clean-up. The present caches (stage cache, pass cache, unit caches, asset
  pool, prerendered store) converge into it; each stays selectable until then.
  The same key giving different outputs in two builds is reported as a
  determinism or key bug.
- **Input check against the reference**: the game data hashes per edition, so a
  build can say before it starts whether the data files match a known edition.
- **Whole-image reproducibility**: FFS dates and volume stamps from the source
  (a fixed epoch), so the disk image itself can match byte for byte.

## Shared storage pool: store once

Disk images, stage outputs and packages used to be kept as full copies in
every run folder, every reused run, every prerendered entry and every package
folder. The shared storage pool keeps each file once, by its SHA-256, and puts
read-only hard links in those places instead.

* **One store.** The pool is the asset pool's object store,
  `WORKSPACE/cache/asset-pool-v1/objects/SHA[:2]/SHA` (`tools/file_cache.py`
  converter outputs, `tools/storage_pool.py` everything else). One content,
  one file, whatever stage, build or version made it.
* **No first copy either.** A file is stored by a hard link to its own inode,
  so pooling a run writes no bytes; the next file with the same content is
  replaced by a link and its own copy is freed.
* **Read-only.** Pooled files are made read-only; the builder's writers
  replace files (temporary name and rename), they never edit them in place,
  so a later build can never change bytes another run shares.
* **Verified.** A file is checked against its SHA-256 when it is pooled and
  whenever it is placed in a run; a damaged object is never linked and is
  replaced from a good copy.
* **Never across file systems, never as root, not on Windows.** There the
  pool cannot protect a shared file (or would add a copy), so nothing is
  pooled and builds behave exactly as before.

What uses it:

| Where | What happens |
| --- | --- |
| A passed development build | `tools/build.py --storage-pool auto` (default): when the build passed, its outputs, and the prerendered entries it stored, are pooled and linked back read-only; `profile/storage-pool.json` records files, links and bytes freed. `on` does the same for every build; `off` is for debugging only. Logs, profile and scratch are not pooled; an image the emulator was launched on is never shared. |
| `--reuse-from RUN --reuse-mode pool` | Reused stage outputs are linked from the pool (the old run's file is pooled by a link first), never copied. `copy` (default) and `hardlink` stay selectable. Linked files are read-only in every run sharing them. |
| Packages, extracted deliveries, older runs | `python tools/storage_pool.py adopt POOL FOLDER... --apply` pools any folder on the same volume (dry run without `--apply`). |

Played disk copies are never links: a copy the emulator writes to is an
ordinary copy (`storage_pool.place(..., link=False)`), made and removed by the
job that plays it.

Release candidates and finals are still built from scratch: the pool only
saves space, it never decides what is rebuilt.

```
python tools/storage_pool.py scan ROOT...            # duplicate bytes by content, by kind (read-only)
python tools/storage_pool.py adopt POOL FOLDER...    # what pooling would free (add --apply to link)
python tools/storage_pool.py stats POOL              # objects, and how many no run links any more
```

## One pool for several workspaces and the CHIMporter

The pool folder can be named, so several build workspaces and the CHIMporter
(`tools/chimport.py`, `docs/chim/CHIMPORT.md`) share ONE pool: a file any of
them stored is stored once for all of them. The folder is chosen in this order:

1. `--storage-pool-dir DIR` (`tools/build.py` and `tools/chimport.py`);
2. the build config key `storage_pool_dir` (`--build-config FILE`; a relative
   path is relative to the config file);
3. the environment variable `AMIWIND_STORAGE_POOL`;
4. the default, `WORKSPACE/cache/asset-pool-v1` (unchanged when nothing is set).

Naming a pool changes no stage key: the pool is a content-addressed store, so a
named pool gets the same location token in the stage fingerprints as the
default one, and `AMIWIND_STORAGE_POOL` is not a stage input.

Hard links need the pool on the same file system AND the same mount as the
run (two container mounts of one disk are still two mounts). The builder checks
this once per build by linking a probe file. When it cannot link, it prints one
loud warning, records it in the build state (`storage_pool`) and in
`profile/storage-pool.json`, and copies instead: reused files are copied
(`--reuse-mode pool` and `hardlink` fall back to `copy`) and outputs are not
pooled (pooling would add a copy). The build never fails because of the pool.

```
python tools/build.py --storage-pool-dir /pool/shared ...          # this build
AMIWIND_STORAGE_POOL=/pool/shared python tools/build.py ...        # every build of this shell
python tools/chimport.py run ... --storage-pool on --reuse-mode pool --storage-pool-dir /pool/shared
python tools/build_gc.py plan VOLUME --pool /pool/shared           # the collector sees a named pool too
```

## Garbage collector: one retention policy

`tools/build_gc.py` is the one collector for build workspaces, the pool and
job scratch. It applies the same rules everywhere:

| Decision | Items |
| --- | --- |
| kept: pinned | release and release-candidate references, owner pins (`WORKSPACE/cache/pins.json`, edited with `build_gc.py pin` / `unpin`) |
| kept: reuse source | the newest passed run of every build line (version, builder type and recipe) |
| kept: active | runs still building; items whose owning job is still active; build caches |
| expires | run folders, played or smoke copies, package and extraction scratch and test workspaces whose owning job is done; scratch left in a finished run; pooled objects that no run links and no reuse key (or CHIMport cell manifest key) names; pool temporaries older than a day |
| unregistered | anything without an owner: reported with its size, never deleted |

Owners come from a registry file (`--registry FILE`):
`{"items": [{"path": ..., "owner": ..., "purpose": ..., "state": "active"|"done"}]}`.

Sizes are what deletion really frees: a file shared by hard links counts only
when every one of its links is in the deletion set, so deleting an old run
whose files the pool and a newer run still link frees almost nothing, and the
plan says so.

The collector is a dry run by default. `--delete` removes the expired items,
and `--item PATH` limits that to an approved list; pinned, active and
unregistered items are never deleted, and a run that started building again
since the plan was made is left alone.

```
python tools/build_gc.py plan VOLUME_OR_WORKSPACE... [--registry FILE] [--json plan.json]
python tools/build_gc.py plan ... --delete --item PATH [--item PATH ...]
python tools/build_gc.py pin WORKSPACE build/RUN --kind rc --reason "release candidate reference"
```

## Work pool: leased workspaces

Instead of each job keeping its own volume or folder, jobs lease a workspace
from ONE shared work pool (`tools/work_pool.py`):

* **A lease names its owner, purpose, quota and expiry.** It is granted only
  while the quotas of all live leases plus the new one fit the pool's
  capacity minus its reserve: a job that does not fit waits for a lease, it
  cannot fill the machine.
* **Inputs and outputs come by hard link from the content pool**
  (`work_pool.py link`, `storage_pool.place`). Bytes shared with the pool or
  another workspace do not count against the quota; only bytes the
  workspace alone holds do.
* **Over quota pauses the job, not the machine.** `work_pool.py enforce`
  marks a lease over quota and runs `--on-over-quota CMD` once for that lease
  (for example a command that pauses the job's container, with `{container}`,
  `{owner}`, `{id}`, `{path}`, `{used}`, `{quota}` filled in); a lease back
  under quota is active again.
* **Returned and expired leases are collected.** The job returns its lease
  when it ends (`work_pool.py return`); `build_gc.py plan --work-pool ROOT`
  treats live leases as active owners and returned or expired ones as done,
  so their workspaces expire under the same dry-run-first rules.

```
python tools/work_pool.py init ROOT --capacity 400 --reserve 40      # GB
python tools/work_pool.py lease ROOT --owner JOB --purpose TEXT --quota 60 --hours 12 [--container NAME]
python tools/work_pool.py usage ROOT
python tools/work_pool.py enforce ROOT --on-over-quota "CMD {container}"
python tools/work_pool.py return ROOT LEASE
python tools/build_gc.py plan --work-pool ROOT [--delete]
```

Tests: `tests/test_storage_pool.py` (store once, read-only links, verified
placement, played copies, dry run, duplicate scan),
`tests/test_build_gc.py` (retention keys, pins, owners, dry run, hard-link
aware sizes, deletion of approved items only), `tests/test_work_pool.py`
(leases, admission, quota from unique bytes, per-job pause, collection) and the pool reuse mode in
`tests/test_build_cache.py`.
