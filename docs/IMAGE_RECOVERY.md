# Recover an rc3 image-stage failure

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.

**First prerequisite: sufficient build capacity.** Before starting, verify
usable space for all required models/content, intermediates, staging copies,
temporary images, final outputs, verification copies and a safety margin. Check
the actual output filesystem and quota. RAM-backed scratch also consumes the
process/container memory budget; it is not extra independent disk capacity.
If space is insufficient, provide capacity before expensive conversion begins.
Do not skip NPC models or gallery creation to make the build fit.

**All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.**

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

rc3 can finish the full terrain conversion and fail image assembly with
`Incomplete world/journal conversion receipt`. The world-UI receipt writer
included `regions.awr`, owned by world terrain, while its validator correctly
expected only `map.awm`, `journal.awj`, `entries.dat` and `quests.awq`.
rc6 records only those four generated files and retains strict validation.
rc7 adds its own region-name table to the owned-file set; terrain output remains
separate.
The regression fixture includes a terrain directory, an unrelated subdirectory,
repeat generation and a corrupted journal payload.

New full builds generate and validate world UI, then prepare a small copied
actor payload and check its contact before world-terrain. The early check uses
actual converted maps/models, creates the Seyda subregions, annotates source
identities and applies the same grounding baker. It leaves the input scene
untouched. The rc6 baker reproduces 23 strict failures on the retained rc3 scene. The rc7
mesh-aware fitter corrects initial placement before this unchanged audit.
Final image assembly repeats the complete audit. Content fingerprinting,
filesystem limits and image readback also remain required.

## Preserve and recover

**Recovery MUST include the NPC gallery by default, even when the retained run
omitted it. Conversion time and disk size are not reasons to skip it.** All
original NPCs/creatures and required assets remain necessary for a complete game;
only explicit `--no-npc-gallery` permits a debugging-only inspection-gallery
omission. It never removes required world NPC content.

Keep the failed run, particularly `build-state.json`, `intro-scene`,
`world-terrain`, `world-survey` and `music`. Apply the complete rc10 source update
after the original process has exited. Use a fresh output name:

```bash
bash build.sh \
  --recover-image-from /path/to/build/failed-rc3-run \
  --data-files '/path/to/Morrowind/Data Files' \
  --tools-dir /path/to/amiwind-tools \
  --workspace /path/to/amiwind-tests \
  --name rc10-image-recovery
```

Repeat original non-default `--hands`, `--bitmap-paper-ink` or `--intro-captions`
settings. Explicit SDK/tool options remain available. `--check` verifies
prerequisites and retained terrain without building; `--plan` prints the three default
commands. Actual recovery also hashes current game inputs and compares them
with the original run before any command runs.

Recovery is limited to a failed rc3 full build with all 22 pre-image stages
recorded as passed. It checks recorded source against the published rc3
baseline, compatible build choices, complete survey/region receipts, the
published region directory and every published terrain BSP hash. It rejects
missing/corrupt terrain or mixed game inputs. It never executes arbitrary
command strings from the old receipt.

The new run compiles the current versioned engine/preflight, converts the required
NPC gallery, then assembles the image from retained scene/music outputs. No terrain conversion is scheduled.
The old run and failed image directory are preserved; the image builder copies
its input scene into new staging. The new receipt records the recovery origin
and hashes. Completion time covers recovery provenance, engine/gallery/image work and
final hashing, not the original terrain run or prerequisite recovery checks.

Disk space is still required for the copied scene and image staging. Recovery
provenance guards are covered by synthetic fixtures. A full rc7 game HDF has
not been validated here; consult the current [validation receipt](validation/rc7-source.json). The owner reported a completed rc3 private-test HDF
from the image-only hotfix in 144.664 seconds; its actor gate remained failed.

## Explicit private-test acceptance

This option was introduced for the rc3/rc6 unresolved findings. It remains an
explicit diagnostic mechanism, not the normal rc7 correction path. Do not pass
the old report to a newly corrected payload. For a separately reviewed current
failure report, the diagnostic option is:

```text
--allow-known-actor-ground-findings /path/to/reviewed/actor-initial-contact.json
```

Use the report produced by the current failed image, not a historical report
with a matching count. The checker reruns normally. Zero findings pass normally.
Otherwise the report, tolerance, identities and measured contacts must match
exactly (recorded BSP/model hashes as described below). A changed/new/missing failure
or payload fails. Invalid classification, corrupt model or missing-owner errors
cannot be accepted through this option. The source audit report remains failed
and is never overwritten by the new report.

`actor-ground-acceptance.json` and the completed image's `build.json` separately
record `owner-accepted-known-findings`, the report hashes, unresolved count and
`production_gate_passed: false`. The HDF receives a `-private-test` suffix; the
build footer and summary JSON explicitly identify private-test-only acceptance.
This does not repair floating NPCs or satisfy the production placement gate.

On new full builds one approved report serves both checks, so one image pass
suffices. The early actor-contact check compares everything except the
not-yet-built `vfNNNN` terrain hashes. The image step compares the findings:
every row (map, reference, pose samples, gaps, support), every error and the
counts must equal the approved report; payload hashes are not compared there,
because image assembly rewrites map and model bytes and world maps were never
part of the approved findings. Any new, changed or missing finding, or a new
grounded actor, refuses the waiver. Release candidates and final versions refuse
the option. Never change the baseline merely to get past an unexpected
difference: inspect the new report.
Keep the old run and reports if any later gate fails. No terrain conversion is
required for another image recovery attempt.

## Default NPC gallery: required unless explicitly disabled

Every normal AGA game build and image recovery includes the NPC/creature gallery.
It is a debugging and regression-inspection tool, not optional content selected
silently by the builder. A missing catalogue, selected model, footprint,
inspection map or budget receipt fails the default build.

Only the owner's explicit `--no-npc-gallery` flag permits an exceptional
debugging build without it, for example to isolate a gallery-specific failure.
This must not be used as a time/space optimization. The build receipt, final
summary and image metadata record the choice; the console explains
that the gallery was disabled. The separate asset-free CI/dry-run recipe does not
contain owned game assets and therefore cannot include the game catalogue.

The `npc-gallery` stage converts the complete source catalogue and compiles
`charplane.bsp`, with bounded model-budget retries and byte-specific allowances.
It reads the reserved scene palette after Census; its own files live in a separate
output tree. World-terrain waits for it, exposing failures before the expensive
island pass. Image assembly checks the required file inventory and every checksum,
stages existing greetings, then verifies the final filesystem payload on readback.
A gallery visual inspection is still required; conversion success is not visual
approval of every model.

Recovery reuses terrain and music but creates the missing gallery in the new run.
The first recovery with this fix therefore has a substantial additional conversion
stage. An older image's missing catalogue never implies an opt-out. rc10 uses a verified persistent model cache across runs while still assembling
each new output independently. See [cache identity, compatible rc9 import and
capacity checks](NPC_MODEL_CACHE.md).


**Warning: gallery omission is for debugging builds only. All NPCs and their
required assets remain necessary for a complete game. `--no-npc-gallery` skips
inspection-only conversion/packaging; it must never remove world NPC placements,
models, dialogue or other gameplay dependencies, or be advertised as a complete
content profile. Normal builds include the NPC gallery for debugging and
regression inspection. This requirement does not claim that every original
world NPC has already been converted or placed by the current demake.**
