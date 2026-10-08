# BUILD-FINALIZE-TORCHTEST-32: The image step fails at its very end: finalize_image uses an undefined torch test report

## Status: 8 October 2026

Fixed in source on v0.0.32-dev and the dev1 build source. Found by the v0.0.32-dev1 from-scratch build.

## Symptom

After all four partitions were written (44 minutes), the image step stopped with "NameError: name
'torchtest_report' is not defined" in `finalize_image`.

## Where

`tools/build_aga.py` `finalize_image` (reads the other staging reports from disk but not the torch test one).

## How it happened

The image step was split into `image()` and `finalize_image()` in v0.0.29; the torch test report stayed a local of
`image()`.

## Why it was not caught

No full image was built by the builder since the split; images were patched (BUILD-NOT-FROM-SCRATCH-32).

## Reproduction

Any full image build that reaches the receipt.

## Repair

`finalize_image` loads `torchtest-staging.json` like the other staging reports.

## Verification

A stdlib undefined-name check over the builder finds no other case (nested closures excepted); the dev1
image rebuild (r7) must pass the receipt step.

## Prevention

An undefined-name test over the builder modules in the suite.
