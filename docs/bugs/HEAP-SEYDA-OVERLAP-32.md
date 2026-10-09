# HEAP-SEYDA-OVERLAP-32: Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:heap |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Seyda Neen maps sn019, sn026, sn035 (world map heap gate) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31, v0.0.32-dev1 (last seen) |
| Severity | medium: Modelled heap reserve exceeded; allocation ceiling respected, temporary bypass in place. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the map loader rework (decoding without staging). v0.0.32 ships sn019, sn026 and
sn035 through a temporary pre-CHIM bypass of the strict heap gate (owner decision A, 8 October
2026): a temporary bypass for the legacy builder, removed when Seyda Neen moves to CHIM (milestone
M2). M2 must pass the strict heap gate without it.

## Symptom

seyda, sn018-sn021, sn026 and sn035 from the v0.0.31 image fail the v0.0.32 heap model, before
and after the loader change: the peak is the conservative allowance for harvest and guard
companion loads overlapping the map load, not the map itself.

## Where

`tools/check_world_map_heap.py` (allowance) and the shipped Seyda maps.

## How it happened

The allowance was raised after these maps shipped.

## Why it was not caught

The shipped Seyda maps are reused, not rebuilt (BUILD-SEYDA-REGEN-30).

## Reproduction

Run the heap check over the v0.0.31 Seyda maps.

dev1 image (8 October 2026): 2,738 of 2,741 maps clear the modeled allowance; minimum clearance -238,180
bytes. The image ran with the warning budget policy (private test).

Harvest admission (8 October 2026, dev1 image stage, repository heap check): with its harvest
catalogue sn018, sn019, sn020, sn021, sn026, sn035 and sn055 fail, so the harvest step ships them
without harvest. Without a catalogue sn019 (-238,180 bytes), sn026 (-104,356) and sn035 (-12,148)
still fail; sn018 (+7,212), sn020 (+92,652), sn021 (+26,540) and sn055 (+86,364) pass. Six of
the seven had harvest in v0.0.31, so this is a player-visible regression:
[HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md).

## Repair

Not yet: measure the real overlap in the emulator and set the allowance from it; Seyda Neen
is rebuilt by CHIM.

Temporary pre-CHIM bypass (owner decision A, 8 October 2026; from-scratch build dev3-r2 stopped at
"World-map heap clearance estimate failed: estimate_failed; sn019.bsp, sn026.bsp, sn035.bsp"):

- `config/heap-bypass.json`, section `temporary_pre_chim_heap_bypass`: each entry names the map,
  the SHA-256 of the exact recorded map (the same as in `config/seyda-recorded-v0.0.31.json`), the
  builder (`legacy`), `until: "CHIM M2 (Seyda Neen on CHIM)"`, this bug and the owner decision. A
  separate file rather than the recorded-stage pin: the pin says which bytes are shipped, this file
  is a gate decision with its own end date, and it is read by the heap gate whether or not the
  recorded stage is used.
- `build_aga.apply_map_budget_policy` (strict): an allowance-only failure of a listed map whose
  bytes match is accepted with the status "temporary pre-CHIM bypass", printed by the builder
  ("[heap] sn019.bsp: temporary pre-CHIM bypass (HEAP-SEYDA-OVERLAP-32; ends with CHIM M2 ...)").
  Any other failing map, a listed map with other bytes, an allocation-ceiling failure, or a build
  with the CHIM builder still fails; refusals are recorded with their reason.
- Receipts: `map-budget-policy.json`, `heap-watcher.json` and `build.json` record the bypassed maps,
  their clearance and end date; the status is `estimate_passed_with_temporary_pre_chim_bypass`,
  `production_memory_gate` reads "passed with temporary pre-CHIM bypass: sn019.bsp, sn026.bsp,
  sn035.bsp" and `modeled_allowance_passed` stays false.
- Allowed for release versions (the file is a repository input, no command-line switch); the
  private `--map-budget-policy warning` stays limited to -devN builds.

Known in v0.0.32: three Seyda Neen sub-cells ship over the modelled heap reserve (allocation ceiling
respected) through the temporary pre-CHIM bypass; harvest stays off in them
(HARVEST-SEYDA-HEAP-REFUSED-32).

## Verification

- `tests/test_heap_bypass.py`: a listed map with its exact bytes passes and is recorded (never a
  clean pass); changed bytes fail; an unlisted map fails; an allocation-ceiling failure fails even
  when listed; the CHIM builder refuses the bypass; the shipped entries equal the recorded maps'
  hashes and end with CHIM M2; the image step passes the map bytes and records the bypass.
- Pending: the next from-scratch build passing the heap gate with exactly these three maps bypassed.

## Prevention

Heap check on reused maps in every build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

Related bugs in other categories:

- [ESTIMATE-HEAP-STALE-32](ESTIMATE-HEAP-STALE-32.md): World estimate heap coefficients were fitted to the old loader model
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions

<!-- END GENERATED CATEGORY -->
