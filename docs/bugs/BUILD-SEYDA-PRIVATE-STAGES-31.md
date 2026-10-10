# BUILD-SEYDA-PRIVATE-STAGES-31: repository builder cannot regenerate the shipped Seyda Neen maps

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.31-dev |
| Where | image step (tools/build_aga.py), Seyda Neen maps |
| Reproduction | always |
| Duplicate of | [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md) |
| Persists in | v0.0.31-dev (last seen) |
| Severity | high: The repository builder cannot regenerate the shipped Seyda Neen maps. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Closed: duplicate of [BUILD-SEYDA-REGEN-30](../journals/BUG_JOURNAL-v0.0.31.md#build-seyda-regen-30-public-build-cannot-regenerate-seyda-neen-7-october-2026),
recorded again while preparing v0.0.31. Current status lives there. Note: the image
build has had `--canonical-land-source` since v0.0.30-dev5; the remaining gap is
the three private stages below.

## Symptom

A full image build from this repository does not reproduce the Seyda Neen
sub-cell maps that the playtest and release images contain, and as written it
stops before Seyda: terrain culling is enabled by default, but the image
build passes no canonical terrain source to the Seyda region conversion.

## Where

`tools/build_aga.py image` (Seyda region conversion call), the Seyda region
tools, and the later stages that produced the shipped maps.

## How it happened

The shipped Seyda maps are the end of a seven-stage chain: the full-town mesh
map and its partition (public tools), the image finalisation passes (public),
then a canonical terrain fit, a palette remap and a ground-winding repair that
were run as one-off scripts outside the repository. Later releases cloned
earlier images and patched individual files instead of rebuilding maps, so the
public path was never exercised end to end.

## Why it was not caught

Release checks verified the published source archive and the playtest image
separately; nothing required the repository builder to reproduce the image.

## Reproduction

Run `tools/build_aga.py image` from this repository with Seyda culling enabled
(the default) and no canonical terrain source.

## Repair

Bring the three missing stages into the repository as tested builder steps,
pass the canonical terrain source in the image build, and add the release gate
in [RELEASE_WORKFLOW.md](../RELEASE_WORKFLOW.md): a clean repository build must
reproduce the release payload.

## Verification

Pending: a full repository image build compared file by file with the release
image.

## Prevention

The release gate above.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

<!-- END GENERATED CATEGORY -->
