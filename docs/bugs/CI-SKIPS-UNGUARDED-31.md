# CI-SKIPS-UNGUARDED-31: Hosted CI does not fail on skipped tests; JavaScript test coverage unpinned

## Status: 8 October 2026

Open. The local gate now fails on unexpected skips and runs the JavaScript tests (Node 24).

## Symptom

No CI job fails on skips. The JavaScript inspector test relies on whatever Node the hosted
runner happens to have, and is always skipped in the builder-image job.

## Where

`.github/workflows/source-check.yml`.

## How it happened

Skips were treated as harmless.

## Why it was not caught

Skip lists are not compared with an expected list.

## Reproduction

Read the CI logs for skipped tests.

## Repair

Not yet: pin Node in CI, add an expected-skip list, fail on others.

## Verification

Pending.

## Prevention

Same expected-skip list as the local gate.
