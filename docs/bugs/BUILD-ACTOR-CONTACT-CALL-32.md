# BUILD-ACTOR-CONTACT-CALL-32: Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt). Release blocker for the public builder.

## Symptom

`tools/check_scene_actors.py` calls `convert(maps/'seyda.bsp', maps)`, but `convert` has needed
`source_map`, `palette` and `ericw_bin` keyword arguments since v0.0.27, so the stage stops with
a TypeError on every from-scratch build.

## Where

`tools/check_scene_actors.py` line 34.

## How it happened

Signature changed without updating the caller.

## Why it was not caught

No from-scratch build was run between releases; release images were patched up from older images.

## Reproduction

Run the builder past the bsp stage.

## Repair

Fixed in source (v0.0.32-dev, 511da01): `prepare_seyda_regions.convert_builder_scene` is the one
region-conversion call used by both the image step and `check_scene_actors.py`, which gained
the arguments it needs; `build.py` passes them.

## Verification

From-scratch build reaches and runs actor-contact. Tests: `tests/test_builder_stage_entries.py`
(every stage parses the exact command line build.py generates, in three variants; actor-contact
runs end to end on a synthetic scene with signature-enforcing stand-ins) and
`tests/test_tool_call_signatures.py` (4,057 calls between modules bind to current signatures;
the only stale call before the fix was this one).

## Prevention

Builder stage smoke tests on synthetic inputs in the suite.
