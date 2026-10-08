# PLAYTEST-PAYLOAD-COVERAGE-32: The v0.0.32-dev1 playtest has no first-person hands and no harvest

## Status: 8 October 2026

Open (process). Found by the payload diff of the v0.0.32-dev1 playtest against v0.0.31.

## Symptom

The dev1 playtest build lacks file classes v0.0.31 ships: the 40 first-person hand models
(`.mdl`), `hand-models.awh`, `hand-torch.awt`, the 371 harvest catalogues and the shared harvest
models. In play there are no first-person hands and no harvestable mushrooms.

## Where

The v0.0.32-dev1 playtest package. The builder on the v0.0.32 development line now makes both
classes (BUILD-HANDS-NOT-BUILT-32, BUILD-HARVEST-NOT-BUILT-32).

## How it happened

dev1 was built from a source snapshot (978475d, branched from 5aacdc0) that predates the merges of
the hand-catalog builder step (6741425) and the harvest step (6b9c2ff). A dev build was cut from a
snapshot without re-checking its release coverage against the last release.

## Why it was not caught

No packaging step compares a playtest payload with the last release. `tools/payload_coverage.py
check` exists (it lists missing features and release classes, with `--allow-known-gaps`) and is
tested in `tests/test_release_coverage.py`, but neither the builder (`tools/build.py`,
`tools/build_aga.py`) nor the packaging (`tools/package_dry_run.py`) runs it.

## Reproduction

`tools/payload_coverage.py check` on the dev1 payload manifest: the hands and harvest features and
their release classes are reported missing.

## Repair

Not yet. The fix to make: playtest and release packaging run `payload_coverage.py check` on the
finished payload against the last release, and a missing feature or release class blocks
packaging unless it is listed as a known issue of that build. dev2 and later are built from a
source that contains the hand and harvest steps.

## Verification

Pending: the next playtest payload shows no missing class, or only listed known issues.

## Prevention

The packaging gate above, with a test that a payload missing a release class is refused unless it
is listed as a known issue.
