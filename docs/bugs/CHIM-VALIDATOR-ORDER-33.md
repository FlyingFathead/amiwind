# CHIM-VALIDATOR-ORDER-33: The CHIM validator's walk depended on Python's string hashing

## Status: 8 October 2026

Open: fixed on the CHIM branch (v0.0.33-chim-format, commit 028904d), not merged into the v0.0.32
development line.

## Symptom

The validator's crossing walk could report different reads, cache contents and read runs for the
same world between runs, because the cache order followed iteration over sets of paths.

## Where

`tools/chim/validate.py` (walk and ring reads).

## How it happened

Sets of paths iterate in an order that depends on Python's per-process string hashing
(`PYTHONHASHSEED`).

## Why it was not caught

Single runs looked plausible; no test ran the walk under different hash seeds.

## Reproduction

Run the walk with two different `PYTHONHASHSEED` values and compare the reports.

## Repair

On the CHIM branch (028904d): the walk orders paths explicitly, so its reads no longer depend on
string hashing.

## Verification

`tests/test_chim_format.py` `test_ring_reads_do_not_depend_on_string_hashing` runs the walk under
several hash seeds; it fails without the fix.

## Prevention

That test; builder rule: no output may depend on set or dictionary order of strings.
