# CI-ERICW-SKIP-31: Torch test room test never runs in hosted CI or the builder image

## Status: 8 October 2026

Open. Found while itemising gate skips.

## Symptom

The enclosed torch test room test skips unless ERICW_BIN is set; hosted CI and the public
builder image never set it, although the tools are installed there.

## Where

`.github/workflows/source-check.yml`, `tools/build_docker.py` (image environment),
`tests/test_torchtest_room.py`.

## How it happened

The local gate sets ERICW_BIN itself, so the test ran locally only.

## Why it was not caught

Skips do not fail CI.

## Reproduction

Run the suite in the builder image without ERICW_BIN.

## Repair

Not yet: set ERICW_BIN in the builder image and CI.

## Verification

Pending.

## Prevention

CI fails on unexpected skips ([CI-SKIPS-UNGUARDED-31](CI-SKIPS-UNGUARDED-31.md)).
