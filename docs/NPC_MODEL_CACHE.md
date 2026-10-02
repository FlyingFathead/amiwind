# Persistent NPC model conversion cache

Normal builds and image recovery MUST include the complete NPC/creature gallery.
This optimization reuses verified conversion work; it never omits models,
reduces catalogue coverage, changes polygon budgets or bypasses validation.
Any exception to either gallery's mandatory coverage/quality requires a specific
documented case and explicit approval from the project owner, outside the builder.
Build time, disk pressure and convenience are not approval.

## What rc10 implements

`npc-gallery: pre-baking in-game character models...` identifies the stage.
Its gallery models are inspection/rest-pose presentations of the game characters;
this stage does not replace the separate gameplay animation conversion.
The next message reports verified cache hits and conversions actually required.
Final `gallery-cache.json` records hits, conversions, dependency/conversion timing,
worker time, capacity estimates and optional rc9 import counts.

The default cache is `WORKSPACE/cache/npc-gallery-v1`, outside individual build
runs. `--gallery-cache PATH` selects a separate private cache. New build outputs
remain independent copies. No cache payload enters public source packages.
Unchanged models are copied from verified entries; misses use the unchanged
converter and existing bounded retry policy. A complete catalogue, footprint
models, inspection map and strict model-budget audit are produced every time.

The key includes the full appearance specification, resolved mesh/texture bytes,
absent preferred DDS candidates, skeleton/animation input, palette, converter
source identity, protected quality settings, Python/platform and relevant package
versions. Changing a head only invalidates appearances depending on that head;
global converter or quality-policy changes may conservatively invalidate more.
A cache hit requires matching identity, model size and SHA-256 and matching
vertex/triangle counts. Invalid or incomplete entries are rebuilt. Model data
and its receipt are atomically replaced; the receipt is the commit marker.
Interrupted writes cannot become accepted partial models. Model pairs completed
before cancellation remain usable in the persistent cache.

No additional runtime work is moved onto the Amiga. Final complete MDL models,
geometry budgets and gallery coverage retain their existing representation.
Dagoth Ur's protected quality profile remains unchanged.

## Completion-driven scheduling in v0.0.25

Independent gallery models use a bounded completion queue with at most twice the
worker budget submitted and unfinished. Freed slots are refilled before results
are reported; a slow early model cannot hold later submissions behind it. Other
conversion stages that require input order continue using their existing helper.

Progress shows disjoint cumulative reused, converted and failed counts; their
sum is the completion count. Converted means successful fresh conversion, not
attempts including failures. Remaining is total minus completed. A failed model
is printed immediately and still blocks the final complete-gallery gate. Results
are restored to original spec order before catalogues, audits and footprints are
written, so worker completion order does not leak into exported content.

`gallery-cache.json` includes `failed`, `completed` and
`scheduler: bounded-completion-v1`, alongside existing hit and conversion counts.
The model converter, cache implementation and cache keys are unchanged from rc10;
existing compatible entries remain reusable without an import or cache migration.
This is a scheduling improvement, not a measured complete cold-build speedup.

## Reuse a stopped rc9 build

Keep the rc9 build running until its output can be retained, or stop it with
Ctrl+C and wait for the shell prompt before applying new source. Never replace
source under a running build. Preserve the entire run directory, including
`build-state.json` and `npc-gallery/`.

Pass `--gallery-seed-run /path/to/stopped-rc9-run` with an rc10 build/recovery.
This imports completed model/receipt pairs only after verifying the old run's
full game input inventory, recorded converter sources, Python/package versions,
palette and per-model protected quality settings and output hashes. It accepts
passed, failed or cancelled rc9 runs; a running run is rejected. Missing or
partial model pairs are converted normally. Incompatible provenance stops with
an explanation instead of silently trusting old files. Omit the seed option for
an ordinary cache lookup/conversion. Loose model files without build provenance
are not migration inputs.

The original failed rc3 run is still the source of retained terrain/music for
`--recover-image-from`; the stopped rc9 run supplies optional character models.
They serve different purposes and neither retained run is modified.

## Capacity and limits

Before model conversion, the gallery checks available storage for its output,
new cache entries, auxiliary map/catalogue files and a margin, combining totals
when output/cache share a filesystem. Hits use verified sizes; misses use a
conservative bound for the existing single-frame gallery format. An rc9 import
also checks its copy footprint. Insufficient capacity stops without omitting
content. This is a gallery-stage storage check, not a guaranteed peak estimate
for a complete HDF build or shared-memory scratch; check those budgets separately.
No automatic cache eviction removes required output or gallery coverage. Retain
completed run outputs; cache lifecycle management can be added independently.

This first optimization helps repeated builds and compatible rc9 recovery.
An empty cache still converts all required appearances. Component-level shared
baking, runtime modular assembly and whole-world terrain caching are separate
work, not claimed implementations in rc10.

## Next experiment: component reuse

**Mutable equipment is a requirement.** Looting a corpse or changing equipment
must change the actor's appearance; equipped/base gallery snapshots cannot
represent arbitrary partial removal. Complete-model reuse in rc10 is an interim
host optimization. The [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md)
requires source-derived reusable parts and per-actor equipment state, with
measured load/change-time composition or attached-part rendering. Do not
pre-bake every possible outfit combination.

The supplied base master has 2,675 humanoid records. The current equipped/base
resolver produces 3,500 humanoid appearances using 942 component NIF paths across
68,001 part uses. The additional 260 creature records share 51 model specs.
These are measured catalogue counts, not a promised speedup.

Profile assembly, simplification, per-face texture sampling and encoding before
changing their algorithms. A part's triangle quota depends on its outfit, and
shell preservation depends on actor height: a filename-only component cache is
incorrect. Preserve complete source dependencies, pose/scale, quota, palette and
quality policy. Require byte-identical complete outputs for host-only reuse.
Later load-time composition needs separate loading/RAM/frame-time measurements;
separate per-frame body-part drawing can repeat culling/lighting/skin setup even
at the same polygon count. No runtime assembly change is included here.

## Measured rc10 check

On the retained base-master input and unchanged converter, the full warm-cache
gallery completed in 89.501 seconds with 3,551 hits and zero conversions. The
earlier rc9 cold gallery took 3,622.619 seconds. These are local observations,
not a cross-machine speed guarantee; the warm run used three workers and the
cold run six. First conversion remains expensive. All 3,551 models and all
7,106 non-map payload files were byte-identical. The threaded inspection-map
light compiler changed lightmap packing; all 464 faces, their lighting samples
and other BSP lumps matched. No terrain or target-runtime speedup is claimed.

Keep [recoverable checkpoints](BUILD_RECOVERY_STORAGE.md) outside transient
working storage; the cache does not make an ephemeral workspace persistent.

## v0.0.25 validation

The completion-queue test holds the first model until a later job beyond the
initial submission window runs. This passes without starving that later job.
All 404 source tests pass. A full real-data gallery run reused all 3,551 rc10
cache models with zero conversions or failures; all 7,106 non-map payload files
and catalogue/audit bytes match rc10. All 464 inspection-map faces and their
actual lighting samples match; threaded lightmap packing/padding differs.
These checks establish reuse and output preservation, not a measured speedup
for a complete cold gallery. Both native hand modes compile as asset-free images.
