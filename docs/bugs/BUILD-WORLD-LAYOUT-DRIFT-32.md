# BUILD-WORLD-LAYOUT-DRIFT-32: the world region layout depends on the town maps, so a from-scratch build lays out a different world

## Status: 8 October 2026

Fixed in source on v0.0.32-dev; layout verified against v0.0.31; not shipped at the time of writing. Found by the
first from-scratch build of v0.0.32-dev1, where it stopped the build at `world-terrain`.

## Symptom

`world-terrain` stops after 0.2 s: `prepare_world_regions.py` raises "Refinement parent must be
an unsplit cell". The two recorded refinements (`config/world-region-refinements.json`, cells
-4,-4 and -3,2, added in v0.0.28-rc1) expect an unsplit cell, but the fresh survey has already
split both cells in two.

The cause is larger than the two cells. The survey's geometry ceiling was not fixed:

| Survey | Ceiling (source triangles) | Taken from | Cells 1 / 2 / 4 / 8 divisions | World regions |
|---|---:|---|---|---:|
| Shipped layout (earlier full builds) | 140,801 | Seyda Neen sn012 | 1,078 / 314 / 12 / 0 | 2,526 |
| dev1 from scratch | 115,288 | Balmora bm020 | 811 / 513 / 70 / 10 | 4,623 |

So a from-scratch build would lay out the open world in about 1.8 times as many regions as the
shipped one, with different map numbers, and never match the released image.

## Where

`tools/survey_vvardenfell.py`: `limit = a.triangle_limit or max(...calibration...)`;
`tools/build.py` calls the survey without `--triangle-limit`.

## How it happened

The ceiling was measured as the largest existing town region. The town region layouts have
changed since the shipped survey (27 of 89 calibration regions differ, Seyda Neen sn025-sn034 are
gone, sn012 went from 140,801 to 93,601), so the ceiling moved with them.

## Why it was not caught

No from-scratch build ran between v0.0.28 and v0.0.32 (BUILD-NOT-FROM-SCRATCH-32); the world
regions were reused, and no test pins the survey settings.

## Reproduction

Full build from scratch with the repository builder at 5aacdc0; compare
`world-survey/world-survey.json` `settings.source_triangle_limit` with the shipped survey.

## Repair

The ceiling is now a recorded builder setting:

- `config/world-region-refinements.json` holds `survey_source_triangle_limit` (140,801), next to
  the two refinements that belong to that layout.
- `tools/build.py` always passes it to the survey as `--triangle-limit`.
- `tools/prepare_world_regions.py` refuses a survey made with any other ceiling (or none) and
  says which value to use. A refinement that does not fit now names the cell and how the survey
  split it.

What this fix does not do: it brings back the shipped world exactly, including its known memory
limits. 140,801 is the size of Seyda Neen's sn012 region, which the heap model already showed
about 1.68 MB over budget in v0.0.29. The fixed ceiling makes the layout reproducible, not safer.
A better layout is the world streamer's job, not this builder's.

## Verification

- Tests (Docker): `test_world_regions`, `test_build`, `test_builder_stage_entries` and
  `test_build_jobs` pass (28 tests). New tests check that a survey with another ceiling is
  refused, that the recorded ceiling and refinement parents are the shipped ones, and that the
  builder passes the ceiling.
- Fresh survey of the game data with the fixed ceiling (20 s with the mesh cache):
  - All 1,404 cells are divided exactly as in the earlier full builds' survey.
  - The master and archive hashes and the terrain bounds are the same.
- The planned world (2,532 maps) was compared with the region directory `id1/world/regions.awr`
  read from the v0.0.31 image.
  - All 2,532 maps have the same name, position, core and coverage.
  - Not compared: the height of each map's origin, which `world-terrain` fills in from the
    terrain.
- The rebuilt `id1/world/regions.awr` of the v0.0.32-dev1 from-scratch build is byte-identical to
  v0.0.31's (SHA-256 0660b2f6...1d89).
- My mistake on the way: the fix was first committed after running only four test modules; it
  broke eight recovery tests (their synthetic survey had no ceiling). The next full gate caught
  it and the fixture was fixed in the following commit. Full gates run before every commit now.

## Prevention

A test that the builder passes the recorded ceiling; the from-scratch comparison checks the world
directory.
