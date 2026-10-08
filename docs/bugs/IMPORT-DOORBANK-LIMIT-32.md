# IMPORT-DOORBANK-LIMIT-32: Town importer did not check the engine's 128-row door bank limit

## Status: 8 October 2026

Fixed in source on the cantons branch: the importer now enforces the limit.

## Symptom

The exterior door bank had no check for the engine's 128-row limit, so extra rows would have
been silently dropped.

## Where

`tools/import_town.py` door bank.

## How it happened

Limit not mirrored in the tool.

## Why it was not caught

No town had that many doors.

## Reproduction

Import a town with more than 128 door rows.

## Repair

The importer refuses more than 128 rows (fixed on the cantons branch).

## Verification

Pending.

## Prevention

Importer test at the limit.
