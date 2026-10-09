# BUILD-SEYDA-REGEN-30: Public build cannot regenerate the Seyda Neen sub-cells

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 7 October 2026, in v0.0.29 |
| Where | image step Seyda Neen region conversion (tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29, v0.0.32 (last seen) |
| Severity | high: Builder cannot regenerate shipped Seyda maps; recorded exception ships them instead. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |
| Playtest version | v0.0.29 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; recorded exception for v0.0.31 and again for v0.0.32 (owner decision, 8 October 2026). The
shipped Seyda Neen stages are used as a recorded input; Seyda Neen is rebuilt by the world streamer
(v0.0.33), so the legacy builder is not fixed. Report page written 8 October 2026 from the
[journal entry](../BUG_JOURNAL.md#build-seyda-regen-30-public-build-cannot-regenerate-seyda-neen-7-october-2026)
and the closed duplicate [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md).

## Symptom

A full image build from the repository does not reproduce the shipped Seyda Neen sub-cell maps.

## Where

`tools/build_aga.py image` (Seyda region conversion) and the Seyda region tools; the stages that
produced the shipped maps.

## How it happened

The shipped Seyda maps are the end of a chain whose last three stages (a canonical terrain fit, a
palette remap and a ground-winding repair) ran as one-off scripts outside the repository. Later
releases cloned earlier images and patched files instead of rebuilding maps. Details in
BUILD-SEYDA-PRIVATE-STAGES-31; from-scratch builds also stop in the Seyda terrain cull
([BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md)).

## Why it was not caught

Nothing required the repository builder to reproduce the release image
([BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md)).

## Reproduction

Run the repository builder from scratch with your own data and compare the Seyda Neen maps with the
release.

## Repair

Recorded exception: the image step installs the recorded v0.0.31 Seyda Neen maps. Condition
(8 October 2026): the exception must be honoured byte for byte, or any later change to those maps
must be intended and documented here. dev1 broke it: later image passes rewrote the recorded maps
([BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md)). The real repair is the
world streamer's Seyda Neen.

Builder option (v0.0.32-final-blockers): `--seyda-recorded DIR`, where `DIR/id1` holds the recorded
maps from the owner's own v0.0.31 image (`maps/sn000.bsp` .. `sn063.bsp`, `intro_docks.bsp`,
`sncourt.bsp`, `seyda-regions.txt`, `seyda-regions.json`; `maps/seyda.bsp` optional), checked
against `config/seyda-recorded-v0.0.31.json`. The recorded files are owner-provided input and are
never shipped with the source. Every later image pass keeps them byte for byte; the builder checks
it after each pass (`tools/recorded_stage.py`).

Intended differences from v0.0.31 (each named here and in the pin):

| File | Shipped as | Reason |
| --- | --- | --- |
| `maps/seyda.bsp` | a copy of the recorded fallback region `maps/sn029.bsp` (3,892,672 bytes) instead of v0.0.31's complete town (4,411,968 bytes) | Owner decision (option A), 8 October 2026. The builder's own region conversion writes the same alias. The v0.0.32 release actor audit refuses the complete town's seven actor copies; the recorded region maps with this alias pass (24 of 24 placements grounded). `dbg tp seydaneen` and region streaming use `seyda-regions.txt` and are unchanged. |
| `maps/sn019.bsp`, `maps/sn026.bsp`, `maps/sn035.bsp` | the recorded maps, byte for byte, through a temporary pre-CHIM bypass of the strict world-map heap gate | Owner decision A, 8 October 2026: they exceed the modelled reserve allowance only (dev1 estimate -238,180, -104,356 and -12,148 bytes), not the allocation ceiling. A temporary bypass for the legacy builder, removed when Seyda Neen moves to CHIM (milestone M2); listed by name and SHA-256 in `config/heap-bypass.json` ([HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md)). |

## Verification

Pending: from-scratch build whose Seyda Neen maps equal the recorded stage (with the one named
alias). Source checks: `tests/test_recorded_stage.py`.

## Prevention

The from-scratch comparison ([DEVELOPMENT.md](../DEVELOPMENT.md)) checks maps under a recorded
exception against the recorded bytes.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

Related bugs in other categories:

- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built

<!-- END GENERATED CATEGORY -->
