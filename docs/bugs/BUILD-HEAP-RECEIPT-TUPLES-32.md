# BUILD-HEAP-RECEIPT-TUPLES-32: The image step refuses its own final heap receipt (tuples against lists)

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (2ca08b5), not shipped at the time of writing. Found by the
v0.0.32-dev2 image build.

## Symptom

The dev2 image step stopped at the very end, after about 20 minutes, with "Saved final heap
receipt differs from the supplied audit".

## Where

`tools/build_aga.py` (`audit_world_map_heap_with_receipt`, `bind_heap_report`),
`tools/compact_harvest_heap.py`.

## How it happened

Since the harvest builder step (BUILD-HARVEST-NOT-BUILT-32), the heap audit's
`harvest_external_profile.fingerprint_entries` held Python tuples (made by
`compact_harvest_heap`). Saved as JSON they come back as lists. `bind_heap_report` compares the
audit held in memory with the saved receipt, so every tuple counted as a difference and the
binding refused. dev1 had no harvest catalogues, so the list was empty and nothing tripped.

## Why it was not caught

The harvest tests used synthetic data and never ran the final heap binding with a non-empty
harvest profile.

## Reproduction

On the real dev2 maps: 389 differences between the in-memory audit and the saved receipt, all
tuple against list.

## Repair

In source (2ca08b5): `audit_world_map_heap_with_receipt` returns exactly the saved JSON, and the
fingerprint entries are built as lists.

## Verification

`tests/test_heap_receipt_roundtrip.py` (`test_returned_audit_equals_saved_receipt_with_tuples`,
`test_compact_harvest_fingerprint_entries_are_lists`). A finished dev2 image is pending.

## Prevention

The round-trip test; the finalize stages bind to the saved receipts, not to in-memory objects.
