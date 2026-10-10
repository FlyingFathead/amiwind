# Bug journal

Entries for v0.0.35 (from 10 October 2026). Older entries are frozen: [8 October 2026 to the v0.0.34 release](journals/BUG_JOURNAL-v0.0.34.md), [7 October 2026](journals/BUG_JOURNAL-v0.0.31.md) and [v0.0.29 and earlier](journals/BUG_JOURNAL-v0.0.29.md). The current status of every bug is in the [register](BUGS.md).

<!-- contents start -->
## Contents

- [CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM at about 1 frame per second on a slow 68040, 9 October 2026](#chim-slowcpu-frametime-33-balmora-on-chim-at-about-1-frame-per-second-on-a-slow-68040-9-october-2026)
- [ANIMKIT-TORCH-STANDING-35, 10 October 2026](#animkit-torch-standing-35-10-october-2026)
- [TEST-WORKER-SYSPATH-32, 10 October 2026](#test-worker-syspath-32-10-october-2026)
- [ANIMKIT-ACTOR-ABI-SITES-35, 10 October 2026](#animkit-actor-abi-sites-35-10-october-2026)
- [ANIMKIT-ITEM-TAG-FRAMES-35, 10 October 2026](#animkit-item-tag-frames-35-10-october-2026)
- [BUILD-CELL-PROGRESS-KEY-BUGS-35, 10 October 2026](#build-cell-progress-key-bugs-35-10-october-2026)
- [BUILD-POOL-ARG-UNFINGERPRINTED-35, 10 October 2026](#build-pool-arg-unfingerprinted-35-10-october-2026)
- [ANIMKIT-IMAGE-FORMATS-35, 10 October 2026](#animkit-image-formats-35-10-october-2026)
- [BUILD-SEYDA-REPORT-HOST-PATHS-35, 10 October 2026](#build-seyda-report-host-paths-35-10-october-2026)
- [BUILD-CHIM-KEY-UNDERDECLARED-35, 10 October 2026](#build-chim-key-underdeclared-35-10-october-2026)
- [BUILD-POOL-APPLY-READ-MISS-35, 10 October 2026](#build-pool-apply-read-miss-35-10-october-2026)
- [BUILD-SCENE-DIAGNOSTIC-COPY-35, 10 October 2026](#build-scene-diagnostic-copy-35-10-october-2026)
- [BUILD-POOL-READONLY-SCENE-WRITE-35, 10 October 2026](#build-pool-readonly-scene-write-35-10-october-2026)
- [BUILD-RESUME-OUTPUTS-DIFFER-35, 10 October 2026](#build-resume-outputs-differ-35-10-october-2026)
- [BUILD-RESUME-HAZARD-STATIC-35, 10 October 2026](#build-resume-hazard-static-35-10-october-2026)
- [BUILD-GALLERY-JSON-KEY-ORDER-35, 10 October 2026](#build-gallery-json-key-order-35-10-october-2026)
- [ANIMKIT-GROUND-CHECK-LAYOUT-35, 10 October 2026](#animkit-ground-check-layout-35-10-october-2026)
- [NPC-NO-RUN-ANIM-35, 10 October 2026](#npc-no-run-anim-35-10-october-2026)
- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35, 10 October 2026](#build-seyda-converted-not-staged-35-10-october-2026)
- [BUILD-IMAGE-STALE-PYTHONPATH-35, 10 October 2026](#build-image-stale-pythonpath-35-10-october-2026)
- [BUILD-REUSE-KEYS-TOO-BROAD-35, 10 October 2026](#build-reuse-keys-too-broad-35-10-october-2026)
- [Engine crash paths and engine table limits (BUILD-BUDGET-ENGINE-LIMITS-35 and fifteen more), 10 October 2026](#engine-crash-paths-and-engine-table-limits-build-budget-engine-limits-35-and-fifteen-more-10-october-2026)
- [CHIMPORT-NO-SHARED-POOL-35, 10 October 2026](#chimport-no-shared-pool-35-10-october-2026)
- [Engine review fixes (ENGINE-PAK-HEADER-TRUST-35 and thirteen more), 10 October 2026](#engine-review-fixes-engine-pak-header-trust-35-and-thirteen-more-10-october-2026)
- [MWAD data-reader review fixes, 10 October 2026](#mwad-data-reader-review-fixes-10-october-2026)
- [CHIM streaming crash paths from a source review, 10 October 2026](#chim-streaming-crash-paths-from-a-source-review-10-october-2026)
- [BUILD-FLORA-FALLBACK-RETRY-35, 10 October 2026](#build-flora-fallback-retry-35-10-october-2026)
- [BUILD-CACHE-OWNER-FAILS-STAGE-34 and the published-release check, 10 October 2026](#build-cache-owner-fails-stage-34-and-the-published-release-check-10-october-2026)
- [BUILD-SURVEY-KEY-CONFIG-35, 10 October 2026](#build-survey-key-config-35-10-october-2026)
- [BUILD-SCHEDULER-TABLE-KEY-35, 10 October 2026](#build-scheduler-table-key-35-10-october-2026)
- [CI-SUITE-TWICE-33, 10 October 2026](#ci-suite-twice-33-10-october-2026)
- [HARVEST-BITTERCOAST-29 and HARVEST-PLANTS-IN-COLLISION-33, 10 October 2026](#harvest-bittercoast-29-and-harvest-plants-in-collision-33-10-october-2026)
- [MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 for v0.0.34, 10 October 2026](#mesh-lod-open-seams-33-and-chim-strider-ring-33-for-v0034-10-october-2026)
- [BUILD-SEYDA-REGEN-30 fixed in source: no recorded Seyda Neen input, 10 October 2026](#build-seyda-regen-30-fixed-in-source-no-recorded-seyda-neen-input-10-october-2026)

<!-- contents end -->

## CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM at about 1 frame per second on a slow 68040, 9 October 2026
[CHIM-SLOWCPU-FRAMETIME-33](bugs/CHIM-SLOWCPU-FRAMETIME-33.md): owner play report of the private CHIM
preview (engine 0d8bf4f, world format 0.4, v0.0.32 disks) on the slow accelerator preset: unplayable.
Same-session A/B/A at the five Balmora cameras (FS-UAE cycle-exact 68040 at 49.7 MHz, relative):
CHIM 1.06-1.61 s per frame, legacy 2.03-4.13 s, so not a CHIM regression; slow-hardware work is
deferred to after v0.0.33. The brush-model clip walk is 65-72 percent of the CHIM view. New:
[RENDER-FOG-PASS-COST-33](bugs/RENDER-FOG-PASS-COST-33.md) (fog and day-night sky pass 150-210 ms),
[SERVER-FRAME-ARRIVAL-33](bugs/SERVER-FRAME-ARRIVAL-33.md) (226 ms server frame at the arrival
camera), [DEBUG-TP-CHIMTOWNS-33](bugs/DEBUG-TP-CHIMTOWNS-33.md) (dbg tp after chim_towns 0).

## ANIMKIT-TORCH-STANDING-35, 10 October 2026

[ANIMKIT-TORCH-STANDING-35](bugs/ANIMKIT-TORCH-STANDING-35.md): with the animation kit, guards hold their torch only
while standing; the walk and run models have no torch attachment. Known in v0.0.35.

## TEST-WORKER-SYSPATH-32, 10 October 2026

[TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md): fixed. The release suite record (one interpreter) failed
twice on the actor ground bake test: a spawned pool worker inherited a path with `tools/` before `src/`, imported
`tools/mwad.py` as `mwad` and died unpickling its task. Pool workers now put `src/` first when they start; a
regression test covers it. Builds were not affected (their path already lists `src/` first).

## ANIMKIT-ACTOR-ABI-SITES-35, 10 October 2026

[ANIMKIT-ACTOR-ABI-SITES-35](bugs/ANIMKIT-ACTOR-ABI-SITES-35.md): the third image step in a row stopped on a tool
that assumed the previous 8 or 21 actor frames, this time the guard torch companions. A sweep of every site
that reads actor frames found two more that would have stopped later builds (the CHIM frame map actor contact
and two 32-frame ceilings). One helper now answers every site from the model's declared layout, kit guards get
an idle-group torch companion, and the payload preflight checks actor layouts first.

## ANIMKIT-ITEM-TAG-FRAMES-35, 10 October 2026

[ANIMKIT-ITEM-TAG-FRAMES-35](bugs/ANIMKIT-ITEM-TAG-FRAMES-35.md): the new preflight check found that kit
residents' weapon and shield tag tables had one row per kit sample instead of per model frame, and the model they
fight in had none: armed residents fought without drawing their items. The tags now follow each model's frames
and the engine reads the fighting model's tag.

## BUILD-CELL-PROGRESS-KEY-BUGS-35, 10 October 2026

[BUILD-CELL-PROGRESS-KEY-BUGS-35](bugs/BUILD-CELL-PROGRESS-KEY-BUGS-35.md): a self-naming label made the
cell-progress key cover all of docs/, so each bug registration stopped builds. Fixed in the key scan; an advisory
stage never stops a build.

## BUILD-POOL-ARG-UNFINGERPRINTED-35, 10 October 2026

[BUILD-POOL-ARG-UNFINGERPRINTED-35](bugs/BUILD-POOL-ARG-UNFINGERPRINTED-35.md): balmora was never reusable once
the shared storage pool passed 512 MiB: its `--npc-model-pool` folder was hashed as a stage input. The pool now
counts as its token for every stage (it is content-addressed); the read trace refuses any pool read that is not a
keyed lookup, and the resident bake's pool key covers all the code it runs.

## ANIMKIT-IMAGE-FORMATS-35, 10 October 2026

[ANIMKIT-IMAGE-FORMATS-35](bugs/ANIMKIT-IMAGE-FORMATS-35.md): the image step's palette overlay did not know the
animation kit's layout and item tag files and stopped late. Both formats are declared, and the payload
preflight now checks every staged file's format first.

## BUILD-SEYDA-REPORT-HOST-PATHS-35, 10 October 2026

[BUILD-SEYDA-REPORT-HOST-PATHS-35](bugs/BUILD-SEYDA-REPORT-HOST-PATHS-35.md): with the Seyda Neen preflight
repaired, the next default build stopped at the host-paths check: the converted `id1/seyda-regions.json`
named its inputs by absolute build path. The shipped file now names them relative to the image folder (same
schema and hashes as the recorded file); the full report stays in the build folder.

## BUILD-CHIM-KEY-UNDERDECLARED-35, 10 October 2026

[BUILD-CHIM-KEY-UNDERDECLARED-35](bugs/BUILD-CHIM-KEY-UNDERDECLARED-35.md): the CHIM stage ran the cell progress
tracker (8 files, 2 light_sources functions) as a subprocess whose name was written in two parts, so its
fingerprint left them out although the tracker writes a stage output; the read trace refused the reuse. The tracker
now runs as its own stage, cell-progress, with its own key; the fingerprint scan follows names built from literal
parts; build_audit reports uncovered reads of every stage.

## BUILD-POOL-APPLY-READ-MISS-35, 10 October 2026

[BUILD-POOL-APPLY-READ-MISS-35](bugs/BUILD-POOL-APPLY-READ-MISS-35.md): in a pool-mode build every reused stage
read tools/storage_pool.py through the reuse step and was then refused as the next build's reuse source. The reuse
step's own modules are no longer counted as inputs of a reused stage.

## BUILD-SCENE-DIAGNOSTIC-COPY-35, 10 October 2026

[BUILD-SCENE-DIAGNOSTIC-COPY-35](bugs/BUILD-SCENE-DIAGNOSTIC-COPY-35.md): npcs, hands, interior and intro were
never reusable: copying the previous scene, logs included, counted as reading another stage's diagnostics. A byte
copy of a diagnostic into a diagnostic is no longer a read; any other read still is.

## BUILD-POOL-READONLY-SCENE-WRITE-35, 10 October 2026

[BUILD-POOL-READONLY-SCENE-WRITE-35](bugs/BUILD-POOL-READONLY-SCENE-WRITE-35.md): a pool-mode resume failed in 17
s: npcs could not rewrite its own copy of seyda.bsp, because copytree copied the pool's read-only mode. Every
folder copy now goes through mwad.paths.copy_tree, which makes the new copy writable and never touches the pooled
file.

## BUILD-RESUME-OUTPUTS-DIFFER-35, 10 October 2026

[BUILD-RESUME-OUTPUTS-DIFFER-35](bugs/BUILD-RESUME-OUTPUTS-DIFFER-35.md): every v0.0.35 resume refused the stages
after a rerun scene-chain stage as 'outputs differ' without comparing a byte: the comparison gave up on any
non-reusable record. Records refused only for what they read are now compared; the reruns were identical apart from
logs.

## BUILD-RESUME-HAZARD-STATIC-35, 10 October 2026

[BUILD-RESUME-HAZARD-STATIC-35](bugs/BUILD-RESUME-HAZARD-STATIC-35.md): a resume stopped in area on 8 files census
had left out, although census had run again and written them. The rebuild hazard is now kept per stage and checked
against what really ran.

## BUILD-GALLERY-JSON-KEY-ORDER-35, 10 October 2026

[BUILD-GALLERY-JSON-KEY-ORDER-35](bugs/BUILD-GALLERY-JSON-KEY-ORDER-35.md): 3,460 NPC gallery files differed
between two builds only in JSON key order (cached results sorted, fresh ones not). Every gallery JSON writer now
sorts its keys.

## ANIMKIT-GROUND-CHECK-LAYOUT-35, 10 October 2026

[ANIMKIT-GROUND-CHECK-LAYOUT-35](bugs/ANIMKIT-GROUND-CHECK-LAYOUT-35.md): with the animation kit as the default,
the actor ground check refused resident models with more than their 8 idle frames and stopped the image step.
It now reads the model's kit layout and checks the idle poses.

## NPC-NO-RUN-ANIM-35, 10 October 2026

[NPC-NO-RUN-ANIM-35](bugs/NPC-NO-RUN-ANIM-35.md): in v0.0.34 companions and hostile NPCs walked but never ran:
release residents carried only idle frames. The animation kit is now the default (`--anim-kit on`), with
`dbg animkit` to inspect it and `--anim-kit off` for the previous frames.

## BUILD-SEYDA-CONVERTED-NOT-STAGED-35, 10 October 2026

[BUILD-SEYDA-CONVERTED-NOT-STAGED-35](bugs/BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): the first full v0.0.35
development build stopped at the image step's payload preflight after all its stages: the early preflight
required the Seyda Neen region table and special maps, which the same step converts later. The early
preflight now checks the files the image step writes itself before its frame maps as planned (the
conversion's plan, or the pinned recorded set); the later preflight checks them written. Verified read only
on the failed run's own staged files; the failed run is resumed with `--reuse-from`.

## BUILD-IMAGE-STALE-PYTHONPATH-35, 10 October 2026

[BUILD-IMAGE-STALE-PYTHONPATH-35](bugs/BUILD-IMAGE-STALE-PYTHONPATH-35.md): builder container images keep an
old builder copy on `PYTHONPATH`; a run of a newer mounted source without its own `PYTHONPATH` could import
old code silently, and one read the wrong version from it. Every build now runs an import guard (builder
code only from the source tree being built; other builder trees dropped from `PYTHONPATH` before any
stage), `tools/build.py --check-entry` is the read-only entry check for workers, and
`tools/build.py --developer-mode` checks the working version, the integration head, the storage pool, the
run name and the reuse plan before any stage.

## BUILD-REUSE-KEYS-TOO-BROAD-35, 10 October 2026

[BUILD-REUSE-KEYS-TOO-BROAD-35](bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md): the first v0.0.35 development build
reused 0 of 35 stages from the v0.0.34 build, and 0 of 3,551 gallery models. Every stage's own key had
really changed (sources in 35 stages, game inputs in 28, settings in 21), so nothing could be reused
safely, but the build only said so in its state file. A reuse preflight now lists, before any stage runs,
every rebuild with its reason and the changed files that touch it. It stops the build when a rebuild is
not explained (`--accept-rebuild` overrides), and `tools/build.py --reuse-plan OLD_RUN` runs it alone. The
gallery model key now covers the code its converter reaches, which also adds modules the old file list
left out. Build run names now carry date, version, purpose and commit.

## Engine crash paths and engine table limits (BUILD-BUDGET-ENGINE-LIMITS-35 and fifteen more), 10 October 2026

- [BUILD-BUDGET-ENGINE-LIMITS-35](bugs/BUILD-BUDGET-ENGINE-LIMITS-35.md): registered; fixed in source on
  v0.0.35-crash-fixes-2. Every map the image ships is counted the way the engine loads it (edicts, model and
  sound precaches, statics, scenery catalogue, visible entities, leaves) in the payload preflight and the image
  step; town budgets may only tighten the engine. Worst shipped map: 25 model slots left (vf1258).
- [ENGINE-MAP-NAME-OVERFLOW-35](bugs/ENGINE-MAP-NAME-OVERFLOW-35.md),
  [ENGINE-FRAME-TIME-FLOAT-35](bugs/ENGINE-FRAME-TIME-FLOAT-35.md),
  [ENGINE-LOADGAME-SYSERROR-35](bugs/ENGINE-LOADGAME-SYSERROR-35.md): registered; fixed in source.
- [ENGINE-SUBMODEL-LIMIT-32](bugs/ENGINE-SUBMODEL-LIMIT-32.md): fixed in source (map unavailable instead of a
  precache overflow).
- [ENGINE-FATAL-PATH-SWEEP-35](bugs/ENGINE-FATAL-PATH-SWEEP-35.md): the sweep of every fatal path data or a
  player can reach, with the table of what was fixed and what was left and why. Fixed in source from it:
  [ENGINE-SOUND-NAME-SYSERROR-35](bugs/ENGINE-SOUND-NAME-SYSERROR-35.md),
  [ENGINE-MODEL-NAME-SYSERROR-35](bugs/ENGINE-MODEL-NAME-SYSERROR-35.md),
  [ENGINE-WRITE-OPEN-SYSERROR-35](bugs/ENGINE-WRITE-OPEN-SYSERROR-35.md),
  [ENGINE-CBUF-OVERFLOW-35](bugs/ENGINE-CBUF-OVERFLOW-35.md),
  [ENGINE-COM-TOKEN-UNBOUNDED-35](bugs/ENGINE-COM-TOKEN-UNBOUNDED-35.md),
  [ENGINE-ENTITY-TEXT-UNBOUNDED-35](bugs/ENGINE-ENTITY-TEXT-UNBOUNDED-35.md),
  [ENGINE-LEAF-LIMIT-UNCHECKED-35](bugs/ENGINE-LEAF-LIMIT-UNCHECKED-35.md),
  [ENGINE-QC-ARGS-SYSERROR-35](bugs/ENGINE-QC-ARGS-SYSERROR-35.md) and
  [CHIM-STATIC-PLACE-HOST-ERROR-35](bugs/CHIM-STATIC-PLACE-HOST-ERROR-35.md).

## CHIMPORT-NO-SHARED-POOL-35, 10 October 2026

[CHIMPORT-NO-SHARED-POOL-35](bugs/CHIMPORT-NO-SHARED-POOL-35.md): the CHIMporter kept its own unit store in
each run folder beside the builder's shared hashed storage pool, so a second run folder or workspace converted
and stored everything again. `tools/chimport.py` now takes the builder's `--storage-pool`, `--reuse-mode` and
the new `--storage-pool-dir` (also for `tools/build.py`; build config key `storage_pool_dir`, environment
`AMIWIND_STORAGE_POOL`): units and whole cells are stored once and linked, and every run reports stored vs
linked bytes. Default off. Also new: `--region NAME` and a lock that refuses a second `run` on one folder.

## Engine review fixes (ENGINE-PAK-HEADER-TRUST-35 and thirteen more), 10 October 2026

A source review of the engine found fifteen problems; fourteen are fixed in source on the v0.0.35 line, each
with a regression check. High: [ENGINE-PAK-HEADER-TRUST-35](bugs/ENGINE-PAK-HEADER-TRUST-35.md) (the pak loader
trusted its header and directory) and [ENGINE-STACK-UNCHECKED-35](bugs/ENGINE-STACK-UNCHECKED-35.md) (no
check of the start-up stack). Medium: [ENGINE-C2P-ROWSTRIDE-35](bugs/ENGINE-C2P-ROWSTRIDE-35.md),
[ENGINE-VID-UPDATE-FIRST-RECT-35](bugs/ENGINE-VID-UPDATE-FIRST-RECT-35.md),
[ENGINE-VA-UNBOUNDED-35](bugs/ENGINE-VA-UNBOUNDED-35.md),
[ENGINE-FILEBASE-UNBOUNDED-35](bugs/ENGINE-FILEBASE-UNBOUNDED-35.md),
[ENGINE-UDP-ADDRESS-OVERFLOW-35](bugs/ENGINE-UDP-ADDRESS-OVERFLOW-35.md). Low:
[ENGINE-FLOATTIME-DIV64-35](bugs/ENGINE-FLOATTIME-DIV64-35.md), [ENGINE-ANGLEMOD-RANGE-35](bugs/ENGINE-ANGLEMOD-RANGE-35.md),
[ENGINE-HARVEST-MESSAGE-BOUND-35](bugs/ENGINE-HARVEST-MESSAGE-BOUND-35.md),
[ENGINE-SCENE-NAME-BOUND-35](bugs/ENGINE-SCENE-NAME-BOUND-35.md), [ENGINE-FOPEN-TEXT-MODE-35](bugs/ENGINE-FOPEN-TEXT-MODE-35.md),
[ENGINE-UNLINK-STUB-35](bugs/ENGINE-UNLINK-STUB-35.md) and [ENGINE-GAMMA-POW-35](bugs/ENGINE-GAMMA-POW-35.md) (the
gamma table no longer links pow, so the FPU gate lost its last pow exception). Open:
[AUDIO-DMA-CLOCK-DRIFT-35](bugs/AUDIO-DMA-CLOCK-DRIFT-35.md), the mixer's estimated audio position; to be
measured before any change.

## MWAD data-reader review fixes, 10 October 2026

- [MWAD-STRING-DECODE-35](bugs/MWAD-STRING-DECODE-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-TEXT-WRITER-LF-35](bugs/MWAD-TEXT-WRITER-LF-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-DELETED-RECORD-35](bugs/MWAD-DELETED-RECORD-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-WALK-ORDER-35](bugs/MWAD-WALK-ORDER-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-READER-CHECKS-35](bugs/MWAD-READER-CHECKS-35.md): registered and fixed in source on v0.0.35-mwad-fixes.

## CHIM streaming crash paths from a source review, 10 October 2026

A review of the CHIM engine found paths where bad data or a full pool ended the map. Each is now a failed load, a wait or a counted fallback, with a native test: [CHIM-PACK-LRU-STREAM-35](bugs/CHIM-PACK-LRU-STREAM-35.md), [CHIM-BRUSH-BAD-DATA-35](bugs/CHIM-BRUSH-BAD-DATA-35.md), [CHIM-EFRAG-UNCAPPED-35](bugs/CHIM-EFRAG-UNCAPPED-35.md), [CHIM-GRAFT-FAIL-NO-FLOOR-35](bugs/CHIM-GRAFT-FAIL-NO-FLOOR-35.md), [CHIM-ZONE-UNSATISFIABLE-EVICT-35](bugs/CHIM-ZONE-UNSATISFIABLE-EVICT-35.md), [CHIM-MIPTEX-OFFSET-UNCHECKED-35](bugs/CHIM-MIPTEX-OFFSET-UNCHECKED-35.md), [CHIM-ALIAS-STATIC-HUNK-35](bugs/CHIM-ALIAS-STATIC-HUNK-35.md), [CHIM-VIEW-LEAF-NO-PVS-35](bugs/CHIM-VIEW-LEAF-NO-PVS-35.md).

## BUILD-FLORA-FALLBACK-RETRY-35, 10 October 2026

## BUILD-CACHE-OWNER-FAILS-STAGE-34 and the published-release check, 10 October 2026

[BUILD-CACHE-OWNER-FAILS-STAGE-34](bugs/BUILD-CACHE-OWNER-FAILS-STAGE-34.md): unit cache entries owned by another
user stopped the v0.0.34 release build four minutes in. A refused cache read or write no longer fails a stage, and
a build preflight checks cache ownership, free space and the game data before any stage. The previous-release
check ([RELEASE-PREVIOUS-FIXES-MISSING-33](bugs/RELEASE-PREVIOUS-FIXES-MISSING-33.md)) now requires the
published release commit and prints the merge that fixes a missing one.

## BUILD-SURVEY-KEY-CONFIG-35, 10 October 2026

[BUILD-SURVEY-KEY-CONFIG-35](bugs/BUILD-SURVEY-KEY-CONFIG-35.md): the world survey re-ran on the v0.0.34
build because its key held every configuration file: a path built from a loop name over a written-out list
counted as the whole folder. Loop names with written-out string values now name their files (world survey 56
-> 6 data files; world terrain, world UI and CHIM narrowed the same way).

## BUILD-SCHEDULER-TABLE-KEY-35, 10 October 2026

## CI-SUITE-TWICE-33, 10 October 2026

[CI-SUITE-TWICE-33](bugs/CI-SUITE-TWICE-33.md): hosted CI ran the full test suite twice per
revision (source checks job and the Docker builder job). The Docker check now runs a short set of builder
test modules; `--full-suite` keeps the previous method.

## HARVEST-BITTERCOAST-29 and HARVEST-PLANTS-IN-COLLISION-33, 10 October 2026

[HARVEST-BITTERCOAST-29](bugs/HARVEST-BITTERCOAST-29.md): seen again in v0.0.33 at the same Bitter Coast
cluster. Cause: the pick ray stops on a tree's convex root collision that also contains two of the three
mushrooms. The engine now keeps a plant as the target when the solid that stopped the ray contains the
plant's own centre; a new island-wide pick audit (51 of 934 plants unpickable before, 0 after) gates the
image. The enclosing solids are tracked as
[HARVEST-PLANTS-IN-COLLISION-33](bugs/HARVEST-PLANTS-IN-COLLISION-33.md).

## MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 for v0.0.34, 10 October 2026

[MESH-LOD-OPEN-SEAMS-33](bugs/MESH-LOD-OPEN-SEAMS-33.md): the owner saw the strider's open hull again in
v0.0.33; it shipped as a known issue (the repair was held), not a regression. v0.0.34 takes the repair
and its seam audit, with the strider boundary-locked at 0.45, which fits CHIM Balmora's ring
([CHIM-STRIDER-RING-33](bugs/CHIM-STRIDER-RING-33.md)). The audit now measures the profile the town and
CHIM converters compose, not the group profile alone.

## BUILD-SEYDA-REGEN-30 fixed in source: no recorded Seyda Neen input, 10 October 2026

[BUILD-SEYDA-REGEN-30](bugs/BUILD-SEYDA-REGEN-30.md): the builder no longer needs the recorded v0.0.31 Seyda
Neen maps. `--seyda-recorded DIR` is optional; without it a CHIM build converts the Seyda Neen region maps from
your data, without the terrain visual cull, and checks the CHIM frame maps against them. The cull cannot complete
from scratch ([BUILD-SEYDA-CULL-STABLE-32](bugs/BUILD-SEYDA-CULL-STABLE-32.md), reproduced again and measured;
open for the legacy builder) and is not needed for maps that never ship. The actor-contact stage passes from data
(65 Seyda Neen maps, 759 s at 12 workers); a full from-scratch image build is pending.
