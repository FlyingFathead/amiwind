# CI-BOOTSTRAP-NUMPY-32: The public CI tool bootstrap fails: tools/build.py imports numpy before the tools exist

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (6cb4fc4), not shipped at the time of writing.

## Symptom

GitHub CI on main 5e97310 (v0.0.32-pre) failed in two jobs: `source-and-dry-run` at "Bootstrap all
public tools into an empty directory" and `docker-builder` at "Build tools-only image and validate
the Linux container builder". `python tools/build.py --autoinstall --install-dependencies` stopped
with `ModuleNotFoundError: No module named 'numpy'` before it could install anything.

## Where

`tools/scenery_reduce.py` imported numpy at module level; `tools/build.py` imports its option
helpers while it builds the command-line parser.

## How it happened

The scenery reduction options were added to the builder's command line. The helper module also
holds the numpy mesh code, so importing the options pulled in numpy on the system Python.

## Why it was not caught

The local gate runs every check inside the finished tools environment, where numpy is installed.
Nothing ran the builder on a bare Python before the push.

## Reproduction

On a Python without numpy: `python tools/build.py --help`.

## Repair

numpy is loaded on first use in `tools/scenery_reduce.py`; the option helpers need only the
standard library.

## Verification

`tests/test_build_bootstrap_imports.py` runs `tools/build.py --help` and
`tools/build.py --install-dependencies --plan` with every third-party module blocked (standard
library and the repository's own modules only). It fails on 5e97310 with the numpy import and
passes with the repair.

## Prevention

The same test is part of the full suite, so any third-party import reached before the tools
exist fails the gate.
