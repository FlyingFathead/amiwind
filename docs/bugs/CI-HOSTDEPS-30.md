# CI-HOSTDEPS-30: host CI job failed on a NIF-reader dependency

## Status: 7 October 2026

Fixed in source after the first v0.0.30 push; ships in the v0.0.30 release
commit. The first push was not tagged or released.

## Symptom

The hosted CI job `host-launcher-parity` failed on Ubuntu 24.04 (Windows was
cancelled with it) for the first v0.0.30 push: `test_host_asset_formats`
stopped with `ModuleNotFoundError: No module named 'pyffi'`.

## Where

`tools/prepare_scenery.py`, `export_refs`. The game, the maps and the engine
are unaffected.

## How it happened

v0.0.30-dev5 added flame extraction (`model_flames`) to the scenery export.
It asked for the NIF reader (`pyffi`) for every exported model. The host test
feeds `export_refs` a synthetic model that is not a NIF, and the host CI job
installs only `numpy` and `Pillow`, so importing the reader failed.

## Why it was not caught

The local gates run the full suite in the complete tools environment, where
`pyffi` is installed. Nothing ran the host-parity tests with the hosted job's
reduced dependency set before pushing.

## Reproduction

A fresh Python 3.12 virtual environment with only `numpy` and `Pillow`:
`python -B -m unittest discover -s tests -p test_host_asset_formats.py` fails
with the same error before the repair.

## Repair

Flames are read only from real NIF data (files starting with
`NetImmerse File Format`); real conversions are unchanged and still require
the NIF reader. The four host-parity test files pass in the reduced
environment on Linux and natively on Windows.

## Verification

The four host-parity test files (`test_build_host.py`, `test_build_windows*.py`,
`test_setup_windows.py`, `test_host_asset_formats.py`) pass with only
`numpy` and `Pillow` installed, and in the full Linux suite.

## Prevention

Every handoff now also runs the hosted CI job's host-parity tests in a fresh
environment with only that job's dependencies, on Linux and on Windows, before
the transfer kit is built.
