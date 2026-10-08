# TEST-WORKER-SYSPATH-32: Pool workers started from tests import tools/mwad.py instead of the mwad package

## Status: 8 October 2026

Open. Found by the image-parallel work. The builder itself is not affected.

## Symptom

Spawned worker processes inherit the parent's `sys.path`. Test modules put `tools/` first, so in
their workers `tools/mwad.py` shadows the `src/mwad` package and a worker can run different code
from the parent.

## Where

Tests that start the shared pool (`build_parallel.process_pool`, spawn workers) after inserting
`tools/` at the front of `sys.path`.

## How it happened

`tools/mwad.py` and the `src/mwad` package share a name; test modules order the import path for the
parent process only.

## Why it was not caught

Tests had not used real spawned workers before the parallel image work.

## Reproduction

In a test that inserts `tools/` first, run a pool task that imports `mwad` and print its file.

Second manifestation (8 October 2026, found by the Seyda Neen recorded-stage work):
`tests/test_build_defaults.py` (and `tests/test_builder_stage_entries.py`) put `tools/` ahead of
`src/` on `sys.path` in the test process itself, so `tools/mwad.py` hides the `src/mwad` package
there too. `tests/test_actor_ground.py` then fails to import when it runs after either module in
the same process. The gate passes only because of its default test order.

## Repair

Mitigation: the worker identity tests pin `src/` first. Not yet fixed for every test module.
Proposed fix: tests never put `tools/` before `src/` (one shared test helper sets the import path),
plus a test that imports `mwad` after each module that changes `sys.path` and checks it is the
package.

## Verification

Identity tests pass with `src/` first.

## Prevention

A test that a spawned worker imports the same `mwad` as the builder, and a test that `mwad` is
still the package after every module that changes `sys.path` (any test order).
