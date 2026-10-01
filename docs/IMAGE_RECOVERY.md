# Recover an rc3 image-stage failure

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

Keep the failed run, particularly `build-state.json`, `intro-scene`,
`world-terrain`, `world-survey` and `music`. Apply the complete rc7 source update
after the original process has exited. Use a fresh output name:

```bash
bash build.sh \
  --recover-image-from /path/to/build/failed-rc3-run \
  --data-files '/path/to/Morrowind/Data Files' \
  --tools-dir /path/to/amiwind-tools \
  --workspace /path/to/amiwind-tests \
  --name rc7-image-recovery
```

Repeat original non-default `--hands`, `--bitmap-paper-ink` or `--intro-captions`
settings. Explicit SDK/tool options remain available. `--check` verifies
prerequisites and retained terrain without building; `--plan` prints the two
commands. Actual recovery also hashes current game inputs and compares them
with the original run before either command runs.

Recovery is limited to a failed rc3 full build with all 22 pre-image stages
recorded as passed. It checks recorded source against the published rc3
baseline, compatible build choices, complete survey/region receipts, the
published region directory and every published terrain BSP hash. It rejects
missing/corrupt terrain or mixed game inputs. It never executes arbitrary
command strings from the old receipt.

The new run compiles the current versioned engine/preflight and assembles the
image from retained scene/music outputs. No terrain conversion is scheduled.
The old run and failed image directory are preserved; the image builder copies
its input scene into new staging. The new receipt records the recovery origin
and hashes. Completion time covers recovery provenance, engine/image work and
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
Otherwise the complete report, tolerance, identities, measured contacts and
all recorded BSP/model hashes must match exactly. A changed/new/missing failure
or payload fails. Invalid classification, corrupt model or missing-owner errors
cannot be accepted through this option. The source audit report remains failed
and is never overwritten by the new report.

`actor-ground-acceptance.json` and the completed image's `build.json` separately
record `owner-accepted-known-findings`, the report hashes, unresolved count and
`production_gate_passed: false`. The HDF receives a `-private-test` suffix; the
build footer and summary JSON explicitly identify private-test-only acceptance.
This does not repair floating NPCs or satisfy the production placement gate.

On new full builds, the early comparison excludes only not-yet-built `vfNNNN`
terrain hashes; final image acceptance checks all hashes. Never change the
baseline merely to get past an unexpected difference: inspect the new report.
Keep the old run and reports if any later gate fails. No terrain conversion is
required for another image recovery attempt.
