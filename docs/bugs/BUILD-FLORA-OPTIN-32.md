# BUILD-FLORA-OPTIN-32: a from-scratch build without --tree-sprites leaves out the trees and grass every release ships

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (not shipped at the time of writing; a from-scratch build with the default options
is still to confirm it). Found by the from-scratch v0.0.32-dev1 build: its image step stopped
after 23 minutes.

## Symptom

The image step stops with "Missing/unsafe sprite asset: progs/aw_flora/f_18299fefe9e2791c.spr".
The Seyda Neen maps reused under the recorded exception (BUILD-SEYDA-REGEN-30) reference flora
sprites, and v0.0.31 ships 76 of them, but a build without `--tree-sprites` never makes them.

## Where

`tools/build.py`: world flora (`world-flora-assets`, `world-flora`) is opt-in through
`--tree-sprites`; the from-scratch recipe used for dev1 did not pass it.

## How it happened

Trees and grass arrived in v0.0.28 as an opt-in builder option and stayed opt-in although every
release since ships them. Release images were built by patching earlier images, so the recipe
never had to carry the option (BUILD-NOT-FROM-SCRATCH-32).

## Why it was not caught

No from-scratch build ran between v0.0.28 and v0.0.32, and nothing records which builder options
a release needs; the missing sprites show only at the very end of the image step.

## Reproduction

From-scratch build at 5aacdc0 without `--tree-sprites`, with the recorded Seyda exception.

## Repair

- World flora is built by default in every real AGA build (`tools/build.py`,
  `world_flora_status`): the `world-flora-assets` and `world-flora` stages run and the image gets
  `--world-flora`, `--town-flora-source-index` and `--town-flora-scene-report`, the same pattern as
  the NPC gallery. `--no-tree-sprites` leaves flora out for debugging only and prints a warning;
  `--tree-sprites` is still accepted and has no effect; giving both is an error. Asset-free
  `--dry-run`, `--stage terrain` and the rc3 image recovery make no flora, as before.
- The measured Balmora layout repair (`--balmora-cache`, since v0.0.27) had been passed only
  together with `--tree-sprites`, so a build without it also skipped that repair. It is now passed
  in every AGA image build, with or without flora.
- `build-state.json` records `world_flora` (`requested`, `status`, `policy_sha256`), and the build
  summary footer and `build-summary.json` name the flora selection next to the NPC gallery
  selection.
- The image step's sprite check (`tools/sprite_heap.py`) now says "World flora was not built"
  when maps place `progs/aw_flora/*.spr` sprites that are missing, with the count, the first
  names and the cause (`--no-tree-sprites`, or a hand-run image step without `--world-flora`),
  instead of only "Missing/unsafe sprite asset".

## Verification

- `tests/test_build_defaults.py`: the default command list has every stage the release payload
  needs, including both flora stages; the image gets every shipped input (flora, Balmora cache,
  gallery, 3D hands, hidden-surface cull, shared sky, canonical land, night table sources) with
  the shipped values; `--tree-sprites` gives the same command list as the default;
  `--no-tree-sprites` removes only the flora stages and inputs; every `--no-*` option is
  "DEBUGGING ONLY"; every builder option is classified against what a release ships (a new
  option fails until classified); dry-run and terrain recipes stay flora-free; the receipt and
  summary record flora; the missing-flora message names the cause. Turning flora or the
  Balmora cache back into an opt-in fails these tests (checked by editing the builder in a
  scratch copy).
- Updated: `tests/test_world_flora_integration.py`, `tests/test_builder_stage_entries.py`
  (every stage parses the default and `--no-tree-sprites` command lines) and
  `tests/test_build_setup.py` (its receipt fixture now carries the flora policy).
- Full suite in Docker: 1,435 tests pass; the 3 skips are the Windows-only tests.
- Pending: a from-scratch default build (no flora option) compared file by file with the
  release payload.

## Prevention

The from-scratch check compares the payload with the last release file by file; a builder
config file states the release's options instead of a remembered command line.
`tests/test_build_defaults.py` fails when a shipped feature leaves the default build or a new
builder option is not classified against the release.
