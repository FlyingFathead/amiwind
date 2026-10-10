# BUILD-SEYDA-CULL-STABLE-32: From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | actor-contact stage, region sn000 terrain cull |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32, v0.0.33 (last seen) |
| Severity | critical: From-scratch builds stop in Seyda Neen terrain culling; covered only by the recorded exception. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open, for the legacy builder only. Reproduced on 9 October 2026 with a current from-scratch scene
(region sn000, the same message). An experimental fallback that kept each non-settling placed face
whole (not shipped) showed the cut cannot complete from scratch: 130 to 2,852 placed faces per
region do not settle, water cuts fail the same way, the canonical cull always reports its result
as incomplete, which blocks the region installation, and one region (sn005) was still being culled
after 40 minutes. CHIM builds no longer need this cull: their converted Seyda Neen region maps are
only the frame maps' check reference and are made without it
([BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md)). A legacy build with Seyda Neen still needs
`--seyda-recorded`.

## Status: 8 October 2026

Open. Found by the from-scratch build after the builder fixes. Part of the Seyda Neen regeneration gap (BUILD-SEYDA-REGEN-30); covered by the recorded exception for v0.0.32.

## Symptom

The actor-contact stage fails on region sn000 in `canonical_bsp_cull._stable_local_parts`:
"Serialized placement fragment is not repeat-stable". This is the first time a from-scratch
build reached it; the stage crashed earlier before (BUILD-ACTOR-CONTACT-CALL-32).

## Where

`tools/canonical_bsp_cull.py` (Seyda Neen canonical terrain cull).

## How it happened

Unknown.

## Why it was not caught

The stage never ran from scratch since v0.0.27.

## Reproduction

Run the builder from scratch with your own data.

## Repair

Not yet; Seyda Neen is rebuilt by the CHIM streamer, so this is handled by the recorded
exception until then.

## Verification

Pending.

## Prevention

From-scratch builds before every release.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

Related bugs in other categories:

- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28

<!-- END GENERATED CATEGORY -->
