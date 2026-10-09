# Speed

How the repository builder saves time: the worker count (`--jobs`, see
[Parallel build](../../PARALLEL_BUILD.md)), stage reuse from one earlier run
(`--reuse-from`) and the build profile (see [Build profile](../../BUILD_PROFILE.md)),
and the prerendered store, which keeps finished stage outputs across builds and
workspaces.

## Prerendered store (`--prerendered DIR`)

Converting the same area again gives the same files: a CHIM world, its frame
maps and the converted interiors depend only on your game files, the builder
code they run and their settings. The prerendered store keeps those outputs in
a folder of your choice, by version and area, and a later build uses them
whenever nothing they depend on changed.

```bash
python3 tools/build.py --data-files "/path/to/Morrowind" --builder chim \
  --name dev-b --prerendered /path/to/prerendered
```

The store holds data converted from your own game files: keep it private, like
the build workspace. Never publish it or copy it into the source package.

### What decides a hit

The stage fingerprint of the stage cache (see
[Build profile](../../BUILD_PROFILE.md#stage-reuse-for-development-builds)): the
stage's command, the repository code it can reach and the data files that code
names, the game input hashes, the map tools, the build switches it reads, the
Python version and packages, and the fingerprints of every stage it depends on.
The store is the same cache with a longer memory: the same fingerprints, the
same output manifests, the same verified copy.

A stage that `--reuse-from` does not reuse and whose fingerprint has an entry
is copied from the store (or hard-linked with `--reuse-mode hardlink` when the
store is on the same file system), every file's SHA-256 checked while it is
copied, after the stage's input files in the run were checked against the
stored hashes. Any doubt runs the stage instead. The build state, the stage log
and the summary say `reused (fingerprint ...) from prerendered <entry>`.

### What is stored

Each chosen stage is copied aside when it passes. The copies become store
entries only when the whole build passed, every later check and gate
included: a build that fails or is cancelled stores nothing. Stages whose
outputs the stage cache marks as not reusable (their reads were not covered by
the fingerprint, or another stage changed the same files at the same time) are
never stored.

`--prerendered-stages` chooses the stages:

| Value | Stores |
| --- | --- |
| `default` | the heavy per-area outputs: the CHIM world (`chim`), the interiors (`interior`, `balmora-interiors`), Balmora's region work (`balmora`), the area stage (`area`) and imported towns (`town-*`) |
| `all` | every reusable stage |
| `a,b,...` | the named stages (`town-*` style patterns allowed) |

Release candidates and finals are built from scratch: they store their stages
but never use stored ones (unless `--allow-release-reuse`, only while the
from-scratch gate runs separately on the same commit).

### Layout

```text
prerendered/
  index.json                      every entry: path, stage, size, created, versions
  usage.jsonl                     every build that stored or used an entry
  chim/<CHIM version>/<world format>/<areas>/<fingerprint>/
  interiors/<fingerprint>/
  legacy/<AmiWind version>/<stage>/<fingerprint>/      region and town maps
  stages/<AmiWind version>/<stage>/<fingerprint>/      other stages (--prerendered-stages)
```

Each entry holds `receipt.json` (stage, AmiWind, builder type, CHIM and world
format versions, source and builder commit, source and game input digests,
size, file count, creation time, fingerprint parts), `manifest.json` (the
stage's output manifest) and `files/` (the outputs at their paths in the run
folder, read-only). The version folders are for people browsing the store;
only the fingerprint decides reuse.

### Measured (9 October 2026)

A CHIM Balmora build cut to the chim stage and the 13 stages it depends on
(the scene chain, the world survey, the flora assets, the harvest table),
v0.0.33-dev1, `--jobs 4`, on a busy host (other builds ran at the same time),
`--prerendered-stages all`:

| | Empty store (miss) | Same store, new workspace (hit) |
| --- | --- | --- |
| chim stage | 280 s (4 CPUs) | 0.8 s |
| interior stage | 222 s | 1.4 s |
| all 14 stages | 1,138 s to 1,416 s | 14.6 s (1 CPU) |
| stored | 14 entries, 560 MB | used 14 of 14 |

The hit build's 3,669 stage output files are byte-identical to the miss
build's. Two fresh builds wrote the same CHIM world bytes apart from their
receipts and statistics (times). The second miss figure ran its last stages
on one CPU.

### Looking after the store

```bash
python3 tools/build.py --prerendered list /path/to/prerendered     # entries, sizes, ages, which builds used them
python3 tools/build.py --prerendered verify /path/to/prerendered   # SHA-256 of every stored file
python3 tools/build.py --prerendered prune /path/to/prerendered    # removal candidates; deletes nothing
```

`prune` lists entries that a newer entry of the same stage, area and version
replaced, entries never used for 14 days (`tools/prerendered.py prune DIR
--days N`) and copies left by builds that stopped. Removing an entry is your
decision: delete its folder, then run `list` to refresh the index. A damaged
entry (found by `verify`, or by the copy check of a build) is never used.

`tools/prerendered.py import DIR RUN --source CHECKOUT` stores the passed stages
of an earlier run, fingerprinted with the checkout that built it. It refuses a
checkout whose files differ from the run's source record, a run made with
another Python, and stages whose files a later stage of that run replaced.

### Docker

Keep the store on a Docker volume, next to the build workspace: big files
copied between a container and a host folder are much slower than inside a
volume.

```bash
docker volume create amiwind-prerendered
docker run ... -v amiwind-prerendered:/prerendered ... \
  python3 tools/build.py ... --prerendered /prerendered
```

The quickest way to a test image is often to leave content out; see
[Quick test builds](QUICK_TEST_BUILDS.md). Back to the
[CHIM build guide](README.md).
