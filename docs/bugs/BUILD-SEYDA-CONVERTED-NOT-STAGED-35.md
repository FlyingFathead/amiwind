# BUILD-SEYDA-CONVERTED-NOT-STAGED-35: A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | Image step: early payload preflight before the Seyda Neen region conversion (build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: Every default full build stopped after all its stages, at the image step (50 min into the first v0.0.35 build); the recorded path too. |
| Family | Seyda Neen recorded stage (`seyda-recorded`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.35-dev1 full build (source 901f8e9) |
| From commit | source 901f8e9, engine 901f8e9, CHIM world 901f8e9 |
| CHIM engine version | CHIM 0.1.0, engine 901f8e9, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Repair in v0.0.35 development (not shipped).

## Symptom

The first full v0.0.35 development build (source 901f8e9, the default CHIM build with Balmora and Seyda
Neen, without `--seyda-recorded`) built all 34 stages before the image step in 50 minutes. The image step's
payload preflight then stopped it after 5.8 seconds:

```
chim-inputs: CHIM frame map inputs are not staged: seyda-regions.txt, maps/intro_docks.bsp, maps/sncourt.bsp
```

## Where

- `tools/build_aga.py`, `image()`: the payload preflight runs as soon as the scene copy, world terrain,
  scenery and flora are staged. The Seyda Neen region conversion (`prepare_seyda_regions.convert_builder_scene`)
  runs further down in the same step and writes `seyda-regions.txt`, the 64 region maps, `intro_docks.bsp`,
  `sncourt.bsp` and the fallback `seyda.bsp`.
- `tools/payload_preflight.py`, `check_chim_inputs`: it required those files to be staged already.

## How it happened

The payload preflight first ran at the start of `finalize_image`, after the Seyda Neen conversion (or the
recorded install). The image resume work (BUILD-IMAGE-NO-RESUME-33) added a second, earlier call in
`image()`, so that a payload error shows in the step's first minute. The earlier call reached the
`chim-inputs` check before the step had written the Seyda Neen files that check reads. The order is the
same with `--seyda-recorded`: the recorded install also runs after the early call, so that path stops in
the same way. The v0.0.33 and v0.0.34 release builds passed because their source did not have the early
call yet. On the v0.0.35 line, the converted path became the default (BUILD-SEYDA-REGEN-30) and the image
resume branch was merged in the same week; no full image was built from the merged line before this build.

## Why it was not caught

The early call was tested on small staged payloads without a CHIM world, and the `chim-inputs` check was
tested on its own. No test ran the default plan's image options through the early preflight with a CHIM
world that holds Seyda Neen. The branch gates do not build a full image.

## Reproduction

`python3 tools/build.py --check-payload RUN` on the failed run (read only) with source 901f8e9 reports the
error above. The same command with the repair reports `8 checks, 0 errors`.

## Repair

The check is not weakened. The image step now tells the early preflight which files it will still write
before its CHIM frame maps (`build_aga.seyda_pending`):

- converted Seyda Neen (the default): the conversion's own plan from the layout `convert()` uses
  (`prepare_seyda_regions.regions()`: the region table with the regions in layout order, every region map,
  the special maps and `seyda.bsp`). The plan is only given when the conversion's inputs (the scene's
  complete `seyda.bsp` and `seyda.map`) are there; otherwise the files are reported missing as before;
- `--seyda-recorded DIR`: the pinned recorded set (`recorded_stage.check_source`, the same pin check the
  install makes, then `recorded_stage.shipped`), with the region names read from the recorded table;
- MiniWind images: none (they convert no Seyda Neen).

`check_chim_inputs` counts a planned file as staged and takes a planned region table's region names from
the plan. `--check-payload RUN` uses the same plan. The preflight at the start of `finalize_image`, after
the conversion or install, gets no plan and checks the written files. The repair changes only
`tools/build_aga.py` and `tools/payload_preflight.py`, which only the image step reaches, so a resumed
build reuses every other stage.

## Verification

- Failed run, read only, `--check-payload`: source 901f8e9 reports the `chim-inputs` error; the repaired
  source reports 8 checks, 0 errors (5.5 s).
- The plan equals what the same run's actor-contact stage converted with the same function: the region table
  text is identical and all 68 planned files are there.
- `tests/test_seyda_pending_preflight.py`: the default plan's image options (CHIM world, no recorded maps)
  pass the preflight on a staged fixture of the failed run's state; without the plan, or when the conversion
  cannot run, the same fixture still fails with the original message; a plan missing a region map or a
  special map is refused; the recorded plan comes from the pinned set and fails on a changed file; the image
  step passes the plan to the early call only, before the conversion, and not to `finalize_image`.

## Prevention

A payload check that runs before a step must be told what that step writes itself before the files are used,
and a test runs the default plan through it. Resume the failed build with `--reuse-from` the failed run; its
34 finished stages are reused.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Seyda Neen recorded stage (`seyda-recorded`). Recorded v0.0.31 maps are kept byte for byte; their heap headroom limits what can be added and the public builder cannot regenerate them. See [families](README.md#families).

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-PRIVATE-STAGES-31](BUILD-SEYDA-PRIVATE-STAGES-31.md): Repository builder cannot regenerate the shipped Seyda Neen maps
- [BUILD-SEYDA-RECORDED-REWRITTEN-32](BUILD-SEYDA-RECORDED-REWRITTEN-32.md): Later image passes rewrite the recorded Seyda Neen maps, so the exception is not the recorded stage
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [HARVEST-SEYDA-HEAP-REFUSED-32](HARVEST-SEYDA-HEAP-REFUSED-32.md): Seven Seyda Neen sub-cells lose harvest to the heap check, six of which had it in v0.0.31
- [HEAP-SEYDA-OVERLAP-32](HEAP-SEYDA-OVERLAP-32.md): Shipped Seyda Neen maps fail the current heap model (harvest and guard overlap allowance)
- [SEYDA-REGIONS-PIN-33](SEYDA-REGIONS-PIN-33.md): The recorded Seyda Neen region table differs from what the region layout writes, and its only copy was inside a build volume

Related bugs in other categories:

- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out

<!-- END GENERATED CATEGORY -->
