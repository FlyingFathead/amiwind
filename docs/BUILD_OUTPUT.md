# Build completion output

_Last updated with AmiWind v0.0.48 (24 October 2026)._

<!-- contents start -->
## Contents

- [HDF capacity versus installed content](#hdf-capacity-versus-installed-content)
  - [Disk layout: the fewest partitions, each with headroom](#disk-layout-the-fewest-partitions-each-with-headroom)
- [Size ledger](#size-ledger)
- [Completion footer](#completion-footer)
- [HDFs and emulator runners](#hdfs-and-emulator-runners)
- [Timing](#timing)
- [Compiler and toolkit inventory](#compiler-and-toolkit-inventory)
- [Warnings](#warnings)
- [Failures, modes and saved results](#failures-modes-and-saved-results)
  - [Release readiness](#release-readiness)

<!-- contents end -->

rc10 adds [verified persistent NPC model reuse](NPC_MODEL_CACHE.md). Full gallery
coverage and protected model quality remain mandatory.

## HDF capacity versus installed content

The final HDF's byte size is its virtual disk capacity, including filesystem
metadata and free space. It is not a count of converted game assets. The image
uses the fewest partitions its payload needs, each sized from its payload plus a
fixed headroom ([disk layout](#disk-layout-the-fewest-partitions-each-with-headroom) below;
the legacy layout sized each from its payload plus about 20 percent and 16 MiB,
rounded up to 128 MiB). Each partition stays below 2 GiB and also starts below 2 GiB on its drive,
because Kickstart 3.1 does not mount a later one (see
[AMIGA-DISK-2GIB-LIMIT-33](bugs/AMIGA-DISK-2GIB-LIMIT-33.md)); the combined legacy
hardfile stays below 4 GiB. When the complete partition set will not fit,
additional HDFs are created automatically and recorded in `hdf_files`.
All drives must remain mounted together.

The reported rc7 image is 3,221,258,240 bytes: two 1.5 GiB partitions plus
32 KiB of disk-layout space. Its exact free space must be read from that build,
not estimated from the container size. `image/build.json` records total
`payload_bytes`, and per-partition `bytes`, `payload_bytes`, `free_bytes` and
file counts after readback of the completed HDF. Capacity minus payload also
includes filesystem overhead; use the recorded bitmap free bytes for available
space. Allocated host-disk blocks, compressed download size and runtime RAM are
different measurements again.

### Disk layout: the fewest partitions, each with headroom

The layout planner (`tools/layout_plan.py`) decides the partitions before the
image step writes anything. It runs in the payload preflight (seconds: it reads
file sizes only), prints one line per partition, and writes the plan to the run
as `image/layout-plan.json`:

- the units are the boot payload (`DH0`, volume `AMIWIND`), the CHIM world (one
  volume, files under `id1/chim/`, written in the order the engine reads them)
  and the open-world maps the region directory names (`id1/maps/vfNNNN.*`);
- the open-world maps go onto the CHIM world volume first (they are world data),
  then onto `DH0`, and only when neither has room is another world partition
  opened. The engine finds a map on any world volume: it adds `AW_WORLD0:id1` ...
  to its search path from `world/volumes.awv`, so both layouts load the same way;
- every partition is sized from its payload: the blocks its files take on
  classic FFS (header, data and extension blocks, one block per directory, root
  and bitmap blocks; the estimate equals what `xdftool` writes) plus a fixed
  free space, the headroom, rounded up to whole MiB;
- the headroom is 100 MiB per partition by default (builder setting
  `partition_headroom_mib` in `config/build-defaults.json` or a `--build-config`
  file, `--partition-headroom-mib` on the command line). The boot partition,
  where the game writes saves and settings, can keep its own
  (`boot_partition_headroom_mib`, `--boot-partition-headroom-mib`; by default the
  same);
- the Amiga limits win: if a partition's payload plus its headroom would reach
  2 GiB, another partition is opened; the headroom is never shrunk. Partition
  starts below 2 GiB and drives below 4 GiB are kept as before;
- a boot payload too large for one partition is split: the files the engine
  opens only through its search path move to a world volume in units (the CHIM
  interior store `id1/chimi/` whole, a map with its sidecars, an actor model
  with its mover, layout and tag files), the largest first, only until `DH0`
  fits with twice its headroom. They go onto the world volumes first (the CHIM
  world volume first), and only when none has room into a further partition
  (role `store`). Music, saves, settings and everything else stay on `DH0`. The
  plan line `Boot payload ... moved to world volumes` gives the units by kind
  and the largest boot folders; a payload that cannot fit even so is refused
  with its largest folders named. The plan counts what the image step adds
  later: the soundtrack, the media, the actor library, the room batches and
  the CHIM interior store.

When the staged payload still matches the plan, the image step follows it: the
same partitions with the same maps and boot units in each. Since v0.0.48, a
payload that changed after the plan (the room actor bake adds actor models
inside the image step; payload sharing then stores skins and files once) is
planned once more from the staging folder as it is, with one fit rule for
packing and the minimality check, and the partition count follows from that
(fewer or more than the early plan is normal). In the v0.0.48 release candidate
the boot payload went from 2.45 to 3.01 GB inside the image step and then lost
156 MB to payload sharing; three builds stopped on the old rule before this.
The [roadmap](ROADMAP.md#build-turnaround-first-24-october-2026) has the next
step: a layout that always falls back to a valid layout and never throws away
finished work. Otherwise the image step refuses when a partition's payload moved by more than
its headroom since the plan, and it writes every partition at the same time (one worker per
partition; one FFS volume is written by one `xdftool` process). After writing,
the disk-layout gate refuses:

- a partition with less free space than its headroom;
- a partition over 16 MiB that is mostly empty (more free space than its
  headroom plus half its size);
- a plan with more partitions than the payload needs (a partition of maps that
  would fit into another one below 2 GiB with that one's headroom).

Each refusal names the partition, its payload and its free bytes.
`image/build.json` records the settings and the plan in `disk_layout_plan`
(layout, headroom, per partition payload, size, free bytes and share).

The v0.0.46 release payload, planned and written this way (the partitions and
the drive written again from that build's staged files, 20 October 2026): 2
partitions on one drive of 3,076,554,752 bytes, `DH0` 1,524 MiB (payload
1,457,977,095 bytes, 105,678,336 bytes free) and `DW0` with the CHIM world and
the 1,348 frame maps, 1,410 MiB (payload 1,329,865,092 bytes, 105,166,336 bytes
free); the planned free space matched the written one to the byte. The release itself was built with
the earlier layout: 3 partitions on 3,623,911,424 bytes, one of them (`DW0`,
128 MiB) holding only the frame maps, 98 percent empty
(BUILD-PARTITION-GROWTH-UNGATED-36 in the [bug register](BUGS.md)).

`--disk-layout legacy` (config `disk_layout: legacy`) builds the earlier layout
for comparison: the open-world maps balanced against the boot payload onto
volumes of their own, every partition payload + 20 % + 16 MiB in 128 MiB steps.
Its mostly-empty partitions are printed and recorded as findings, not refused.

## Size ledger

From v0.0.42 every image build also says what its game data weighs, folder by
folder, in GiB (two decimals; the exact bytes are kept in the files). The
builder (`tools/size_ledger.py`) reads the image receipt and the file lists of
the partitions it just wrote and groups the payload into: classic maps, CHIM
world (CHIM frame maps, far terrain and the CHIM volume), NPC gallery, sound,
music, video, progs and other. It also lists each drive image's size. Each
partition's grouped bytes are checked against the bytes the image step read
back; a difference is named and the ledger is marked "partial". A run without an
image receipt (no image step) has no ledger; a receipt that cannot be read is
judged like a failed guard.

The result is compared with:

- the previous release, the one `tools/previous-release.json` names: the
  `size-ledger.json` of its release build in the same workspace (the newest
  passed run named `..._v<version>_release[-tryN]_<git>`), else the committed
  record `tools/size-baseline.json` when it is of that release (v0.0.45: 2.57 GiB
  of game data, of which the NPC gallery is 0.22 GiB). A record of another release
  is never compared: the build prints "release record: no record of vX" and the
  guard does not judge against a release; and
- a previous build, when you give its record: `--size-baseline FILE`
  (that run's `size-ledger.json`).

Until v0.0.45 the committed record was always used, whatever release it was of:
the v0.0.45 release build was compared with v0.0.41 and its guard failed on
0.44 GiB of CHIM world that v0.0.42 to v0.0.44 had already shipped, although every
folder was the size of v0.0.44's (BUILD-SIZE-GUARD-OLD-BASELINE-45).

Only builds with the same content are compared like-for-like. An image built
without the NPC gallery, a partial-area (MiniWind) image or one with excluded
content (for example video) is labelled, its differences are printed as
"NOT like-for-like" with the reason, and the size guard does not judge it.

The size guard: a folder that grew by more than `--size-growth-margin`
(default 0.05 GiB) against a like-for-like record needs a reason,
`--size-growth-reason TEXT`, which is recorded. Without one, an rc or final
build ends with exit code 4 (the stages passed; their outputs stay valid and
reusable), while a `-devN` build prints a warning. `--size-guard fail|warn|off`
overrides that choice (`off` is for debugging only).

The table is printed in the completion footer, written to `size-ledger.json`
in the run folder and copied into `build-summary.json` (`size_ledger`). It can
be shown again for any finished run without writing anything:

```text
python3 tools/size_ledger.py show RUN [--baseline OTHER/size-ledger.json]
```

and `python3 tools/size_ledger.py baseline RUN OUT` writes a new baseline
record from a finished run (refused when that run's ledger is partial).

## Completion footer

From v0.0.25-rc5, `build.sh` / `tools/build.py` print a completion footer after the
selected pipeline finishes. The first and last lines are dashes matching the
terminal width (80 columns when no width is available). Long paths/checksums
remain complete even if the terminal wraps them.

A successful image build reports:

```text
Compilation finished without errors
AmiWind v<version> | AGA conversion and image
Started: <local date and time, including UTC offset>
Finished: <local date and time, including UTC offset>
Elapsed: <hours> hrs <minutes> mins <seconds> secs
Python: <detected version>
Python environment packages (not all required by every recipe):
  <package>: <installed version>
Selected compiler/toolkit versions and identities (captured before build):
  <tool>: <detected version or identity explanation>
    Binary SHA-256: <recorded binary digest>
Worker budget: <count> | stage scheduling: <mode>
Compiler warning lines: <count> (engine log)
Warning details: <run>/logs/22-engine.log
File: AmiWind-v<version>.hdf
Path: <run>/image/AmiWind-v<version>.hdf
Size: <GiB> GiB (<exact bytes> bytes)
SHA-256: <64 hexadecimal digits>
Summary: <run>/build-summary.json
```

The success sentence appears only after all selected stages return successfully
and the completed output is readable and checksummed. A missing output or a
hashing failure makes the build fail. The HDF is read in 1 MiB chunks; hashing
does not load the whole image into RAM. A detected change to the file during
hashing also rejects success. The digest identifies the complete file, including
filesystem metadata; it is not a promise of reproducible bytes across builds.

## HDFs and emulator runners

From v0.0.27-rc2, full and asset-free image assembly generates both configuration
formats beside the HDFs. Each configuration mounts every required disk from the
verified layout; the boot drive comes first. An optional owned Kickstart path
is applied locally. Without it, select your own ROM before starting the emulator.
Docker exports also receive configurations with host-local paths.

The final terminal-width footer includes:

```text
--------------------------------------------------------------------------------
Your .hdf file(s):
1. <output>/AmiWind-v<version>.hdf
2. <output>/AmiWind-v<version>-world-01.hdf

FS-UAE and WinUAE runners:
1. FS-UAE: <output>/AmiWind-v<version>-FS-UAE.fs-uae
2. WinUAE: <output>/AmiWind-v<version>-WinUAE.uae
--------------------------------------------------------------------------------
```

Only disks actually required are listed. Saved build summaries include the same
artifact paths; `image/build.json` retains per-drive size, SHA-256, partitions
and readback results. Local paths and ROMs are not public release payloads.

## Timing

`Compilation started:` is printed once after prerequisite checks and setup,
before input/tool/source provenance hashing. The reported elapsed time covers
that hashing, all build stages and final output hashing. It excludes dependency
installation, prerequisite/input checks and any subsequent emulator session.
Start/end use the host's local time with a UTC offset. Elapsed time uses a
monotonic clock and therefore does not depend on wall-clock corrections.
The terminal displays whole elapsed seconds; JSON retains milliseconds. Hours
continue beyond 24 instead of wrapping at midnight.

The footer ends with the build profile: wall and CPU time, average cores
against the job budget, the critical path, the slowest stages and idle-core
warnings, and any stages reused from an earlier run. Per-stage detail is in
`build-profile.json`; see [BUILD_PROFILE.md](BUILD_PROFILE.md).

## Compiler and toolkit inventory

From rc6 the footer repeats the pre-build observations for the tools selected
by the current recipe: GNU make, Amiga GCC, vasm, QCC, ericw map tools, FFmpeg and
amitools commands where selected. Python and installed conversion-package
versions are shown separately as environment information. An asset-free build
does not claim to use all the tools or packages of the full conversion pipeline.

Detected versions are never replaced with the recorded reference versions.
QCC is identified by its binary SHA-256 where no reliable version is recorded;
amitools commands report that their CLI lacks a version flag, alongside the
installed amitools package version. Other unknown/failed probes remain labelled
as such. Binary hashes identify the selected executable bytes, not all shared
libraries or the complete SDK. The JSON also retains selected executable paths.
No extra version probes run at completion. A failed build still lists the
selected environment; this is an inventory, not proof that every tool ran.

The footer also names four content selections, all recorded in
`build-summary.json` (`build_environment`) and the run's `build-state.json`:
`NPC gallery selection` (`enabled` unless `--no-npc-gallery`),
`World flora (trees and grass)` (`enabled` unless `--no-tree-sprites`),
`Harvestable mushrooms` (`enabled` unless `--no-harvest`) and `Extra towns`
(the shipped towns, `vivec_arena (shipped by default)`, plus any `--extra-town`;
`--no-extra-town` and `--only-core-towns` are named as left out); `asset-free` for
`--dry-run`, `not applicable (terrain stage)` for `--stage terrain`. Any
opt-out marks a debugging build that does not match a release; see
[LINUX_BUILD.md](LINUX_BUILD.md#world-flora-default). After an image, the
footer line `Harvestable mushrooms in the image` gives the maps admitted by the
heap check, the plants and the shared models (`harvest` in `build-summary.json`
and the image's `build.json`; details in `image/harvest/harvest-staging.json`).

## Warnings

Warnings are listed separately from success/failure. The footer counts recognized
`warning:` / `warning <number>:` diagnostic lines in the engine stage log; it
is not a count of unique defects. When the count is nonzero, it prints the log
path. Full compiler messages remain in that log and the live build output.
Other conversion/tool warnings remain in their own stage logs. A zero engine
count is not a claim that every stage was warning-free. Missing/unreadable
engine logs are reported as not counted. No compiler warnings are suppressed,
promoted to errors, or repaired by this reporting change.

## Failures, modes and saved results

A caught build failure or cancellation gets its own title and timing, with
`Output: no completed output verified`. A partial HDF is not labelled complete
and is not assigned a final checksum. Existing error messages and exit statuses
remain. Failures before the build starts keep their existing prerequisite/setup
messages. An uncatchable process termination or machine failure cannot print a
footer.

`--dry-run` is explicitly labelled an asset-free, non-playable build; it compiles
the engine/preflight and packages a test HDF. It does not validate game conversion.
Terrain-only output is a directory, so it reports total file bytes and marks a
single-file SHA-256 as not applicable. Check/plan/setup-only modes create no
build-completion receipt. A successful compile/image result does not establish
native runtime or playtest success. Optional emulator launch follows the footer
and retains its separate result.

`build-summary.json` contains the status, mode, version, both timestamps,
`elapsed_seconds`, human-readable elapsed time, output identity and compiler
warning count/log paths. `build_environment` records the interpreter, packages,
selected tool versions/hashes/paths, worker budget, stage scheduling mode and
`jobs_warning`: the one warning printed at the start when an explicit `--jobs N`
exceeds the usable CPU threads (otherwise null; the build still runs N workers).
It is saved atomically when the run directory exists.
If saving the receipt fails, the terminal reports that separately. The receipt
contains local paths: keep it with private build evidence outside the source
checkout. Public release documentation uses sanitized results only.

This does not alter the existing production image acceptance gates. Native
Windows build/image output passed at the [dated checkpoint](history/validation/VALIDATION-WINDOWS-2026-10-02.md);
v0.0.27 also passed hosted Windows launcher parity. Those results do not certify
every build mode or full-game reliability; see the remaining limits in
[the Windows roadmap](WINDOWS_BUILD_ROADMAP.md).


### Release readiness

Before the first stage every AGA build prints a release readiness block: each
option a release candidate or final would refuse, with its tracker ID. It
lists the private-test waivers (taken from the builder's own refusal check,
`require_private_test_version`, so nothing is listed twice: accepted actor or
stair findings, quick-test exclusions such as `--no-npc-gallery`, MiniWind and
direct-start options), an accepted entity loss (`--accept-entity-loss`), retired
flags used with `--override`, and debugging opt-outs of shipped features
(`--no-tree-sprites`, `--only-core-towns`, `--skip-dressing`,
`--no-entity-baseline`). The block is saved in `build-state.json` as
`release_readiness`.

```text
========================================================================
Release readiness: what a release candidate or final would refuse in this build
  1. --allow-known-actor-ground-findings [private-test waiver]: known actor ground findings accepted -> VIVEC-ARENA-ACTORS-32 (--readiness-id)
  2. --exclude npc-gallery [skipped shipped feature]: quick test build leaves out NPC gallery -> NO TRACKER ID (name it: --readiness-id exclude-npc-gallery=ID)
  3. --accept-entity-loss [accepted entity loss]: reason: harvest loss on six cells, HARVEST-CHIM-REGION-LOSS-41 -> HARVEST-CHIM-REGION-LOSS-41 (reason text)
  3 release blocker(s) until fixed, or maintainer-accepted for the release with their tracker links
========================================================================
```

Every item needs a tracker ID registered in `docs/bugs/bugs.json`: the IDs of
`--accept-known-stair-findings`, the IDs written in the `--accept-entity-loss`
reason, or `--readiness-id KEY=ID[,ID]` (KEY is the option without its dashes,
as the block prints it; an exclusion group also answers to its other names,
e.g. `no-npc-gallery`). A full build with an item that has no registered ID
stops before any stage. MiniWind area tests (never a release) and `--plan`,
`--check` and `--dry-run` print the block without that requirement. An empty
block reads `none: nothing here stops a release candidate or final`. Origin:
v0.0.41-dev5 passed with a waiver, an accepted plant loss and no NPC gallery,
and the final found all three on its first run
([BUILD-RELEASE-READINESS-HIDDEN-41](bugs/BUILD-RELEASE-READINESS-HIDDEN-41.md)).

Private diagnostic builds with explicitly accepted actor findings use the footer
`Private test image assembled; production actor gate DID NOT PASS`. They do not
print `Compilation finished without errors`. Their summary records
`validation: private-test-only` and includes the actor acceptance receipt; the
HDF name ends in `-private-test.hdf`. A completed execution status is distinct
from passing the production contact gate. The raw contact report stays failed.

The NPC stage heading reads `npc-gallery (pre-baking in-game character models...)`
in both serial and parallel builds, including image recovery. The saved stage
identifier and log filenames remain `npc-gallery` for recovery and cache compatibility.

NPC gallery progress reports cumulative `reused`, successfully `converted`,
`failed`, and `remaining` model counts, plus elapsed conversion seconds. The
initial dependency/cache scan is reported separately. Completion counts reflect
finished jobs immediately, rather than input-order results waiting on slow models.
