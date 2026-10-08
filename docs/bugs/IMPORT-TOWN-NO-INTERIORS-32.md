# IMPORT-TOWN-NO-INTERIORS-32: The town importer converts no interiors; all Vivec Arena doors say "Interior unavailable"

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt).

## Symptom

`tools/import_town.py` has no interior step, so all 26 Arena doors have no target and the
engine shows "Interior unavailable".

## Where

`tools/import_town.py`.

## How it happened

The generic importer was built for exteriors first.

## Why it was not caught

First town with doors through the importer.

## Reproduction

Build with `--extra-town vivec_arena` and use any Arena door.

## Repair

Not yet: an interior step in the importer using the interior converter, linking door targets.

## Verification

Pending.

## Prevention

Importer test with a synthetic interior behind a door.
